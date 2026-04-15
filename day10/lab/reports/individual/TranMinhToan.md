# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Minh Toàn  
**Vai trò:** Sprint 3 Lead (Evaluation & Quality Control)  
**Ngày nộp:** 15/04/2026

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
- `etl_pipeline.py`: Thực hiện kịch bản inject dữ liệu bẩn thông qua các flag `--no-refund-fix` và `--skip-validate`.
- `eval_retrieval.py`: Chạy đánh giá retrieval so sánh Before/After.
- `docs/quality_report.md`: Tổng hợp bằng chứng cho nhóm.

**Kết nối với thành viên khác:**
Tôi làm việc chặt chẽ với chủ sở hữu phần **Cleaning** để đảm bảo các quy tắc xử lý (như lọc từ khóa nháp) được tích hợp đúng cách. Tôi cũng phối hợp với phần **Ingestion** để kiểm soát số lượng bản ghi thô nạp vào pipeline (`raw_records=10`).

**Bằng chứng (comment trong code):**
Tôi đã thực thi các phiên chạy `sprint3-clean` và `sprint3-dirty` để kiểm chứng độ bền của hệ thống khi có dữ liệu lỗi lọt vào.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Một quyết định quan trọng mà tôi thực hiện là việc sử dụng chiến lược **"Defense in Depth" (Phòng thủ đa lớp)** trong pipeline. Thay vì chỉ dựa vào một logic sửa lỗi duy nhất (`apply_refund_window_fix`), tôi đã đề xuất thêm quy tắc làm sạch dựa trên từ khóa `contains_draft_or_error_keywords`. 

Quyết định này được đưa ra sau khi nhận thấy rằng nếu người dùng cố ý bỏ qua bước validation (sử dụng flag `--skip-validate`), các lỗi logic vẫn có thể lọt vào Vector Store. Bằng cách thêm lớp lọc từ khóa nháp (ví dụ: "lỗi migration"), tôi đã giúp hệ thống tự bảo vệ mình ngay cả khi các logic xử lý nghiệp vụ bị tắt. Điều này giúp tăng tính ổn định của Agent lên đáng kể, giảm thiểu rủi ro cung cấp thông tin sai lệch cho người dùng cuối.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Trong quá trình thực hiện Sprint 3, tôi phát hiện ra một Anomaly nghiêm trọng: mặc dù đã tắt tính năng fix lỗi refund, kết quả retrieval vẫn trả về con số "7 ngày" thay vì "14 ngày" như mong đợi trong kịch bản "Dirty". 

Thông qua việc kiểm tra **Quarantine Log** (`artifacts/quarantine/quarantine_sprint3-dirty.csv`), tôi nhận ra bản ghi "14 ngày" (ID 3) đã bị chặn bởi quy tắc quét từ khóa nháp do có chứa cụm từ "(ghi chú: bản sync cũ policy-v3 — lỗi migration)". 

**Triệu chứng:** Kết quả retrieval không thay đổi dù đã inject dữ liệu.  
**Detection:** Kiểm tra file `quarantine_sprint3-dirty.csv` thấy ID 3 bị loại với lý do `contains_draft_or_error_keywords`.  
**Xử lý:** Tôi đã ghi nhận đây là một tính năng bảo vệ lớp sâu (expected behavior) và giải thích rõ trong báo cáo chất lượng để nhóm nắm được sức mạnh của pipeline.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Dưới đây là bằng chứng so sánh từ file `eval_grading_questions.csv` cho câu hỏi chính sách hoàn tiền (`gq_d10_01`):

- **Run ID: sprint3-dirty**
  - `top1_preview`: "...Yêu cầu được gửi trong vòng 7 ngày làm việc..."
  - `hits_forbidden`: **no** (Dữ liệu 14 ngày đã được ngăn chặn từ lớp Clean).

- **Run ID: sprint3-clean**
  - `top1_preview`: "...Yêu cầu được gửi trong vòng 7 ngày làm việc..."
  - `contains_expected`: **yes**

Hệ thống cho thấy sự nhất quán tuyệt đối nhờ các lớp filter hoạt động hiệu quả.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ triển khai **Auto-Eval bằng LLM** để đánh giá nội dung retrieval. Hiện tại chúng ta đang đánh giá dựa trên keyword match (`must_contain` / `must_not_contain`), vốn khá cứng nhắc. Một lớp LLM sẽ giúp phát hiện các lỗi sai về mặt ngữ nghĩa tinh vi hơn mà metadata hay keyword không thể lọc hết được.
