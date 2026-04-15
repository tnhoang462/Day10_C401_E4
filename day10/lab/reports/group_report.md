# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

_________________

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

_________________

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `normalize_effective_date_ddmmyyyy_to_iso` (rule) | non-ISO date còn xuất hiện ở raw (`01/02/2026`) | `non_iso_rows=0` sau clean | `artifacts/logs/run_sprint2.log`, dòng expectation `effective_date_iso_yyyy_mm_dd` |
| `quarantine_stale_hr_policy_before_2026` (rule) | Có bản HR cũ 2025 trong raw | Loại khỏi cleaned, không còn stale marker `10 ngày phép năm` trong cleaned | `artifacts/logs/run_sprint2.log`, expectation `hr_leave_no_stale_10d_annual` |
| `dedupe_chunk_text_normalized` (rule) | raw có duplicate chunk refund (2 dòng gần trùng) | `quarantine_records=4`, cleaned giữ 1 bản chuẩn | `artifacts/logs/run_sprint2.log`, `artifacts/quarantine/quarantine_sprint2.csv` |
| `effective_date_iso_yyyy_mm_dd` (expectation, halt) | Trước clean có ngày không ISO | Sau clean pass: `non_iso_rows=0` | `artifacts/logs/run_sprint2.log` |
| `hr_leave_no_stale_10d_annual` (expectation, halt) | Trước clean có phrase stale HR 2025 | Sau clean pass: `violations=0` | `artifacts/logs/run_sprint2.log` |

**Rule chính (baseline + mở rộng):**

- Allowlist `doc_id` và quarantine `unknown_doc_id`.
- Chuẩn hoá `effective_date` về `YYYY-MM-DD`; quarantine nếu thiếu/sai format.
- Quarantine bản `hr_leave_policy` cũ (`effective_date < 2026-01-01`).
- Quarantine chunk rỗng; dedupe theo normalized text.
- Fix stale refund window `14 ngày làm việc -> 7 ngày làm việc` cho `policy_refund_v4`.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Khi chạy kịch bản inject (`--no-refund-fix --skip-validate`), expectation `refund_no_stale_14d_window` fail với `violations=1` (xem `artifacts/logs/run_sprint3-dirty.log`). Cách xử lý là chạy lại pipeline chuẩn (bật refund fix, không skip validate) để expectation pass và publish lại cleaned snapshot.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- …
