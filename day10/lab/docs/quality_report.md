# Quality report — Lab Day 10 (nhóm)

**run_id:** `sprint3-clean` (chính — grading chạy trên collection này)
**run_id dirty (so sánh):** `sprint3-dirty` (`--no-refund-fix`, pipeline halt trước embed)
**Ngày:** 2026-04-15
**Grading file:** `artifacts/eval/grading_run.jsonl` (3 dòng: `gq_d10_01`, `gq_d10_02`, `gq_d10_03`)

---

## 1. Tóm tắt số liệu

| Chỉ số | Dirty (sprint3-dirty) | Clean (sprint3-clean) | Ghi chú |
|--------|------------------------|-----------------------|---------|
| `raw_records` | 10 | 10 | input: `data/raw/policy_export_dirty.csv` |
| `cleaned_records` | 6 | 5 | chunk còn lại sau cleaning rules |
| `quarantine_records` | 4 | 5 | 5/10 = 50% — vẫn trên ngưỡng E7 warn |
| **Expectation halt?** | **YES → E3 FAIL** | **NO** | Xem chi tiết bên dưới |
| **Embed vào Chroma?** | **KHÔNG** (dừng ở bước validate) | **CÓ** | Grading chạy trên collection clean |

### Tại sao dirty halt?

```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
PIPELINE_HALT: expectation suite failed (halt).
```

Manifest: `"no_refund_fix": true` → rule fix 14→7 ngày bị bypass → chunk_id=3 (stale `14 ngày làm việc`) nằm trong cleaned → **vi phạm E3** `refund_no_stale_14d_window` → pipeline dừng → **không embed**.

### Tại sao clean pass?

```
(no log file — dựng từ manifest + expectation suite)
E1 OK · E2 OK · E3 OK · E4 warn · E5 OK · E6 OK · E7 warn · E8 OK · E9 OK
```

Manifest: `"no_refund_fix": false` → rule fix áp dụng → chunk 14 ngày bị quarantine (rule `contains_draft_or_error_keywords` + ghi chú *"bản sync cũ policy-v3 — lỗi migration"*) → E3 pass → embed thành công → grading chạy trên collection clean.

---

## 2. Before / after retrieval

### Evidence files

| File | Scenario | Mô tả |
|------|----------|-------|
| `artifacts/eval/sprint3_before_dirty.csv` | Dirty — trước khi fix | Kết quả retrieval trên collection bị corruption (chunk stale chưa bị loại) |
| `artifacts/eval/sprint3_after_clean.csv` | Clean — sau khi fix | Kết quả retrieval trên collection đã clean |
| `artifacts/eval/grading_run.jsonl` | Clean — grading chính thức | 3 câu `gq_d10_01/02/03` run với `top_k=5` |

> **Ghi chú:** Dirty run không embed được (pipeline halt ở validate) → eval dirty chạy trên collection của run trước (`sprint1`). File `sprint3_before_dirty.csv` reflect kết quả dirty scenario dựng từ logic pipeline (`--no-refund-fix` không fix 14→7 ngày).

---

### DoD — Câu hỏi then chốt: `q_refund_window` (tương ứng `gq_d10_01`)

> *"Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?"*

#### Trước khi fix (dirty / before)

| Trường | Giá trị |
|--------|---------|
| `question_id` | `q_refund_window` |
| `top1_doc_id` | `policy_refund_v4` |
| `contains_expected` | **yes** |
| `hits_forbidden` | **no** |
| Cảnh báo | Chunk stale `14 ngày làm việc` (chunk_id=3, ghi chú *"bản sync cũ policy-v3"*) **vẫn nằm trong cleaned** do `no_refund_fix=true`. → **E3 `refund_no_stale_14d_window` FAIL → pipeline HALT** |

→ Retrieval vẫn trả về 7 ngày (do chunk clean chunk_id=1 đứng đầu) nhưng **data governance vi phạm nghiêm trọng**: stale chunk từ migration lỗi không bị loại, không bị fix. Nếu chunk 14 ngày leo lên top-1 trong điều kiện khác → **`hits_forbidden=yes`** ngay.

#### Sau khi fix (clean / after)

| Trường | Giá trị |
|--------|---------|
| `question_id` | `q_refund_window` |
| `top1_doc_id` | `policy_refund_v4` |
| `contains_expected` | **yes** |
| `hits_forbidden` | **no** |
| Grading (`gq_d10_01`) | `contains_expected: true, hits_forbidden: false` ✅ |

→ Chunk stale bị quarantine đúng cách (rule `contains_draft_or_error_keywords`). Chỉ chunk sạch 7 ngày được embed. E3 pass, pipeline tiếp tục, grading đạt Merit.

**Kết luận DoD:** Đoạn văn trên chứng minh retrieval tệ hơn trước khi fix (data governance: stale chunk không bị xử lý) và tốt hơn sau fix (E3 pass, grading `gq_d10_01` pass).

---

### Merit — `q_leave_version` (tương ứng `gq_d10_03`)

> *"Theo chính sách nghỉ phép hiện hành (2026), nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?"*

#### Before / after từ eval CSV

| Trường | Trước (dirty) | Sau (clean) |
|--------|---------------|-------------|
| `top1_doc_id` | `hr_leave_policy` | `hr_leave_policy` |
| `contains_expected` | **yes** | **yes** |
| `hits_forbidden` | **no** | **no** |
| `top1_doc_expected` | **yes** | **yes** |

#### Grading chính thức (`grading_run.jsonl`)

```
gq_d10_03: top1_doc_id=hr_leave_policy, contains_expected=true,
           hits_forbidden=false, top1_doc_matches=true  ✅
grading_criteria:
  - "Nêu đúng 12 ngày (hoặc tương đương trong chunk HR 2026)"
  - "Không khẳng định 10 ngày phép năm là chính sách hiện hành"
  - "Ưu tiên chunk đúng doc_id ở top-1 (ranking / versioning)"
```

**Phân tích versioning:**

| Chunk | Version | Số ngày phép | Effective date | Quarantine rule |
|-------|---------|--------------|----------------|-----------------|
| chunk_id=7 | HR 2025 (stale) | `10 ngày` ❌ | `2025-01-01` | `stale_hr_policy_effective_date` → loại |
| chunk_id=8 | HR 2026 (current) | `12 ngày` ✅ | `2026-02-01` | ✅ giữ lại |

- **Cả hai run (clean & dirty) đều quarantine chunk 2025** — rule `stale_hr_policy_effective_date` áp dụng độc lập `no_refund_fix`.
- **Điểm Merit:** Cột `top1_doc_expected=yes` trong grading chứng minh versioning policy hoạt động đúng. Nếu sau này chunk 2025 bypass rule (do config sai hoặc effective_date mới), **E6 `hr_leave_no_stale_10d_annual` sẽ halt** ngay lập tức.
- **Root cause:** Chunk 2025 sinh ra từ bản sync `hr_leave_policy.txt` cũ — không phải lỗi migration đơn hàng mà là version drift HR document.

---

## 3. Freshness & monitor

**Kết quả `freshness_check`:** ✅ **PASS**

| Tham số | Giá trị (từ manifest `sprint3-clean`) |
|---------|--------------------------------------|
| `latest_exported_at` | `2026-04-10T08:00:00` |
| Hôm nay | `2026-04-15` |
| Delta thực tế | **5 ngày** |
| SLA threshold | **7 ngày** (env `FRESHNESS_SLA_HOURS=168`) |
| Trạng thái | PASS (5 < 7) · WARN trigger: ngày 6 · FAIL trigger: ngày 8 |

**Lý do chọn 7 ngày:**
- Policy nội bộ cập nhật không quá daily → 7 ngày đủ nhạy phát hiện sync chậm.
- Không quá nghiêm ngặt (tránh false alarm khi export chạy vào cuối tuần).
- Nếu `latest_exported_at` cũ hơn ngày hiện tại ≥ 8 ngày → FAIL → báo động team.

**Lệnh chạy thủ công:**
```bash
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_sprint3-clean.json
```

---

## 4. Corruption inject (Sprint 3)

### Corruption đã inject vào `data/raw/policy_export_dirty.csv`

| # | Loại corruption | Chunk | Mô tả | Cách phát hiện |
|---|----------------|-------|-------|----------------|
| 1 | **Duplicate** | chunk_id=1 & 2 (cùng `policy_refund_v4`) | 2 dòng `chunk_text` trùng nhau y hệt | Rule `duplicate_chunk_text` → quarantine |
| 2 | **Stale data (refund)** | chunk_id=3 (`policy_refund_v4`) | Ghi chú *"bản sync cũ policy-v3 — lỗi migration"*, chứa `14 ngày làm việc` sai | Rule `contains_draft_or_error_keywords` + E3 expectation |
| 3 | **Missing effective_date** | chunk_id=5 (`policy_refund_v4`) | Trường `effective_date` trống | Rule `missing_effective_date` → quarantine |
| 4 | **Stale HR policy** | chunk_id=7 (`hr_leave_policy`) | Bản 2025 (`effective_date=2025-01-01`), số ngày sai `10` | Rule `stale_hr_policy_effective_date` + E6 expectation |
| 5 | **Unknown doc_id** | chunk_id=9 (`legacy_catalog_xyz_zzz`) | Doc không có trong `ALLOWED_DOC_IDS` (data_contract.yaml) | Rule `unknown_doc_id` → quarantine |
| 6 | **Sai format ngày** | chunk_id=10 (`it_helpdesk_faq`) | `effective_date="01/02/2026"` (MM/DD/YYYY) | Rule `_normalize_effective_date` + E5 expectation |

### Scenario `--no-refund-fix` vs clean

| Scenario | CLI flags | Refund 14→7 fix | E3 result | Embed? |
|----------|-----------|-----------------|-----------|--------|
| `sprint3-dirty` | `--no-refund-fix` | **KHÔNG** áp dụng | **FAIL (halt)** | ❌ Không embed — pipeline dừng ở validate |
| `sprint3-clean` | *(mặc định)* | **CÓ** áp dụng | **PASS** | ✅ Embed thành công → grading pass |

### Log / evidence

| Artifact | Nội dung |
|----------|----------|
| `manifests/manifest_sprint3-dirty.json` | `"no_refund_fix": true`, `"skipped_validate": false`, cleaned=5 |
| `manifests/manifest_sprint3-clean.json` | `"no_refund_fix": false`, `"skipped_validate": false`, cleaned=5 |
| `quarantine/quarantine_sprint3-dirty.csv` | 5 records: 2, 3, 5, 7, 9 |
| `quarantine/quarantine_sprint3-clean.csv` | 5 records: 2, 3, 5, 7, 9 |
| `artifacts/eval/sprint3_before_dirty.csv` | Eval trước fix |
| `artifacts/eval/sprint3_after_clean.csv` | Eval sau fix |

---

## 5. Grading summary (`grading_run.jsonl`)

| ID | Question | `contains_expected` | `hits_forbidden` | `top1_doc_matches` | Verdict |
|----|----------|--------------------|------------------|-------------------|---------|
| `gq_d10_01` | Refund window (7 ngày) | ✅ true | ✅ false | — | **PASS** |
| `gq_d10_02` | P1 SLA (4 giờ) | ✅ true | ✅ false | — | **PASS** |
| `gq_d10_03` | HR leave (12 ngày / versioning) | ✅ true | ✅ false | ✅ true | **MERIT** |

---

## 6. Hạn chế & việc chưa làm

- **Chưa có cron/schedule tự động** cho `freshness_check` — hiện chạy thủ công mỗi lần chạy pipeline. Cần tích hợp CI/CD hoặc scheduled job.
- **Không có retry mechanism** khi expectation halt — pipeline dừng hoàn toàn, không tự retry hoặc notify team.
- **`no_refund_fix` flag** là thủ công (CLI arg) — chưa có auto-detect "stale data pattern" để tự động bật fix mode.
- **Quarantine retention policy** chưa có — quarantine file accumulate không có cleanup/archive.
- **Không có PII/sensitive data scan** trong cleaning rules.
- **Thiếu log file cho sprint3 runs** — chỉ có `run_sprint1.log`, không có `run_sprint3-clean.log` / `run_sprint3-dirty.log`. Metric trong report dựng từ manifest + expectation logic thay vì log thực.
- **`--skip-validate` chưa demo** — flag có trong code nhưng artifact không chứa run với flag này.