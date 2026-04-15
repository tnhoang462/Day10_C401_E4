# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trương Đặng Gia Huy
**MSSV:** 2A202600436
**Vai trò trong nhóm:** Supervisor Owner
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm xây dựng **Supervisor Orchestrator** trong file `graph.py` — bộ não điều phối toàn hệ multi-agent của nhóm.

Các việc tôi đã hoàn thành:
- Giữ nguyên `AgentState` TypedDict với đầy đủ 16 field theo contract, đảm bảo state chảy xuyên graph không mất dữ liệu.
- Triển khai `supervisor_node()` với 3 tập keyword (policy, retrieval, risk) và logic override cho `human_review` khi task chứa mã lỗi không rõ (ERR-xxx) mà không có ngữ cảnh.
- Bảo đảm `route_reason` luôn cụ thể — liệt kê chính xác keyword matched — thay vì giá trị generic như "default route" (vi phạm contract).
- Thêm **safety wrapper** try/except bao quanh các worker node để graph không crash khi Sprint 2 workers gặp sự cố import.
- Tự động lưu trace JSON sau mỗi run vào `artifacts/traces/` — phục vụ Sprint 4 evaluation.

**Bằng chứng:** `python graph.py` pass 3 test query với routing chính xác, trace file sinh ra đầy đủ metadata.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Dùng **rule-based keyword matching** cho supervisor routing thay vì LLM classifier, đồng thời thêm **safety wrapper** bao quanh worker node.

**Lý do:** Trong lab này, trace rõ ràng và reproducibility quan trọng hơn độ thông minh. LLM classifier cho phép hiểu ngữ cảnh tốt hơn nhưng có 3 nhược điểm: (1) latency thêm ~500ms mỗi câu, (2) kết quả không deterministic — chạy lại có thể route khác, (3) khó debug khi group report cần bằng chứng cụ thể. Rule-based keyword cho kết quả <1ms, nhất quán 100%, và `route_reason` tự động liệt kê keyword matched — debug dễ.

Về safety wrapper: do tôi chỉ phụ trách Sprint 1, workers thật do team viết Sprint 2. Nếu worker crash (import lỗi, ChromaDB chưa index, API key thiếu), graph sẽ fail toàn bộ. Safety wrapper biến crash thành log graceful, vẫn hoàn thành flow. DoD #1 ("chạy không lỗi") được bảo vệ khỏi phụ thuộc code Sprint 2.

**Trade-off:** Keyword routing không handle edge case như "store credit 110%" (q10 — có "hoàn tiền" ngầm nhưng không có keyword trực tiếp). Chấp nhận miss vì DoD chỉ yêu cầu ≥2 loại route đúng.

**Bằng chứng từ trace:**
```json
"route_reason": "task contains policy keyword(s): cấp quyền, level 3 | risk signals: khẩn cấp"
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** `route_reason` không đủ cụ thể + keyword `"emergency"` bị phân loại sai.

**Symptom:**
1. Khi task không match keyword nào, `route_reason` set cứng thành `"default route"` — vi phạm constraint `worker_contracts.yaml:51` ("không được là chuỗi rỗng hoặc 'unknown'") và ảnh hưởng 2đ scoring.
2. Keyword `"emergency"` ban đầu được đặt trong `risk_keywords` (chỉ flag risk), nhưng theo README gợi ý thì phải vào `policy_keywords` để route sang policy_tool_worker.

**Root cause:**
1. Logic supervisor ban đầu không có nhánh riêng cho trường hợp không match — fallthrough vào giá trị default hardcode.
2. Đọc README không kỹ — nhầm giữa "emergency = tình huống khẩn cấp (risk)" và "emergency = cấp quyền khẩn cấp (policy)".

**Cách sửa:**
1. Refactor thành if/elif/else tường minh: match policy → match retrieval → fallback `"no specific signal → default retrieval"` (vẫn cụ thể).
2. Di chuyển `"emergency"` từ `risk_keywords` sang `policy_keywords`, đồng thời dùng danh sách `matched_*` để `route_reason` tự liệt kê keyword đã match.

**Bằng chứng:** Sau sửa, query *"Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp"* route đúng `policy_tool_worker` với reason liệt kê cả `cấp quyền, level 3` và risk flag `khẩn cấp`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Routing logic đạt toàn bộ DoD (3/3 test query route đúng), `route_reason` luôn cụ thể đủ cho 2đ scoring. Safety wrapper là đóng góp thêm ngoài spec — giúp nhóm không bị block khi Sprint 2 có bug.

**Tôi làm chưa tốt ở điểm nào?**
Chỉ nhắm minimum DoD nên keyword list chưa tối ưu cho 15 test questions — ví dụ q02 ("hoàn tiền 7 ngày") expected retrieval nhưng code của tôi route policy. `run_id` chỉ dùng giây → 3 trace cùng giây bị ghi đè, phải có Trace Owner fix thêm microsecond khi eval thật.

**Nhóm phụ thuộc tôi ở đâu?**
Nếu routing sai, mọi worker dù có tốt cũng trả lời sai câu hỏi. Supervisor là chốt chặn đầu tiên định hình chất lượng output.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ: (1) thay keyword matching bằng **LLM classifier** cho các edge case mơ hồ (q02 vs q07 đều có "hoàn tiền" nhưng route khác nhau) — dùng LLM chỉ khi keyword không đủ tin cậy để tiết kiệm cost; (2) implement **HITL real-pause** với `input()` CLI thay vì auto-approve, đúng tinh thần human-in-the-loop của Sprint 3 bonus; (3) sửa `run_id` thêm microsecond `%f` để 15 trace không ghi đè nhau khi eval.

---
