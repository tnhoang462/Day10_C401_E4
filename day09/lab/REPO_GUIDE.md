# Day09 Repo Guide

## 1. Repo này dùng để làm gì?

`day09/lab` là bài lab refactor hệ thống hỏi đáp nội bộ từ mô hình **single-agent RAG** của Day 08 sang kiến trúc **Supervisor + Workers + MCP + Trace**.

Mục tiêu chính:

- tách trách nhiệm giữa `supervisor`, `retrieval`, `policy/tool`, `synthesis`
- ghi trace rõ ràng để debug được từng bước
- mô phỏng kết nối capability bên ngoài qua `mcp_server.py`
- chạy evaluation trên bộ câu hỏi test và grading

Nói ngắn gọn: Day 08 tập trung vào `retrieve + answer`, còn Day 09 thêm lớp `orchestration`.

---

## 2. Cấu trúc thư mục quan trọng

```text
day09/lab/
├── graph.py
├── mcp_server.py
├── eval_trace.py
├── requirements.txt
├── .env.example
├── SCORING.md
├── README.md
├── REPO_GUIDE.md
├── workers/
│   ├── retrieval.py
│   ├── policy_tool.py
│   └── synthesis.py
├── contracts/
│   └── worker_contracts.yaml
├── data/
│   ├── test_questions.json
│   └── docs/
│       ├── access_control_sop.txt
│       ├── hr_leave_policy.txt
│       ├── it_helpdesk_faq.txt
│       ├── policy_refund_v4.txt
│       └── sla_p1_2026.txt
├── docs/
│   ├── system_architecture.md
│   ├── routing_decisions.md
│   └── single_vs_multi_comparison.md
└── reports/
    ├── group_report.md
    └── individual/
        └── template.md
```

### Vai trò từng file chính

- `graph.py`: entry point orchestration, tạo `AgentState`, route task, gọi worker, lưu trace.
- `workers/retrieval.py`: dense retrieval qua ChromaDB.
- `workers/policy_tool.py`: kiểm tra policy, detect exception, gọi mock MCP tools nếu cần.
- `workers/synthesis.py`: tổng hợp câu trả lời grounded bằng LLM.
- `mcp_server.py`: mock MCP server, expose tool schemas và dispatch tool calls.
- `eval_trace.py`: chạy batch test, sinh trace, phân tích metrics, tạo báo cáo so sánh Day 08 vs Day 09.
- `contracts/worker_contracts.yaml`: contract input/output chuẩn cho supervisor, workers và MCP server.
- `data/docs/*.txt`: knowledge base nội bộ dùng để retrieve.
- `data/test_questions.json`: bộ 15 câu hỏi để test single-hop, multi-hop, abstain và temporal scoping.
- `docs/*.md`: template tài liệu nhóm cần điền.
- `SCORING.md`: rubric chấm điểm, format trace bắt buộc, deadline nộp bài.

---

## 3. Kiến trúc tổng thể

Luồng thiết kế của lab:

```text
User Question
   |
   v
Supervisor (graph.py)
   |
   +--> retrieval_worker
   |
   +--> policy_tool_worker
   |
   +--> human_review
          |
          v
     retrieval_worker
          |
          v
   synthesis_worker
          |
          v
      Final Answer + Trace
```

### Shared state

`graph.py` định nghĩa `AgentState` là state đi xuyên suốt toàn pipeline. Các field quan trọng:

- `task`: câu hỏi đầu vào
- `supervisor_route`: worker mà supervisor chọn
- `route_reason`: lý do route
- `risk_high`: có cờ rủi ro hay không
- `needs_tool`: có cần MCP/tool call hay không
- `hitl_triggered`: có kích hoạt human review hay không
- `retrieved_chunks`, `retrieved_sources`: evidence từ retrieval
- `policy_result`: kết quả policy analysis
- `mcp_tools_used`: log các tool đã gọi
- `final_answer`, `sources`, `confidence`: output cuối
- `history`, `workers_called`: trace từng bước
- `latency_ms`, `run_id`: metadata cho observability

---

## 4. Luồng hoạt động của từng thành phần

### 4.1 `graph.py`

Đây là file điều phối chính.

Nó làm 4 việc:

1. tạo state ban đầu bằng `make_initial_state(task)`
2. gọi `supervisor_node(state)` để chọn route
3. gọi worker phù hợp theo `route_decision(state)`
4. luôn kết thúc bằng `synthesis_worker_node(state)`

### Routing logic hiện tại

Supervisor đang dùng keyword-based routing:

- chứa các từ như `hoàn tiền`, `refund`, `flash sale`, `license`, `cấp quyền`, `access`, `level 3`  
  → `policy_tool_worker`
- chứa các từ như `emergency`, `khẩn cấp`, `2am`, `không rõ`, `err-`  
  → bật `risk_high = True`
- nếu `risk_high` và task có `err-`  
  → `human_review`
- còn lại  
  → `retrieval_worker`

### Điểm cần lưu ý

`graph.py` hiện là **scaffold chạy được**, nhưng các wrapper worker bên trong vẫn đang dùng **placeholder output**, chưa import trực tiếp `workers/*.py`.

Cụ thể:

- `retrieval_worker_node()` trả về chunk mẫu về SLA P1
- `policy_tool_worker_node()` trả về `policy_result` mẫu
- `synthesis_worker_node()` trả về câu trả lời placeholder

Điều này nghĩa là:

- repo thể hiện rất rõ kiến trúc supervisor-worker
- nhưng để đạt trạng thái lab hoàn chỉnh, bạn cần nối các wrapper này với:
  - `workers.retrieval.run`
  - `workers.policy_tool.run`
  - `workers.synthesis.run`

---

## 5. Chi tiết từng worker

### 5.1 `workers/retrieval.py`

Worker này chịu trách nhiệm tìm evidence.

Luồng xử lý:

1. lấy embedding function bằng `_get_embedding_fn()`
2. ưu tiên dùng `sentence-transformers`
3. nếu không có thì thử OpenAI embeddings
4. nếu vẫn không có thì fallback sang random embedding để test
5. query ChromaDB collection `day09_docs`
6. trả về `retrieved_chunks` và `retrieved_sources`

Output chunk có format:

```python
{
  "text": "...",
  "source": "sla_p1_2026.txt",
  "score": 0.92,
  "metadata": {...}
}
```

Worker cũng append `worker_io_logs` vào state để trace được input/output.

### 5.2 `workers/policy_tool.py`

Worker này xử lý các câu hỏi policy hoặc tool-related.

Hai phần chính:

- `analyze_policy(task, chunks)`: rule-based policy analysis
- `_call_mcp_tool(tool_name, tool_input)`: mock MCP client gọi `dispatch_tool()` từ `mcp_server.py`

Các exception hiện đã được detect:

- `flash_sale_exception`
- `digital_product_exception`
- `activated_exception`

Worker còn có logic temporal scoping:

- nếu task chứa tín hiệu như `31/01`, `30/01`, `trước 01/02`
- nó thêm `policy_version_note` rằng đơn hàng trước `01/02/2026` có thể thuộc policy v3, trong khi repo hiện chỉ có v4

Nếu `needs_tool=True` và chưa có chunks, worker sẽ gọi MCP tool:

- `search_kb`

Nếu task liên quan ticket/P1/Jira, worker có thể gọi thêm:

- `get_ticket_info`

### 5.3 `workers/synthesis.py`

Worker này tổng hợp answer cuối.

Luồng xử lý:

1. build context từ `retrieved_chunks` và `policy_result`
2. tạo grounded prompt với quy tắc:
   - chỉ dùng context được cung cấp
   - không đủ thông tin thì phải abstain
   - có citation nguồn
3. gọi LLM qua `_call_llm()`
4. tính `confidence` bằng heuristic

LLM provider hỗ trợ:

- OpenAI qua `OPENAI_API_KEY`
- Gemini qua `GOOGLE_API_KEY`

Nếu không gọi được LLM, worker trả về:

```text
[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env.
```

Confidence được ước tính từ:

- số chunk và score chunk
- answer có phải abstain không
- số exception policy phát hiện được

---

## 6. `mcp_server.py` đang mô phỏng gì?

File này đóng vai trò mock MCP server trong cùng process.

### Tool schemas được expose

- `search_kb(query, top_k)`
- `get_ticket_info(ticket_id)`
- `check_access_permission(access_level, requester_role, is_emergency)`
- `create_ticket(priority, title, description)`

### Ý nghĩa

- `list_tools()` mô phỏng bước discovery kiểu MCP
- `dispatch_tool()` mô phỏng bước tool execution
- worker không cần hard-code logic từng external capability trong cùng file

### Dữ liệu mock quan trọng

`get_ticket_info("P1-LATEST")` trả về ticket mẫu có:

- `created_at = 2026-04-13T22:47:00`
- `sla_deadline = 2026-04-14T02:47:00`
- `notifications_sent = ["slack:#incident-p1", "email:incident@company.internal", "pagerduty:oncall"]`

`check_access_permission()` có rules:

- Level 1: 1 approver
- Level 2: có emergency bypass
- Level 3: không có emergency bypass

Đây là nền tảng để test các câu multi-hop như cấp quyền khẩn cấp khi đang có P1.

---

## 7. Dataset và loại câu hỏi

Knowledge base của Day09 có 5 tài liệu:

- `sla_p1_2026.txt`
- `policy_refund_v4.txt`
- `access_control_sop.txt`
- `it_helpdesk_faq.txt`
- `hr_leave_policy.txt`

`data/test_questions.json` chứa 15 câu, trải trên nhiều dạng:

- retrieval đơn giản
- policy exception
- temporal scoping
- abstain
- multi-detail
- multi-hop cross-document
- multi-worker multi-doc

Một vài case quan trọng:

- `q09`: hỏi về `ERR-403-AUTH`, kỳ vọng hệ thống abstain
- `q12`: đơn trước `01/02/2026`, kiểm tra temporal policy scoping
- `q13`: contractor cần Level 3 trong P1, kiểm tra logic access + incident
- `q15`: case khó nhất, yêu cầu vừa SLA notification vừa Level 2 emergency access

---

## 8. Contract giữa supervisor và workers

Repo này dùng `contracts/worker_contracts.yaml` làm chuẩn I/O.

Ý nghĩa thực tế:

- supervisor chỉ quyết định luồng, không tự trả lời domain knowledge
- retrieval phải trả về chunk thật hoặc list rỗng, không được bịa
- policy worker phải ghi rõ `mcp_tools_used`
- synthesis phải abstain nếu không đủ evidence

Nếu bạn mở rộng repo, nên sửa contract trước hoặc cùng lúc với code để tránh state drift.

---

## 9. Setup môi trường

Chạy trong thư mục `day09/lab`.

### 9.1 Cài thư viện

```bash
pip install -r requirements.txt
```

Các dependency chính:

- `chromadb`
- `sentence-transformers`
- `openai`
- `pyyaml`
- `pytest`

### 9.2 Tạo `.env`

Repo có sẵn `.env.example`.

```bash
cp .env.example .env
```

Biến môi trường đáng chú ý:

- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `CHROMA_DB_PATH=./chroma_db`
- `CHROMA_COLLECTION=day09_docs`
- `RETRIEVAL_TOP_K=3`
- `TRACE_OUTPUT_DIR=./artifacts/traces`

### 9.3 Build hoặc chuẩn bị ChromaDB

`workers/retrieval.py` đang query collection `day09_docs` từ `./chroma_db`.

README hiện gợi ý build index bằng script Python đọc `data/docs/`. Nếu chưa có index:

- tạo collection `day09_docs`
- add documents từ 5 file trong `data/docs/`
- metadata nên chứa ít nhất `source`

Nếu không build index trước:

- retrieval có thể trả list rỗng
- `search_kb` trong MCP sẽ fallback về mock response

---

## 10. Cách chạy repo

### Chạy orchestrator thủ công

```bash
python graph.py
```

Lệnh này sẽ chạy 3 query mẫu:

- SLA ticket P1
- refund cho Flash Sale
- cấp quyền Level 3 cho P1 khẩn cấp

Sau mỗi query, `graph.py` sẽ:

- in route
- in reason
- in workers_called
- in answer
- lưu trace JSON vào `./artifacts/traces/`

### Test từng worker riêng lẻ

```bash
python workers/retrieval.py
python workers/policy_tool.py
python workers/synthesis.py
```

### Test mock MCP server

```bash
python mcp_server.py
```

File này sẽ demo:

- tool discovery
- `search_kb`
- `get_ticket_info`
- `check_access_permission`
- invalid tool handling

### Chạy evaluation

```bash
python eval_trace.py
python eval_trace.py --analyze
python eval_trace.py --compare
python eval_trace.py --grading
```

Ý nghĩa:

- mặc định: chạy `data/test_questions.json`, lưu trace, in metrics, sinh `artifacts/eval_report.json`
- `--analyze`: chỉ đọc trace có sẵn và tính metrics
- `--compare`: tạo report so sánh Day 08 và Day 09
- `--grading`: chạy `grading_questions.json` nếu file đã được public

---

## 11. Output được sinh ra ở đâu?

Repo hiện chưa có thư mục `artifacts/` sẵn trong cây thư mục. Thư mục này sẽ được tạo khi chạy pipeline.

Các output chính:

- `artifacts/traces/*.json`: trace từng câu hỏi hoặc từng lần chạy graph
- `artifacts/grading_run.jsonl`: log chấm điểm
- `artifacts/eval_report.json`: báo cáo tổng hợp sau compare

Trace state điển hình sẽ chứa:

- câu hỏi đầu vào
- route của supervisor
- lý do route
- workers đã gọi
- sources retrieve được
- answer cuối
- confidence
- latency
- log MCP tools

---

## 12. Metrics trong `eval_trace.py`

Script phân tích trace đang tính:

- `routing_distribution`
- `avg_confidence`
- `avg_latency_ms`
- `mcp_usage_rate`
- `hitl_rate`
- `top_sources`

Phần compare Day 08 vs Day 09 hiện mới là khung:

- Day 09 lấy số liệu thật từ trace
- Day 08 vẫn đang để placeholder hoặc đọc từ file baseline nếu bạn cung cấp

Tức là `compare_single_vs_multi()` đã có format đúng, nhưng cần bổ sung baseline thực tế để tài liệu so sánh hoàn chỉnh.

---

## 13. Tài liệu và rubric cần nộp

Các file phục vụ nộp bài:

- `docs/system_architecture.md`
- `docs/routing_decisions.md`
- `docs/single_vs_multi_comparison.md`
- `reports/group_report.md`
- `reports/individual/template.md`
- `SCORING.md`

`SCORING.md` là file rất quan trọng vì nó quy định:

- deadline code: `18:00`
- format `artifacts/grading_run.jsonl`
- các tiêu chí mất điểm vì hallucination hoặc thiếu trace fields
- rubric điểm nhóm và cá nhân

Nếu dùng repo này để nộp bài, cần đọc `SCORING.md` trước khi hoàn thiện code.

---

## 14. Trạng thái implementation hiện tại

Đây là phần quan trọng nhất khi đọc repo.

### Những gì đã có

- cấu trúc supervisor-worker rõ ràng
- `AgentState` khá đầy đủ
- retrieval worker có query ChromaDB thật
- policy worker có rule-based analysis và MCP mock call
- synthesis worker có grounded prompt và hỗ trợ OpenAI/Gemini
- mock MCP server có 4 tools
- eval script có luồng test, analyze, compare, grading
- contracts, docs templates và scoring rubric đã đầy đủ

### Những gì còn TODO hoặc mới ở mức scaffold

- `graph.py` chưa nối thật vào `workers/*.py`
- routing logic vẫn chủ yếu dựa vào keyword đơn giản
- `human_review` mới là placeholder auto-approve
- compare Day 08 vs Day 09 chưa có baseline số liệu thật
- retrieval phụ thuộc vào ChromaDB index đã được tạo trước
- synthesis cần API key nếu muốn answer thật thay vì message lỗi

### Kết luận thực dụng

Repo này phù hợp cho 2 mục đích:

- học kiến trúc multi-agent orchestration
- làm lab scaffold để nhóm hoàn thiện tiếp

Nó chưa phải production-ready repo, nhưng đã đủ rõ để phát triển tiếp rất nhanh.

---

## 15. Cách hoàn thiện repo nếu muốn dùng để demo hoặc nộp bài

Thứ tự hợp lý:

1. build `day09_docs` trong ChromaDB từ `data/docs/`
2. nối `graph.py` với `workers.retrieval.run`, `workers.policy_tool.run`, `workers.synthesis.run`
3. kiểm tra `route_reason` cho từng nhóm câu hỏi trong `test_questions.json`
4. đảm bảo `synthesis` abstain đúng khi retrieval rỗng
5. chạy `python eval_trace.py`
6. điền 3 file trong `docs/`
7. chạy `--grading` khi có `grading_questions.json`

---

## 16. Tóm tắt nhanh

Nếu chỉ cần hiểu repo trong 1 phút:

- `graph.py` là supervisor orchestrator
- `workers/` là 3 worker chuyên trách
- `mcp_server.py` là mock external capability layer
- `eval_trace.py` là batch runner + analyzer
- `contracts/worker_contracts.yaml` là ranh giới I/O chuẩn
- `data/docs/` là knowledge base
- `data/test_questions.json` là bộ test chính
- repo đã có kiến trúc đúng, nhưng `graph.py` vẫn cần nối worker thật để hoàn chỉnh lab
