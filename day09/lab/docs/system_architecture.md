# System Architecture — Lab Day 09

**Nhóm:** C401_E4  
**Ngày:** 2026-04-14  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**

Supervisor-Worker cho phép phân tách rõ ràng trách nhiệm: supervisor chỉ quyết định routing, còn mỗi worker chuyên xử lý một loại task cụ thể (retrieval, policy check, synthesis). Điều này giúp dễ debug (test từng worker độc lập), dễ mở rộng (thêm worker mới không ảnh hưởng phần còn lại), và có trace rõ ràng để audit từng bước ra quyết định.

---

## 2. Sơ đồ Pipeline

> Vẽ sơ đồ pipeline dưới dạng text, Mermaid diagram, hoặc ASCII art.
> Yêu cầu tối thiểu: thể hiện rõ luồng từ input → supervisor → workers → output.

**Sơ đồ thực tế của nhóm:**

```
User Request (task: str)
        │
        ▼
┌─────────────────────────┐
│      Supervisor Node    │  ← keyword matching trên task
│  (graph.py)             │    sets: supervisor_route, route_reason,
│                         │          risk_high, needs_tool
└──────────┬──────────────┘
           │
       [route_decision]
           │
   ┌───────┴──────────────────────┬──────────────────┐
   │                              │                  │
   ▼                              ▼                  ▼
Retrieval Worker          Policy Tool Worker    Human Review
(workers/retrieval.py)   (workers/policy_tool  (human_review_node)
  Dense retrieval          .py) → NVIDIA LLM:     HITL placeholder
  via ChromaDB             gpt-oss-120b (Reasoning)→ auto-approve
  (all-MiniLM-L6-v2)      → MCP tools:           → re-routes to
  top_k = 3               search_kb,                retrieval_worker
  → retrieved_chunks       get_ticket_info,       
  → retrieved_sources     check_access_permission
        │                 → policy_result
        └───────────┬─────────────┘
                    │
                    ▼
           Synthesis Worker
          (workers/synthesis.py)
           LLM: gpt-4o-mini / gemini-1.5-flash
           temperature: 0.1
           builds context from
           chunks + policy_result
           → final_answer (với citation [1],[2]…)
           → confidence (0.0–0.95)
           → sources
                    │
                    ▼
             AgentState Output
         (saved to artifacts/traces/)
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích task, quyết định routing sang worker phù hợp, đánh dấu risk_high và needs_tool |
| **Input** | `task` (câu hỏi từ user) |
| **Output** | supervisor_route, route_reason, risk_high, needs_tool |
| **Routing logic** | Keyword matching: policy_keywords → `policy_tool_worker`; retrieval_keywords → `retrieval_worker`; "err-" không rõ context → `human_review`; default → `retrieval_worker` |
| **HITL condition** | Khi task chứa mã lỗi dạng "err-" mà không có keyword policy hay retrieval đi kèm |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Dense semantic retrieval từ ChromaDB, trả về top-k chunks có score cao nhất |
| **Embedding model** | `sentence-transformers/all-MiniLM-L6-v2` (offline, fallback: OpenAI `text-embedding-3-small`) |
| **Top-k** | 3 (DEFAULT_TOP_K, có thể override qua state `retrieval_top_k`) |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Xử lý câu hỏi liên quan đến policy/access control; hỗ trợ **Reasoning** thông qua NVIDIA API trước khi kết luận |
| **LLM model** | `openai/gpt-oss-120b` (qua NVIDIA API) với cơ chế parse `reasoning_content` để Explainable AI |
| **MCP tools gọi** | `search_kb` (semantic search KB), `get_ticket_info` (tra cứu ticket Jira), `check_access_permission` |
| **Exception cases xử lý** | Rule-Based Exception Filter (phát hiện nhanh vi phạm như Flash Sale, Đã kích hoạt...); Fallback an toàn nếu MCP lỗi |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` (OpenAI), hoặc `gemini-1.5-flash` (Google) linh hoạt theo cấu hình `.env` |
| **Temperature** | 0.1 (low — grounded, tránh hallucination) |
| **Grounding strategy** | Chỉ dùng `retrieved_chunks` + `policy_result` làm context; KHÔNG dùng kiến thức ngoài; citation [1],[2],... bắt buộc |
| **Abstain condition** | Nếu answer chứa "không tìm thấy" / "không có thông tin" → confidence 0.2; nếu không có chunks lẫn policy → confidence 0.1 |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources, total_found |
| get_ticket_info | ticket_id | ticket details (priority, status, assignee, sla_deadline, ...) |
| check_access_permission | access_level, requester_role, is_emergency | can_grant, required_approvers, emergency_override, notes |
| create_ticket | priority, title, description | ticket_id, url, created_at (MOCK) |

---

## 4. Shared State Schema

> Liệt kê các fields trong AgentState và ý nghĩa của từng field.

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------| 
| task | str | Câu hỏi đầu vào | supervisor đọc |
| supervisor_route | str | Worker được chọn (`retrieval_worker` / `policy_tool_worker` / `human_review`) | supervisor ghi |
| route_reason | str | Lý do route (keyword nào matched, risk signals nào) | supervisor ghi |
| risk_high | bool | True nếu task chứa risk keywords (khẩn cấp, 2am, err-…) | supervisor ghi |
| needs_tool | bool | True nếu route sang policy_tool_worker (cần MCP calls) | supervisor ghi |
| hitl_triggered | bool | True nếu human_review_node đã được gọi | human_review ghi |
| retrieved_chunks | list | Evidence chunks từ ChromaDB `{text, source, score, metadata}` | retrieval/policy_tool ghi, synthesis đọc |
| retrieved_sources | list | Danh sách file nguồn (deduplicated) | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả kiểm tra policy `{policy_applies, exceptions_found, source, …}` | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Log các MCP tool calls `{tool, input, output, timestamp}` | policy_tool ghi |
| final_answer | str | Câu trả lời cuối với citation | synthesis ghi |
| sources | list | Sources được cite trong final_answer | synthesis ghi |
| confidence | float | Mức tin cậy 0.0–0.95 (dựa vào avg chunk score + citation bonus) | synthesis ghi |
| history | list | Chuỗi log steps đã qua (dùng để debug) | mọi node ghi |
| workers_called | list | Thứ tự các worker đã được gọi | mọi worker ghi |
| worker_io_logs | list | Structured input/output log của từng worker | mọi worker ghi |
| latency_ms | int | Tổng thời gian xử lý tính bằng ms | graph ghi khi kết thúc |
| run_id | str | ID định danh run (`run_YYYYMMDD_HHMMSS`) | make_initial_state ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó — không rõ lỗi ở đâu | Dễ hơn — test từng worker độc lập |
| Thêm capability mới | Phải sửa toàn prompt | Thêm worker/MCP tool riêng |
| Routing visibility | Không có | Có route_reason trong trace |
| Truy vết tool calls | Không có | `mcp_tools_used` log đầy đủ input/output/timestamp |
| Confidence trung bình | 0.568 (Day 08 actual) | 0.716 (Day 09 actual, +26%) |
| Latency | ~10,552 ms | ~9,715 ms (−8%) |

**Nhóm điền thêm quan sát từ thực tế lab:**

Trong thực tế, khi pipeline trả lời sai (ví dụ gq08 — câu hỏi về mật khẩu), nhờ có `route_reason` và `history` trong trace ta biết ngay supervisor đã route sang `retrieval_worker` với lý do "no specific signal → default retrieval" — cho thấy nguyên nhân là knowledge base chưa có file IT security policy, chứ không phải lỗi code. Nếu dùng single agent, phải đọc toàn bộ pipeline mới suy luận được điều này.

---

## 6. Giới hạn và điểm cần cải tiến

> Nhóm mô tả những điểm hạn chế của kiến trúc hiện tại.

1. **Routing dùng keyword matching đơn giản**: Supervisor hiện dùng hard-coded keyword list thay vì LLM classifier — dễ miss hoặc sai với câu hỏi phức tạp/đa nghĩa (ví dụ: câu về "access" trong văn cảnh HR vs IT sẽ đều route sang policy_tool_worker).
2. **HITL chưa implement thật**: `human_review_node` chỉ là placeholder — auto-approve rồi route về retrieval. Chưa có cơ chế thật sự pause graph để chờ human input.
3. **workers_called trùng lặp**: Mỗi worker wrapper append tên vào `workers_called` thêm một lần nữa dù worker đã tự append — dẫn đến duplicate entries trong trace (thấy rõ trong grading_run.jsonl: `["policy_tool_worker", "policy_tool_worker", "synthesis_worker", "synthesis_worker"]`).
