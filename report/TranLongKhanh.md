# Báo cáo vai trò thành viên — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Trần Long Khánh |
| MSSV | 2A202602538 |
| Khóa/Lớp | K4 |
| Tên nhóm | ActionPlan |
| Vai trò chính | Corruption, repair & integration review |
| Repository | <https://github.com/ilkhangnd/K4-L3-DAY10-ActionPlan-DataPipeline> |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Bộ tiêm lỗi có kiểm soát | `src/ingestion/corruption.py` — `corrupt_clean_dataframe` | Clean dataframe 24 dòng | Corrupted dataframe và `corruption_log.json` đủ 6 lỗi | Hoàn thành |
| Luồng phục hồi idempotent | `src/pipelines/corruption_flow.py` — `main` | Raw records, baseline metrics, test set cố định | Corrupted/repaired artifacts, hash kiểm chứng, 3 Chroma collections | Hoàn thành |
| Báo cáo đối chiếu | `src/observability/reporting.py` — `generate_corruption_report` | Metrics, GX và freshness của ba trạng thái | `data/reports/corruption_report.md` | Hoàn thành |
| Dashboard và nghiệm thu CP6 | `streamlit_app.py`, `script/verify_submission.py` | Các JSON/CSV/Markdown artifact | UI review và 13 kiểm tra tự động | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Module được hỗ trợ | Kết quả |
|---|---|---|
| Kiểm tra khả năng chạy offline | `src/retrieval/embeddings.py` | Loader ưu tiên model cache cục bộ, tránh HEAD request không cần thiết |
| Rà soát CP5/CP6 theo README và rubric | Toàn pipeline | Hai entrypoint chạy exit code 0; checklist tự động PASS |
| Chuẩn bị live demo | `docs/DEMO.md` | Có kịch bản 3–5 phút và bộ câu hỏi phản biện kỹ thuật |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Tiêm sáu dạng lỗi xác định | `corruption.py`, `corruption_log.json` | Drop 5 bản ghi mới, blank 3 summary, inject noise 3 summary, truncate 3 title, stale 8 date, duplicate 3 dòng | Kiểm tra `scenario_count = 6` và danh sách `paper_ids` trong log |
| Tự động kích hoạt repair | `corruption_flow.py` | GX/freshness fail ở dữ liệu lỗi làm `repair_triggered_by_failed_gate = true` | Chạy `python script/run_corruption_flow.py` |
| Chứng minh idempotency | `repair_verification.json` | Hai lần repair cho cùng SHA-256; repaired khớp baseline; test set không đổi | Đối chiếu ba hash dataframe và hash test set |
| Chứng minh suy giảm/phục hồi | Ba file metrics | Hit Rate `1.00 → 0.80 → 1.00`; Token F1 `1.00 → 0.50 → 1.00` | Mở `corruption_report.md` hoặc dashboard |
| Nghiệm thu tự động | `verify_submission.py` | 13/13 kiểm tra PASS | Chạy `python script/verify_submission.py` |

Output tiêu biểu là `data/results/repair_verification.json`. Artifact này ghi rõ raw artifact dùng để repair, lý do kích hoạt repair, hai hash của hai lần dựng lại dataframe, hash baseline, và hash test set trước/sau. Vì các hash trùng nhau, kết luận “repair idempotent và không làm thay đổi benchmark” có thể kiểm chứng độc lập.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

RAG có thể tiếp tục trả lời trôi chảy dù dữ liệu bị thiếu, trùng, rỗng, nhiễu hoặc quá cũ. Phần việc này cần tạo lỗi có chủ đích đủ mạnh để Quality Gate và benchmark phát hiện, sau đó phục hồi từ nguồn raw đáng tin cậy mà không sửa chắp vá dữ liệu lỗi.

### Cách triển khai

Corruption suite chọn bản ghi theo quy tắc xác định để mọi lần chạy có thể so sánh trực tiếp. Sáu lỗi được áp dụng lên bản sao của clean dataframe; sau mọi thay đổi, `summary_chars` và `text_for_embedding` được dựng lại để index thật sự nhận dữ liệu lỗi. Luồng orchestration chạy GX/freshness trước, tự kích hoạt repair khi gate fail, xây collection `papers-corrupted`, đánh giá bằng test set hiện có, rồi dựng lại dữ liệu từ `data/raw/crossref_records.json`.

Repair được chạy hai lần với cùng `run_date`. `pandas.testing.assert_frame_equal` và SHA-256 chứng minh hai kết quả giống nhau. Test set cũng được hash trước và sau để bảo đảm baseline, corrupted và repaired dùng đúng một benchmark. Cuối cùng, pipeline tạo collection `papers-repaired`, đánh giá lại và sinh báo cáo ba trạng thái.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | Canonical clean dataframe; raw `PaperRecord`; `test_set.json`; baseline metrics |
| Output | Corrupted/repaired CSV+JSON, embedding manifests, answer logs, metrics, quality/freshness reports, comparison report |
| Module phụ thuộc | `cleaning.py`, `crossref.py`, `quality.py`, `metrics.py`, `index.py` |
| Module sử dụng output | `reporting.py`, `verify_submission.py`, `streamlit_app.py` |
| Điều kiện lỗi cần xử lý | Thiếu baseline artifact; corruption không kích hoạt gate; repaired data vẫn fail; test set bị thay đổi; repair không idempotent |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
uv run python script/verify_submission.py
uv run streamlit run streamlit_app.py
```

- **Kết quả mong đợi:** baseline PASS; corrupted FAIL và metric giảm; repaired PASS, metric về baseline; verifier exit code 0.
- **Kết quả thực tế:** cả hai pipeline exit code 0; verifier báo 13/13 PASS; dashboard đọc được đầy đủ artifact.
- **Artifact/log:** `data/results/`, `data/quality/`, `data/reports/`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Có thể sửa từng ô dữ liệu lỗi tại chỗ hoặc dựng lại toàn bộ clean dataset từ raw snapshot.
- **Các phương án đã cân nhắc:** (1) đảo ngược từng corruption trên corrupted dataframe; (2) tái tạo canonical dataframe từ raw records rồi rebuild index.
- **Phương án đã chọn:** Tái tạo từ raw records.
- **Lý do:** Sửa ngược từng lỗi phụ thuộc vào lịch sử mutation, dễ bỏ sót duplicate/drop và không đảm bảo idempotency. Dựng lại từ raw giữ lineage rõ, cô lập trạng thái và có thể chạy lặp lại.
- **Bằng chứng:** `baseline_dataframe_sha256`, `first_repair_dataframe_sha256` và `second_repair_dataframe_sha256` cùng giá trị `a4412bd1...98c91e2`; `baseline_matches_repaired = true`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Lần chạy corruption đầu tiên dừng khi `SentenceTransformer` gửi HEAD request tới Hugging Face và nhận `WinError 10013`, dù model vừa được tải vào cache.
- **Lệnh tái hiện:** `uv run python script/run_corruption_flow.py` sau khi baseline đã tải MiniLM.
- **Nguyên nhân gốc:** Mỗi process mới khởi tạo model theo tên remote; thư viện vẫn kiểm tra metadata online trước khi dùng cache.
- **Cách xử lý:** Sửa `_load_model` để gọi `SentenceTransformer(..., local_files_only=True)` trước, chỉ fallback tải remote khi cache chưa tồn tại.
- **Cách xác minh sau khi sửa:** Chạy lại corruption flow trong môi trường không cho phép request; pipeline hoàn tất exit code 0.
- **Điều học được:** “Có cache” chưa đồng nghĩa “offline-safe”; cần chủ động cấu hình client ưu tiên tài nguyên local.

## 7. Hiểu biết về luồng end-to-end

1. Crossref API hoặc snapshot được parse thành raw `PaperRecord`; cleaning chuẩn hóa text, ngày, tác giả, category, khử trùng theo DOI và tạo `text_for_embedding`; MiniLM biến text thành vector và ChromaDB lưu vector cùng metadata.
2. Mỗi câu hỏi trong evaluation set có `ground_truth` và `ground_truth_doc_ids`. Retrieval Hit Rate kiểm tra tài liệu đúng có xuất hiện trong top-k; Token F1 và judge so câu trả lời với ground truth.
3. GX kiểm tra row count, null, uniqueness và độ dài summary; freshness đo tỷ lệ `age_days > 180`. Vì vậy dữ liệu đúng schema vẫn có thể vi phạm độ tươi.
4. Giữ nguyên test set loại bỏ biến nhiễu do thay câu hỏi/ground truth. Hash `4d330a1c...38f8fc7` được giữ nguyên trong toàn flow.
5. Repair thành công khi repaired GX/freshness PASS, dataframe khớp baseline, hai lần repair cùng hash, test set không đổi và bốn metric trở lại mức baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | Mất 20 điểm phần trăm do drop/truncate làm thất lạc tài liệu đúng; repair phục hồi hoàn toàn |
| `mean_token_f1` | 1.00 | 0.50 | 1.00 | Giảm mạnh nhất vì blank/noise/stale làm sai nội dung câu trả lời |
| `judge_accuracy` | 1.00 | 0.50 | 1.00 | Heuristic judge xác nhận 5/10 câu bị sai đáng kể ở trạng thái lỗi |
| `mean_judge_score` | 5.00 | 3.00 | 5.00 | Giảm 2 điểm rồi trở lại mức tối đa |
| Quality checks | PASS | FAIL | PASS | GX bắt được summary rỗng và DOI trùng |
| Freshness status | FRESH (0%) | STALE (50%) | FRESH (0%) | Vượt ngưỡng cho phép 25% ở trạng thái lỗi |

### Kết luận từ số liệu

1. Drop latest + blank/noise/truncate + stale/duplicate → GX fail và stale ratio tăng từ 0% lên 50% → Hit Rate giảm còn 0.80, Token F1 và Judge Accuracy giảm còn 0.50.
2. Rebuild từ raw snapshot → GX/freshness trở lại PASS/FRESH, hash repaired trùng baseline → toàn bộ metric trở lại `1.00/1.00/1.00/5.00`.

Corruption ảnh hưởng rõ nhất đến chất lượng câu trả lời là `blank_summary` kết hợp `inject_noise`: exact lookup vẫn có thể tìm đúng DOI nhưng nội dung dùng để trả lời đã rỗng hoặc bắt đầu bằng chuỗi rác, khiến Token F1 giảm sâu hơn Hit Rate. Kết quả đáng chú ý là Hit Rate chỉ giảm 20% trong khi answer metric giảm 50%; điều này chứng minh retrieval đúng chưa đủ nếu metadata/context bên trong đã hỏng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw preservation và stable document ID là nền tảng để repair có thể tái tạo dữ liệu thay vì đoán cách hoàn tác lỗi.
2. Observability cần kết hợp constraint-based checks với SLA freshness; chỉ một nhóm kiểm tra sẽ bỏ sót lỗi còn lại.
3. Đánh giá RAG phải tách retrieval quality khỏi answer quality: tìm đúng tài liệu không bảo đảm câu trả lời đúng khi context bị corruption.

### Nếu có thêm thời gian

Tôi sẽ bổ sung CI chạy unit/integration tests với dữ liệu fixture nhỏ, đo coverage trên corruption, quality, repair và dashboard. Điều kiện cải thiện là pipeline chạy offline trong CI, coverage trên 80%, và pull request bị chặn nếu repaired metrics không trở lại baseline.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo khớp với code, artifact và metric của phiên bản hiện tại.
- [x] Mọi kết luận kỹ thuật đều có artifact hoặc lệnh kiểm chứng đi kèm.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Nội dung không sao chép nguyên văn báo cáo nhóm hay báo cáo của thành viên khác.
- [ ] Tôi đã tự đọc lại, có thể giải thích luồng end-to-end và xác nhận nội dung phản ánh đúng phần đóng góp cá nhân của mình.

**Họ và tên:** Trần Long Khánh  
**Ngày xác nhận:** 25/09/2026
