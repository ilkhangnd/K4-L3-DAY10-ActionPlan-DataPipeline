# Báo cáo nhóm — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 — L3 Day 10 |
| Tên nhóm | ActionPlan |
| Repository | <https://github.com/ilkhangnd/K4-L3-DAY10-ActionPlan-DataPipeline> |
| Ngày hoàn thành | 2026-09-25 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Pha và deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Đình Khang | 2A202602584 | Trưởng nhóm; ingestion, cleaning, observability | **Pha 2** và phối hợp **Pha 6:** `crossref.py`, `cleaning.py`, `quality.py`; safe repair, quality/freshness và đối chiếu ba trạng thái |
| 2 | Phạm Hồ Quang Dũng | 2A202602860 | Benchmark & vector index | **Pha 3:** `evaluation/testset.py`, ChromaDB/MiniLM index, smoke test retrieval |
| 3 | Ngô Gia Quốc | 2A202602757 | Baseline integration & reporting | **Pha 4:** `pipelines/phase1.py`, baseline evaluation/report, tích hợp artifact và portability khi load index |
| 4 | Trần Long Khánh | 2A202602538 | Corruption, repair orchestration & integration review | **Pha 5** và phối hợp **Pha 6:** `ingestion/corruption.py`, `pipelines/corruption_flow.py`, `generate_corruption_report()` và nghiệm thu flow |

Pha 6 do Nguyễn Đình Khang và Trần Long Khánh phối hợp: Khang phụ trách contract raw-to-repaired, quality/freshness và đối chiếu ba trạng thái; Khánh phụ trách orchestration, corruption/comparison và nghiệm thu integration. Hai phần bổ trợ nhau trong cùng repair flow.

## 2. Tóm tắt kết quả

Nhóm hoàn thiện pipeline RAG data observability theo chuỗi Crossref → clean data → Great Expectations/freshness → ChromaDB → benchmark/evaluation → corruption → repair. Dữ liệu nguồn có 24 raw records và sau cleaning còn 24 clean records. Baseline tạo được CSV/JSON sạch, manifest embedding, collection `papers-baseline`, test set 10 câu, metrics/answers, quality/freshness reports và `phase1_report.md`.

Thử nghiệm corruption chủ động tạo sáu lỗi: bỏ bản ghi mới, summary rỗng, noise trong embedding text, title bị cắt, ngày stale và DOI trùng. Corrupted corpus vẫn có 24 dòng nhưng Quality Gate FAIL, freshness FAIL với 8/24 bài stale (33.33%), Retrieval Hit Rate giảm từ 1.0 xuống 0.8, Token F1 giảm từ 0.7403 xuống 0.5403 và judge score giảm từ 3.8 xuống 3.0.

Repair không patch dữ liệu lỗi tại chỗ mà dựng lại clean dataframe từ raw records đã lưu. Sau repair, GX/freshness đều PASS và các metrics quay về đúng baseline. Benchmark hiện có 10 câu source-grounded; Ragas chưa chạy vì `RUN_RAGAS` chưa được bật.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API / local snapshot
    -> raw response + normalized PaperRecord
    -> cleaning: normalize, validate, deduplicate, age_days, text_for_embedding
    -> GX 1.x Quality Gate + Freshness SLA
    -> MiniLM embedding + ChromaDB (papers-baseline)
    -> fixed source-grounded test set + baseline evaluation/report
    -> six corruption scenarios -> corrupted index/evaluation
    -> rebuild from preserved raw records -> repaired index/evaluation
    -> three-state comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref `/works` hoặc snapshot | Retry, fallback offline, parse DOI/text/date/authors/category | `data/raw/crossref_response.json`, `crossref_records.json` | Nguyễn Đình Khang — Pha 2 |
| Cleaning | `PaperRecord` | Normalize, loại record thiếu trường bắt buộc, deduplicate DOI, `age_days`, embedding text | `data/clean/papers_clean.csv/.json` | Nguyễn Đình Khang — Pha 2 |
| Observability | Clean/corrupted/repaired DataFrame | GX 1.x ephemeral và Freshness SLA | `data/quality/*quality_report.json`, `*freshness_report.json` | Nguyễn Đình Khang — Pha 2; phối hợp Pha 6 |
| Benchmark/index | Clean dataframe | Sinh test set source-grounded; MiniLM + Chroma cosine index | `data/eval/test_set.json`, `data/embeddings/`, `data/chroma/` | Phạm Hồ Quang Dũng — Pha 3 |
| Baseline orchestration | Các output Pha 2–3 | Quality trước index, evaluate, report baseline | `baseline_metrics.json`, `baseline_answers.json`, `phase1_report.md` | Ngô Gia Quốc — Pha 4 |
| Corruption/repair | Clean/raw data + fixed test set | Tiêm 6 lỗi, re-index/evaluate, rebuild từ raw, compare | Corrupted/repaired artifacts, `corruption_log.json`, `corruption_report.md` | Trần Long Khánh — Pha 5; Nguyễn Đình Khang & Trần Long Khánh — Pha 6 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| Python | `>=3.11,<3.14` |
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4.1-mini` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Crossref records tối đa | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày; stale ratio tối đa 25% |
| Test set | 10 câu fixed-source; không random seed |

API key chỉ nằm trong `.env` local và không xuất hiện trong report hoặc artifact.

### Lệnh cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Lệnh chạy

```bash
# Tạo baseline: raw/clean/quality/index/test set/metrics/report
python script/run_phase1.py

# Tạo corruption, repaired state và report so sánh
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Lần chạy có artifact hiện tại | Bằng chứng |
| --- | --- | --- | --- |
| `python script/run_phase1.py` | Thành công | 2026-09-25 16:42 +0700 | `data/reports/phase1_report.md`, `baseline_metrics.json` |
| `python script/run_corruption_flow.py` | Thành công | 2026-09-25 16:38 +0700 | `data/reports/corruption_report.md`, corrupted/repaired metrics |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API `/works`; fallback snapshot local |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-03-29,has-abstract:true` |
| Số record raw/clean | 24 / 24 |
| Retry/fallback | Tối đa 2 request, timeout 12 giây; lỗi HTTP/mạng/JSON dùng `data/raw/crossref_response.json` |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | string | Có | DOI chuẩn hóa, document identity | Bỏ prefix DOI/URL, lowercase; loại record nếu rỗng; deduplicate |
| `title` | string | Có | Tiêu đề bài báo | Gom khoảng trắng; loại record nếu rỗng |
| `summary` | string | Có | Abstract phục vụ answer/context | Bỏ HTML/JATS; loại record nếu rỗng; GX yêu cầu ≥30 ký tự |
| `authors`, `categories` | list[string] | Không | Metadata học thuật | Chuẩn hóa text; fallback `Unknown`/`Uncategorized` khi join |
| `published` | ISO date string | Có | Ngày công bố | Parse `published`/`published-print`/`published-online`/`issued`; loại record nếu không parse được |
| `age_days` | integer | Có | Tuổi dữ liệu tại thời điểm chạy UTC | `(run_date - published).days`; dùng cho freshness SLA |
| `text_for_embedding` | string | Có | Nội dung đưa vào vector store | Template gồm Title, Authors, Published, Categories, Summary |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động ở baseline hiện tại | Cách xác minh |
| --- | --- | ---: | --- |
| Normalize DOI/title/summary và bỏ markup | Validity/consistency | 24 được chuẩn hóa | `papers_clean.json` và `crossref.py` |
| Loại record thiếu DOI/title/summary/published | Completeness | 0 bị loại | Raw và clean đều 24 records |
| Deduplicate theo `paper_id` | Uniqueness | 0 duplicate ở baseline | GX unique DOI PASS |
| Dựng `age_days`, `summary_chars`, `text_for_embedding` | Freshness/retrievability | 24 dòng | Schema clean JSON và smoke test index |

`text_for_embedding` có định dạng cố định: `Title`, `Authors`, `Published`, `Categories`, `Summary`. DOI là document ID xuyên suốt raw, clean, Chroma metadata, ground truth và quality report.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 5 |
| `question_type` | `summary`, `authors`, `date`, `category`, `multi_hop` |
| Ground-truth document ID | DOI từ `paper_id`; multi-hop có 2 DOI |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB, cosine space; baseline `papers-baseline` |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenAI / `gpt-4.1-mini`; current judge mode `llm` |
| Test set dùng chung | `data/eval/test_set.json` cho baseline, corrupted và repaired |

Test set phải giữ nguyên để mọi khác biệt metric chỉ đến từ corpus/index ở từng trạng thái. `phase1.py` còn kiểm tra mọi `ground_truth_doc_ids` có thuộc clean corpus không; nếu không, test set được rebuild trước khi evaluate.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/crossref_response.json`, `crossref_records.json` | Có | 24 records chuẩn hóa |
| Cleaned dataset | `data/clean/papers_clean.csv/.json` | Có | 24 clean records |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Collection `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu, DOI ground truth |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Judge mode `fallback_heuristic` |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Có | GX PASS, Freshness PASS |
| Baseline report | `data/reports/phase1_report.md` | Có | Generated 2026-09-25 |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | DOI ground truth xuất hiện trong top-4 cho 10 samples hiện tại |
| `mean_token_f1` | 0.7403 | Mốc answer quality của clean corpus |
| `judge_accuracy` | 0.7000 | Tỷ lệ answer đạt judge criterion |
| `mean_judge_score` | 3.8000 / 5 | Điểm judge trung bình ở baseline |
| Ragas | Chưa chạy | `RUN_RAGAS` chưa được bật vì pass này chậm hơn |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| Table row count | Completeness | 5–5000 | PASS, observed 24 | Baseline GX report |
| `paper_id`, `title`, `text_for_embedding` not null | Completeness | 0 unexpected mỗi cột | PASS | Baseline GX report |
| `paper_id` unique | Uniqueness | 0 duplicate | PASS | Baseline GX report |
| `summary` length | Content validity | ≥30 ký tự | PASS | Baseline GX report |

GX dùng `gx.get_context(mode="ephemeral")`, pandas data source và dataframe batch; không sinh GX project files phụ trong repository.

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness đo tại | Clean dataframe trước khi baseline index; chạy lại cho corrupted/repaired |
| Published-date range baseline | 2026-04-01 đến 2026-09-15 |
| Ngưỡng | `age_days > 180` là stale; stale ratio tối đa 25% |
| Baseline | PASS: 0/24 stale, 0.00% |
| Ý nghĩa | Data có thể qua GX nhưng vẫn cũ; freshness là signal thời gian bổ sung |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng/thực tế | Cách repair |
| --- | --- | ---: | --- | --- |
| `drop_latest_records` | Bỏ 20% bài mới nhất | 5 | Không có expectation riêng; evidence mới bị thiếu, latest date lùi | Rebuild full corpus từ raw |
| `blank_summary` | Xóa summary của các dòng chọn trước | 2; thành 4 summary rỗng sau duplicate | Summary length FAIL | Rebuild full corpus từ raw |
| `inject_text_noise` | Chèn chuỗi vô nghĩa vào embedding text | 2 | Không có GX rule riêng; có thể làm semantic context kém | Rebuild embedding text từ raw-clean |
| `truncate_title` | Cắt title còn 8 ký tự | 2 | Không có GX title-length rule; làm metadata/lookup kém tin cậy | Rebuild title từ raw |
| `stale_date` | Đưa published/age về 5 năm trước | 8 | Freshness FAIL: 8/24 = 33.33% > 25% | Recompute published/age từ raw |
| `duplicate_rows` | Duplicate 5 dòng để giữ row count 24 | 5 DOI lặp | Unique DOI FAIL; 10 unexpected values | Rebuild/deduplicate từ raw |

Corruption log tồn tại tại `data/results/corruption_log.json`, ghi đủ 6 scenario, timestamp, mô tả, DOI bị tác động và `rows_affected`.

Repair bỏ hẳn corrupted dataframe và gọi lại `load_raw_records()` + `build_clean_dataframe()` để tạo `papers_clean_repaired.csv/.json`. Vì source và cleaning rules được bảo toàn, repair không che lỗi bằng cách sửa artifact corrupted tại chỗ; index/metrics/report repaired cũng được ghi ra path riêng để audit.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | +0.2000 | Retrieval suy giảm rồi phục hồi trên benchmark 10 câu |
| `mean_token_f1` | 0.7403 | 0.5403 | 0.7403 | -0.2000 | +0.2000 | Answer quality giảm 20 điểm phần trăm và trở lại baseline |
| `judge_accuracy` | 0.7000 | 0.5000 | 0.7000 | -0.2000 | +0.2000 | Judge signal suy giảm rồi phục hồi |
| `mean_judge_score` | 3.8000 | 3.0000 | 3.8000 | -0.8000 | +0.8000 | Mức độ đúng của answer giảm 0.8/5 |
| Quality Gate | PASS | FAIL | PASS | PASS → FAIL | FAIL → PASS | Corrupted fail unique DOI và summary length |
| Freshness SLA | PASS, 0.00% stale | FAIL, 33.33% stale | PASS, 0.00% stale | +33.33 pp stale | -33.33 pp stale | Stale-date scenario vượt SLA |

Hai kết luận nhân quả được artifacts hỗ trợ:

1. Sáu corruption cùng làm thay đổi content/date/identity → GX FAIL và freshness FAIL → Retrieval Hit Rate, Token F1 và judge accuracy cùng giảm 0.2000; judge score giảm 0.8000. Các signal chất lượng và evaluation cùng xác nhận silent failure.
2. Rebuild từ `data/raw/crossref_records.json` qua canonical cleaning → Quality Gate/Freshness trở lại PASS → Token F1, judge accuracy và judge score phục hồi đúng baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Một benchmark artifact cũ có thể trỏ đến DOI không còn thuộc clean corpus mới, dẫn tới evaluation trả metric thấp hoặc vô nghĩa dù pipeline không ném exception.
- **Nguyên nhân:** `load_or_create_test_set()` có thể tái dùng file test set đã tồn tại; nếu raw source được refresh thì document identity/title thay đổi.
- **Cách xử lý:** Sau khi load/build test set, `phase1.py` thu tập mọi `ground_truth_doc_ids` và so với `paper_id` trong clean dataframe. Nếu không phải tập con, pipeline rebuild test set với `refresh=True` trước evaluation.
- **Cách xác minh:** Artifact hiện tại có 10 samples với DOI ground truth thuộc clean corpus; baseline `retrieval_hit_rate = 1.0` và `data/eval/test_set.json` được dùng lại cho cả three-state comparison.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Test set mới có 10 câu nhưng nhiều câu vẫn chứa title | Hit rate có thể lạc quan với câu truy vấn exact-title | Thêm câu paraphrase Việt/Anh không chứa title; so sánh hit/F1/judge theo nhóm câu hỏi |
| Sáu scenario chạy cùng lúc | Không tách được mức ảnh hưởng của từng lỗi lên F1/judge | Chạy ablation: mỗi scenario một lần, sau đó chạy tổ hợp; ghi metric theo scenario |
| Ragas chưa chạy | Chưa có một lớp đánh giá RAG bổ sung | Chạy với `RUN_RAGAS=1`; lưu score/error và thời gian chạy trong report |
| Snapshot offline có thể cũ | Pipeline vẫn chạy nhưng corpus có thể không mới | Theo dõi `latest_published`, stale ratio và refresh snapshot có kiểm soát |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế; Pha 6 do Nguyễn Đình Khang và Trần Long Khánh phối hợp theo phần việc quality/repair và orchestration/integration.
- [x] Baseline và corruption flow có artifact thành công ngày 2026-09-25.
- [x] Baseline, corrupted và repaired dùng cùng `data/eval/test_set.json`.
- [x] Bảng metrics khớp các file trong `data/results/` hiện tại.
- [x] Quality/freshness conclusions khớp `data/quality/` hiện tại.
- [x] Đường dẫn report và artifact đều tồn tại.
- [x] Cả bốn thành viên có báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong báo cáo.
