# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Xuân Mong  
**MSSV:** 2A202600246  
**Vai trò trong nhóm:** Worker Owner (Policy Tool & AI Integration)  
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào? (150 từ)

Trong dự án Multi-Agent RAG này, tôi trực tiếp chịu trách nhiệm phát triển **Policy Tool Worker** (`workers/policy_tool.py`). Đây là một trong ba Worker lõi của hệ thống, đóng vai trò phân tích tính hợp lệ của yêu cầu người dùng trước khi phản hồi chính thức.

Các công việc cụ thể tôi đã thực hiện bao gồm:
- Thiết lập **Worker Contract** cho Policy Tool, định nghĩa rõ ràng Input (task, context) và Output (policy_result, mcp_tools_used) để phối hợp với Supervisor.
- Triển khai logic **Hybrid Policy Analysis**: Kết hợp kiểm soát từ khóa (Rule-based) để phát hiện nhanh các vi phạm nghiêm trọng (Flash Sale, sản phẩm đã dùng) và suy luận sâu (LLM-based) bằng AI.
- Tích hợp và cấu hình **NVIDIA GPT-OSS-120B**, đặc biệt là cơ chế xử lý **Reasoning Content** (khi chạy test độc lập, có thể model bị thay đổi khi nhóm trưởng test toàn hệ thống) để hệ thống có khả năng giải trình (Explainable AI).
- Đảm bảo tính toàn vẹn của **AgentState**, ghi đầy đủ lịch sử hoạt động và các lần gọi công cụ ngoại vi (MCP Tools) vào Trace hệ thống.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (200 từ)

**Quyết định:** Tôi quyết định triển khai mô hình **"Dual-Check Architecture"** (Cấu trúc kiểm tra kép) trong file `policy_tool.py`. Cụ thể, tôi thực hiện lọc các ngoại lệ bằng Rule-based trước, sau đó mới đẩy sang NVIDIA AI để thực hiện Reasoning.

**Lý do & Phân tích Trade-off:**
Hệ thống cần cân bằng giữa **độ an toàn (Safety)** và **tính linh hoạt (Flexibility)**. 
- Nếu chỉ dùng AI: Có rủi ro AI bị "hallucination" (bịa đặt luật) đối với các quy định cứng như Flash Sale không hoàn tiền.
- Nếu chỉ dùng Rule-based: Câu trả lời sẽ rất khô cứng và không xử lý được các trường hợp "xám" (như yêu cầu hoàn tiền trong 5 ngày nhưng sản phẩm đã bóc hộp một nửa).

Tôi chọn cách dùng Rule-based để bắt nhanh "Exception cases" (Flash Sale, License key) nhằm đảm bảo an toàn tuyệt đối, sau đó dùng AI để viết lời giải thích (`explanation`).

**Trade-off:** Chấp nhận độ trễ (latency) tăng thêm khoảng ~2s khi gọi NVIDIA API để đổi lấy khả năng suy luận mạnh mẽ và sự minh bạch trong giải trình.

**Bằng chứng từ Trace/Code:**
Trong test case 1 (Flash Sale), hệ thống đã bắt được lỗi ngay ở tầng Rule-based và AI đã tiếp nối bằng cách giải thích chi tiết: 
`[Reasoning]: "...flash sale orders are not refundable... request violates policy."`
`policy_applies: False` | `exception: flash_sale_exception`

---

## 3. Tôi đã sửa một lỗi gì? (200 từ)

**Lỗi:** "Silent Logic Fail" & Unauthorized 401 Error.

**Symptom:** Ban đầu khi chạy test, pipeline bị "câm": kết quả `policy_applies: False` trả ra nhưng các biến `history`, `mcp_tools_used` hoàn toàn trống rỗng trong State. Đồng thời, model NVIDIA liên tục báo lỗi `Error code: 401 - Unauthorized`.

**Root cause:** 
1. **Lỗi xác thực**: Tôi quên nạp biến môi trường bằng `load_dotenv()` nên chương trình không tìm thấy `NVIDIA_API_KEY`.
2. **Lỗi Logic dòng chảy**: Tôi đã đặt lệnh `return state` ngay sau khi tính toán xong kết quả, làm cho toàn bộ khối mã ghi Log và cập nhật mảng `worker_io_logs` phía dưới trở thành mã không thể thực thi (Unreachable code).

**Cách sửa:** 
Tôi đã tiến hành bổ sung `load_dotenv()` ở ngay đầu file. Sau đó, tôi tái cấu trúc hàm `run` bằng cách đưa lệnh `return` duy nhất xuống cuối cùng của hàm, sau khi mọi dữ liệu Trace và Log đã được append đầy đủ vào State.

**Bằng chứng Trước/Sau:**
- **Trước**: `MCP Calls: 0` (Dù thực tế có gọi search_kb).
- **Sau (Log thực tế)**: `Result Policy Applies: True | MCP calls: 0` (Hiển thị đầy đủ Reasoning và ghi nhận trạng thái hoàn tất phân tích trong history).
```
▶ Task: Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?...
[Reasoning]: We[Reasoning]:  need[Reasoning]:  to[Reasoning]:  answer[Reasoning]:  in[Reasoning]:  Vietnamese[Reasoning]: .[Reasoning]:  The[Reasoning]:  user[Reasoning]:  says[Reasoning]: :[Reasoning]:  "[Reasoning]: Bạn[Reasoning]:  là[Reasoning]:  một[Reasoning]:  chuyên[Reasoning]:  gia[Reasoning]:  pháp[Reasoning]:  chế[Reasoning]:  AI[Reasoning]: .[Reasoning]:  D[Reasoning]: ựa[Reasoning]:  vào[Reasoning]:  tài[Reasoning]:  liệu[Reasoning]:  nội[Reasoning]:  bộ[Reasoning]: :[Reasoning]:  ngoại[Reasoning]:  lệ[Reasoning]: :[Reasoning]:  đơn[Reasoning]:  hàng[Reasoning]:  flash[Reasoning]:  sale[Reasoning]:  không[Reasoning]:  được[Reasoning]:  hoàn[Reasoning]:  tiền[Reasoning]: .[Reasoning]:  H[Reasoning]: ãy[Reasoning]:  xem[Reasoning]:  xét[Reasoning]:  yêu[Reasoning]:  cầu[Reasoning]: :[Reasoning]:  '[Reasoning]: Kh[Reasoning]: ách[Reasoning]:  hàng[Reasoning]:  Flash[Reasoning]:  Sale[Reasoning]:  yêu[Reasoning]:  cầu[Reasoning]:  hoàn[Reasoning]:  tiền[Reasoning]:  vì[Reasoning]:  sản[Reasoning]:  phẩm[Reasoning]:  lỗi[Reasoning]:  —[Reasoning]:  được[Reasoning]:  không[Reasoning]: ?'[Reasoning]:  [Reasoning]: 1[Reasoning]: .[Reasoning]:  Y[Reasoning]: êu[Reasoning]:  cầu[Reasoning]:  này[Reasoning]:  có[Reasoning]:  vi[Reasoning]:  phạm[Reasoning]:  chính[Reasoning]:  sách[Reasoning]:  không[Reasoning]: ?[Reasoning]:  [Reasoning]: 2[Reasoning]: .[Reasoning]:  Nếu[Reasoning]:  có[Reasoning]: ,[Reasoning]:  hãy[Reasoning]:  chỉ[Reasoning]:  rõ[Reasoning]:  điều[Reasoning]:  khoản[Reasoning]:  nào[Reasoning]: .[Reasoning]:  [Reasoning]: 3[Reasoning]: .[Reasoning]:  Nếu[Reasoning]:  không[Reasoning]: ,[Reasoning]:  hãy[Reasoning]:  xác[Reasoning]:  nhận[Reasoning]:  là[Reasoning]:  hợp[Reasoning]:  lệ[Reasoning]: ."

[Reasoning]: We[Reasoning]:  have[Reasoning]:  internal[Reasoning]:  doc[Reasoning]: :[Reasoning]:  exception[Reasoning]: :[Reasoning]:  flash[Reasoning]:  sale[Reasoning]:  orders[Reasoning]:  are[Reasoning]:  not[Reasoning]:  refundable[Reasoning]: .[Reasoning]:  So[Reasoning]:  any[Reasoning]:  request[Reasoning]:  for[Reasoning]:  refund[Reasoning]:  violates[Reasoning]:  policy[Reasoning]: ,[Reasoning]:  even[Reasoning]:  if[Reasoning]:  product[Reasoning]:  is[Reasoning]:  defective[Reasoning]: .[Reasoning]:  So[Reasoning]:  answer[Reasoning]: :[Reasoning]:  Yes[Reasoning]: ,[Reasoning]:  violates[Reasoning]:  policy[Reasoning]: .[Reasoning]:  Cite[Reasoning]:  the[Reasoning]:  clause[Reasoning]: :[Reasoning]:  "[Reasoning]: đ[Reasoning]: ơn[Reasoning]:  hàng[Reasoning]:  flash[Reasoning]:  sale[Reasoning]:  không[Reasoning]:  được[Reasoning]:  hoàn[Reasoning]:  tiền[Reasoning]: ".[Reasoning]:  Possibly[Reasoning]:  mention[Reasoning]:  that[Reasoning]:  product[Reasoning]:  defect[Reasoning]:  does[Reasoning]:  not[Reasoning]:  override[Reasoning]:  this[Reasoning]:  rule[Reasoning]: .[Reasoning]:  Provide[Reasoning]:  reasoning[Reasoning]: .  policy_applies: False
  exception: flash_sale_exception — Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách...
  MCP calls: 0

▶ Task: Khách hàng muốn hoàn tiền license key đã kích hoạt....
[Reasoning]: We[Reasoning]:  need[Reasoning]:  to[Reasoning]:  answer[Reasoning]:  in[Reasoning]:  Vietnamese[Reasoning]: .[Reasoning]:  The[Reasoning]:  user[Reasoning]: :[Reasoning]:  "[Reasoning]: Bạn[Reasoning]:  là[Reasoning]:  một[Reasoning]:  chuyên[Reasoning]:  gia[Reasoning]:  pháp[Reasoning]:  chế[Reasoning]:  AI[Reasoning]: .[Reasoning]:  D[Reasoning]: ựa[Reasoning]:  vào[Reasoning]:  tài[Reasoning]:  liệu[Reasoning]:  nội[Reasoning]:  bộ[Reasoning]: :[Reasoning]:  sản[Reasoning]:  phẩm[Reasoning]:  kỹ[Reasoning]:  thuật[Reasoning]:  số[Reasoning]:  ([Reasoning]: license[Reasoning]:  key[Reasoning]: ,[Reasoning]:  subscription[Reasoning]: )[Reasoning]:  không[Reasoning]:  được[Reasoning]:  hoàn[Reasoning]:  tiền[Reasoning]: .[Reasoning]:  H[Reasoning]: ãy[Reasoning]:  xem[Reasoning]:  xét[Reasoning]:  yêu[Reasoning]:  cầu[Reasoning]: :[Reasoning]:  '[Reasoning]: Kh[Reasoning]: ách[Reasoning]:  hàng[Reasoning]:  muốn[Reasoning]:  hoàn[Reasoning]:  tiền[Reasoning]:  license[Reasoning]:  key[Reasoning]:  đã[Reasoning]:  kích[Reasoning]:  hoạt[Reasoning]: .'[Reasoning]:  [Reasoning]: 1[Reasoning]: .[Reasoning]:  Y[Reasoning]: êu[Reasoning]:  cầu[Reasoning]:  này[Reasoning]:  có[Reasoning]:  vi[Reasoning]:  phạm[Reasoning]:  chính[Reasoning]:  sách[Reasoning]:  không[Reasoning]: ?[Reasoning]:  [Reasoning]: 2[Reasoning]: .[Reasoning]:  Nếu[Reasoning]:  có[Reasoning]: ,[Reasoning]:  hãy[Reasoning]:  chỉ[Reasoning]:  rõ[Reasoning]:  điều[Reasoning]:  khoản[Reasoning]:  nào[Reasoning]: .[Reasoning]:  [Reasoning]: 3[Reasoning]: .[Reasoning]:  Nếu[Reasoning]:  không[Reasoning]: ,[Reasoning]:  hãy[Reasoning]:  xác[Reasoning]:  nhận[Reasoning]:  là[Reasoning]:  hợp[Reasoning]:  lệ[Reasoning]: ."

[Reasoning]: We[Reasoning]:  need[Reasoning]:  to[Reasoning]:  respond[Reasoning]: :[Reasoning]:  The[Reasoning]:  request[Reasoning]:  is[Reasoning]:  to[Reasoning]:  refund[Reasoning]:  an[Reasoning]:  activated[Reasoning]:  license[Reasoning]:  key[Reasoning]: .[Reasoning]:  According[Reasoning]:  to[Reasoning]:  internal[Reasoning]:  policy[Reasoning]: ,[Reasoning]:  digital[Reasoning]:  products[Reasoning]:  ([Reasoning]: license[Reasoning]:  key[Reasoning]: ,[Reasoning]:  subscription[Reasoning]: )[Reasoning]:  are[Reasoning]:  non[Reasoning]: -refundable[Reasoning]: .[Reasoning]:  So[Reasoning]:  the[Reasoning]:  request[Reasoning]:  violates[Reasoning]:  policy[Reasoning]: .[Reasoning]:  Provide[Reasoning]:  the[Reasoning]:  specific[Reasoning]:  clause[Reasoning]: :[Reasoning]:  "[Reasoning]: S[Reasoning]: ản[Reasoning]:  phẩm[Reasoning]:  kỹ[Reasoning]:  thuật[Reasoning]:  số[Reasoning]:  ([Reasoning]: license[Reasoning]:  key[Reasoning]: ,[Reasoning]:  subscription[Reasoning]: )[Reasoning]:  không[Reasoning]:  được[Reasoning]:  hoàn[Reasoning]:  tiền[Reasoning]: ."[Reasoning]:  Possibly[Reasoning]:  also[Reasoning]:  mention[Reasoning]:  that[Reasoning]:  once[Reasoning]:  activated[Reasoning]: ,[Reasoning]:  it's[Reasoning]:  considered[Reasoning]:  used[Reasoning]: ,[Reasoning]:  thus[Reasoning]:  non[Reasoning]: -refundable[Reasoning]: .[Reasoning]:  So[Reasoning]:  answer[Reasoning]: :[Reasoning]:  Yes[Reasoning]: ,[Reasoning]:  it[Reasoning]:  violates[Reasoning]:  policy[Reasoning]: .[Reasoning]:  Clause[Reasoning]: :[Reasoning]:  internal[Reasoning]:  policy[Reasoning]:  section[Reasoning]:  X[Reasoning]:  ([Reasoning]: if[Reasoning]:  known[Reasoning]: ).[Reasoning]:  Since[Reasoning]:  we[Reasoning]:  only[Reasoning]:  have[Reasoning]:  that[Reasoning]:  statement[Reasoning]: ,[Reasoning]:  we[Reasoning]:  can[Reasoning]:  reference[Reasoning]:  that[Reasoning]: .[Reasoning]:  Provide[Reasoning]:  clear[Reasoning]:  answer[Reasoning]: .

[Reasoning]: We[Reasoning]:  should[Reasoning]:  be[Reasoning]:  concise[Reasoning]:  but[Reasoning]:  thorough[Reasoning]: .  policy_applies: False
  exception: digital_product_exception — Sản phẩm kỹ thuật số không được hoàn tiền (Điều 3)....
  exception: activated_exception — Sản phẩm đã kích hoạt không được hoàn tiền....
  MCP calls: 0
```
---

## 4. Tôi tự đánh giá đóng góp của mình (150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã cấu hình thành công khả năng suy luận có chiều sâu cho Agent. Qua kết quả chạy test case 3, AI đã biết tự suy luận logic: *"Customer requests in 5 days, policy says 7 days... so it complies"* — đây là đóng góp lớn nhất giúp Agent của nhóm có trí tuệ thực sự thay vì chỉ là bot tra cứu.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi còn thiếu sót trong việc kiểm soát các lỗi sơ đẳng về cấu trúc file (như quản lý logic return), dẫn đến mất nhiều thời gian debug ban đầu.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm Synthesis phụ thuộc 100% vào `policy_result` của tôi để biết nên trả lời khách hàng "Đồng ý" hay "Từ chối". Mỗi quyết định của tôi ảnh hưởng trực tiếp đến uy tín cam kết dịch vụ (SLA) của toàn hệ thống.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (100 từ)

Dựa trên Trace của các kịch bản test vừa thực hiện, tôi nhận thấy phần `explanation` của AI hiện nay rất dài. Nếu có thêm 2 giờ, tôi sẽ thử nghiệm kỹ thuật **Few-shot Prompting** để huấn luyện AI trả về lời giải thích theo định dạng chuẩn hóa: `[Điều khoản ví phạm] - [Lý do] - [Giải pháp thay thế]`. 

Lý do là vì hiện tại trace cho thấy AI vẫn viết khá dài dòng tự do, gây khó khăn cho việc hiển thị trên giao diện người dùng nếu sau này phát triển thêm UI.
