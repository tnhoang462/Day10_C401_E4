# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Nhật Hoàng  
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án này, tôi đảm nhận vai trò **Trace & Docs Owner**, tập trung vào việc xây dựng bộ công cụ đánh giá và quan sát hệ thống (Observability). Công việc chính của tôi tập trung vào tệp `day09/lab/eval_trace.py`, nơi tôi chịu trách nhiệm thiết kế quy trình chạy thử nghiệm tự động cho toàn bộ 26 câu hỏi (bao gồm 15 test questions và 11 grading questions).

Tôi đã hiện thực hóa các chức năng chính trong module đánh giá:
- Chương trình chạy pipeline và tự động lưu vết (tracing) cho mỗi câu hỏi vào `artifacts/traces/`.
- Hàm `analyze_traces` để tổng hợp các chỉ số quan trọng như: phân bổ điều hướng của Supervisor (Routing Distribution), độ trễ trung bình (Latency), và mức độ tự tin (Confidence).
- Module so sánh hiệu năng giữa kiến trúc Single-Agent (Day 08) và Multi-Agent (Day 09) để chứng minh giá trị của hệ thống mới.

**Bằng chứng:**
- File chính: `day09/lab/eval_trace.py`
- Commit hash: `c6b406c` ("add eval trace")
- Dữ liệu trace thực tế: `day09/lab/artifacts/traces/` tỉ lệ routing được ghi nhận là 53% cho Retrieval và 46% cho Policy Tool.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi đã quyết định xây dựng một module so sánh tự động (`compare_single_vs_multi`) tích hợp trực tiếp vào quy trình đánh giá thay vì chỉ in kết quả thô.

**Lý do:** Thông thường, khi chuyển đổi sang kiến trúc Multi-Agent, nhóm chỉ cảm nhận hệ thống "thông minh hơn" một cách cảm tính. Tôi muốn có bằng chứng định lượng. Tôi đã thu thập kết quả benchmark từ Day 08 và đưa vào làm baseline. Quyết định này giúp chúng tôi phát hiện ra một sự thật quan trọng: mặc dù Multi-Agent làm tăng độ trễ (latency), nhưng mức độ tự tin và khả năng trích dẫn chính xác (citation accuracy) lại tăng vượt trội.

**Trade-off đã chấp nhận:** Việc lưu lại trace chi tiết cho từng stage (input/output của từng worker) khiến dung lượng đĩa tăng lên và code evaluation trở nên phức tạp hơn khi phải xử lý hàng chục file JSON. Tuy nhiên, điều này cực kỳ quan trọng cho việc debug. Nếu Supervisor điều hướng sai (ví dụ: câu hỏi về Policy lại đưa vào Retrieval), chúng tôi có thể nhìn vào `route_reason` để biết LLM đã nghĩ gì tại thời điểm đó.

**Bằng chứng từ trace/code:**
Trong `artifacts/eval_report.json`, module của tôi đã chỉ ra sự cải thiện rõ rệt về Confidence:
```json
"day08_single_agent": {
  "avg_confidence": 0.534
},
"day09_multi_agent": {
  "avg_confidence": 0.829
}
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** LLM Reasoning Flood (Tràn nội dung suy luận làm nhiễu log).

**Symptom (pipeline làm gì sai?):** Khi chạy file `eval_trace.py`, terminal bị flooded (tràn ngập) bởi hàng ngàn dòng text có tiền tố `[Reasoning]:`. Điều này khiến việc theo dõi trực tiếp quá trình đánh giá bằng mắt trở nên bất khả thi, đồng thời làm log file phình to không cần thiết, che lấp các thông tin quan trọng về worker logic.

**Root cause:** Lỗi nằm ở worker logic trong file `day09/lab/workers/policy_tool.py`. Do sử dụng mô hình DeepSeek-R1 (mã `openai/gpt-oss-120b`) qua NVIDIA API với chế độ `stream=True`, hàm `_call_llm` đã được cấu hình để in mọi token trong trường `reasoning_content` ra terminal (`stdout`) kèm tiền tố `[Reasoning]:`.

**Cách sửa:** Tôi đã can thiệp vào hàm `_call_llm` của `policy_tool.py`, thực hiện comment out hoặc loại bỏ các dòng `print` không cần thiết. Thay vì in trực tiếp ra terminal, tôi đề xuất chỉ giữ lại nội dung này trong biến `full_content` (nếu cần) và chỉ hiển thị khi người dùng bật flag `--debug`.

**Bằng chứng trước/sau:**
- **Trước khi sửa:** Trace log bị xen lẫn bởi các đoạn suy luận dài dòng của AI: `[Reasoning]: Step 1: Check context... [Reasoning]: Step 2: Compare with rule...`.
- **Sau khi sửa:** Terminal sạch sẽ, chỉ hiển thị trạng thái của Graph: `[01/26] gq01: SLA ticket P1... ✓ route=retrieval_worker, conf=0.92`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?** Tôi đã xây dựng được một hệ thống quan sát (observability) hoàn chỉnh cho nhóm. Việc tự động hóa phân tích trace giúp nhóm tiết kiệm ít nhất 2 giờ làm báo cáo vì các con số đã có sẵn.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?** Tôi chưa tối ưu được tốc độ chạy evaluation. Hiện tại chương trình chạy tuần tự, mất khoảng 10 phút để xong 26 câu, điều này gây ức chế khi cần test nhanh các thay đổi nhỏ.

**Nhóm phụ thuộc vào tôi ở đâu?** Toàn bộ dữ liệu về độ chính xác và so sánh trong báo cáo nhóm (`group_report.md`) đều phụ thuộc vào kết quả trích xuất từ `eval_report.json` của tôi.

**Phần tôi phụ thuộc vào thành viên khác:** Tôi cần Supervisor Owner hoàn thiện logic điều hướng ổn định để các trace thu thập được có giá trị và không bị lỗi chain-of-thought.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ hiện thực hóa tính năng **Parallel Evaluation** bằng cách sử dụng `asyncio`. Với kiến trúc Multi-Agent hiện tại, việc gọi LLM chiếm 90% thời gian latency. Nếu chạy song song các câu hỏi trong bộ test, tôi có thể giảm thời gian eval xuống còn 1/5, giúp nhóm thu được nhiều trace đa dạng hơn cho các câu hỏi khó như `gq09` và `gq11`.

---
