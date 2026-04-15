# Runbook — Lab Day 10 (Incident Response)

---

## Symptom

- Trợ lý AI (Agent) nhắc lại policy quá hạn (Ví dụ: khách hỏi chính sách hoàn tiền, Bot phản hồi "Sẽ đổi trả trong 14 ngày làm việc" thay vì quy định mới là 7 ngày).
- Agent trích dẫn nội dung thô chứa thẻ HTML `<script>`, thư mục báo lỗi, hoặc các bản nháp chứa chữ "TBD", "lỗi migration".
- Người dùng tra cứu báo cáo "không tìm thấy policy X", nguyên do ETL pipeline bị sập ngầm ở chặng Ingestion và không hề update data vào ứng dụng RAG.

---

## Detection

- Pipeline khựng lại (Halt) khi các bộ Expectation Rules bắt được dữ liệu không sạch:
  - `expectation[refund_no_stale_14d_window] FAIL (halt): violations > 0`
  - `expectation[no_placeholder_in_cleaned] FAIL (halt): placeholder_chunks > 0`
  - `expectation[hr_leave_no_stale_10d_annual] FAIL (halt)`
- Freshness module báo **FAIL** trên Dashboard: Lệnh `python etl_pipeline.py freshness` phát hiện vi phạm SLA age_hours.
- Theo dõi log `artifacts/manifests/*.json` thấy độ chênh lệch cực lớn khi `quarantine_records` vượt ngưỡng an toàn (ví dụ trên 50% số lượng `raw_records`).

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Xác định file `artifacts/manifests/manifest_<run_id>.json` của run lỗi | Xác định tỷ lệ Raw vs Clean. Đánh giá xem có Expectation nào bị fail khiến lệnh chạy halt không. |
| 2 | Mở file csv `artifacts/quarantine/quarantine_<run_id>.csv` của lần chạy lỗi | Tìm xem cột `reason` là gì (Vd: `contains_draft_or_error_keywords`, `chunk_text_too_short`). Nhận diện phòng ban (domain owner) đẩy rác vào. |
| 3 | Chạy kịch bản Retrieval Test Offline: `python grading_run.py --out artifacts/eval/grading_run.jsonl` | Báo cáo Log sẽ hiển thị dòng `hits_forbidden=true`, chứng minh Document lạc hậu/bị cấm đang nằm lù lù trong Vector DB. |

---

## Mitigation

1. **Rerun Extract bằng Clean Mode:** Chạy lại dòng lệnh chữa lửa `python etl_pipeline.py run` và đảm bảo biến số sửa data `apply_refund_window_fix` được bật, để hệ thống tự động châm chước vá và cứu các dòng lỗi Quarantine, đưa bản Data sạch lên lưu trữ.
2. **Prune Vector Store:** Dựa vào hàm `embed_prune_removed` để tự sửa, tự loại bỏ vector thừa. Trong sự kiện Chroma index ngộ độc quá sâu (bug hệ thống), ngắt kết nối agent đi, xóa thư mục vật lý `chroma_db/`, và cho gọi ETL chạy nạp fresh data lại từ file CSV sạch 100%.
3. **Rollback Source:** Quay Collection của ứng dụng RAG về database an toàn của ngày hôm trước (Day T-1) nếu file gốc csv lấy về của ngày hôm nay quá trình độ cứu chữa logic.

---

## Prevention

- **Sửa Luật Nguồn Gốc:** Ký kết chặt chẽ theo `data_contract.md` với các team nghiệp vụ HR, CS. Yêu cầu không nhồi nguyên liệu Draft nháp vào chunk Data published.
- **Tăng Cường Chắn Rác (Guardrails):** Đội Data Quality định kỳ update các cụm từ bẩn / format xấu vào Expectation `halt` tại file `quality/expectations.py` để chặn đứng từ tầng ETL, không để chúng kịp xuất hiện ở Vector DB.
- **Alert Tự Động Pipeline:** Gắn Freshness Check cronjob chạy báo động, ping notification trực tiếp cho Data Engineer khi SLA bị quá hạn (stale_data).
