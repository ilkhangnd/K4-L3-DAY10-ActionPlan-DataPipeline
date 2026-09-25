# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên nhóm:** `ActionPlan`
- **Mã nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-ActionPlan-DataPipeline`

---

## Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Đình Khang | 2A202602584 | 26ai.khangnd2@vinuni.edu.vn | **Trưởng nhóm; Pha 2 & phối hợp Pha 6.** Thu thập Crossref, cleaning, GX/freshness; safe repair và đối chiếu ba trạng thái. | [`2A202602584_NguyenDinhKhang.md`](../report/2A202602584_NguyenDinhKhang.md) |
| 2 | Phạm Hồ Quang Dũng | 2A202602860 | 26ai.dungphq@vinuni.edu.vn | **Pha 3.** Benchmark test set, MiniLM embedding, ChromaDB vector index và smoke test retrieval. | [`2A202602860_PhamHoQuangDung.md`](../report/2A202602860_PhamHoQuangDung.md) |
| 3 | Ngô Gia Quốc | 2A202602757 | 26ai.quocng@vinuni.eu.vn | **Pha 4.** Tích hợp baseline pipeline, baseline evaluation/report và portability khi nạp index. | [`2A202602757_NgoGiaQuoc.md`](../report/2A202602757_NgoGiaQuoc.md) |
| 4 | Trần Long Khánh | 2A202602538 | — | **Pha 5 & phối hợp Pha 6.** Bộ corruption sáu kịch bản, corruption flow, repair/integration và nghiệm thu báo cáo đối chiếu. | [`2A202602538_TranLongKhanh.md`](../report/2A202602538_TranLongKhanh.md) |

---

## Cá nhân

### Nguyễn Đình Khang — 2A202602584

- **Vai trò:** Trưởng nhóm; phụ trách **Pha 2 - Thu thập dữ liệu, làm sạch & Data Quality Gate GX 1.x** và phối hợp **Pha 6** cùng Khánh.
- **Công việc chi tiết đã hoàn thành:**
  - Hoàn thiện `src/ingestion/crossref.py`: parse DOI, title, abstract, authors, categories và ngày ISO; có fallback từ Crossref API sang snapshot offline.
  - Hoàn thiện `src/ingestion/cleaning.py`: chuẩn hóa schema, tạo `age_days`, `summary_chars`, `text_for_embedding` và deduplicate theo `paper_id`.
  - Xây dựng Data Quality Gate GX 1.x trong `src/observability/quality.py`: row count, required fields, DOI unique, summary length và Freshness SLA.
  - Phối hợp **Pha 6**: safe repair bằng cách dựng lại từ raw records, kiểm tra lại quality/freshness và đối chiếu Baseline → Corrupted → Repaired qua `corruption_flow.py` và `corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Raw snapshot và data lineage là điều kiện để repair có thể tái lập; không sửa chắp vá corrupted dataframe.
  - Retrieval Hit Rate có thể giữ nguyên trong khi Token F1/judge giảm, nên cần xem đồng thời quality, freshness và answer metrics để phát hiện silent failure.

### Phạm Hồ Quang Dũng — 2A202602860

- **Vai trò:** Phụ trách **Pha 3 — Benchmark Test Set và ChromaDB Vector Index**.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng `src/evaluation/testset.py` để sinh test set source-grounded, có `id`, `type`, `question`, `ground_truth` và `ground_truth_doc_ids`.
  - Tích hợp `sentence-transformers/all-MiniLM-L6-v2`, xây ChromaDB collection baseline từ trường `text_for_embedding` và lưu metadata truy vết DOI/title/authors/date/category/summary.
  - Kiểm tra semantic search và tính portable của embedding manifest khi nạp trên máy khác.
- **Điều học được / Đóng góp chính:**
  - Test set cố định với DOI ground truth giúp so sánh baseline, corrupted và repaired công bằng.
  - Vector index chỉ đáng tin khi document identity và metadata được bảo toàn xuyên suốt pipeline.

### Ngô Gia Quốc — 2A202602757

- **Vai trò:** Phụ trách **Pha 4 — Baseline Pipeline Integration & Reporting**.
- **Công việc chi tiết đã hoàn thành:**
  - Ghép các module thành entrypoint `src/pipelines/phase1.py`: raw → clean → quality/freshness → index → test set → evaluation → report.
  - Tạo baseline metrics, answer log và `data/reports/phase1_report.md`; quality gate được chạy trước bước index.
  - Kiểm tra test set có DOI thuộc clean corpus trước evaluation; hỗ trợ portability khi load Chroma manifest và tránh phụ thuộc artifact nhị phân trên Git.
- **Điều học được / Đóng góp chính:**
  - Artifact tồn tại không đồng nghĩa artifact hợp lệ: test set cũ lệch corpus có thể làm metric sai dù pipeline không lỗi.
  - Baseline tái lập là mốc cần thiết để đánh giá chính xác degradation và repair ở các pha sau.

### Trần Long Khánh — 2A202602538

- **Vai trò:** Phụ trách **Pha 5 — Data Corruption** và phối hợp **Pha 6 — Repair & Comparison**.
- **Công việc chi tiết đã hoàn thành:**
  - Hoàn thiện `src/ingestion/corruption.py` với sáu kịch bản xác định: drop latest records, blank summary, inject text noise, truncate title, stale date và duplicate rows.
  - Ghi đầy đủ log về scenario, DOI bị tác động và số dòng tại `data/results/corruption_log.json`.
  - Phối hợp Pha 6: hoàn thiện/rà soát `corruption_flow.py`, kiểm tra khả năng chạy offline của embedding loader, repair flow và báo cáo đối chiếu trước nghiệm thu.
- **Điều học được / Đóng góp chính:**
  - Các lỗi dữ liệu khác nhau có tín hiệu khác nhau: duplicate/blank summary bị GX phát hiện, stale date cần Freshness SLA, còn noise có thể chỉ lộ qua evaluation.
  - Corruption cần xác định và có log để degradation/recovery có thể so sánh, giải thích và tái hiện.

---

## Quy ước phối hợp

1. Pha 2 tạo clean-data contract cho Pha 3 và Pha 4.
2. Pha 3 bàn giao test set/index cho baseline evaluation ở Pha 4.
3. Pha 5 tiêm lỗi có kiểm soát; Pha 6 do Nguyễn Đình Khang và Trần Long Khánh phối hợp dựng lại dữ liệu từ raw source, kiểm tra repair flow và xác minh phục hồi qua quality/freshness/metrics.
4. Cả nhóm dùng chung `data/eval/test_set.json` để ba trạng thái có thể so sánh công bằng.
5. Không commit `.env` hoặc API key; mỗi thành viên tự nộp link repository nhóm theo quy định LMS.
