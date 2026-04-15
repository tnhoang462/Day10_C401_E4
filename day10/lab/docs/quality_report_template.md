# Quality report — Lab Day 10 (nhóm)

**run_id:** `sprint3-clean` vs `sprint3-dirty` (2 manifest: `manifest_sprint3-clean.json`, `manifest_sprint3-dirty.json`)
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (dirty) | Sau (clean) | Ghi chú |
|--------|---------------|-------------|---------|
| raw_records | 10 | 10 | input: `data/raw/policy_export_dirty.csv` |
| cleaned_records | 6 | 5 | chunk qua cleaning rules |
| quarantine_records | 4 | 5 | reason: duplicate, stale, missing date, unknown doc |
| **Expectation halt?** | **YES (E3 FAIL)** | **NO** | Dirty: stale 14-day refund chunk `no_refund_fix=true` → vi phạm E3 `refund_no_stale_14d_window` |

> **Khác biệt then chốt:** Dirty run bật `no_refund_fix=true` trong manifest, dẫn đến E3 (halt) fail — pipeline dừng không đưa data vào Chroma. Clean run bật `no_refund_fix=false`, E3 pass → pipeline tiếp tục bình thường.

---

## 2. Before / after retrieval

> File nguồn: `artifacts/eval/sprint3_before_dirty.csv` (dirty) và `artifacts/eval/sprint3_after_clean.csv` (clean)

### Câu hỏi then chốt: refund window (`q_refund_window`)

**Câu hỏi:** *"Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?"*

| | Trước (dirty) | Sau (clean) |
|---|---|---|
| `top1_doc_id` | `policy_refund_v4` | `policy_refund_v4` |
| `top1_preview` | "Yêu cầu được gửi trong vòng **7 ngày** làm việc…" | "Yêu cầu được gửi trong vòng **7 ngày** làm việc…" |
| `contains_expected` | yes | yes |
| `top_k_used` | 3 | 3 |

**Phân tích:** Cả hai đều trả về đúng `policy_refund_v4` với preview đúng 7 ngày. Sự khác biệt nằm ở **tầng dưới**:
- **Dirty** — chunk stale `14 ngày làm việc` (chunk_id=3, từ bản migration lỗi `policy-v3`) **không bị fix** (`no_refund_fix=true`), vẫn tồn tại trong raw → bị quarantine bởi rule `contains_draft_or_error_keywords` với ghi chú *"bản sync cũ policy-v3 — lỗi migration"*. → **E3 vi phạm (halt FAIL)**
- **Clean** — pipeline chạy đúng luồt (`no_refund_fix=false`), stale chunk bị quarantine đúng cách, chỉ chunk 7 ngày sạch được embed. → **E3 pass, pipeline tiếp tục**

---

### Merit — versioning HR: `q_leave_version`

**Câu hỏi:** *"Theo chính sách nghỉ phép hiện hành (2026), nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?"*

| | Trước (dirty) | Sau (clean) |
|---|---|---|
| `top1_doc_id` | `hr_leave_policy` | `hr_leave_policy` |
| `contains_expected` | yes | yes |
| `hits_forbidden` | no | no |
| `top1_doc_expected` | **yes** | **yes** |

**Phân tích:**
- **Dirty:** Chunk chunk_id=7 stale (`10 ngày phép năm — bản HR 2025`, effective_date `2025-01-01`) bị quarantine bởi rule `stale_hr_policy_effective_date`; chunk chunk_id=8 đúng 2026 (`12 ngày phép năm`) được giữ lại. Retrieval vẫn trả về đúng doc — nhưng hệ thống đã mất 1 phiên bản cũ.
- **Clean:** Cùng kết quả retrieval vì cleaning rule `stale_hr_policy_effective_date` đã loại stale chunk ở cả hai pipeline. Điểm merit: **cột `top1_doc_expected=yes`** chứng minh versioning policy được giám sát — nếu sau này chunk 2025 bị bypass quarantine rule, E6 `hr_leave_no_stale_10d_annual` sẽ halt ngay.

---

## 3. Freshness & monitor

**Kết quả `freshness_check`:** ✅ **PASS**

| Tham số | Giá trị |
|---------|---------|
| `latest_exported_at` (manifest) | `2026-04-10T08:00:00` |
| Hôm nay | `2026-04-15` |
| Delta | **5 ngày** |
| SLA threshold | **7 ngày** (→ WARN ở ngày 6, FAIL ở ngày 8) |
| Quyết định | 7 ngày phù hợp cho policy nội bộ — không quá nghiêm ngặt (tránh false alarm) nhưng đủ nhạy để phát hiện sync chậm. |

> **Script:** `monitoring/freshness_check.py` — check `latest_exported_at` trong manifest JSON, so sánh với threshold config.

---

## 4. Corruption inject (Sprint 3)

### Loại corruption đã inject vào `policy_export_dirty.csv`

| # | Loại | Chunk bị ảnh hưởng | Mô tả | Cách phát hiện |
|---|------|-------------------|-------|---------------|
| 1 | **Duplicate** | chunk_id=1 & 2 (cùng `policy_refund_v4`) | 2 dòng trùng hoàn toàn `chunk_text` | Rule `duplicate_chunk_text` → quarantine |
| 2 | **Stale data** | chunk_id=3 (`policy_refund_v4`) | Ghi chú rõ: *"bản sync cũ policy-v3 — lỗi migration"*, chứa cửa sổ sai `14 ngày` | Rule `contains_draft_or_error_keywords` → quarantine; E3 kiểm tra sau clean |
| 3 | **Missing effective_date** | chunk_id=5 (`policy_refund_v4`) | Trường `effective_date` rỗng | Rule `missing_effective_date` → quarantine |
| 4 | **Stale HR policy** | chunk_id=7 (`hr_leave_policy`) | Bản 2025 (`2025-01-01`) với số ngày phép sai `10` | Rule `stale_hr_policy_effective_date` → quarantine; E6 sau clean |
| 5 | **Unknown doc_id** | chunk_id=9 (`legacy_catalog_xyz_zzz`) | Doc không có trong `data_contract.yaml` allowlist | Rule `unknown_doc_id` → quarantine |

### Bonus: format error
| 6 | **Sai định dạng ngày** | chunk_id=10 (`it_helpdesk_faq`) | `effective_date = "01/02/2026"` (MM/DD/YYYY) thay vì ISO `YYYY-MM-DD` | Rule `effective_date_iso_yyyy_mm_dd` + E5 expectation |

### Tổng kết quarantine
```
quarantine_sprint3-clean.csv  (5 records): 2, 3, 5, 7, 9
quarantine_sprint3-dirty.csv   (5 records): 2, 3, 5, 7, 9
```
→ **5/10 records (50%) bị loại** — đúng ngưỡng E7 warn (unique doc coverage ≥ 3 vẫn đảm bảo sau clean: 4 doc_ids).

---

## 5. Hạn chế & việc chưa làm

- **Chưa có cron/schedule tự động** cho `freshness_check` — hiện chạy thủ công mỗi lần chạy pipeline. Cần tích hợp vào CI/CD hoặc scheduled job.
- **Không có root-cause tracking** cho các chunk bị quarantine — không lưu audit trail về upstream source (bản migration nào sinh ra chunk lỗi).
- **Không có retry mechanism** khi expectation halt — pipeline dừng hoàn toàn, không tự retry hoặc notify.
- **`no_refund_fix` flag** là thủ công (CLI arg `--no-refund-fix`) — chưa có auto-detect "stale data pattern" để tự động bật fix mode.
- **Quarantine retention policy** chưa có — quarantine file cứ accumulate, không có cleanup hoặc archive sau N ngày.
- **Không có PII/sensitive data scan** trong cleaning rules — nếu chunk chứa thông tin nhạy cảm sẽ không bị phát hiện.
- **thiếu `before_after_eval.csv` tổng hợp** — 2 file riêng biệt `sprint3_before_dirty.csv` / `sprint3_after_clean.csv` chưa được gộp vào 1 file duy nhất theo template.

