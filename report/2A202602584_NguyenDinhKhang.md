# Báo cáo vai trò thành viên — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Đình Khang |
| MSSV | 2A202602584 |
| Khóa/Lớp | K4 (K4-L3-DAY10) |
| Tên nhóm | [ActionPlan] |
| Vai trò chính | Trưởng nhóm — Thu thập dữ liệu, làm sạch & Data Quality Gate; phục hồi an toàn, đối chiếu 3 trạng thái (Pha 2 & Pha 6) |
| Repository | <https://github.com/ilkhangnd/K4-L3-DAY10-ActionPlan-DataPipeline> |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Nạp và chuẩn hóa Crossref | `src/ingestion/crossref.py` — `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | API response hoặc snapshot JSON | `PaperRecord`, `data/raw/crossref_records.json` | Hoàn thành |
| Làm sạch dữ liệu RAG | `src/ingestion/cleaning.py` — `build_clean_dataframe` | `PaperRecord`, thời điểm chạy UTC | `papers_clean.csv/.json`, `age_days`, `text_for_embedding` | Hoàn thành |
| Quality Gate và freshness | `src/observability/quality.py` — `run_data_quality_checks`, `build_freshness_report` | DataFrame và `Settings` | GX/freshness report cho baseline, corrupted, repaired | Hoàn thành |
| Repair và đối chiếu ba trạng thái | `src/pipelines/corruption_flow.py` — `main`, `_require_baseline_artifacts` | Baseline artifacts, raw records, test set cố định | Repaired artifacts và `data/reports/corruption_report.md` | Hoàn thành |

Phase 2 tạo clean-data contract cho benchmark, embedding và baseline pipeline. Ở Phase 6, raw artifact được giữ làm nguồn đáng tin cậy để dựng lại trạng thái repaired; kết quả repaired được đối chiếu với baseline và corrupted trên cùng benchmark.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chuẩn hóa đường dẫn artifact | `core.config.Paths` và các pipeline | Các artifact clean, quality, metrics và report dùng cùng quy ước dưới `data/` |
| Kiểm tra nguồn offline | Các bước embedding/evaluation dùng raw data | Snapshot `data/raw/crossref_response.json` giúp pipeline vẫn có 24 bản ghi khi API không phản hồi |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Parse DOI, title, abstract, tác giả, category và ngày Crossref | `src/ingestion/crossref.py` | 24 `PaperRecord` chuẩn hóa; DOI lowercase, abstract sạch HTML/JATS | `fetch_source_records()` trả 24 records |
| Dựng clean dataframe và embedding text | `src/ingestion/cleaning.py`, `data/clean/papers_clean.json` | 24 DOI unique, 16 cột canonical | `build_clean_dataframe()` trả 24 dòng |
| Chạy GX 1.x ephemeral | `src/observability/quality.py`, baseline quality report | Baseline quality/freshness PASS | `run_data_quality_checks(..., "test")['success']` là `True` |
| Rebuild dữ liệu repaired từ raw, không vá dataframe lỗi | `corruption_flow.py`, `papers_clean_repaired.json` | Repaired có 24 dòng, quality/freshness PASS | Chạy `python script/run_corruption_flow.py` |
| Báo cáo ba trạng thái | `data/reports/corruption_report.md` | So sánh chung một test set 5 câu | Đối chiếu report với JSON metrics trong `data/results/` |

Output tiêu biểu là `data/quality/corrupted_quality_report.json`. Artifact này cho thấy corrupted state vẫn có 24 dòng nhưng FAIL: DOI unique có 10 giá trị unexpected (5 DOI xuất hiện hai lần), summary length có 4 summary rỗng và freshness có 8/24 bài cũ hơn 180 ngày (33.33%). Vì vậy, chỉ kiểm tra số dòng không đủ để khẳng định dữ liệu sạch.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline không nên phụ thuộc hoàn toàn vào Crossref API vì rate-limit hoặc mất mạng có thể làm gián đoạn lab. Dữ liệu lấy về cần được chuẩn hóa trước khi tạo embedding. RAG cũng có thể tiếp tục trả lời khi corpus bẩn, nên cần Quality Gate độc lập và repair tái lập được từ raw artifact thay vì sửa chắp vá dataframe corrupted.

### Cách triển khai

- **Thu thập có fallback:** `fetch_source_records()` thử gọi Crossref hai lần với timeout 12 giây. Khi request lỗi HTTP/mạng, response không hợp lệ hoặc API quá tải, hàm đọc `data/raw/crossref_response.json`. Snapshot không bị ghi đè khi remote fetch thất bại.
- **Chuẩn hóa Crossref:** DOI bỏ prefix `doi:`/URL và chuyển lowercase; title và text được gom khoảng trắng; abstract được `html.unescape` rồi bỏ tag HTML/JATS. Ngày ưu tiên `published`, sau đó là `published-print`, `published-online` và `issued`; date-parts thiếu tháng/ngày được chuẩn hóa thành ISO 8601 hợp lệ.
- **Clean contract:** Bản ghi thiếu DOI, title, summary hoặc ngày publish bị loại. `age_days` là chênh lệch giữa ngày chạy UTC và `published`. `text_for_embedding` ghép title, authors, published, categories và summary theo template cố định. Cuối bước dataframe được deduplicate theo `paper_id`, sort và reset index.
- **GX và freshness tách bạch:** GX 1.x chạy bằng `gx.get_context(mode="ephemeral")`, pandas data source, dataframe asset và whole-dataframe batch trong RAM. Sáu expectation thuộc bốn nhóm rule: row count 5–5000; ba cột bắt buộc không null; DOI unique; summary tối thiểu 30 ký tự. Freshness đo riêng tỷ lệ `age_days > 180`; SLA PASS khi tỷ lệ không quá 25%.
- **Safe repair:** Corruption flow vẫn index/evaluate corrupted corpus để đo silent failure, nhưng repaired không lấy corrupted dataframe làm input. Flow gọi `load_raw_records()` và `build_clean_dataframe()`, ghi file repaired riêng, chạy lại quality/freshness, xây repaired index và evaluate bằng test set giữ nguyên.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input Phase 2 | Crossref `message.items`, snapshot local, `PaperRecord`, `run_date` timezone-aware |
| Output Phase 2 | Raw normalized records; clean CSV/JSON gồm DOI, title, summary, authors/categories, published, `age_days`, `text_for_embedding` |
| Input Phase 6 | Clean data, raw records, test set, baseline metrics/quality/freshness artifacts |
| Output Phase 6 | Corrupted/repaired data, embedding manifests, quality/freshness reports, metrics/answers và comparison report |
| Module phụ thuộc | `core.config`, `core.utils`, `ingestion.corruption`, `evaluation.metrics`, `retrieval.index`, `observability.reporting` |
| Module sử dụng output | `evaluation.testset`, `retrieval.index`, `pipelines.phase1`, `pipelines.corruption_flow`, UI demo |
| Điều kiện lỗi cần xử lý | API unavailable; source fields thiếu; baseline artifact thiếu; GX/freshness fail; raw records không đọc được |

### Cách xác minh

```bash
# Phase 2 — chạy từ project root sau khi đã `source .venv/bin/activate`
# Bước 1: Crossref API hoặc snapshot offline
python -c 'from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f"Tín hiệu hoàn thành: Đã nạp {len(r)} bài báo")'

# Bước 2: Cleaning, age_days và text_for_embedding
python -c 'from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f"Tín hiệu hoàn thành: Clean thành công {len(df)} dòng")'

# Bước 3: Great Expectations 1.x + freshness check
python -c 'from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, "test"); print("Tín hiệu hoàn thành: Quality check status =", res["success"])'

# Phase 6
python script/run_corruption_flow.py
```

- **Tín hiệu Phase 2 mong đợi:** Lần lượt in `Tín hiệu hoàn thành: Đã nạp 24 bài báo`, `Tín hiệu hoàn thành: Clean thành công 24 dòng` và `Tín hiệu hoàn thành: Quality check status = True`. Bước 3 cũng ghi report kiểm tra tạm ở `data/quality/test_quality_report.json`.
- **Kết quả mong đợi Phase 6:** Corrupted FAIL, repaired PASS; repaired metrics quay về baseline.
- **Kết quả thực tế:** Artifacts hiện tại ghi 24 raw, 24 clean và 24 repaired records. Baseline quality/freshness PASS; corrupted quality/freshness FAIL; repaired quality/freshness PASS. Lệnh Phase 6 in `Corruption flow complete: baseline, corrupted, and repaired artifacts are ready.`
- **Artifact/log:** `data/raw/crossref_records.json`, `data/clean/papers_clean.json`, `data/quality/*_quality_report.json`, `data/quality/*freshness_report.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Sau khi tiêm lỗi có thể sửa trực tiếp ô rỗng, ngày cũ hoặc DOI trùng; nhưng cách đó cần biết chính xác mọi lỗi và dễ giữ lại noise hoặc sửa sai dữ liệu gốc.
- **Các phương án đã cân nhắc:** (1) Patch từng lỗi trên corrupted dataframe. (2) Dùng baseline clean dataframe đã lưu. (3) Bỏ corrupted dataframe, dựng lại từ raw records đã bảo toàn qua cùng cleaning function.
- **Phương án đã chọn:** (3), ghi output riêng thành `papers_clean_repaired.csv/.json`.
- **Lý do:** Raw snapshot có lineage rõ nhất; cùng input và cleaning rule tạo cùng nội dung nghiệp vụ. Cách này không phụ thuộc vào việc nhận biết đủ sáu corruption scenario, không ghi đè evidence corrupted và audit được ba trạng thái độc lập.
- **Bằng chứng quyết định phù hợp:** Repaired có 24 dòng, GX PASS, stale ratio 0.00%; retrieval hit rate, Token F1, judge accuracy và judge score đều bằng baseline trong comparison report.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `FileNotFoundError: Baseline artifacts are missing. Run 'python script/run_phase1.py' first: ...`
- **Lệnh hoặc bước tái hiện:** Chưa tạo một trong các file `papers_clean.json`, `test_set.json`, baseline metrics, baseline quality/freshness rồi chạy `python script/run_corruption_flow.py`.
- **Nguyên nhân gốc:** Corruption/repair không thể so sánh có ý nghĩa nếu thiếu clean corpus, benchmark hoặc baseline signals. Tiếp tục chạy sẽ tạo comparison report không có mốc tham chiếu.
- **Cách xử lý:** `_require_baseline_artifacts()` kiểm tra năm artifact bắt buộc trước khi tạo corrupted/repaired state. Nếu thiếu, flow dừng với thông báo lệnh cần chạy thay vì âm thầm tạo kết quả thiếu.
- **Cách xác minh sau khi sửa:** Chạy `python script/run_phase1.py`, rồi `python script/run_corruption_flow.py`; flow hoàn tất và sinh report/metrics ba trạng thái.
- **Điều học được:** Với pipeline nhiều giai đoạn, precondition cho artifact quan trọng cũng là data observability. Một bước không lỗi chưa bảo đảm phép so sánh là hợp lệ.

## 7. Hiểu biết về luồng end-to-end

1. **Từ Crossref đến vector index:** Response được parse thành `PaperRecord`; khi không có mạng, snapshot thay API. Cleaning chuẩn hóa, deduplicate, tính `age_days`, dựng `text_for_embedding`. Sau Quality Gate, Chroma index embed trường này bằng MiniLM và lưu metadata DOI, title, authors, published, category, summary.
2. **Evaluation set và ground-truth IDs:** Mỗi sample có câu hỏi, đáp án chuẩn và `ground_truth_doc_ids`. Retrieval hit được tính khi DOI đúng nằm trong top-k; Token F1 so answer với ground truth; LLM judge chấm answer quality. DOI giúp phép đo không phụ thuộc thứ tự dòng.
3. **Quality checks và freshness:** GX kiểm tra cấu trúc/nội dung: số dòng, null, duplicate DOI, summary ngắn. Freshness đo tỷ lệ bài quá 180 ngày. Dữ liệu có thể valid về schema nhưng vẫn cũ, nên cần cả hai signal.
4. **Cùng test set cho ba trạng thái:** Nếu benchmark đổi giữa các lần chạy, khác biệt metric có thể đến từ câu hỏi chứ không phải corruption/repair. Giữ nguyên `test_set.json` làm phép so sánh công bằng.
5. **Tiêu chí repair thành công:** Repaired phải được tạo từ raw source, sinh đủ artifact riêng, GX PASS, freshness PASS và đưa metrics về baseline. Hiện tại: 24 repaired records, stale ratio 0%, Token F1 0.8370 và judge score 4.4 đều khớp baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 | Hit rate không giảm ở 5 câu hiện tại; chỉ số này một mình chưa phát hiện silent failure. |
| `mean_token_f1` | 0.8370 | 0.6370 | 0.8370 | Corruption giảm 0.2000 (20 điểm phần trăm); repair khôi phục đúng baseline. |
| `judge_accuracy` | 0.8000 | 0.6000 | 0.8000 | Tỷ lệ answer đạt tiêu chí judge giảm 20 điểm phần trăm rồi phục hồi. |
| `mean_judge_score` | 4.4000 | 3.8000 | 4.4000 | Chất lượng answer giảm 0.6/5 rồi phục hồi. |
| Quality checks | PASS | FAIL | PASS | Corrupted fail DOI uniqueness và summary length; repaired pass toàn bộ. |
| Freshness status | PASS, 0/24 stale | FAIL, 8/24 stale (33.33%) | PASS, 0/24 stale | Freshness phát hiện stale-date injection vượt SLA 25%. |

Các số liệu lấy từ `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, quality reports và `corruption_report.md` của cùng bộ test 5 câu.

### Kết luận từ số liệu

1. **Blank summaries + duplicate DOI + stale dates** → GX fail (unique DOI, summary length) và freshness FAIL (33.33% > 25%) → dù hit rate vẫn 1.0, Token F1 giảm 0.8370 xuống 0.6370, judge accuracy giảm 0.8 xuống 0.6. Đây là silent failure: hệ thống vẫn trả lời nhưng answer quality đã suy giảm.
2. **Rebuild từ `crossref_records.json` bằng `build_clean_dataframe`** → GX PASS và freshness về 0% stale → Token F1, judge accuracy và judge score phục hồi về 0.8370, 0.8 và 4.4; hit rate giữ 1.0.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

Trong lần chạy này, nhóm lỗi blank summary, duplicate rows và noise ảnh hưởng rõ nhất đến F1/judge; stale date có signal freshness rõ nhất với 8/24 bản ghi vượt ngưỡng. Không nên quy toàn bộ F1 giảm cho một scenario vì 6 scenario được áp dụng cùng lúc trên state corrupted và test set chỉ có 5 câu.

**Kết quả nào khác với kỳ vọng ban đầu?**

Kỳ vọng trực giác là retrieval hit rate cũng sẽ giảm sau corruption, nhưng thực tế giữ 1.0. Khả năng cao là năm câu benchmark vẫn có DOI ground truth còn trong collection hoặc câu hỏi dùng title giúp exact lookup. Vì benchmark quá nhỏ, report dùng đồng thời Quality Gate, freshness, Token F1 và judge score thay vì suy luận từ hit rate duy nhất.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Fallback snapshot và canonical schema giúp pipeline tái lập khi external API không ổn định; raw data cần được giữ lại để truy vết và rebuild.
2. **Data quality/observability:** 24 dòng không có nghĩa là data sạch. Duplicate DOI, summary rỗng và bài quá cũ chỉ lộ ra khi GX expectation và freshness monitoring cùng chạy.
3. **Ảnh hưởng của data đến RAG agent:** RAG có thể giữ hit rate nhưng câu trả lời kém hơn. Cần đo cả retrieval, answer quality và data signals để tránh tin vào một metric đẹp.

### Nếu có thêm thời gian

Tôi sẽ mở rộng test set bằng câu hỏi paraphrase tiếng Việt/tiếng Anh không chứa nguyên title, đồng thời phân tầng theo loại corruption. Đo riêng hit rate, Token F1 và judge score cho từng nhóm trước/sau corruption sẽ giảm ảnh hưởng của exact-title lookup và cho biết scenario nào làm retrieval hay answer quality suy giảm.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đình Khang  
**Ngày xác nhận:** 2026-09-25
