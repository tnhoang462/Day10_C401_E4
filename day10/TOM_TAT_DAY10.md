# Tóm tắt công việc Day 10

## Mục tiêu của Day 10

Day 10 tập trung vào **Data Pipeline & Data Observability** cho case CS + IT Helpdesk đã dùng từ Day 08 và Day 09. Mục tiêu không chỉ là làm pipeline chạy được, mà còn phải:

- ingest dữ liệu raw và map schema rõ ràng
- làm sạch dữ liệu, tách quarantine, tránh silently drop
- viết expectation suite để kiểm tra chất lượng dữ liệu
- embed/publish dữ liệu vào index theo cách **idempotent**
- đo freshness, theo dõi manifest, log và `run_id`
- chứng minh bằng **before/after evidence** rằng data tốt hơn thì retrieval/agent tốt hơn

## Các việc cần hoàn thiện

### 1. Pipeline chính

- Hoàn thiện luồng `ingest -> clean -> validate -> embed -> publish`
- Chạy được bằng một lệnh chính: `python etl_pipeline.py run`
- Log được các chỉ số tối thiểu:
  - `run_id`
  - `raw_records`
  - `cleaned_records`
  - `quarantine_records`
- Đảm bảo embed **idempotent**:
  - upsert theo `chunk_id` ổn định
  - rerun không tạo duplicate
  - xóa/prune vector cũ không còn thuộc cleaned data

### 2. Làm sạch và kiểm tra chất lượng dữ liệu

- Đọc và xử lý file raw: `lab/data/raw/policy_export_dirty.csv`
- Mở rộng tối thiểu:
  - **>= 3 cleaning rules mới**
  - **>= 2 expectation mới**
- Các rule/expectation mới phải có **tác động đo được**, không được làm kiểu hình thức
- Phân biệt rõ mức xử lý:
  - `warn`
  - `quarantine`
  - `halt`

### 3. Đánh giá before/after

- Tạo kịch bản inject corruption có chủ đích
- Chạy eval retrieval trước và sau khi fix
- Có bằng chứng cho thấy:
  - khi data xấu thì retrieval tệ hơn
  - khi data sạch lại thì retrieval tốt hơn
- Dùng:
  - `python eval_retrieval.py`
  - `python grading_run.py` nếu lớp yêu cầu grading JSONL

### 4. Monitoring và observability

- Dùng manifest để kiểm tra freshness
- Chạy:
  - `python etl_pipeline.py freshness --manifest ...`
- Giải thích được PASS/WARN/FAIL
- Có runbook cho incident và debug theo thứ tự:
  - Freshness / version
  - Volume & errors
  - Schema & contract
  - Lineage / run_id
  - Sau đó mới tới model/prompt

### 5. Docs và báo cáo

- Hoàn thiện các file docs:
  - `lab/docs/pipeline_architecture.md`
  - `lab/docs/data_contract.md`
  - `lab/docs/runbook.md`
  - `lab/docs/quality_report.md` hoặc file theo template
- Hoàn thiện báo cáo:
  - `lab/reports/group_report.md`
  - `lab/reports/individual/*.md`
- README nhóm cần có phần hướng dẫn chạy bằng **một lệnh**

## 4 sprint cần hoàn thành

### Sprint 1 - Ingest & Schema

- Đọc raw CSV
- Xác định source map trong `docs/data_contract.md`
- Chạy pipeline lần đầu với `run_id`
- Kiểm tra log đầu ra

**DoD**
- Có `run_id`
- Có `raw_records`, `cleaned_records`, `quarantine_records`

### Sprint 2 - Clean + Validate + Embed

- Hoàn thiện cleaning rules
- Viết thêm expectation
- Đảm bảo pipeline chuẩn chạy `exit 0`
- Đảm bảo embed idempotent

**DoD**
- `python etl_pipeline.py run` chạy thành công
- Không bị halt ngoài ý muốn
- Index phản ánh đúng cleaned data

### Sprint 3 - Inject Corruption & Before/After

- Cố ý làm hỏng dữ liệu để tạo tình huống lỗi
- Chạy eval ở trạng thái xấu và trạng thái đã fix
- Lưu evidence bằng CSV/log/screenshot có gắn `run_id`

**DoD**
- Có bằng chứng before/after rõ ràng
- Chứng minh retrieval xấu đi khi inject và cải thiện sau khi fix

### Sprint 4 - Monitoring + Docs + Report

- Hoàn thiện freshness check
- Viết runbook
- Hoàn thiện architecture, contract, group report, individual report
- Chuẩn bị peer review/demo

**DoD**
- Docs đủ
- Báo cáo đủ
- Có giải thích freshness PASS/WARN/FAIL
- Có hướng dẫn chạy rõ ràng

## Deliverables cần nộp

- Code pipeline:
  - `etl_pipeline.py`
  - `transform/`
  - `quality/`
  - `monitoring/`
- Contract:
  - `contracts/data_contract.yaml`
- Artifact:
  - `artifacts/logs/`
  - `artifacts/manifests/`
  - `artifacts/quarantine/`
  - `artifacts/eval/`
- Docs:
  - `pipeline_architecture.md`
  - `data_contract.md`
  - `runbook.md`
  - `quality_report.md`
- Reports:
  - `group_report.md`
  - `individual/*.md`
- Nếu có grading:
  - `artifacts/eval/grading_run.jsonl`

## Tiêu chí hoàn thành quan trọng

- Pipeline chạy được và reproducible
- Có `run_id` và log đủ để truy vết
- Có quality gate thật, không làm hình thức
- Có evidence before/after rõ ràng
- Có monitoring freshness và runbook xử lý sự cố
- Có docs và báo cáo khớp với artifact/code

## Gợi ý thứ tự làm

1. Chạy pipeline baseline để hiểu artifact hiện có
2. Bổ sung cleaning rules và expectations
3. Kiểm tra idempotency khi rerun
4. Inject corruption để tạo case before/after
5. Hoàn thiện freshness, runbook, docs, report

