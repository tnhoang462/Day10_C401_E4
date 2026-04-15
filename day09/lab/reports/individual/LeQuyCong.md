# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Quý Công  
**MSSV:** 2A202600104  
**Vai trò trong nhóm:** Trace & Eval Owner  
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi phụ trách phần **đánh giá và đối chiếu hệ thống** giữa Day 08 và Day 09, trọng tâm là file `day09/lab/eval_trace.py`. Công việc của tôi không dừng ở việc chạy test questions, mà là biến kết quả từ Day 08 thành một baseline đủ rõ để so sánh với kiến trúc multi-agent của Day 09. Cụ thể, tôi đọc lại `day08/lab/eval.py`, `rag_answer.py`, các scorecard trong `day08/lab/results/`, sau đó map các chỉ số từ pipeline single-agent sang các metric mà Day 09 cần như `avg_confidence`, `avg_latency_ms`, `abstain_rate` và `multi_hop_accuracy`. Tôi cũng rà lại luồng `run_test_questions()`, `run_grading_questions()`, `analyze_traces()` và `compare_single_vs_multi()` để xác định chỗ nào đã có dữ liệu thật, chỗ nào mới là placeholder. Các thay đổi và phần hoàn thiện liên quan tới `eval_trace.py` đã được push lên repository, thể hiện qua các commit `de9a056` và `11f454f`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chọn cách **so sánh Day 08 và Day 09 bằng baseline được chuẩn hóa theo cùng một bộ câu hỏi**, thay vì bê nguyên các scorecard của Day 08 sang file compare.

**Lý do:**  
Lúc đầu nhìn vào `day08/lab/results/scorecard_baseline.md`, tôi thấy hệ đã có các số như `Faithfulness`, `Relevance`, `Context Recall`, `Completeness`. Tuy nhiên, Day 09 lại cần một bộ metric khác: `avg_confidence`, `avg_latency_ms`, `abstain_rate`, `multi_hop_accuracy`. Nếu tôi copy thẳng các số của Day 08 vào `compare_single_vs_multi()`, kết quả sẽ nhìn có vẻ hợp lệ nhưng thực ra không công bằng, vì hai lab đang đo hai lớp hành vi khác nhau. Day 08 chủ yếu chấm chất lượng answer; Day 09 ngoài answer còn đo trace, route, HITL và tool usage.

Vì vậy tôi quyết định dùng Day 08 như baseline logic, nhưng khi đối chiếu sang Day 09 thì phải chuẩn hóa lại: cùng bộ câu hỏi, cùng cách tính, cùng định nghĩa metric. Với các chỉ số Day 08 chưa có sẵn như latency hay confidence, tôi xác định rõ đâu là metric phải đo lại, đâu là metric có thể suy ra tạm bằng heuristic. Trade-off của cách này là tốn thêm công sức phân tích, nhưng bù lại kết quả compare có giá trị kỹ thuật hơn và dùng được thật cho `docs/single_vs_multi_comparison.md`.

**Bằng chứng:** Logic compare và phần cập nhật evaluation đã được push trong commit `de9a056`.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Phần `compare_single_vs_multi()` trong `eval_trace.py` có khung đúng nhưng chưa dùng được như một comparison thật, vì baseline Day 08 gần như chỉ là placeholder.

**Symptom:** Khi đọc file, tôi thấy `day08_baseline` đang để:
- `avg_confidence = 0.0`
- `avg_latency_ms = 0`
- `abstain_rate = ?`
- `multi_hop_accuracy = ?`

Điều này làm cho report compare có hình thức, nhưng không tạo ra được bằng chứng thật để nhóm điền tài liệu hoặc bảo vệ kết luận “multi-agent tốt hơn single-agent ở đâu”.

**Root cause:** Day 08 và Day 09 không cùng format output. `day08/lab/eval.py` chấm scorecard cho answer quality, còn `day09/lab/eval_trace.py` lại cần metrics cấp pipeline. Vì vậy baseline không thể lấy trực tiếp từ scorecard cũ nếu không qua bước mapping lại.

**Cách sửa:** Tôi rà lại toàn bộ luồng đánh giá của Day 08, xác định rõ metric nào có thể kế thừa, metric nào cần đo lại hoặc suy ra bằng heuristic, rồi đề xuất cấu trúc baseline chuẩn để cắm vào `compare_single_vs_multi()`. Tôi cũng chỉnh cách nhìn vào `run_test_questions()` và `analyze_traces()` để dùng trace Day 09 như nguồn số liệu thật, thay vì để compare chỉ toàn ghi chú TODO.

**Bằng chứng:** Sau khi hoàn thiện phần này, file `eval_trace.py` và tài liệu đi kèm đã phản ánh rõ ranh giới giữa baseline thật, baseline suy ra, và phần còn cần chạy đo bổ sung. Commit sửa và dọn xung đột đã được push ở `de9a056` và `11f454f`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**  
Tôi làm tốt nhất ở phần nhìn evaluation theo hướng hệ thống, không chỉ nhìn answer đúng hay sai. Tôi giúp nhóm hiểu rằng Day 09 không thể chỉ “chạy được” mà còn phải “đo được”, và việc so sánh với Day 08 phải dựa trên metric tương thích chứ không được ghép số theo cảm tính.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**  
Tôi mất khá nhiều thời gian ở bước đầu vì Day 08 và Day 09 dùng hai ngôn ngữ đánh giá khác nhau. Nếu chuẩn bị tốt hơn từ đầu, tôi có thể viết sớm một helper để tự động hóa việc convert baseline thay vì phải đọc thủ công nhiều artifact.

**Nhóm phụ thuộc vào tôi ở đâu?**  
Nếu không có phần trace/eval, nhóm rất khó chứng minh route nào tốt, câu nào fail vì retrieval, câu nào fail vì synthesis, và cũng không có số liệu rõ ràng để viết phần so sánh Day 08 và Day 09 trong báo cáo nhóm.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm 2 giờ, tôi sẽ hoàn thiện luôn một script baseline runner để chạy `day08/lab/rag_answer.py` trên chính bộ `day09/lab/data/test_questions.json`, đo trực tiếp `latency`, suy ra `confidence`, tính `abstain_rate`, `multi_hop_accuracy`, rồi xuất thẳng ra JSON cho `compare_single_vs_multi()`. Làm vậy thì phần compare sẽ không còn nửa thủ công nửa suy luận nữa, mà trở thành một pipeline đánh giá hoàn chỉnh và tái chạy được.

---
*Người viết: Lê Quý Công*
