# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Customer Service Policy (`policy_refund_v4`, `sla_p1_2026`) | Batch Export (CSV từ DB/Wiki) | Chứa chunk quá hạn (stale), duplicate chunk, thiếu dữ liệu (rỗng) | `no_stale_refund_window` (halt), `no_duplicate_chunk_text`, `hits_forbidden` |
| HR Policy (`hr_leave_policy`) | Batch Export (CSV từ HR Portal) | Lẫn lộn chính sách cũ/mới (2025 vs 2026), xung đột phiên bản | Quarantine count, Date format/version expectation |
| IT Helpdesk (`it_helpdesk_faq`) | Batch Export (CSV từ ITSM/Confluence) | Định dạng ngày tháng không chuẩn ISO (ví dụ `dd/mm/yyyy`), thiếu `effective_date` | Expectation về format ISO 8601 (`valid_date_format`) |
| Legacy Systems (`legacy_catalog_xyz_zzz`) | Unplanned Ingestion (Crawler/Dump) | Không có trong `allowed_doc_ids`, rác dữ liệu | Alert Quarantine (Doc ID lạ) |


---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | … |
| doc_id | string | Có | … |
| chunk_text | string | Có | … |
| effective_date | date | Có | … |
| exported_at | datetime | Có | … |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?
