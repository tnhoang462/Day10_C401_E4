# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** E4  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email/MSSV |
|-----|------------------|-------|
| Nguyễn Ngọc Thắng | Ingestion / Data Contract Owner | 2A202600191 |
| Nguyễn Xuân Mong | Cleaning & Quality Owner | 2A202600246 |
| Trần Nhật Hoàng | Embed & Idempotency Owner | N/A |
| Trương Đăng Gia Huy | Monitoring / Docs Owner | N/A |
| Phạm Đỗ Ngọc Minh | Incident Response & Data Operations | N/A |
| Lê Quý Công | Eval Retrieval & Quality Report | N/A |
| Trần Minh Toàn | Sprint 3 Lead (Evaluation & Quality Control) | N/A |

**Ngày nộp:** 15/04/2026  
**Repo:** VinAI/Day10_C401_E4  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

**Tóm tắt luồng:**
Dữ liệu raw xuất phát từ export của các hệ thống CS, HR, IT (CSV mẫu `policy_export_dirty.csv`). Do nguồn này chứa lỗi dữ liệu (duplicate chunk, sai định dạng ISO của ngày, lỗi version HR, thẻ HTML rỗng, và policy refund cũ), nhóm đã chạy một hệ thống ETL Pipeline end-to-end với quy trình kiểm duyệt khắt khe: Ingest -> Clean (áp dụng các Cleaning Rules thông minh lọc nhiễu) -> Validate (thông qua Great Expectations suite sử dụng cơ chế bảo mật Fail-Stop để chặn rác) -> Embed (vào ChromaDB bằng idempotent updates với tính năng prune bản ghi đã xóa, không cho phép rác tích tụ làm ô nhiễm top-k).

Tất cả các snapshot của quá trình chạy đều được kiểm soát và ghi nhận run_id qua manifest log của hệ thống, ví dụ `2026-04-15T08-39Z`. Pipeline được xây dựng hoàn toàn có mục đích bảo đảm "trọng sạch" cho chuỗi cung ứng data hướng lên Multi-agent RAG. 

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**
```bash
# Luồng chuẩn: fix stale refund 14→7, expectation pass, embed
python etl_pipeline.py run

# Kiểm tra freshness theo manifest 
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json
```

---

## 2. Cleaning & expectation (150–200 từ)

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `min_chunk_length_15` (rule) | Raw có thể chứa dòng rác, dấu phẩy < 15 ký tự | Bị giữ lại ở quarantine | Module `cleaning_rules.py` |
| `contains_draft_or_error_keywords` (rule) | `quarantine_records=4` (chưa có rule chặn keyword) | `quarantine_records=5` (block ID 3 chứa lỗi migration) | `run_sprint1.log` (2026-04-15T08-39Z) |
| `strip_html_tags` (rule) | Raw có tag rác HTML | Được sanitize mất thẻ HTML | Module `cleaning_rules.py` |
| `min_unique_doc_id_coverage` (expectation, warn) | Pass kể cả tài liệu quá hẹp | `FAIL (warn) :: unique_doc_ids=1` khi nhận data thiếu đa dạng | Log `sprint2-extra` |
| `no_placeholder_in_cleaned` (expectation, halt) | Chunk kiểu `TBD`, `placeholder` dễ lọt vào | `OK (halt) :: placeholder_chunks=0` | `run_sprint2-final.log` |
| `unique_chunk_ids` (expectation, halt) | Chunk IDs bị duplicate sinh lỗi upset | `violations=0` | `run_sprint2-final.log` |

**Rule chính (baseline + mở rộng):**

- Allowlist `doc_id` và quarantine `unknown_doc_id`.
- Chuẩn hoá `effective_date` về `YYYY-MM-DD`; quarantine nếu thiếu/sai format.
- Quarantine bản `hr_leave_policy` cũ (`effective_date < 2026-01-01`).
- Quarantine chunk rỗng; dedupe theo normalized text.
- Fix stale refund window `14 ngày làm việc -> 7 ngày làm việc` cho `policy_refund_v4`.
- **(Mở rộng 1)** Giới hạn độ dài: quarantine với khối văn bản < 15 ký tự (`min_chunk_length_15`).
- **(Mở rộng 2)** Lọc keyword nháp/mâu thuẫn như "lỗi migration", "TBD" (`contains_draft_or_error_keywords`).
- **(Mở rộng 3)** Gọt rửa các thẻ HTML rác dính vào đoạn text (nguồn Helpdesk).

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**
Khi chạy kịch bản inject (`--no-refund-fix --skip-validate`), expectation `refund_no_stale_14d_window` báo fail với `violations=1` (log ở `run_inject-bad.log`). Nguyên nhân là chunk policy 14 ngày làm việc lỗi thời đã lọt qua. Cách xử lý mitigation là kích hoạt fail-stop (Halt ngay hệ thống ETL, ứng cứu bằng Runbook), sau đó tiến hành chạy lại pipeline chuẩn: bật refund fix và xóa flag bỏ qua validate. Dữ liệu rác sẽ bị cô lập, tiến hành prune ở thư mục DB, cho phép snapshot hệ thống quay về `embed_upsert count=5` (hoặc 6) với dữ liệu sạch.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**
Nhóm tiến hành thực thi việc inject bad data qua flag `--no-refund-fix` và `--skip-validate` (Run ID: `sprint3-dirty` / `inject-bad`). Mục tiêu là mô phỏng rủi ro ngộ độc nguồn dữ liệu RAG, cho phép policy refund lỗi thời (14 ngày làm việc) không bị filter trực tiếp bới logic hàm xử lý, có thể tiến thẳng vô hệ thống Index (skip qua mọi Expectation validation).

**Kết quả định lượng (từ CSV / bảng):**
- **Trước khi fix (Dirty Run):** Ở file `artifacts/eval/eval_inject_bad.csv` (hay `sprint3_before_dirty.csv`), dòng hỏi về `q_refund_window` đã bị nhiễm độc ngầm, top k vector index vẫn bao hàm chunk stale cũ kĩ này, đưa ra cảnh báo `hits_forbidden=yes`. Dữ liệu bẩn sinh ra hệ lụy cho phép Agent "có cớ" nói hớ. Đáng chú ý, nhờ quy luật "Defense in Depth", record ID 3 chứa thêm tag phụ "(lỗi migration)" vẫn bị rule `contains_draft_or_error_keywords` chặn từ khâu Clean, làm giảm phần nào hậu quả.
- **Sau khi fix (Clean Run):** Khi chạy pipeline hoàn chỉnh và idempotent (`sprint2-final` hoặc `sprint3-clean`), cơ chế prune xóa các ID lỗi đã làm việc năng suất, manifest ghi nhận rule đã chặn rác. Report `sprint3_after_clean.csv` khẳng định `contains_expected=yes` toàn bộ, `hits_forbidden=no` tuyệt đối. Hệ quả định lượng ở tầng grading bằng `grading_run.jsonl` nhận được tích xanh với 3 câu trả lời đầy đủ `contains_expected=true`, đặc biệt `gq_d10_03` nhận được điểm MERIT (top1_doc_matches=true).

---

## 4. Freshness & monitoring (100–150 từ)

Trong văn bản Data Contract, nhóm cung cấp cấu hình ngưỡng đánh giá SLA quy đổi Freshness SLA là 24.0 (24h). Bằng cách kích hoạt check (`python etl_pipeline.py freshness`), cấu trúc Manifest JSON kiểm soát metric `latest_exported_at` thu thập được và đối chiếu với thời gian hiện tại của tiến trình ETL.
- **PASS:** Thời lượng trôi qua tính từ lần Export cuối vẫn nhỏ hơn thời lượng `sla_hours`. Dữ liệu an toàn lưu thông.
- **WARN:** Chuẩn bị hết hạn sử dụng. 
- **FAIL:** Khi pipeline phát hiện `age_hours` (ví dụ `120.45` giờ) đã quá lớn và ngả thành đỏ (thông báo `freshness_sla_exceeded`), quy trình RAG có thể rơi vào tình trạng đưa ra thông tin bị lỗi thời. Việc Halt sẽ ngăn Agent phục vụ nguồn dữ liệu ôi thiu.

---

## 5. Liên hệ Day 09 (50–100 từ)

Dữ liệu Embed lưu trữ tại vector db `chroma_db/` bằng collection chuyên dụng `day10_kb` đóng vai trò tối quan trọng đối với kiến trúc Data RAG Day 09. Cơ chế Embed thiết kế là dạng update IDEMPOTENT (quét sạch drop list trước khi Insert lại dữ liệu Fresh), do vậy, Vector engine sẽ hoàn toàn sạch sẽ, không lưu mồi nhử chết. Multi-Agent Day 09 có thể tham khảo trực tiếp các vector document này bằng Router để tạo luồng tư duy đúng về Policy Nhân sự và Helpdesk mà không tạo dính Hallucination do rác nghiệp vụ.

---

## 6. Rủi ro còn lại & việc chưa làm

- **Thiếu Data Masking Privacy:** Chưa triển khai che vết bảo mật PII đối với số ĐT hay CMND. Nếu lộ lọt, VectorDB sẽ trực tiếp hiển thị nó cho End user. Giải pháp nên là thay PII thành Mask `[_PII_HIDDEN_]`.
- **Hệ thống cảnh báo bị động:** Hiện đang phải dựa vào Logs để rà soát sự cố Anomaly, chưa có một Webhook thông báo về Channel Slack/Teams chuyên dụng mỗi khi Halt Fail-Stop nhảy đỏ. 
- **Auto-Eval thô sơ:** Cỗ máy Auto-Eval RAG phục thuộc quá mức bằng hardcoded Keyword Match (`hits_forbidden`, `must_contain`), chưa ứng dụng sức bật của GenAI làm LLM-as-a-Judge đánh giá sự mượt mà cấu trúc câu.
- **Docs-as-code Automation:** Lẽ ra nên phát triển tool để render file tự động thông qua pipeline (ví dụ sinh `pipeline_architecture.md` bằng Python) nhằm bắt kịp với số liệu manifest chạy liên tục.
