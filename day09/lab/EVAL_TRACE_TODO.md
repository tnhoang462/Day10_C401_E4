# Hướng Dẫn Hoàn Thiện `eval_trace.py`

## Mục tiêu của file này

`eval_trace.py` là script để:

- chạy batch câu hỏi test
- lưu trace cho từng run
- sinh file grading log
- đọc trace để tính metrics
- so sánh Day 08 và Day 09

Hiện tại file này **đã có khung chạy được**, nhưng vẫn còn một số phần chưa hoàn chỉnh nếu mục tiêu là:

- nộp bài đúng rubric
- có số liệu thật để điền vào docs
- so sánh Day 08 vs Day 09 có ý nghĩa
- debug được pipeline khi trả lời sai

---

## 1. `eval_trace.py` hiện đã làm được gì?

### 1.1 `run_test_questions()`

Đã làm được:

- đọc `data/test_questions.json`
- gọi `run_graph(question_text)`
- lưu trace từng câu vào `artifacts/traces/`
- gom thông tin cơ bản như `id`, `question`, `expected_answer`, `expected_sources`, `difficulty`, `category`

### 1.2 `run_grading_questions()`

Đã làm được:

- đọc `data/grading_questions.json` nếu file đã tồn tại
- chạy pipeline cho từng câu
- ghi `artifacts/grading_run.jsonl`
- lưu các field quan trọng như:
  - `id`
  - `question`
  - `answer`
  - `sources`
  - `supervisor_route`
  - `route_reason`
  - `workers_called`
  - `mcp_tools_used`
  - `confidence`
  - `hitl_triggered`
  - `latency_ms`
  - `timestamp`

### 1.3 `analyze_traces()`

Đã làm được:

- đọc các trace `.json`
- tính:
  - `routing_distribution`
  - `avg_confidence`
  - `avg_latency_ms`
  - `mcp_usage_rate`
  - `hitl_rate`
  - `top_sources`

### 1.4 `compare_single_vs_multi()`

Đã có khung:

- lấy metrics của Day 09
- tạo object compare
- có chỗ để load baseline Day 08 từ file JSON nếu có

---

## 2. Những phần còn thiếu cần hoàn thiện

## 2.1 Chưa chấm kết quả model so với expected answer

Đây là thiếu sót lớn nhất.

Hiện tại `run_test_questions()` chỉ chạy pipeline và lưu kết quả, nhưng chưa đánh giá:

- câu trả lời có đúng không
- source có khớp không
- route có đúng với kỳ vọng không
- câu abstain có xử lý đúng không

### Cần làm

Thêm một bước scoring cho từng câu hỏi test, ví dụ:

- `answer_match`: đúng / một phần / sai
- `source_match`: có lấy đúng tài liệu kỳ vọng không
- `route_match`: `supervisor_route` có khớp `expected_route` không
- `abstain_ok`: với câu loại abstain, hệ có từ chối đúng cách không

### Vì sao cần

Nếu không có scoring thật thì:

- `eval_trace.py` chỉ là runner, chưa phải evaluator
- bạn không có số liệu thật để điền `docs/single_vs_multi_comparison.md`
- khó chứng minh pipeline tốt hơn sau khi sửa

---

## 2.2 Chưa có hàm đánh giá theo loại câu hỏi

Bộ `test_questions.json` có nhiều loại:

- `single_worker`
- `abstain`
- `temporal_scoping`
- `multi_worker`
- `multi_worker_multi_doc`
- `multi_detail`

Nhưng `eval_trace.py` chưa tận dụng `test_type`.

### Cần làm

Viết logic evaluate riêng theo từng loại:

- `single_worker`: check answer và source
- `abstain`: check answer có nêu không đủ thông tin, không hallucinate
- `temporal_scoping`: check answer có nhắc đúng việc policy v3 chưa có tài liệu
- `multi_worker`: check có dùng đủ worker cần thiết
- `multi_worker_multi_doc`: check có đủ nhiều nguồn và đủ 2 phần của câu trả lời
- `multi_detail`: check đủ nhiều chi tiết trong answer

### Vì sao cần

Không phải câu nào cũng chấm theo cùng một tiêu chí.

Ví dụ:

- câu abstain không cần answer cụ thể, nhưng cần từ chối đúng
- câu multi-hop không chỉ cần đúng một ý, mà phải đủ các ý

---

## 2.3 Chưa có accuracy metrics thật

`analyze_traces()` hiện chưa tính:

- accuracy
- route accuracy
- source recall
- abstain rate thật
- hallucination count
- multi-hop accuracy

### Cần làm

Thêm các metrics như:

- `answer_accuracy`
- `route_accuracy`
- `source_match_rate`
- `abstain_success_rate`
- `multi_hop_success_rate`
- `hallucination_risk_cases`

### Gợi ý

Nếu chưa có LLM-as-judge, có thể làm phiên bản đơn giản:

- so khớp keyword
- so khớp source filenames
- so khớp route
- check câu trả lời có chứa các ý bắt buộc

---

## 2.4 `compare_single_vs_multi()` vẫn là placeholder

Đây là phần chưa hoàn thiện rõ nhất.

Hiện tại:

- Day 09 có lấy metrics từ trace
- Day 08 baseline vẫn đang là:
  - `avg_confidence = 0.0`
  - `avg_latency_ms = 0`
  - `abstain_rate = ?`
  - `multi_hop_accuracy = ?`

### Cần làm

Có 2 hướng:

### Hướng 1: Có baseline Day 08 thật

- chạy Day 08 eval
- lưu kết quả ra 1 file JSON
- truyền file đó vào `compare_single_vs_multi(day08_results_file=...)`

### Hướng 2: Nếu chưa có baseline thật

- ghi rõ `N/A`
- thêm explanation rằng chưa có dữ liệu Day 08 tương ứng

### Vì sao cần

Nếu không làm phần này:

- file compare chỉ có hình thức, không có giá trị phân tích
- không đủ dữ liệu để điền `docs/single_vs_multi_comparison.md`

---

## 2.5 Chưa sinh dữ liệu đủ để điền 3 file docs

Rubric Day 09 yêu cầu:

- `docs/system_architecture.md`
- `docs/routing_decisions.md`
- `docs/single_vs_multi_comparison.md`

Hiện `eval_trace.py` mới chỉ hỗ trợ một phần cho 2 file sau, nhưng chưa xuất dữ liệu theo format dễ điền.

### Cần làm

Thêm các output trung gian như:

- top 3 routing cases tiêu biểu
- danh sách câu route sai
- distribution số câu vào từng worker
- câu nào có MCP call
- câu nào trigger HITL
- câu nào là multi-hop thành công/thất bại

### Vì sao cần

Khi đó nhóm chỉ cần lấy dữ liệu thật từ report thay vì đọc từng trace file thủ công.

---

## 2.6 Chưa kiểm tra đầy đủ format trace bắt buộc

`SCORING.md` yêu cầu trace phải có các trường bắt buộc.

Hiện tại `eval_trace.py` ghi log, nhưng chưa có hàm validate trace schema.

### Cần làm

Viết một hàm như `validate_trace_record(record)` để kiểm tra:

- có `supervisor_route`
- có `route_reason`
- có `workers_called`
- có `confidence`
- có `timestamp`
- `route_reason` không rỗng
- `workers_called` là list

### Vì sao cần

Nếu trace thiếu field:

- có thể mất điểm dù answer đúng
- bạn chỉ phát hiện lỗi rất muộn khi gần deadline

---

## 2.7 Chưa tận dụng `expected_sources` để kiểm tra grounding

Hiện pipeline lưu `retrieved_sources`, nhưng `eval_trace.py` chưa đo:

- có retrieve đúng nguồn không
- synthesis có dùng đúng nguồn mong đợi không

### Cần làm

Thêm kiểm tra:

- `expected_sources` giao với `retrieved_sources` bao nhiêu
- với câu multi-doc, có đủ cả 2 nguồn không

### Ý nghĩa

Đây là chỉ số rất quan trọng cho bài Day 09, vì hệ multi-agent không chỉ cần answer đúng mà còn phải grounded.

---

## 2.8 Chưa có summary report đủ chi tiết

`save_eval_report()` hiện chỉ lưu object compare, nhưng nội dung report còn mỏng.

### Cần làm

Mở rộng `artifacts/eval_report.json` để có:

- metrics tổng quát
- per-question results
- failed cases
- route mismatch cases
- source mismatch cases
- abstain cases
- recommended fixes

### Vì sao cần

Một report tốt giúp:

- debug nhanh
- điền docs nhanh
- chứng minh cải tiến của nhóm rõ hơn

---

## 3. Thứ tự hoàn thiện hợp lý

Không nên sửa ngẫu nhiên. Thứ tự nên là:

### Bước 1. Thêm evaluation per question

Làm trước các hàm:

- `evaluate_answer(...)`
- `evaluate_sources(...)`
- `evaluate_route(...)`
- `evaluate_case(...)`

Mục tiêu là mỗi câu hỏi sau khi chạy xong đều có một object đánh giá.

### Bước 2. Thêm aggregate metrics

Từ per-question evaluation, tính:

- answer accuracy
- route accuracy
- source match rate
- abstain success rate
- multi-hop success rate

### Bước 3. Thêm trace schema validation

Viết `validate_trace_record(...)` để bắt lỗi field thiếu trước khi nộp.

### Bước 4. Nâng cấp compare Day 08 vs Day 09

- load baseline thật nếu có
- nếu chưa có thì ghi `N/A` rõ ràng

### Bước 5. Nâng cấp eval report

Xuất file report giàu dữ liệu hơn để hỗ trợ viết docs và report nhóm.

---

## 4. Gợi ý cấu trúc công việc cụ thể

Bạn có thể xem `eval_trace.py` còn thiếu theo checklist này:

### Phần bắt buộc nên làm

- chấm đúng/sai cho từng câu test
- chấm route đúng/sai
- chấm source đúng/sai
- validate trace format
- tính accuracy metrics thật
- ghi failed cases vào report

### Phần rất nên làm

- phân loại câu theo `test_type`
- đo multi-hop success
- đo abstain success
- xuất routing cases tiêu biểu

### Phần nâng cao

- dùng LLM-as-judge để chấm answer mềm hơn
- tính semantic similarity thay vì keyword match
- auto-generate draft cho `docs/routing_decisions.md`
- auto-generate draft cho `docs/single_vs_multi_comparison.md`

---

## 5. Output lý tưởng sau khi hoàn thiện

Sau khi hoàn thiện, chạy:

```bash
python eval_trace.py
```

nên cho ra:

- trace từng câu trong `artifacts/traces/`
- `artifacts/eval_report.json` có:
  - metrics tổng
  - đánh giá từng câu
  - câu sai
  - câu route sai
  - câu thiếu source
  - câu abstain đúng/sai
  - câu multi-hop đúng/sai

và chạy:

```bash
python eval_trace.py --grading
```

nên đảm bảo:

- sinh `artifacts/grading_run.jsonl`
- mọi record đều đúng schema theo `SCORING.md`

---

## 6. Tóm tắt ngắn gọn

`eval_trace.py` hiện đã là:

- runner tốt
- trace analyzer cơ bản
- grading log generator

Nhưng nó chưa hoàn chỉnh ở vai trò:

- evaluator thật
- comparator thật giữa Day 08 và Day 09
- nguồn dữ liệu đủ mạnh để điền docs/rubric

## Việc quan trọng nhất cần làm trước

1. thêm đánh giá đúng/sai cho từng câu
2. thêm metrics accuracy thật
3. validate trace schema trước khi nộp
4. hoàn thiện compare Day 08 vs Day 09 bằng số liệu thật hoặc `N/A` có giải thích

---

## 7. Kết luận thực dụng

Nếu chỉ có ít thời gian, hãy ưu tiên:

- route accuracy
- source match
- abstain success
- trace schema validation

Đó là những phần vừa bám sát rubric Day 09, vừa giúp nhóm tránh mất điểm do thiếu trace hoặc do answer không grounded.
