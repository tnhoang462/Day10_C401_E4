# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Nhật Hoàng 
**Vai trò:** Expectation Suite + Embed Chroma (idempotent)  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** 400–650 từ

> Ghi chú: phần dưới đây được tổng hợp từ các thay đổi đang có trong workspace và các artifact/log hiện tại của nhóm.

## 1. Tôi phụ trách phần nào?

Trong Sprint 2, tôi phụ trách phần chính là mở rộng **expectation suite** và kiểm tra cơ chế **embed Chroma idempotent**. Ở lớp quality, tôi bổ sung thêm 3 expectation mới trong `quality/expectations.py`: `min_unique_doc_id_coverage` (warn) để phát hiện tập dữ liệu clean quá lệch về một loại tài liệu, `no_placeholder_in_cleaned` (halt) để chặn trường hợp nội dung kiểu `TBD`, `placeholder`, `please update` lọt vào cleaned CSV, và `unique_chunk_ids` (halt) để đảm bảo không có `chunk_id` trùng lặp – tiền đề bắt buộc để cơ chế idempotent embed hoạt động chính xác. Ở lớp embed, tôi kiểm tra `cmd_embed_internal()` trong `etl_pipeline.py` để xác nhận collection `day10_kb` đang chạy đúng mô hình snapshot publish: lấy toàn bộ `chunk_id` hiện tại, prune ID không còn trong cleaned run, rồi `upsert` lại theo `chunk_id`.

Các file tôi đã thay đổi hoặc chạm tới sát với phần việc này là:

- `day10/lab/quality/expectations.py`
- `day10/lab/etl_pipeline.py`
- `day10/lab/docs/pipeline_architecture.md`
- `day10/lab/docs/runbook.md`

Nếu tính toàn bộ workspace hiện đang có sửa đổi, còn có thêm `transform/cleaning_rules.py`, `contracts/data_contract.yaml`, `docs/data_contract.md`; tuy nhiên đó không phải trọng tâm chính của phần tôi nhận trong Sprint 2.

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là giữ cơ chế embed theo hướng **idempotent + publish boundary rõ ràng** thay vì chỉ append vector mới. Trong `etl_pipeline.py`, collection được lấy bằng `get_or_create_collection`, sau đó pipeline đọc toàn bộ `ids` hiện có, tính tập `drop = prev_ids - cleaned_ids`, gọi `col.delete(ids=drop)`, rồi mới `col.upsert(ids=ids, ...)`. Cách này giải quyết đúng lỗi quan sát được trong RAG là chunk stale vẫn còn trong top-k dù dữ liệu đã được clean ở lần chạy sau.

Bằng chứng từ `artifacts/logs/run_sprint2-final.log` cho thấy cơ chế này hoạt động: `embed_prune_removed=1` và `embed_upsert count=6 collection=day10_kb`. Điều này khớp với manifest `manifest_sprint2-final.json` có `cleaned_records=6`. Tôi chọn để `min_unique_doc_id_coverage` ở mức `warn`, còn `no_placeholder_in_cleaned` và `unique_chunk_ids` ở mức `halt`, vì mất coverage chưa chắc sai dữ liệu, nhưng placeholder hay trùng lặp chunk trong cleaned là lỗi cấu trúc và chất lượng nghiêm trọng trước khi publish.

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly tôi tập trung xử lý là trường hợp expectation pass không đủ để bảo vệ chất lượng retrieval nếu cleaned data vẫn chứa nội dung nháp hoặc collection còn vector cũ. Với bộ `sprint2-extra`, log cho thấy `raw_records=4`, `cleaned_records=1`, `quarantine_records=3`, và expectation `min_unique_doc_id_coverage` báo `FAIL (warn) :: unique_doc_ids=1`. Tín hiệu này giúp phát hiện bộ export quá hẹp, tránh tưởng rằng pipeline “ổn” chỉ vì không halt.

Mặt khác, tôi thêm expectation `no_placeholder_in_cleaned` để chặn tình huống chunk kiểu “TBD placeholder. Please update.” lọt qua cleaning và bị embed. Đây là một expectation dạng halt vì nếu để lọt vào vector DB thì lỗi sẽ chuyển từ tầng data sang tầng retrieval và khó debug hơn. Đồng thời, expectation `unique_chunk_ids` (E9) cũng được thêm vào để giám sát anomaly về trùng lặp định danh. Nếu có bất kỳ `chunk_id` nào trùng nhau lọt qua, pipeline sẽ halt ngay lập tức để bảo vệ tính toàn vẹn cho vòng lặp `upsert` idempotent của ChromaDB.

## 4. Bằng chứng trước / sau

Tôi dùng cặp run `inject-bad` và `sprint2-final` để chứng minh phần mình làm có tác động. Trong `run_inject-bad.log`, expectation `refund_no_stale_14d_window` báo `FAIL (halt) :: violations=1`, nhưng do chạy với `--skip-validate` nên pipeline vẫn embed để làm before-state. Ở `artifacts/eval/eval_inject_bad.csv`, dòng `q_refund_window` có `contains_expected=yes` nhưng `hits_forbidden=yes`, nghĩa là top-k vẫn còn chunk stale.

Sau khi chạy lại clean pipeline bằng `run_id=sprint2-final`, log chuyển thành `expectation[no_placeholder_in_cleaned] OK (halt) :: placeholder_chunks=0` và `embed_upsert count=6`. Trong `artifacts/eval/eval_after_clean.csv`, dòng `q_refund_window` đổi từ `hits_forbidden=yes` sang `hits_forbidden=no`. Đây là bằng chứng rõ nhất cho việc expectation suite và embed idempotent đang hỗ trợ nhau đúng mục tiêu Sprint 2.

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi muốn tách expectation ra thành nhóm `content`, `coverage`, `schema`, rồi ghi kết quả có cấu trúc vào manifest JSON thay vì chỉ log text. Như vậy Sprint 3 và Sprint 4 sẽ dễ làm dashboard hoặc alert hơn, đồng thời giúp peer review đọc được ngay expectation nào fail, ở mức warn hay halt, mà không cần mở log thủ công.
