# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Ngọc Thắng
**Vai trò trong nhóm:** Worker Owner
**Ngày nộp:** 14/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? 

**Module/file tôi chịu trách nhiệm:**
- File chính: `day09/lab/workers/retrieval.py` và file test `day09/lab/workers/retrieval_test.py`.
- Functions tôi implement: Cấu trúc logic chunking text và nhét vào ChromaDB qua hàm trong `index.py`, thực thi logic gọi collection lấy kết quả trong `retrieval.py`.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Phần test worker độc lập của tôi đảm bảo chức năng truy xuất Document (RAG) hoạt động trơn tru với các thông số input contract (`task`, `history`) theo chuẩn. Sau khi kiểm thử đầu ra thành công mang đúng định dạng mảng các `retrieved_chunks`, thành viên làm phần Supervisor có thể yên tâm gọi route tới `retrieval_worker` mà không sợ lỗi data/type mismatch tác động lên toàn graph.

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**
Commit: `"test retrieval.py + add retrieval_test.py"` trong nhật ký Git, nội dung thay đổi được thực hiện trực tiếp tại file `day09/lab/workers/retrieval_test.py`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? 

**Quyết định:** Viết riêng file kiểm thử tĩnh `retrieval_test.py` thay vì test trực tiếp qua Graph hay nhúng script.

**Lý do:**
Việc khởi tạo một biến `test_state = {"task": "SLA ticket P1 là bao lâu?", "history": []}` và mock tham số truy xuất thẳng từ worker function `retrieval_run(test_state)` giúp tôi tách biệt hoàn toàn rủi ro gây ra lỗi logic từ Supervisor (ví dụ lỗi định tuyến route_reason sai). Môi trường cô lập này là bắt buộc để tôi theo dõi và can thiệp kịp thời vào I/O output của mỗi Worker trước khi nhúng.

**Trade-off đã chấp nhận:**
Phải thêm 1 file kiểm thử riêng lẻ, có phần thủ công khi muốn kiểm tra nhiều queries thay vì chạy batch query trên framework tự động.

**Bằng chứng từ trace/code:**
```python
# day09/lab/workers/retrieval_test.py
from retrieval import run as retrieval_run
test_state = {"task": "SLA ticket P1 là bao lâu?", "history": []}
result = retrieval_run(test_state)
print(result["retrieved_chunks"])
```
Khi chạy file này, log trả về bằng chứng rõ ràng worker đã chạy độc lập tốt và bắt đúng context:
`[{'text': 'SLA TICKET - QUY ĐỊNH XỬ LÝ...', 'source': 'sla_p1_2026.txt', 'score': 0.6336, ...]`
Worker đã lấy chính xác file `sla_p1_2026.txt` cho SLA của ticket P1 với độ chính xác khá tốt (score ~0.634).

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Script không tìm thấy dữ liệu nguồn (`FileNotFoundError`) và terminal báo lỗi `UnicodeEncodeError`. Ngoài ra còn có lỗi xung đột Embedding Dimension `InvalidArgumentError`.

**Symptom (pipeline làm gì sai?):**
Khi chạy Worker hay Index script ngoài thư mục `lab/`, hệ thống lập tức sụp đổ báo lỗi `The system cannot find the path specified: './data/docs'`. Sau đó terminal xuất hiện lỗi ký tự lạ dẫn tới không render được output ra màn hình Console, trả về số chunk là `0`. Lỗi ChromaDB thì chặn việc insert vào vector database.

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**
Lỗi ở tầng thao tác Indexing và cấu hình tương tác Local:
- Đường dẫn đọc docs được hardcode tương đối `./data/docs`, do đó chạy script từ root directory (`Day09_C401_E4`) bị sai lệch context.
- Hệ console trên PowerShell Windows mặc định dùng bảng mã `cp1252` thay vì utf-8, làm bung Exception khi in các ký tự mũi tên dạng emoji (▶).
- ChromaDB bị vướng conflict size dimension do base cũ config bằng model khác (384 vector vs 1536 vector).

**Cách sửa:**
- Xóa thủ công index base cũ của ChromaDB để clean collection data.
- Đổi cách đọc thư mục thành tuyệt đối dựa trên `os.path.dirname(__file__)` lấy thư mục cha hiện tại thay vì cwd.
- Chạy terminal bằng cách nhúng string format encoding `$env:PYTHONIOENCODING="utf-8"`.

**Bằng chứng trước/sau:**
Trước khi sửa (Log lỗi):
```
FileNotFoundError: [WinError 3] The system cannot find the path specified: './data/docs'
UnicodeEncodeError: 'charmap' codec can't encode character '\u25b6' in position 2: character maps to <undefined>
```
Sau khi sửa và chạy (Log chạy thành công file indexing && test retrieval):
```
$env:PYTHONIOENCODING="utf-8"; python day09/lab/workers/index.py
Indexed 13 chunks from: access_control_sop.txt
Indexed 16 chunks from: sla_p1_2026.txt
Index ready. (Total docs: 63)
```

---

## 4. Tôi tự đánh giá đóng góp của mình 

**Tôi làm tốt nhất ở điểm nào?**
Tôi giải quyết triệt để lỗi môi trường (environment and encoding bugs) và kiểm soát hoàn hảo đường link index động đến Document. Tôi cũng cô lập và test hiệu quả component qua script riêng.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Do phải mất thời gian lo phần lỗi môi trường hệ thống, tôi phân bố chưa đủ nhiều thời gian để tối ưu tham số overlap token trong ChromaDB Index (điều này có thể dẫn tới Chunk Text bị cụt đoạn ở một vài query dài).

**Nhóm phụ thuộc vào tôi ở đâu?**
Các thành viên khác phụ trách API call (LLM Synthesis Worker) hoàn toàn bị block nếu Retrieval Worker của tôi gặp lỗi hoặc trả về context rỗng (`chunks = 0`). Đây là đầu nối quan trọng bắt buộc cho tính chân thực (grounded) của agent tổng.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi cần định nghĩa Contract được thiết lập chặt chẽ hơn từ Supervisor Owner để worker của tôi tự tin trích xuất biến `history` hoặc `task` chính xác nhất.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? 

Nếu có thêm 2 tiếng, tôi sẽ tiến hành **thực thi metadata filtering ngay trong Worker** - nghĩa là tận dụng metadata `department` hoặc `access` trên từng nguồn file Document để ChromaDB thu hẹp phạm vi search. Lý do: Quan sát trace của câu hỏi về chế độ lương (HR) đôi lúc còn bị nhầm lẫn với IT Helpdesk, nguyên do số lượng vector space hiện tại đang trải đều trên toàn bộ 63 chunks mà chưa áp filter logic. Cải tiến tìm kiếm này sẽ trực tiếp đẩy accuracy cho graph.
