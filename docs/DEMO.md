# CP6 Live Demo & Q&A Runbook

## Kịch bản demo 3–5 phút

1. Chạy baseline và chỉ ra `gx_success=True`, freshness `is_fresh=True`, cùng bốn metric nền:

   ```bash
   python script/run_phase1.py
   ```

2. Chạy luồng lỗi và phục hồi:

   ```bash
   python script/run_corruption_flow.py
   ```

3. Trên console, giải thích ba tín hiệu chính:

   - đủ 6 loại corruption đã được ghi vào `data/results/corruption_log.json`;
   - quality/freshness gate chuyển từ PASS sang FAIL và tự kích hoạt repair;
   - bảng Baseline / Corrupted / Repaired cho thấy metric suy giảm rồi trở về mức nền.

4. Mở `data/reports/corruption_report.md` và `data/results/repair_verification.json` để chứng minh repair đọc lại raw records, chạy hai lần cho cùng hash, và không thay đổi test set.

5. Chạy kiểm tra nghiệm thu một lệnh:

   ```bash
   python script/verify_submission.py
   ```

6. Mở dashboard review (không gọi model/API, chỉ đọc artifact đã sinh):

   ```bash
   streamlit run streamlit_app.py
   ```

## Q&A kỹ thuật ngắn

**Vì sao đây là silent failure?** Ứng dụng vẫn trả lời bình thường trên index bị lỗi; chỉ observability signal và benchmark cho thấy dữ liệu thiếu, trùng, cũ hoặc câu trả lời sai.

**GX và freshness khác nhau thế nào?** GX kiểm tra cấu trúc/completeness/uniqueness/độ dài; freshness kiểm tra tỷ lệ bản ghi vượt SLA 180 ngày. Một dataset có thể hợp lệ về schema nhưng vẫn quá cũ.

**Vì sao giữ nguyên test set?** Thay câu hỏi hoặc ground truth giữa ba trạng thái sẽ làm phép so sánh mất tính công bằng. Pipeline kiểm tra SHA-256 của test set trước và sau luồng.

**Vì sao repair là idempotent?** Repair không sửa nối tiếp trên dữ liệu bẩn mà dựng lại canonical dataframe từ raw snapshot. Hai lần chạy với cùng input và run date tạo cùng dataframe hash.

**Vì sao dùng ba Chroma collection?** Tách `papers-baseline`, `papers-corrupted`, `papers-repaired` ngăn trạng thái cũ rò rỉ và giúp đối chiếu độc lập.

**Nếu LLM/API không truy cập được thì sao?** Retrieval và Token F1 vẫn chạy offline; LLM judge tự hạ xuống heuristic judge. Raw ingestion cũng có snapshot fallback.

## Việc thủ công trước khi nộp

- Điền đúng tên nhóm, thành viên, MSSV và repository trong `docs/TEAM.md` và `report/`.
- Kiểm tra `.env` không được Git theo dõi.
- Kiểm tra mọi thành viên xuất hiện tại GitHub **Insights → Contributors** trên nhánh `main`.
- Mỗi thành viên tự nộp link repository lên LMS đúng hạn.
