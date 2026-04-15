# Báo Cáo Cá Nhân: Lab Day 10 Data Pipeline & Observability

**Họ và tên:** Trương Đăng Gia Huy  
**Vai trò:** Monitoring / Docs Owner (docs/pipeline_architecture.md)  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** 400–650 từ

---

## 1. Em phụ trách phần nào?

Phần em làm trong Sprint 4 là file `docs/pipeline_architecture.md` cho nhóm E4. Nhưng trước khi gõ được chữ nào, em phải ngồi nghe hai bạn trong nhóm giải thích lại toàn bộ pipeline thì mới viết được đầy đủ.

Em hỏi bạn Mong tại sao rule 14 ngày cứ phải match string cứng chứ không dùng regex, rồi bạn mở `cleaning_rules.py:146` cho em xem chỗ replace literal. Em hỏi bạn Hoàng tại sao phải prune trước khi upsert, bạn dẫn em vào `etl_pipeline.py:158-162` giải thích nếu không xoá id cũ thì vector stale vẫn còn trong top-k, kiểu mồi cũ. Em cũng ngồi đọc `monitoring/freshness_check.py` để biết pipeline đo freshness ở đâu, và thấy rằng nó chỉ đọc `latest_exported_at` trong manifest chứ không check watermark DB nguồn.

Sau khi nắm được kiến trúc rồi em mới bắt đầu viết. Em vẽ Mermaid `flowchart TD` thể hiện luồng ingest → clean → validate → embed, có tách nhánh quarantine, gate halt, freshness probe và kết nối xuống `day09/lab`. Bảng ranh giới trách nhiệm em điền input output đúng theo module hai bạn đang giữ. Phần idempotency em dẫn `_stable_chunk_id` ở `cleaning_rules.py:38-40`, upsert + prune ở `etl_pipeline.py:158-175`, và expectation E9 `unique_chunk_ids` của bạn Hoàng. Cuối cùng là 7 rủi ro, mỗi cái gắn với một chỗ cụ thể trong repo.

## 2. Một quyết định kỹ thuật

Quyết định lớn nhất của em là không viết rủi ro theo kiểu slide chung chung. Ban đầu em định gõ kiểu "cần monitor data drift" hay "nên tăng coverage test", vừa nhanh vừa kín trang. Nhưng đọc lại rubric `SCORING.md:106` thì thấy ghi rõ paraphrase slide sẽ bị chấm 0 cho mục đó, mà bản thân em cũng thấy kiểu viết đó reviewer chẳng verify được.

Em đổi hướng: mỗi bullet phải gắn với code thật. Ví dụ thay vì viết "HR stale có thể lọt", em ghi rule phụ thuộc `doc_id == "hr_leave_policy"` và ngày `< 2026-01-01` tại `cleaning_rules.py:108`, lưới an toàn là E6 `hr_leave_no_stale_10d_annual`. Trade-off là sau này ai refactor code thì số dòng sẽ lệch và docs phải update theo. Nhưng đổi lại reviewer verify được trong hai giây, và chính áp lực giữ docs đồng bộ với code mới đúng với tinh thần observability mà lab này đang dạy.

## 3. Một lỗi hoặc anomaly đã xử lý

Lỗi đáng nhớ nhất là render sơ đồ Mermaid. Lúc đầu em muốn label xuống dòng cho gọn nên dùng `<br/>`, kiểu `"data/raw/<br/>policy_export_dirty.csv"`. Nhưng markdown preview em dùng lại không parse tag đó, mà in ra nguyên văn `<br/>` lẫn trong tên file, cả 13 node đều dính. Trông cực kỳ xấu.

Cách fix đơn giản: bỏ `<br/>` đi, flatten label về một dòng rồi tách phần phụ bằng ngoặc tròn. Ví dụ `"load_raw_csv<br/>log: raw_records"` đổi thành `"load_raw_csv (log raw_records)"`. Render lại thì toàn bộ 13 node hiển thị sạch, phần diagram sau khi fix nằm ở lines 12-27 của file. Bài học rút ra là đừng giả định renderer markdown nào cũng cho phép HTML; giữ label đơn giản là an toàn nhất.

## 4. Bằng chứng trước / sau

Trước khi em chạm vào, file dài 45 dòng. Bảng ranh giới 5 dòng đều blank, sơ đồ chỉ là một dòng ASCII `raw → clean → validate → embed → serving`, phần rủi ro có mỗi một dấu gạch đầu dòng rỗng.

Sau khi viết xong, file lên khoảng 90 dòng, Mermaid render đúng, bảng 5 dòng đều có input output thật. Số liệu em trích từ `artifacts/manifests/manifest_2026-04-15T09-07Z.json`: `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`, `latest_exported_at=2026-04-10T08:00:00`, collection `day10_kb`. Bốn lý do quarantine khớp với `quarantine_2026-04-15T09-07Z.csv`: `duplicate_chunk_text`, `missing_effective_date`, `stale_hr_policy_effective_date`, `unknown_doc_id`.

## 5. Cải tiến tiếp theo

Nếu có thêm 2 tiếng, em muốn viết script nhỏ kiểu `docs/generate_diagram.py` đọc manifest mới nhất và kết quả expectation, tự sinh Mermaid block và bullet rủi ro. Như vậy docs luôn đồng bộ với run gần nhất, không phải sửa tay mỗi sprint, tránh được chuyện tài liệu rot dần khi code đổi.
