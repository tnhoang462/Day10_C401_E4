# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Phạm Đỗ Ngọc Minh  
**MSSV:** 2A202600256 
**Vai trò trong nhóm:** MCP Server Developer & Testing / Documentation Lead  
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào? (150 từ)

Trong dự án Multi-Agent RAG này (Sprint), tôi trực tiếp đảm nhiệm hai mảng chính: thứ nhất là phát triển hệ thống ngoại vi **MCP Server** (`mcp_server.py`), thứ hai là thực hiện quá trình chạy thực tế (Grading run) và **viết tài liệu kiến trúc hệ thống**. 

Các công việc cụ thể tôi đã thực hiện bao gồm:
- Hoàn thiện và vận hành **MCP Server** đóng vai trò là cầu nối cho định hướng hành động (Tool-using) của các Worker. Tôi đã tham gia cấu hình các tools cốt lõi như `search_kb` (semantic search với ChromaDB), `get_ticket_info` (tra cứu tình trạng vé Jira), `check_access_permission`, và `create_ticket`.
- Chạy hệ thống đánh giá tự động (Grading run) xuất ra file `grading_run.jsonl`, qua đó phân tích các Trace logs của hệ thống.
- Chịu trách nhiệm khởi tạo và viết ba tài liệu đánh giá kỹ thuật trung tâm của nhóm: `system_architecture.md`, `routing_decisions.md` (phân tích kết quả điều hướng của từ khóa), và `single_vs_multi_comparison.md`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (200 từ)

**Quyết định:** Thiết kế các Tool theo chuẩn schema độc lập của Model Context Protocol (`TOOL_SCHEMAS`) và tạo ra bộ Dispatch trung gian (`TOOL_REGISTRY`), thay vì hardcode thẳng logic API vào bên trong Policy Worker.

**Lý do & Phân tích Trade-off:**
Ban đầu, để test nhanh, nhóm hoàn toàn có thể viết luôn mã lấy dữ liệu ChromaDB hoặc kiểm tra SOP lồng trong file `policy_tool.py`. Tuy nhiên, nếu làm vậy thì Worker sẽ bị gắn chặt (tightly coupled) với nghiệp vụ ngoại vi, khiến sau này rất khó tái sử dụng hoặc mở rộng sang các dạng Agent framework khác. Thay vào đó, tôi chuẩn hóa định dạng Input/Output theo JSON Schema. Khi Worker cần, nó chỉ việc gọi hàm `dispatch_tool()`.

**Trade-off:** Phải bỏ thêm nỗ lực để xử lý catch lỗi, validate schema đầu vào và xử lý luồng, khiến file `mcp_server.py` phình to về số dòng code. Đổi lại, Supervisor và các Worker giữ được tính stateless; ta có thể dễ dàng test độc lập Mock API mà không cần chạy cả chuỗi (như việc test alias `P1-LATEST` trả ra mã trạng thái ticket lập tức độc lập).

**Bằng chứng từ Trace/Code:**
Nhờ Registry này, lịch sử trace (ví dụ gq10) ghi nhận cực kì rõ: `[policy_tool_worker] called MCP search_kb`. Server tự xử lý input JSON và phản hồi cấu trúc `{chunks: [...], sources: [...]}` ổn định.

---

## 3. Tôi đã sửa một lỗi gì? (200 từ)

**Lỗi:** Sự cố đứt gãy luồng Agent (Pipeline crash) do Tool bị lỗi truy xuất và vấn đề đồng bộ Git khi làm việc nhóm.

**Symptom:** Trong giai đoạn đánh giá qua script `eval_trace.py`, đôi khi lệnh truy vấn đến cơ sở dữ liệu có thể fail (chẳng hạn ChromaDB chưa thiết lập đúng đường dẫn hoặc input sai kiểu). Nếu gọi thẳng hàm, cả chương trình bằng Python sẽ sinh Exception khiến Agent dừng chạy, và đầu ra Confidence về mốc 0.

**Root cause:** Bất cứ tương tác ngoại vi (I/O) nào cũng tiểm ẩn rủi ro RuntimeError, nhưng hàm chạy công cụ chưa bọc an toàn.

**Cách sửa:**
Tôi đã triển khai Fallback Response an toàn bên trong MCP Dispatcher. Tại `tool_search_kb` và `dispatch_tool`, tôi sử dụng khối lệnh `try...except`, nếu query gặp lỗi, nó không crash chương trình mà tự động xuất ra một block Mock dữ liệu chuẩn (để cho Supervisor vẫn có luồng giải quyết) và trả về key `"error": str(e)`.
Ngoài ra, trong quá trình push code lưu trữ các đánh giá (3 file tài liệu), tôi gặp lỗi **Git "non-fast-forward" push rejection**. Tôi đã tự xử lý fix lỗi đồng bộ này bằng việc chạy `git pull --rebase origin main` để tích hợp code commit trước lưu thành công cấu trúc kiến trúc.

---

## 4. Tôi tự đánh giá đóng góp của mình (150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi cung cấp cái nhìn toàn cảnh về khả năng của hệ thống qua việc lập bảng thống kê và số liệu so sánh rõ ràng trong `single_vs_multi_comparison.md`. Khả năng debug và chạy ra được file logs chấm điểm `grading_run.jsonl` thành công cũng phản ánh luồng Server Component chạy rất ổn định đáp ứng được luồng của Agent.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Do dành nhiều nguồn lực vào công đoạn tích hợp đánh giá Data ở vòng ngoài cùng (Routing config) và MCP Mock-data, tôi chưa đi sâu vào việc viết Prompt nâng cao cho mô hình ngôn ngữ (LLM) ở Policy.

**Nhóm phụ thuộc vào tôi ở đâu?**
Các Developer làm phần Worker logic hoàn toàn dựa dẫm vào gói dữ liệu mà module của tôi mock trả về (gắn với `check_access_permission`, v.v.). Ngoài ra, bộ báo cáo so sánh Day08 và Day09 là bằng chứng then chốt đánh giá hiệu năng dự án do tôi chịu trách nhiệm cung cấp số liệu.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (100 từ)

Nếu có thêm hai giờ, tôi sẽ nâng cấp kiến trúc `mcp_server.py` từ việc giả lập "chạy thử nội hàm" (mock in-process) sang "giao thức thực tiễn" thông qua **FastAPI**. Bằng cách phơi bày danh sách công cụ tại một endpoint HTTP (vd: `/tools/call`), tôi có thể mô phỏng chính xác phương thức giao tiếp mạng chuẩn MCP, qua đó chứng minh Agent RAG thực chất có thể linh hoạt giao tiếp với bất cứ Backend ngoại vi nào.
