# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Ngọc Thắng -2A202600191
**Vai trò:** Monitoring & Data Governance
**Ngày nộp:** 15/4/2026
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
Trong lab này, tôi trực tiếp đảm nhận việc biên soạn và chuẩn hóa **Data Contract** tại file `day10/lab/docs/data_contract.md`. Đây là tài liệu "hiến pháp" định nghĩa toàn bộ luật chơi cho pipeline: từ schema đầu vào, quy tắc Quarantine cho đến việc xác định các nguồn dữ liệu chính thống (Canonical Sources). 

**Kết nối với thành viên khác:**
Tôi đóng vai trò cầu nối kỹ thuật khi chủ động kết nối với các thành lập phụ trách **Sprint 1** (Ingestion), **Sprint 3** (Embedding/ChromaDB) và **Sprint 4** (Quality Control). Việc này đảm bảo các kỳ vọng (Expectations) tôi đặt ra trong contract được anh em triển khai đồng bộ, tránh tình trạng "râu ông nọ cắm cằm bà kia" khi đẩy dữ liệu từ CSV thô lên Vector Store.

**Bằng chứng (commit / comment trong code):**
Tôi đã cấu hình chi tiết bảng Schema Cleaned và các quy tắc `reason: unknown_doc_id` hoặc `reason: stale_hr_version` trong `data_contract.md` để hướng dẫn logic cho module cleaning.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định kỹ thuật quan trọng nhất của tôi là thiết lập cơ chế **Canonical Source of Truth** và **Version Control** ngay trong Data Contract. Cụ thể, tôi đã quy định tệp `policy_refund_v4.txt` là nguồn duy nhất có giá trị pháp lý (7 ngày làm việc). 

Thay vì chỉ lọc rác đơn thuần, tôi yêu cầu hệ thống phải đối soát metadata `effective_date` và `version`. Quyết định này nhằm giải quyết bài toán AI "nói dựa": nếu pipeline nạp cả chính sách cũ (14 ngày) lẫn mới (7 ngày), RAG sẽ gặp hiện tượng hallucination (ảo giác) do dữ liệu mâu thuẫn. Bằng cách định nghĩa chặt chẽ trong Contract rằng mọi bản ghi có version cũ hoặc nội dung "nháp" phải bị đẩy vào **Quarantine** thay vì **Cleaned**, tôi đã bảo vệ được tính tin cậy của kho tri thức dành cho AI.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Trong quá trình chạy thực tế Sprint 1 để kiểm thử Contract, tôi đã phát hiện một **Anomaly** nghiêm trọng về SLA dữ liệu. Khi chạy lệnh kiểm tra, file `run_sprint1.log` trả về thông báo lỗi đỏ:
`freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.45, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`.

**Triệu chứng:** Pipeline vẫn báo `PIPELINE_OK` về mặt logic xử lý, nhưng hệ thống giám sát của tôi đã bắt được việc dữ liệu đầu vào đã quá hạn 5 ngày (120 giờ), vượt xa ngưỡng 24 giờ cho phép.
**Cách xử lý:** Tôi đã ghi nhận lỗi này vào báo cáo vận hành và yêu cầu đội Ingestion (Sprint 1) kiểm tra lại scheduler. Điều này chứng minh rằng Data Contract không chỉ là lý thuyết mà là công cụ giám sát thực tế giúp chặn đứng dữ liệu "ôi thiu" trước khi nó làm sai lệch câu trả lời của trợ lý ảo.

---

## 4. Bằng chứng trước / sau (80–120 từ)

`cleaned_records=5`
`quarantine_records=5`
Dòng log thay đổi đã làm bằng chứng mạnh mẽ rằng Rule phát huy tính năng. Dòng dữ liệu `chunk_id=3` đã bị đá khỏi list Cleaned. Hệ thống ChromaDB từ đó ở `run_id=2026-04-15T08-39Z` chỉ còn `embed_upsert count=5`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm thời gian (khoảng 2 giờ), tôi sẽ cài đặt thêm Rule Data Masking (Che dấu PII). Thay vì chỉ xoá bỏ HTML hay từ khóa nháp, tôi sẽ viết Rule dùng Regex để quét và làm mờ mọi Số điện thoại cá nhân (090x.xxx) hoặc Căn cước công dân bị lẫn trong dữ liệu IT Helpdesk chuyển nó thành `[_PII_HIDDEN_]` trước khi Embed để bảo mật quyền riêng tư nhân sự.
