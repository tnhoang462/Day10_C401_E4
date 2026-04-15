# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Xuân Mong-2A202600246
**Vai trò:** Cleaning  — Clearning rules  
**Ngày nộp:** 15/4/2026
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
Tôi trực tiếp đảm nhận vai trò **Cleaning Owner**, phụ trách module chính là `transform/cleaning_rules.py`. Nhiệm vụ của tôi ở Sprint 2 là thiết kế và triển khai các bộ lọc (Rules) nhằm ngăn chặn dữ liệu bẩn từ Export thô xâm nhập vào hầm hố chứa Vector AI. Cụ thể, tôi đã viết bổ sung 3 rules hoàn toàn mới bao gồm: loại bỏ khối văn bản quá ngắn (< 15 ký tự), lọc sạch các keyword chứa nội dung xung đột (như "lỗi migration", "bản nháp", "bản sync cũ") và gọt rửa các thẻ HTML rác do lỗi trích xuất.

**Kết nối với thành viên khác:**
Code lọc rác của tôi tạo ra output `artifacts/cleaned/*.csv` và `artifacts/quarantine/*.csv`. Đây chính là đầu vào quan trọng cho bạn phụ trách module `quality/expectations.py` để họ chạy lệnh Validate, cũng như giúp bạn Owner Embed có nguồn dữ liệu text tinh khiết để nhúng vào ChromaDB không bị nhiễu.

**Bằng chứng (commit / comment trong code):**
Đoạn mã tôi đã viết nằm ở hàm `clean_rows` trong file `transform/cleaning_rules.py`, trực tiếp đẩy những chunk có chứa từ khóa nháp vào `quarantine.append({**raw, "reason": "contains_draft_or_error_keywords"})`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quá trình làm Cleaning, tôi phải đưa ra quyết định "Trade-off" (sự đánh đổi) khá gắt gao ở Rule độ dài văn bản (Length Check). Ban đầu tôi băn khoăn việc cài đặt `MIN_CHUNK_LENGTH = 15`. Việc loại bỏ khối văn bản dưới 15 ký tự sẽ ngăn chặn các dòng rác (chỉ chứa một từ vô nghĩa như "Mục lục" hoặc dấu phẩy do công cụ Chunking cắt hỏng). Quyết định kỹ thuật của tôi là chấp nhận việc có thể đánh rơi một số ít thông tin quá ngắn (False Positive), đổi lại tôi có **100% độ chính xác cho Vector DB**. Vector DB cực kỳ nhạy cảm với dữ liệu nhiễu; nếu AI lấy nhầm mã nhúng của chữ "Trang 12" thay vì lấy nội dung chính, chất lượng câu trả lời RAG sẽ đổ sông đổ biển. Quyết định đẩy các ngoại lệ này sang khu vực chứa riêng (Dead Letter Queue - Quarantine) thay vì tự động sửa bằng máy giúp bảo toàn sự trung thực của hệ thống.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Một Anomaly khá điển hình xuất hiện khi tôi khảo sát bằng lệnh `run`. Trước khi áp dụng 3 quy tắc mới (baseline), hệ thống báo `cleaned_records=6` và `quarantine_records=4`. Tuy nhiên, khi nhóm thử test pipeline, chúng tôi phát hiện dòng số 3 trong `policy_export_dirty.csv` đang ghi thông tin mâu thuẫn: *"hoàn tiền được chấp nhận trong vòng 14 ngày... (ghi chú: bản sync cũ policy-v3 — **lỗi migration**)"*.

Triệu chứng: Công cụ lọc cơ bản vẫn thản nhiên cho phép duyệt dòng lỗi này đi tiếp (False Negative), đồng nghĩa AI có nguy cơ học phải lệnh "lỗi migration" đó. 
Cách Fix: Tôi lập tức thêm Rule kiểm soát từ khóa. Sau khi update, tôi chạy lại lệnh qua terminal:
`python etl_pipeline.py run` (với run_id=2026-04-15T08-39Z).
Kết quả trả về chính xác như kỳ vọng: `cleaned_records=5` và `quarantine_records=5`. Dòng dữ liệu nháp của phòng ban đã bị chặn và nhốt thành công với lý do `contains_draft_or_error_keywords`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Bằng chứng log từ Terminal chứng minh sự thay đổi số lượng Quarantine trước và sau khi thêm Rule vào `transform/cleaning_rules.py`:

**Trước (khi chạy rule Baseline)**:
`run_id=2026-04-15T08-34Z`
`raw_records=10`
`cleaned_records=6`
`quarantine_records=4`

**Sau (khi áp dụng 3 rule bổ sung do tôi viết)**:
`run_id=2026-04-15T08-39Z`
`raw_records=10`
`cleaned_records=5`
`quarantine_records=5`
Dòng log thay đổi đã làm bằng chứng mạnh mẽ rằng Rule phát huy tính năng. Dòng dữ liệu `chunk_id=3` đã bị đá khỏi list Cleaned. Hệ thống ChromaDB từ đó ở `run_id=2026-04-15T08-39Z` chỉ còn `embed_upsert count=5`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm thời gian (khoảng 2 giờ), tôi sẽ cài đặt thêm Rule Data Masking (Che dấu PII). Thay vì chỉ xoá bỏ HTML hay từ khóa nháp, tôi sẽ viết Rule dùng Regex để quét và làm mờ mọi Số điện thoại cá nhân (090x.xxx) hoặc Căn cước công dân bị lẫn trong dữ liệu IT Helpdesk chuyển nó thành `[_PII_HIDDEN_]` trước khi Embed để bảo mật quyền riêng tư nhân sự.
