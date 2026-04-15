# Technical Guide - Hoàn thiện `etl_pipeline.py`

## Mục đích tài liệu

Tài liệu này hướng dẫn nhóm **hoàn thiện `etl_pipeline.py`** theo đúng tinh thần Day 10, nhưng **không sửa trực tiếp file**. Mục tiêu là để các thành viên đọc, chia việc, và triển khai thống nhất.

Nếu trong nhóm đang gọi file này là `etl_pipe.py`, hãy hiểu đây là cùng một vai trò: **ETL entrypoint điều phối ingest -> clean -> validate -> embed -> observe**.

File tham chiếu chính:
- `day10/lab/etl_pipeline.py`
- `day10/lab/transform/cleaning_rules.py`
- `day10/lab/quality/expectations.py`
- `day10/lab/monitoring/freshness_check.py`

---

## 1. Vai trò của `etl_pipeline.py`

`etl_pipeline.py` không nên chứa toàn bộ business logic chi tiết. Nó nên đóng vai trò:

- nhận lệnh CLI
- kiểm tra input và môi trường
- gọi đúng thứ tự các bước pipeline
- ghi log và artifact
- quyết định khi nào halt, khi nào tiếp tục
- tạo manifest cho observability

Nói ngắn gọn: file này là **orchestrator của lab**, không phải nơi viết hết mọi rule.

---

## 2. Luồng chuẩn cần có

Luồng chuẩn của pipeline nên giữ đúng thứ tự sau:

1. Nhận tham số CLI
2. Xác định `run_id`
3. Đọc raw data
4. Chạy cleaning rules
5. Ghi cleaned CSV và quarantine CSV
6. Chạy expectation suite
7. Nếu pass thì embed/publish
8. Ghi manifest
9. Chạy freshness check
10. Kết thúc với exit code rõ ràng

Không nên đảo thứ tự `validate` và `embed`, vì Day 10 cần chứng minh rằng dữ liệu phải được kiểm soát trước khi publish.

---

## 3. Trách nhiệm của từng phần trong file

### 3.1. CLI layer

Phần CLI nên chỉ làm các việc sau:

- định nghĩa subcommand như `run`, `freshness`
- parse flag như `--raw`, `--run-id`, `--skip-validate`
- route sang đúng function

Không nên đặt business rule tại đây.

Checklist hoàn thiện:

- tên subcommand rõ và ngắn
- help text đủ để người khác chạy không phải đọc code
- có exit code nhất quán

### 3.2. `cmd_run()`

Đây là luồng chính. Hàm này nên:

- sinh hoặc nhận `run_id`
- kiểm tra raw file tồn tại
- chuẩn bị thư mục artifact
- tạo logger thống nhất
- gọi lần lượt:
  - `load_raw_csv()`
  - `clean_rows()`
  - `write_cleaned_csv()`
  - `write_quarantine_csv()`
  - `run_expectations()`
  - `cmd_embed_internal()`
  - `check_manifest_freshness()`

Checklist hoàn thiện:

- mọi bước đều log được số liệu chính
- mọi artifact đều gắn `run_id`
- mọi nhánh fail đều return code rõ ràng

### 3.3. `cmd_embed_internal()`

Hàm này chỉ nên chịu trách nhiệm publish cleaned data sang vector store.

Nó nên làm:

- load cleaned CSV
- kết nối Chroma
- tạo collection nếu chưa có
- prune dữ liệu cũ không còn hợp lệ
- upsert dữ liệu mới bằng `chunk_id`
- log số record được embed

Không nên nhúng cleaning hoặc expectation vào đây.

### 3.4. `cmd_freshness()`

Đây là operational command riêng. Mục đích:

- đọc manifest đã tạo trước đó
- tính freshness theo SLA
- trả PASS/WARN/FAIL

Lệnh này phải chạy độc lập với `run`, để phục vụ check sau pipeline hoặc demo.

---

## 4. Những phần nhóm cần hoàn thiện thêm

Hiện tại file đã chạy được baseline. Việc “hoàn thiện” nên hiểu là làm cho pipeline:

- đúng hơn
- rõ hơn
- đo được hơn
- ổn định hơn

Các hạng mục nên ưu tiên:

### 4.1. Chuẩn hóa log

Hiện log đang là plain text theo dòng, đây là đủ cho lab. Tuy nhiên nhóm nên thống nhất format để dễ đọc và đối chiếu.

Nên log tối thiểu:

- `run_id`
- `raw_records`
- `cleaned_records`
- `quarantine_records`
- tên file artifact sinh ra
- kết quả từng expectation
- `embed_upsert count`
- `embed_prune_removed`
- `manifest_written`
- `freshness_check`
- trạng thái cuối `PIPELINE_OK` hoặc `PIPELINE_HALT`

Nếu muốn nâng cấp:

- thêm stage marker như `stage=clean`, `stage=validate`, `stage=embed`
- thêm elapsed time cho từng bước

### 4.2. Exit code rõ ràng

Hiện file đang có phân biệt:

- `1`: lỗi input / file không tồn tại
- `2`: expectation halt
- `3`: lỗi embed

Nhóm nên giữ nguyên tinh thần này, và nếu mở rộng thì phải document rõ trong README hoặc doc nhóm.

Không nên để mọi lỗi đều trả cùng một mã, vì rất khó debug khi chấm bài hoặc CI.

### 4.3. Tách phần cấu hình qua `.env`

Những cấu hình nên tiếp tục giữ ở env:

- `CHROMA_DB_PATH`
- `CHROMA_COLLECTION`
- `EMBEDDING_MODEL`
- `FRESHNESS_SLA_HOURS`

Nếu nhóm thêm config mới, ưu tiên thêm vào `.env.example` thay vì hard-code trong file.

Ví dụ config có thể bổ sung:

- `PIPELINE_LOG_LEVEL`
- `QUARANTINE_THRESHOLD`
- `ALLOW_EMPTY_EXPORT`
- `PUBLISH_MODE=snapshot|append`

### 4.4. Làm rõ publish boundary

Một điểm quan trọng của Day 10 là “pipeline chạy xong” chưa chắc đồng nghĩa với “agent đọc đúng dữ liệu”.

Vì vậy nhóm nên giữ rõ ranh giới:

- cleaned CSV là artifact sau transform
- Chroma collection là serving/index boundary
- manifest là bằng chứng một run đã publish cái gì

Nếu sửa `etl_pipeline.py`, không nên làm mờ ba boundary này.

### 4.5. Củng cố idempotency

Đây là điểm kỹ thuật quan trọng nhất.

Mục tiêu:

- rerun cùng dữ liệu không làm collection phình ra
- vector cũ không còn thuộc cleaned snapshot phải bị xóa
- một `chunk_id` phải đại diện ổn định cho một chunk

Nhóm cần rà soát:

- `chunk_id` có thật sự ổn định khi thứ tự input thay đổi không
- logic prune có đủ an toàn không
- rerun hai lần liên tiếp có cho cùng kết quả không

Gợi ý kỹ thuật:

- tránh để `chunk_id` phụ thuộc quá nhiều vào `seq`
- ưu tiên hash từ `doc_id + normalized_chunk_text + effective_date`
- log thêm số lượng id trước và sau prune nếu cần chứng minh idempotency

### 4.6. Tăng độ chặt của manifest

Manifest hiện là trung tâm của observability trong lab. Nhóm nên coi đây là “run summary” chính thức.

Có thể mở rộng manifest với:

- `expectation_summary`
- `halted`
- `embed_count`
- `embed_prune_removed`
- `raw_hash` hoặc `cleaned_hash`
- `pipeline_version`

Mục tiêu là khi nhìn một manifest, người khác hiểu được run đó đã:

- đọc gì
- làm sạch ra sao
- publish bao nhiêu
- có bỏ qua validate hay không

---

## 5. Những phần không nên nhét vào `etl_pipeline.py`

Đây là lỗi nhóm rất dễ mắc khi hoàn thiện bài.

Không nên nhét trực tiếp vào file orchestrator:

- toàn bộ cleaning rules chi tiết
- toàn bộ expectation logic
- toàn bộ query eval
- logic báo cáo nhóm
- business rule rải rác không có module riêng

Nên giữ phân tách như sau:

- `etl_pipeline.py`: orchestration
- `transform/cleaning_rules.py`: transform logic
- `quality/expectations.py`: validation logic
- `monitoring/freshness_check.py`: monitoring logic

Lý do:

- dễ review
- dễ test
- dễ phân vai
- tránh file `etl_pipeline.py` thành “god file”

---

## 6. Definition of Done cho `etl_pipeline.py`

Một bản hoàn thiện đạt yêu cầu nên thỏa các điều sau:

### Bắt buộc

- `python etl_pipeline.py run` chạy được với dữ liệu chuẩn
- sinh ra log, cleaned CSV, quarantine CSV, manifest
- expectation halt hoạt động đúng
- embed hoạt động đúng và có prune dữ liệu cũ
- `python etl_pipeline.py freshness --manifest ...` chạy độc lập được

### Nên có

- log dễ đọc
- config nằm ở `.env`
- code tách vai trò rõ
- exit code nhất quán
- giải thích được luồng chạy từ CLI đến manifest

### Không đạt nếu

- pipeline chỉ chạy được trên máy một người
- rerun làm duplicate vector
- expectation fail nhưng không ai biết vì sao
- artifact sinh ra không gắn `run_id`
- freshness chỉ đo thời điểm chạy thay vì timestamp dữ liệu

---

## 7. Phân công đề xuất cho nhóm

### Thành viên 1 - Orchestration owner

Chịu trách nhiệm:

- `etl_pipeline.py`
- CLI
- log
- exit code
- manifest

Deliverable:

- luồng `run` và `freshness` rõ ràng
- README có lệnh chạy chuẩn

### Thành viên 2 - Cleaning owner

Chịu trách nhiệm:

- `transform/cleaning_rules.py`
- cleaned/quarantine shape
- `chunk_id` strategy

Deliverable:

- thêm rule mới
- có giải thích metric impact

### Thành viên 3 - Quality owner

Chịu trách nhiệm:

- `quality/expectations.py`
- severity `warn` / `halt`
- chứng minh expectation bắt đúng lỗi inject

Deliverable:

- thêm expectation mới
- có before/after evidence

### Thành viên 4 - Embed & Monitoring owner

Chịu trách nhiệm:

- Chroma publish
- idempotency
- prune
- freshness

Deliverable:

- rerun an toàn
- freshness report đúng

---

## 8. Quy trình review trước khi merge

Trước khi merge thay đổi liên quan `etl_pipeline.py`, nhóm nên review theo checklist này:

1. Chạy `python etl_pipeline.py run`
2. Kiểm tra log có đủ key chính
3. Kiểm tra cleaned/quarantine CSV được sinh ra
4. Kiểm tra manifest có đủ field
5. Chạy lại lần hai với cùng dữ liệu
6. Xác minh collection không bị duplicate
7. Chạy `freshness` trên manifest vừa tạo
8. Chạy case inject corruption
9. Kiểm tra expectation halt hoặc skip-validate đúng hành vi mong muốn

Nếu thiếu bước 5 hoặc 8 thì chưa chứng minh được Day 10 đầy đủ.

---

## 9. Rủi ro kỹ thuật cần lưu ý

### 9.1. `chunk_id` không thật sự ổn định

Nếu `chunk_id` phụ thuộc vào thứ tự record, rerun với input reorder có thể tạo id mới và làm hỏng ý tưởng idempotent.

### 9.2. Manifest không phản ánh đúng dữ liệu publish

Nếu manifest ghi thiếu hoặc ghi sai timestamp, freshness check sẽ vô nghĩa.

### 9.3. Skip validate bị dùng sai mục đích

`--skip-validate` chỉ nên dùng cho demo inject corruption, không phải lối tắt để bài “chạy cho xong”.

### 9.4. Embed fail nhưng log không đủ

Nếu Chroma hoặc model embedding lỗi mà không log rõ config/path/model, rất khó debug trong giờ chấm.

### 9.5. Boundary ingest và publish bị nhập nhằng

Pipeline có thể ingest thành công nhưng publish thất bại. Hai trạng thái này phải được log và thể hiện tách biệt.

---

## 10. Khuyến nghị cuối cùng

Khi hoàn thiện `etl_pipeline.py`, nhóm nên giữ nguyên nguyên tắc:

- file này là orchestrator
- module khác mới chứa chi tiết rule
- mọi bước đều phải để lại evidence
- ưu tiên reproducibility hơn “chạy nhanh một lần”

Tiêu chí Day 10 không phải chỉ là “có vector DB”, mà là:

- biết dữ liệu nào đã được publish
- biết khi nào dữ liệu stale
- biết vì sao pipeline fail
- rerun an toàn
- chứng minh được trước và sau khi fix dữ liệu

---

## 11. Lệnh kiểm tra tối thiểu sau khi hoàn thiện

```bash
python etl_pipeline.py run
python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run-id>.json
python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
python eval_retrieval.py --out artifacts/eval/before_after_eval.csv
```

Nếu 4 lệnh này không kể được một câu chuyện hoàn chỉnh về pipeline, thì `etl_pipeline.py` vẫn chưa thật sự hoàn thiện.

