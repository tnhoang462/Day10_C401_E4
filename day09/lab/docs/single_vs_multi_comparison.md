# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401_E4  
**Ngày:** 2026-04-14

> **Nguồn số liệu thực tế:**  
> - Day 08: `eval_report.json` → `day08_single_agent` baseline (10 câu, từ `eval_trace.py --compare`)  
> - Day 09: `eval_report.json` → `day09_multi_agent` (21 traces tổng)

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.568 | 0.716 | **+0.148 (+26%)** | Day 09 cao hơn nhờ grounding tốt hơn + citation bonus |
| Avg latency (ms) | 10,552 | 9,715 | **−837 ms (−8%)** | Day 09 nhanh hơn nhờ không phải re-prompt toàn pipeline |
| Abstain rate (%) | 10% (1/10 câu) | ~5% (1/21 câu thực sự abstain) | −5% | Day 09 abstain ít hơn nhờ MCP bổ sung context |
| Multi-hop accuracy | 0% (0/10) | ~50% (câu đơn giản ok, đa chiều còn sai) | N/A | Day 09 tốt hơn cho single-domain multi-hop |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | ~15 phút | ~3 phút | −12 phút | Nhờ trace có history + route_reason + worker_io_logs |
| MCP tool usage | N/A | 52% câu có MCP call | N/A | 11/21 câu gọi ít nhất 1 MCP tool |

> **Lưu ý:** Day 08 baseline lấy từ field `day08_single_agent` trong `artifacts/eval_report.json`, được commit bởi thành viên nhóm (commit `de9a056 feat: Update evalutate of day08 baseline`).

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | ~70% | ~90% |
| Latency | ~10,552 ms | ~8,500 ms |
| Observation | Trả lời dựa trên prompt lớn toàn pipeline | Retrieval → Synthesis tách bạch rõ, ít noise hơn |

**Kết luận:** Multi-agent cải thiện rõ cho câu đơn giản. Lý do: synthesis worker chỉ nhận context đã lọc từ retrieval (top-3 chunks), không bị "distract" bởi toàn bộ knowledge base như single agent. Ví dụ gq05 (SLA P1 escalation) đạt confidence 0.91.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | 0% (không có trace routing rõ) | ~60–70% cho 2-domain, ~40% cho 3-domain |
| Routing visible? | ✗ | ✓ |
| Observation | Không biết retrieval fail ở bước nào | Trace cho thấy supervisor route sai với câu đa domain |

**Kết luận:** Multi-agent tốt hơn cho multi-hop trong cùng một domain (ví dụ: câu gq06 về probation+remote đạt 0.90 vì cả hai topik đều nằm trong HR docs). Nhưng với câu cross-domain như gq09 (SLA P1 + access permission), kiến trúc single-path routing vẫn còn giới hạn.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | 10% (1/10) | ~5% (1/21) |
| Hallucination cases | Không đo được (không có route trace) | Thấp — synthesis có instruction "KHÔNG dùng kiến thức ngoài" |
| Observation | Khi không tìm thấy, single agent có thể hallucinate | Synthesis worker có explicit abstain check → confidence 0.2 nếu "không tìm thấy" |

**Kết luận:** Day 09 abstain đúng hơn. Ví dụ gq07 (mức phạt vi phạm SLA — không có trong KB): synthesis trả lời "tài liệu không cung cấp thông tin cụ thể" với confidence 0.84 (cao vì vẫn cite SLA docs liên quan). Day 08 có thể đã bịa mức phạt.

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: ~15 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace JSON → xem supervisor_route + route_reason
  → Nếu route sai → sửa keyword list trong supervisor_node()
  → Nếu retrieval sai → test retrieval_worker độc lập (python workers/retrieval.py)
  → Nếu synthesis sai → test synthesis_worker độc lập (python workers/synthesis.py)
Thời gian ước tính: ~3 phút
```

**Câu cụ thể nhóm đã debug:** gq08 — "Nhân viên phải đổi mật khẩu sau bao nhiêu ngày?"  
Pipeline trả về câu trả lời chung chung với confidence 0.65. Đọc trace thấy ngay: `route_reason = "no specific signal → default retrieval"` và `sources = ["hr_leave_policy.txt", "policy_refund_v4.txt"]` — hai file không liên quan. Kết luận ngay: KB chưa có file IT security policy, không phải lỗi code. Debug xong trong ~2 phút.

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

**Nhận xét:**

Trong lab, nhóm đã thêm tool `create_ticket` và `check_access_permission` vào MCP server mà không cần sửa graph.py hay bất kỳ worker nào khác — chỉ thêm vào `TOOL_SCHEMAS` và `TOOL_REGISTRY` trong `mcp_server.py`. Tương tự, thay đổi embedding model trong `retrieval.py` (từ OpenAI sang Sentence Transformers) không ảnh hưởng gì đến supervisor hay synthesis. Đây là lợi thế rõ nhất của kiến trúc modular.

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query (retrieval only) | 1 LLM call | 2 LLM calls (retrieval embed + synthesis via OpenAI gpt-4o-mini / Gemini) |
| Complex query (policy + retrieval) | 1 LLM call | 3 LLM calls (embed + NVIDIA gpt-oss-120b for Reasoning + synthesis) |
| MCP tool call | N/A | 1–2 MCP calls (search_kb, get_ticket_info qua fallback an toàn) |

> _Lưu ý: embedding call là local (SentenceTransformer). LLM Policy call là NVIDIA gpt-oss-120b. Synthesis là GPT/Gemini._

**Nhận xét về cost-benefit:**

Day 09 tốn API calls cho nhiều mô hình khác biệt so với Day 08 nhưng latency thực tế lại **thấp hơn** do: (1) chuyên biệt hóa mô hình — `gpt-oss-120b` (NVIDIA) dùng chuyên để suy luận (Reasoning) exception, còn `gpt-4o-mini`/Gemini chuyên dùng để format text cuối (Synthesis) thay vì đẩy cục bự vào 1 prompt duy nhất; (2) `try-except` fallback an toàn gánh bớt request chết. Confidence tăng 26% là trade-off cực kỳ xứng đáng cho sự linh hoạt và Explainable AI (xem được luồng tư duy Reasoning).

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. **Debuggability**: Trace với `route_reason`, `history`, `worker_io_logs` giúp tìm bug trong ~3 phút thay vì ~15 phút. Với production system, đây là yếu tố quan trọng nhất.
2. **Accuracy & Confidence**: Confidence tăng 26% (0.568 → 0.716) nhờ context focused và grounding tốt hơn. Abstain rate giảm và ít hallucination hơn nhờ synthesis instruction rõ ràng.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. **Multi-domain multi-hop**: Kiến trúc single-path routing không xử lý tốt câu hỏi cần đồng thời 2 domain khác nhau (ví dụ: SLA + access control). Single agent với prompt đủ tốt có thể trả lời tốt hơn cho loại câu này.

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi task đơn giản, không cần routing (chỉ có 1 loại query), hoặc khi latency là yếu tố tối thượng và không thể chấp nhận overhead của nhiều LLM calls. Ví dụ: chatbot đơn giản tra cứu FAQ — single agent với RAG đã đủ.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Thay keyword-based routing bằng **LLM classifier** tại supervisor node (gọi LLM với tool definitions để quyết định route) và cho phép **parallel worker invocation** (gọi song song retrieval + policy tool với multi-hop query). Điều này giải quyết trực tiếp 2 giới hạn lớn nhất quan sát được trong lab.
