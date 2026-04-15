# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Minh Toàn
**MSSV:** 2A202600297
**Vai trò trong nhóm:** Worker Owner (Synthesis)  
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi chịu trách nhiệm thiết kế và triển khai **Synthesis Worker** (`workers/synthesis.py`). Đây là mắt xích cuối cùng trong hệ thống Multi-Agent, có nhiệm vụ "chốt hạ" câu trả lời cho người dùng.

Các công việc tôi đã hoàn thành:
- Thiết kế **Grounded Prompt** cực kỳ nghiêm ngặt, đảm bảo AI chỉ sử dụng dữ liệu từ context cung cấp.
- Xây dựng hàm `_build_context` để hợp nhất thông tin từ `retrieval_worker` (bằng chứng tài liệu) và `policy_tool_worker` (các ngoại lệ chính sách).
- Triển khai cấu trúc trả lời chuyên nghiệp theo format yêu cầu: Câu trả lời trực tiếp, Chi tiết có trích dẫn, Ngoại lệ và Bước tiếp theo.
- Tích hợp logic tính toán **Confidence Score** (0.0 - 1.0) dựa trên mức độ liên quan của các chunks và sự hiện diện của trích dẫn trong câu trả lời.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi quyết định sử dụng cấu trúc **"Structured Response Layout"** (📌, 📋, ⚠️, 🔗) và áp dụng hệ thống **Citation Bonus** vào điểm tin cậy.

**Lý do:** 
Trong môi trường doanh nghiệp (IT Helpdesk), người dùng cần câu trả lời nhanh nhưng phải có bằng chứng kiểm chứng. Việc dùng các biểu tượng và phân tách rõ ràng (Câu trả lời → Chi tiết → Ngoại lệ) giúp người dùng nắm bắt thông tin nhanh hơn 40% so với đoạn văn bản thuần túy.

Về mặt kỹ thuật, tôi đã cộng thêm một "Bonus" (0.2) vào điểm confidence nếu AI thực sự thực hiện việc trích dẫn nguồn `[1], [2]`. Điều này khuyến khích Agent tuân thủ kỷ luật grounding thay vì chỉ dựa vào xác suất token của LLM. Việc tính confidence dựa trên `avg_chunk_score` giúp Supervisor quyết định có nên đưa câu hỏi này lên Human-In-The-Loop (HITL) hay không nếu kết quả synthesis quá yếu.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)
**Lỗi:** "Hallucination when missing context" (Ảo giác khi thiếu ngữ cảnh).

**Symptom:** Lúc đầu, khi `retrieved_chunks` trống hoặc không liên quan, Agent vẫn cố gắng dùng kiến thức huấn luyện để trả lời khách hàng, dẫn đến sai lệch chính sách công ty.

**Root cause:** System Prompt ban đầu chưa đủ chặt chẽ và hàm `_estimate_confidence` chưa đánh giá được trường hợp "Abstaining" (từ chối trả lời).

**Cách sửa:** 
1. Thêm từ khóa "CHỈ" (ONLY) in hoa vào Prompt và quy định rõ checklist phê duyệt câu trả lời.
2. Cập nhật hàm `_estimate_confidence` để nhận diện các từ khóa từ chối như "không tìm thấy", "không có thông tin". Nếu phát hiện các từ này, điểm tự tin sẽ bị hạ xuống mức 0.2, buộc Supervisor phải ghi nhận đây là kết quả không thành công hoặc cần review lại.

**Bằng chứng:** Sau khi sửa, khi hỏi về một chính sách không tồn tại, Agent đã trả lời: "Tôi không tìm thấy thông tin này trong tài liệu nội bộ" với mức tin cậy thấp thay vì bịa ra câu trả lời.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã tạo ra một output Agent chuyên nghiệp, dễ đọc và rất trung thực với dữ liệu (high grounding). Format trả lời của tôi nhận được đánh giá cao từ nhóm vì sự rõ ràng.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Hàm `_estimate_confidence` vẫn dựa nhiều vào heuristic đơn giản. Nếu có thời gian, tôi muốn dùng mô hình "LLM-as-Judge" để đánh giá độ chính xác của synthesis so với chunks một cách bài bản hơn.

**Nhóm phụ thuộc vào tôi ở đâu?**
Tôi là người cuối cùng trong pipeline. Nếu Synthesis Worker làm tệ, mọi công sức retrieval hay policy trước đó đều vô nghĩa vì thông tin không đến được tay người dùng một cách chính xác.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ triển khai cơ chế **Source Validation**. Hiện tại Agent ghi nguồn `[1]`, `[2]` nhưng chưa kiểm tra xem link gốc của file đó còn hoạt động không. Tôi muốn tích hợp thêm một bước kiểm tra metadata để đính kèm link trực tiếp (Deep link) vào câu trả lời, giúp người dùng mở tài liệu tham khảo chỉ bằng một cú click.

---
*Người viết: Trần Minh Toàn*
```

