# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lê Quý Công <br>
**Vai trò:** Eval Retrieval + Quality Report Documentation <br>
**Ngày nộp:** 2026-04-15 <br>
**Độ dài yêu cầu:** 400–650 từ <br>

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.
> Lưu: `reports/individual/LeQuyCong.md`

## 1. Tôi phụ trách phần nào?

**File / module:**
Tôi đảm nhận hai phần chính: **(1)** chạy và hoàn thiện báo cáo đánh giá retrieval bằng `eval_retrieval.py`, và **(2)** viết `docs/quality_report.md` (dựa trên `quality_report_template.md`) với đầy đủ số liệu từ manifest và eval CSV.

Cụ thể, tôi chạy `eval_retrieval.py` trên hai trạng thái ChromaDB khác nhau — dirty (sprint3-dirty, `--no-refund-fix`) và clean (sprint3-clean) — để tạo hai file eval: `sprint3_before_dirty.csv` và `sprint3_after_clean.csv`. Từ đó, tôi hoàn thiện `docs/quality_report.md` bằng cách điền đầy đủ số liệu từ manifest (`manifest_sprint3-clean.json`, `manifest_sprint3-dirty.json`) và `grading_run.jsonl`.

**Kết nối với thành viên khác:**
Kết quả eval của tôi là đầu vào cho grading chính thức (`grading_run.jsonl`), đồng thời cung cấp bằng chứng before/after cho section 2 của `quality_report.md`. Tôi phối hợp với bạn phụ trách `grading_run.py` để đảm bảo 3 câu grading (`gq_d10_01`, `gq_d10_02`, `gq_d10_03`) có `contains_expected`, `hits_forbidden`, `top1_doc_matches` đúng rubric.

**Bằng chứng (commit / file artifact):**
- `artifacts/eval/sprint3_before_dirty.csv` — eval trước khi fix
- `artifacts/eval/sprint3_after_clean.csv` — eval sau khi fix
- `artifacts/eval/grading_run.jsonl` — 3 dòng grading chính thức
- `docs/quality_report.md` — báo cáo hoàn thiện

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định quan trọng nhất khi hoàn thiện `quality_report.md` là cách diễn giải kết quả eval khi **dirty run không embed được** (pipeline halt ở bước validate). Theo logic pipeline: `sprint3-dirty` chạy với `--no-refund-fix`, expectation `refund_no_stale_14d_window` FAIL → pipeline trả exit code 2 → **không embed vào ChromaDB**.

Tôi phải quyết định: nên so sánh với collection nào? Giải pháp của tôi là giữ nguyên eval dirty từ collection của run trước đó (`sprint1`), đồng thời ghi rõ trong report rằng dirty scenario phản ánh **data governance vi phạm** (stale chunk 14 ngày không bị fix/quarantine) chứ không chỉ là "eval kém hơn". Điều này đúng với SCORING: dirty halt chứng minh expectation hoạt động, clean pass chứng minh pipeline đáng tin cậy.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Anomaly tôi phát hiện khi chạy eval là bảng số liệu **trước/sau trong section 1 của quality report** bị sai số. Ban đầu tôi điền `cleaned_records=6` và `quarantine_records=4` (số của sprint1) cho dirty run. Nhưng khi kiểm tra kỹ `manifest_sprint3-dirty.json`, tôi phát hiện cả hai manifest (`sprint3-clean` và `sprint3-dirty`) đều có `cleaned_records=5, quarantine_records=5`.

Lý do: dù dirty run halt ở validate, nhưng bước **cleaning vẫn chạy đầy đủ** — chỉ có bước embed bị bỏ qua. Sự khác biệt nằm ở `no_refund_fix=true`: chunk 14 ngày vẫn nằm trong cleaned CSV (5 bản ghi) chứ không bị quarantine, dẫn đến **E3 FAIL**. Tôi đã sửa lại bảng số liệu và bổ sung giải thích rõ ràng vào report để tránh hiểu nhầm.

---

## 4. Bằng chứng trước / sau (80–120 từ)

**Trước (eval dirty — `sprint3_before_dirty.csv`):**
```
q_refund_window: top1_doc_id=policy_refund_v4,
  contains_expected=yes, hits_forbidden=no
q_leave_version: top1_doc_id=hr_leave_policy,
  contains_expected=yes, hits_forbidden=no, top1_doc_expected=yes
```
→ Grading chưa chạy; số liệu chỉ mang tính tham khảo vì pipeline dirty halt.

**Sau (eval clean — `sprint3_after_clean.csv` + `grading_run.jsonl`):**
```
gq_d10_01: contains_expected=true, hits_forbidden=false  ✅
gq_d10_02: contains_expected=true, hits_forbidden=false  ✅
gq_d10_03: contains_expected=true, hits_forbidden=false,
           top1_doc_matches=true                        ✅ MERIT
```
→ Chunk stale đã bị quarantine đúng cách; retrieval trả về đúng policy 2026; grading đạt Merit.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ viết script tự động so sánh hai file eval CSV và in ra diff giữa dirty/clean — highlight dòng nào đổi từ `hits_forbidden=yes` sang `no`, dòng nào giữ nguyên. Script sẽ tự generate bảng so sánh và dán trực tiếp vào quality report, giảm thao tác thủ công và tránh sai số khi điền tay.