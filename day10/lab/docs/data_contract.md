# Data contract — Lab Day 10

**Owner Team:** Data Engineering / Knowledge Base Team
**Dataset:** `kb_chunk_export`
**Freshness SLA:** 24 giờ (được đo đạc tại thời điểm `publish` đến vector store)

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Customer Service Policy (`policy_refund_v4`, `sla_p1_2026`) | Batch Export (CSV từ DB/Wiki) | Chứa chunk quá hạn (stale), duplicate chunk, thiếu dữ liệu (rỗng) | `no_stale_refund_window` (halt), `no_duplicate_chunk_text`, `hits_forbidden` |
| HR Policy (`hr_leave_policy`) | Batch Export (CSV từ HR Portal) | Lẫn lộn chính sách cũ/mới (2025 vs 2026), xung đột phiên bản | Quarantine count, hr_leave_no_stale_10d_annual |
| IT Helpdesk (`it_helpdesk_faq`) | Batch Export (CSV từ ITSM/Confluence) | Định dạng ngày tháng không chuẩn ISO (ví dụ `dd/mm/yyyy`), thiếu `effective_date` | Expectation về format ISO 8601 (`effective_date_iso_yyyy_mm_dd`) |
| Legacy Systems (`legacy_catalog_xyz_zzz`) | Unplanned Ingestion (Crawler/Dump) | Không có trong `allowed_doc_ids` allowlist, rác dữ liệu | Alert Quarantine (Doc ID lạ) |


---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định và duy nhất sau khi làm sạch (hash từ `doc_id` + text + `seq`). Dùng để upsert idempotent lên Vector DB. |
| doc_id | string | Có | Khóa logic định danh tài liệu nguồn (vd: `policy_refund_v4`). Phải nằm trong allowlist. |
| chunk_text | string | Có | Nội dung văn bản của chunk. Đã làm sạch các keyword nháp/lỗi, thẻ HTML, độ dài tối thiểu phải đạt chuẩn >= 8 ký tự. |
| effective_date | date | Có | Ngày hiệu lực của dữ liệu, đã được chuẩn hóa về định dạng ISO 8601 (`YYYY-MM-DD`). |
| exported_at | datetime | Có | Timestamp ghi nhận thời điểm bản ghi được export từ hệ nguồn. Dùng để tính toán SLA freshness. |

---

## 3. Quy tắc quarantine vs drop

- **Không drop ngầm dữ liệu (silent drop):** Các record không hợp lệ (sai doc_id, ngày lỗi, nội dung nháp, thiếu text, stale hr version) sẽ **không bị drop bỏ/xoá đi**.
- **Cơ chế Quarantine:** Chúng được đánh cờ kèm nguyên nhân lỗi (ví dụ: `reason: unknown_doc_id` hoặc `reason: missing_effective_date`) và đẩy vào file csv riêng tại `artifacts/quarantine/quarantine_<run-id>.csv`.
- **Người approve / Xử lý:** Đội Data Owner của tài liệu (HR Team, CS Team) hoặc Data Steward sẽ định kỳ rà soát logs/manifest và file quarantine. Nếu do map thiếu ID hợp lệ, đội Data Engineer/Data Owner sẽ review và bổ sung vào cấu hình `ALLOWED_DOC_IDS`. Nếu hệ xuất phát bị lỗi/nhập sai, user nguồn phải vào fix tận gốc trên hệ thống xuất và chạy lệnh tái ingestion.

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?

Các version Source of truth (Canonical Sources) được quản lý qua `contracts/data_contract.yaml` và kiểm soát trong Cleaning Rules:

- **Customer Service Policy Refund:** Tệp `data/docs/policy_refund_v4.txt` (`policy_refund_v4`). Version V4 là policy duy nhất có giá trị pháp lý, thời gian xử lý refund là 7 ngày làm việc. Bất kỳ giá trị cũ nào (14 ngày) xuất hiện đều sẽ được rules của pipeline sửa trực tiếp trong bước cleaning, kèm marker theo dõi, và halt quá trình (expectation check) nếu lọt xuống output. 
- **SLA P1 System:** Tệp `data/docs/sla_p1_2026.txt` (`sla_p1_2026`).
- **HR Leave Policy:** Tệp `data/docs/hr_leave_policy.txt` (`hr_leave_policy`). Phiên bản gốc áp dụng từ năm 2026 trở đi. Mọi bản ghi về chính sách trước thời hạn (<=2025) hoặc cũ (quy định 10 ngày nghỉ phép) đều được xem là obsolete và bị chuyển vào quarantine.
- **IT Helpdesk:** Tệp `data/docs/it_helpdesk_faq.txt` (`it_helpdesk_faq`).
