# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phạm Đỗ Ngọc Minh
**Vai trò:** Incident Response & Data Operations
**Ngày nộp:** 15/4/2026
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
Trong lab này, tôi trực tiếp đảm nhận việc biên soạn và chuẩn hóa tài liệu ứng phó sự cố tại file `day10/lab/docs/runbook.md`, đồng thời định nghĩa chi tiết các nguồn Ingestion và Failure mode vào `day10/lab/docs/data_contract.md`. 

**Kết nối với thành viên khác:**
Tôi kết nối công tác chất lượng dữ liệu giữa hệ thống RAG (ứng dụng đầu ra) và quá trình Ingestion (đầu vào). Thông qua việc quy định rõ các metric cảnh báo rác từ Data Contract, tôi giúp đội RAG nhận biết các triệu chứng ảo giác (hallucination) có nguyên nhân gốc từ pipeline hỏng, bằng cách chuẩn hóa các bước kiểm tra manifest và quarantine.

**Bằng chứng (commit / comment trong code):**
Commit `e510530` (mod: runbook) bổ sung quy trình Detection, Mitigation, Prevention; và commit `1932ded` khai báo bảng theo dõi các hệ thống Customer Service, HR, IT Helpdesk.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định kỹ thuật cốt lõi của tôi là xây dựng cơ chế **Fail-Stop (Halt)** thay vì chỉ cảnh báo lỏng lẻo cho Data Pipeline, quy định rõ trong Runbook và Contract. Thay vì để luồng ETL vẫn tiếp tục chạy và "nhồi" dữ liệu bẩn vào Vector Database gây ngộ độc AI, tôi chuẩn hóa lại rằng mọi vi phạm Expectation nghiêm trọng (ví dụ: `expectation[refund_no_stale_14d_window]` hoặc chứa tài liệu nháp) đều phải Halt ngay lập tức. 

Kèm theo đó, thay vì chỉ bỏ qua lỗi, tôi quyết định bổ sung quy trình hồi phục (Mitigation) cụ thể: người vận hành phải chạy kịch bản phục hồi bằng cách dùng tính năng `embed_prune_removed` tống khứ vector rác, hoặc nặng hơn là ngắt tác vụ RAG, xóa thư mục `chroma_db/` vật lý và Rerun luồng ETL. Quyết định này đặt ra lằn ranh đỏ cho vệ sinh dữ liệu, đảm bảo không có rác lạc vào kho tri thức RAG.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Một anomaly nghiêm trọng mà tôi đã xử lý là sự cố Agent RAG trả lời sai do nạp nhầm chính sách lỗi thời.

**Triệu chứng:** Người dùng hỏi Agent về kịch bản hoàn ví, phản hồi là "Sẽ đổi trả trong 14 ngày làm việc" thay vì policy mới là 7 ngày; đồng thời Agent trả ra các đoạn mã HTML rác như `<script>`, chữ "TBD".
**Cách phát hiện và xử lý:** Thông qua Runbook, tôi đã hệ thống hóa bước chạy thử nghiệm offline bằng `python grading_run.py`, từ đó phát hiện metric `hits_forbidden=true` vọt lên cao. Tôi kết hợp kiểm tra file `artifacts/quarantine/quarantine_<run_id>.csv` và nhận ra rằng quá trình ingest kéo nhầm cả những chunk chưa dọn dẹp. Từ sự cố này, tôi đã quy định rõ trong phần Prevention của Runbook: phải cập nhật Guardrails (các cụm từ bẩn) vào Quality Expectation để loại bỏ các record này ngay từ khâu đầu ETL.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Chỉ báo rõ ràng cho hiệu quả công việc là tỷ lệ phát hiện rác lọt qua Pipeline ở các tầng hệ thống khác nhau:
- **Trước khi có Guardrail và Runbook:** Agent trả lời lẫn lộn chính sách năm 2025 (`14 ngày`) vì dữ liệu Stale nằm chung với Fresh data, không ai biết lỗi ở chặng nào.
- **Sau khi áp dụng:** Quá trình ETL lập tức báo Halt đỏ ở `expectation[refund_no_stale_14d_window] FAIL (halt): violations > 0`. Metric `quarantine_records` lập tức cô lập các chunk dơ có chứa "TBD" hay có lỗi `reason: stale_data/format_error`. File báo cáo manifest thể hiện luồng đã ngắt trước khi ChromaDB bị vẩn đục.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm thời gian, tôi sẽ nghiên cứu tích hợp Auto-trigger Webhook để gửi Alert trực tiếp bằng tin nhắn về Slack/Teams ngay khi gặp dấu hiệu cảnh báo từ hệ thống Freshness hoặc khi Rule Expectation báo Halt (Fail-Stop). Ngoài ra, có thể nâng cấp công cụ CLI để thực thi tự động dòng lệnh Rollback mà không cần gỡ bỏ thư mục VectorDB bằng tay.
