# Routing Decisions Log — Lab Day 09

**Nhóm:** C401_E4  
**Ngày:** 2026-04-14

> **Nguồn số liệu:** `artifacts/traces/` (21 traces) và `artifacts/grading_run.jsonl` (10 grading questions).  
> Mỗi entry được lấy trực tiếp từ field `supervisor_route`, `route_reason`, `workers_called`, `mcp_tools_used`, `confidence` trong trace JSON.

---

## Routing Decision #1

**Task đầu vào:**
> "Ticket P1 được tạo và on-call engineer không phản hồi sau 10 phút. Theo đúng SLA, hệ thống sẽ làm gì tiếp theo?" _(gq05)_

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `task contains retrieval keyword(s): p1, sla, ticket`  
**MCP tools được gọi:** Không có (retrieval_worker không gọi MCP)  
**Workers called sequence:** `retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "Hệ thống sẽ tự động escalate ticket lên Senior Engineer. Lead Engineer phân công engineer khác trong vòng 10 phút tiếp theo [2],[3]."
- confidence: 0.91
- Correct routing? **Yes**

**Nhận xét:** Đây là routing đơn giản và chính xác nhất trong lab. Task chứa đồng thời 3 retrieval keywords (`p1`, `sla`, `ticket`) → supervisor nhận diện ngay. Evidence được lấy từ `sla_p1_2026.txt` với score cao, synthesis cho confidence 0.91. Không cần MCP.

---

## Routing Decision #2

**Task đầu vào:**
> "Khách hàng mua sản phẩm trong chương trình Flash Sale, nhưng phát hiện sản phẩm bị lỗi từ nhà sản xuất và yêu cầu hoàn tiền trong vòng 5 ngày. Có được hoàn tiền không?" _(gq10)_

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy keyword(s): hoàn tiền, flash sale`  
**MCP tools được gọi:** `search_kb` (query: câu hỏi gốc, top_k=3)  
**Workers called sequence:** `policy_tool_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "Không được hoàn tiền. Sản phẩm Flash Sale không đủ điều kiện hoàn tiền dù bị lỗi nhà sản xuất [1],[2]."
- confidence: 0.90
- Correct routing? **Yes**

**Nhận xét:** Routing đúng — câu hỏi cần tra policy refund nên phải qua policy_tool_worker với MCP search_kb. Điểm hay là policy_tool_worker dùng luồng tư duy AI với `gpt-oss-120b` (thể hiện qua reasoning_content) nhằm phát hiện Exception vi phạm quy tắc Flash Sale, kết hợp lọc Rule-Based ban đầu. Kết quả synthesis trả lời dứt khoát với confidence cao (0.90) dù question có vẻ muốn tìm ngoại lệ.

---

## Routing Decision #3

**Task đầu vào:**
> "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?" _(run_20260414_164604)_

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task chứa từ khóa policy/access: ['cấp quyền', 'level 3'] → MCP tool sẽ được gọi | risk_high do: ['khẩn cấp']`  
**MCP tools được gọi:** `search_kb` (top_k=3) + `get_ticket_info` (ticket_id="P1-LATEST")  
**Workers called sequence:** `policy_tool_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "On-call IT Admin cấp quyền tạm thời tối đa 24h sau khi Tech Lead phê duyệt bằng lời. Sau 24h phải có ticket chính thức [1]."
- confidence: 0.62
- Correct routing? **Yes**

**Nhận xét:** Đây là trường hợp routing đúng và thú vị nhất: supervisor nhận ra cả `risk_high=True` (do "khẩn cấp") lẫn `needs_tool=True` (do "cấp quyền", "level 3"). Hai MCP tools được gọi song song — `search_kb` lấy context SOP, `get_ticket_info` kiểm tra trạng thái P1 hiện tại (IT-9847, đã quá SLA 5 phút). Confidence 0.62 thấp hơn vì chunks từ `hr_leave_policy.txt` ít liên quan được kéo vào context.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> "Sự cố P1 xảy ra lúc 2am. Đồng thời cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Hãy nêu đầy đủ: (1) các bước SLA P1 notification phải làm ngay, và (2) điều kiện để cấp Level 2 emergency access." _(gq09)_

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `task contains policy keyword(s): access, emergency | risk signals: 2am`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

Câu hỏi này là **multi-hop AND multi-domain**: vừa hỏi về SLA P1 notification (→ nên vào `retrieval_worker`) vừa hỏi về access permission cho contractor trong emergency (→ nên vào `policy_tool_worker`). Supervisor chỉ có một route duy nhất → buộc phải chọn một. Supervisor chọn `policy_tool_worker` do keyword `access` và `emergency` nặng hơn. Kết quả: phần (1) về SLA notification được trả lời chung chung (sources rỗng), phần (2) về access được trả lời tốt hơn. Confidence 0.87 hơi cao so với chất lượng thực tế của (1). Đây là giới hạn của keyword-based single-path routing — cần multi-worker invocation hoặc LLM classifier để xử lý câu hỏi đa chiều.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 10 | 47% |
| policy_tool_worker | 11 | 52% |
| human_review | 1 (triggered) → auto re-route về retrieval | 4% |

> _Nguồn: `artifacts/eval_report.json` — 21 traces tổng_

### Routing Accuracy

> Trong số 21 câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: **20 / 21**
- Câu route sai (đã sửa bằng cách nào?): 1 câu (gq09 — multi-hop cần cả retrieval lẫn policy nhưng chỉ route được sang 1 worker; chưa sửa trong lab do giới hạn kiến trúc single-path)
- Câu trigger HITL: 1 (gq01 hoặc câu có mã lỗi dạng "err-" → auto-approved → tiếp tục retrieval)

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?

1. **Dùng keyword matching nhưng ưu tiên policy_keywords trước retrieval_keywords**: Nếu task chứa cả hai, supervisor chọn policy_tool_worker (vì cần MCP call). Điều này đúng trong hầu hết trường hợp nhưng bỏ sót khi task thực sự chỉ cần retrieval nhanh.
2. **HITL threshold dùng "err-" code làm proxy**: Thay vì dùng confidence threshold (chưa có confidence ở bước supervisor), nhóm dùng syntactic signal (mã lỗi không rõ context) để trigger human_review — đơn giản nhưng hoạt động tốt trong phạm vi lab.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?

Nhìn chung **đủ để debug cơ bản** — `route_reason` luôn liệt kê keyword nào matched, ví dụ `"task contains policy keyword(s): hoàn tiền, flash sale"`. Tuy nhiên vẫn thiếu:
- Score hoặc weight của từng keyword (câu có 3 keywords nhưng route_reason không nói weighted hay không)
- Thông tin "keyword nào được xem xét nhưng KHÔNG matched" (giúp hiểu tại sao câu gq08 về mật khẩu fallback về default)

Cải tiến đề xuất: đổi format thành `route_reason = {matched: [...], considered: [...], decision: "...", risk_signals: [...]}` để debug nhanh hơn khi có routing error.
