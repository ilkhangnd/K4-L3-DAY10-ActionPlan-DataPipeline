# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Ngô Gia Quốc             |
| MSSV               | 2A202602757                     |
| Khóa/Lớp         | K4 (K4-L3-DAY10)              |
| Tên nhóm         | [ActionPlan]     |
| Vai trò chính    | Thành viên 3 — RAG & Vector Index, tích hợp Baseline Pipeline (phase 4) |
| Repository         | https://github.com/ilkhangnd/K4-L3-DAY10-ActionPlan-DataPipeline |
| Ngày hoàn thành | [2026-09-25]               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Baseline pipeline end-to-end | `src/pipelines/phase1.py` — `main()`, `_run_agent_demo()` | `Settings`, `data/raw/crossref_records.json` | `data/clean/`, `data/chroma/`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `baseline_answers.json`, `agent_demo_answers.json` | Hoàn thành (agent demo bị bỏ qua do lỗi SSL) |
| Báo cáo Phase 1 | `src/observability/reporting.py` — `generate_phase1_report()` | source summary, metrics, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Vector index persistence | `src/retrieval/index.py` — `LocalEmbeddingIndex.build()` (ghi manifest), `LocalEmbeddingIndex.load()` | Clean DataFrame / manifest JSON | Collection `papers-baseline`, `data/embeddings/papers_embeddings.json` với `persist_path` tương đối | Hoàn thành |
| Quy ước git cho vector DB | `.gitignore` (`data/chroma/*`, giữ `.gitkeep`) | — | ChromaDB không còn bị commit | Hoàn thành |

Phần việc của tôi dùng output của Dinh Khang (`crossref.py`, `cleaning.py`, `quality.py`) và Pham Ho Quang Dung (`testset.py`, manifest embedding). Output của tôi (`baseline_metrics.json`, `papers_clean.json`, `test_set.json`) là đầu vào cho corruption flow do thành viên khác phụ trách.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Debug `LocalEmbeddingIndex.load()` lỗi khi chạy manifest được build trên máy khác | Pham Ho Quang Dung — `data/embeddings/papers_embeddings.json` | `load()` chạy trên mọi máy. Lệnh kiểm tra ở Guide trả về kết quả tìm kiếm |
| Phát hiện test set lỗi thời so với snapshot raw | Pham Ho Quang Dung — `data/eval/test_set.json` | Pipeline tự tạo lại test set, `retrieval_hit_rate` từ 0.0 lên 1.0 |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Ghép các module thành pipeline baseline 7 bước, chặn index khi GX fail | `src/pipelines/phase1.py` | Toàn bộ artifact baseline | `python script/run_phase1.py` in đủ `[1/7]` → `[7/7]` |
| Viết báo cáo Markdown Phase 1 (source, metrics, 6 expectation GX, freshness) | `src/observability/reporting.py` | `data/reports/phase1_report.md` | Mở file, đối chiếu với `baseline_metrics.json` và `baseline_quality_report.json` |
| Kiểm tra test set khớp dữ liệu sạch, tạo lại nếu lệch | `src/pipelines/phase1.py` | `data/eval/test_set.json` (10 câu) | Log `Test set references papers missing ... rebuilding it`; hit rate = 1.0 |
| Lưu `persist_path` tương đối và thêm fallback khi load | `src/retrieval/index.py` | Manifest `"persist_path": "data/chroma"` | `LocalEmbeddingIndex.load(s).search("machine learning", top_k=2)` trả về 2 kết quả |
| Bỏ ChromaDB nhị phân khỏi git | `.gitignore` | `data/chroma/*` bị ignore | `git status` không còn hiện thư mục UUID trong `data/chroma/` |
Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`data/results/baseline_metrics.json`: `samples = 10`, `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0`, `judge_accuracy = 1.0`, `mean_judge_score = 5`. Kết quả này được sinh sau khi pipeline phát hiện và tạo lại test set lỗi thời. Lần chạy đầu với test set cũ chỉ đạt hit rate 0.0 và F1 0.01. Lưu ý: judge ở đây là fallback heuristic, không phải Gemini (xem mục 6).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Starter chỉ có các module rời (ingestion, cleaning, quality, index, testset, metrics) và `phase1.main()` báo `NotImplementedError`. Phần của tôi nối chúng thành một lệnh duy nhất tạo lại được toàn bộ baseline. Pipeline cũng phải chạy được trên máy bất kỳ trong nhóm, không phụ thuộc vào đường dẫn hay artifact còn sót lại của người khác.

### Cách triển khai

- **Thứ tự bước:** raw → clean → quality/freshness → index → test set → evaluate → report → agent demo. Quality gate chạy **trước** index. Nếu GX fail, pipeline raise lỗi và dừng, không cho dữ liệu hỏng vào serving layer. Freshness chỉ được ghi nhận, không chặn pipeline, vì bài cũ vẫn là dữ liệu hợp lệ, chỉ cần cảnh báo.
- **Raw:** mặc định đọc lại snapshot `crossref_records.json`, và chỉ gọi API khi `REFRESH_SOURCE=1` hoặc chưa có snapshot. Nhờ đó baseline tái hiện được và không phụ thuộc mạng.
- **Test set:** giữ nguyên file cố định để so sánh công bằng. Chỉ tạo lại khi `ground_truth_doc_ids` không nằm trong `paper_id` của dữ liệu sạch, vì khi đó mọi truy vấn chắc chắn miss.
- **Agent demo:** bọc trong `try/except` và ghi lỗi vào `agent_demo_answers.json`, để lỗi LLM không làm hỏng các artifact bắt buộc.
- **Index:** manifest lưu `persist_path` tương đối với project (`as_posix()` để giống nhau giữa Windows và Linux). `load()` ghép lại với `project_dir`, và nếu đường dẫn không tồn tại thì dùng `settings.paths.chroma_dir`, nên manifest cũ có đường dẫn tuyệt đối vẫn đọc được.
- **Report:** in bảng source summary, 5 metric dạng số, Ragas (nếu có), từng expectation GX (type, column, success) và toàn bộ trường freshness.
### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings` từ `load_settings()` (đường dẫn `data/`, `top_k=4`, `freshness_threshold_days=180`, cờ `REFRESH_SOURCE`/`REFRESH_TEST_SET`); `data/raw/crossref_records.json` |
| Output                         | `data/clean/papers_clean.csv/.json`, `data/quality/baseline_quality_report.json`, `freshness_report.json`, `data/chroma/` + `data/embeddings/papers_embeddings.json`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `baseline_answers.json`, `agent_demo_answers.json`, `data/reports/phase1_report.md` |
| Module phụ thuộc             | `ingestion.crossref`, `ingestion.cleaning`, `observability.quality`, `retrieval.index`, `evaluation.testset`, `evaluation.metrics`, `retrieval.agent` |
| Module sử dụng output        | `pipelines/corruption_flow.py` (đọc baseline metrics, clean dataset, test set) |
| Điều kiện lỗi cần xử lý | GX fail thì dừng pipeline; test set lỗi thời thì tạo lại; manifest trỏ tới đường dẫn máy khác thì dùng `data/chroma`; LLM/agent lỗi thì ghi lỗi và tiếp tục |

### Cách xác minh

```bash
python script/run_phase1.py
```

- **Kết quả mong đợi:** Pipeline in đủ 7 bước, sinh 5 artifact theo yêu cầu Pha 4, quality gate pass, hit rate cao.
- **Kết quả thực tế:** `[3/7] Quality gate: gx_success=True is_fresh=True (stale_ratio=0.00%)`, `[4/7] Chroma collection 'papers-baseline' built with 24 documents`, `[6/7] Baseline metrics: hit_rate=1.00 token_f1=1.00 judge_accuracy=1.00 judge_score=5.00`. Agent demo in `skipped` do lỗi SSL.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`, `data/quality/baseline_quality_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Manifest `data/embeddings/papers_embeddings.json` được commit, nhưng `build()` ghi đường dẫn tuyệt đối của người chạy. Khi push, tên user và thư mục máy bị lộ, máy khác không load được, và file bị conflict mỗi khi có người chạy lại.
- **Các phương án đã cân nhắc:** (1) Không lưu `persist_path`, luôn dùng `settings.paths.chroma_dir`. (2) Lưu đường dẫn tương đối và ghép với `project_dir` khi load, kèm fallback. (3) Bỏ manifest khỏi git.
- **Phương án đã chọn:** (2), đồng thời ignore `data/chroma/*`.
- **Lý do:** Giữ nguyên schema manifest mà code khác đang đọc (không đổi contract), manifest giống nhau trên mọi máy và hệ điều hành, và vẫn đọc được manifest cũ. Phương án (3) mất artifact embedding mà đề bài yêu cầu. Vector DB là dữ liệu nhị phân có thể build lại, nên không commit để tránh conflict.
- **Bằng chứng quyết định phù hợp:** Manifest sau khi build chứa `"persist_path": "data/chroma"`. `LocalEmbeddingIndex.load()` chạy và trả kết quả tìm kiếm. `git status` không còn các thư mục UUID của Chroma.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lần chạy đầu `run_phase1.py` in `[6/7] Baseline metrics: hit_rate=0.00 token_f1=0.01 judge_accuracy=0.00 judge_score=1.00`, dù pipeline không báo lỗi.
- **Lệnh hoặc bước tái hiện:** Dùng `data/eval/test_set.json` từ commit `c027439` với snapshot raw hiện tại, chạy `python script/run_phase1.py`.
- **Nguyên nhân gốc:** Test set hỏi về các bài `10.1145/3637528.36718xx`, trong khi `data/raw/crossref_records.json` hiện tại chứa 24 bài Crossref khác. `load_or_create_test_set` thấy file tồn tại nên dùng lại mà không kiểm tra ground truth có trong dữ liệu không. Đây là một silent failure: mọi artifact đều được sinh ra nhưng metric vô nghĩa.
- **Cách xử lý:** Sau khi load test set, so `ground_truth_doc_ids` với `set(df["paper_id"])`. Nếu có id không tồn tại thì gọi `build_test_set(df, paths.eval_testset)`.
- **Cách xác minh sau khi sửa:** Chạy lại pipeline. Log in `Test set references papers missing from the clean data; rebuilding it`, và metric đạt `hit_rate=1.00 token_f1=1.00`.
- **Điều học được:** Artifact "có tồn tại" chưa có nghĩa là "hợp lệ". Mỗi artifact dùng lại giữa các lần chạy cần được kiểm tra nó khớp với dữ liệu hiện tại, nếu không pipeline vẫn "chạy thành công" nhưng kết quả sai.

**Blocker chưa xử lý xong: lỗi SSL khi gọi Gemini/HuggingFace**

- **Phạm vi bị ảnh hưởng:** LLM Judge trong `evaluation/metrics.py` (đã chuyển sang heuristic Token F1), agent demo (`data/results/agent_demo_answers.json` chỉ chứa lỗi), kiểm tra phiên bản model trên HuggingFace (chỉ cảnh báo, vì model đã có trong cache).
- **Những gì đã loại trừ:** `GOOGLE_API_KEY` đã được đặt trong `.env`. Lỗi nguyên văn là `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate`, nghĩa là lỗi xác thực chứng chỉ ở tầng mạng, không phải lỗi key hay lỗi code.
- **Bước tiếp theo:** Cài `pip-system-certs` để Python dùng kho chứng chỉ Windows, chạy lại `run_phase1.py`, rồi kiểm tra `judge.reasoning` trong `baseline_answers.json` không còn là "Fallback heuristic judge".

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Từ Crossref đến vector index:** `fetch_source_records` gọi `/works` với query và filter 180 ngày, lưu nguyên response vào `crossref_response.json` và bản đã parse vào `crossref_records.json`. Khi API lỗi thì dùng snapshot. `build_clean_dataframe` chuẩn hóa text, parse ngày, tính `age_days`, ghép `text_for_embedding` và khử trùng lặp theo `paper_id`. Sau khi qua quality gate, `LocalEmbeddingIndex.build` embed `text_for_embedding` bằng MiniLM và ghi vào collection `papers-baseline` (cosine) trong ChromaDB, kèm metadata để trả lời câu hỏi.
2. **Evaluation set và ground-truth IDs:** Mỗi câu hỏi mang `ground_truth_doc_ids` (DOI). Retrieval được tính là hit nếu DOI đó nằm trong top-4 `retrieved_doc_ids`. Chất lượng câu trả lời đo bằng Token F1 so với `ground_truth` và bằng judge (LLM, hoặc heuristic khi LLM lỗi).
3. **Quality checks và freshness:** Quality checks (GX) kiểm tra cấu trúc và tính hợp lệ của từng bản ghi: số dòng, null, trùng `paper_id`, độ dài summary. Nếu fail, pipeline dừng. Freshness đo độ mới của cả tập (tỉ lệ bài có `age_days` > 180 so với ngưỡng 25%). Dữ liệu có thể hoàn toàn hợp lệ nhưng vẫn cũ, nên freshness chỉ gắn cờ `is_fresh`.
4. **Cùng test set cho ba trạng thái:** Để thay đổi metric chỉ đến từ dữ liệu (corrupt hoặc repair), không đến từ bộ câu hỏi. Lỗi test set lỗi thời tôi gặp cho thấy rõ điều này: đổi dữ liệu mà không đổi test set thì hit rate rơi về 0, dù pipeline không hỏng.
5. [Repair được xem là thành công dựa trên artifact và metric nào?]

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.8 |      1.0 | Baseline đạt tối đa vì câu hỏi chứa nguyên tiêu đề nên `index.lookup` khớp chính xác. Corrupted giảm vì ground truth của `eval_008` và `eval_010` nằm trong 5 bài mới nhất bị drop |
| `mean_token_f1`      |      1.0 |       0.9 |      1.0 | Câu trả lời được trích từ metadata. Ở Corrupted chỉ `eval_010` sai (F1 = 0); `eval_008` lấy sai bài nhưng F1 vẫn 1.0 vì mọi bài đều "Uncategorized" |
| `judge_accuracy`     |      1.0 |       0.9 |      1.0 | Heuristic fallback (F1 ≥ 0.5), không phải Gemini, nên giảm giống F1 |
| `mean_judge_score`   |        5 |       4.6 |        5 | Heuristic cho 5 điểm khi F1 ≥ 0.95; `eval_010` nhận 1 điểm: (9 × 5 + 1) / 10 = 4.6 |
| Quality checks         | 6/6 pass |  4/6 pass |  6/6 pass | Baseline: 24 dòng, không null, không trùng, summary ngắn nhất 826 ký tự. Corrupted fail unique `paper_id` (8 dòng) và độ dài `summary` (3 dòng) |
| Freshness status       |    Fresh |     Fresh |    Fresh | Baseline 0/24 bài quá 180 ngày, mới nhất 2026-09-15. Corrupted có `stale_ratio` 0.174 và bài mới nhất lùi về 2026-08-26, nhưng vẫn dưới ngưỡng 0.25 |

Số liệu Corrupted/Repaired lấy từ `data/results/corrupted_metrics.json`, `repaired_metrics.json` và `data/quality/` của lần chạy `run_corruption_flow.py` ngày 2026-09-25, trên cùng `test_set.json` với baseline.

### Kết luận từ số liệu

1. **Bỏ 20% bài mới nhất (5 bài)** → `latest_published` lùi từ 2026-09-15 về 2026-08-26, nhưng freshness vẫn `True` và không expectation GX nào bắt được vì 23 dòng vẫn hợp lệ → ground truth của 2/10 câu biến mất khỏi index, `retrieval_hit_rate` giảm 1.0 → 0.8, `mean_judge_score` giảm 5 → 4.6.
2. **GX fail (unique `paper_id`, độ dài `summary`) kích hoạt repair từ `data/raw/crossref_records.json`** → dữ liệu repaired có 24 dòng, 6/6 expectation pass, `stale_ratio` = 0 → cả 4 metric về đúng baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest_records` là lỗi duy nhất làm giảm metric agent, và cũng nguy hiểm nhất vì **không tín hiệu nào bắt được**: không expectation GX nào fail, freshness vẫn "fresh". Lỗi này xóa hẳn tài liệu khỏi index, nên retrieval không thể tìm thấy dù model tốt đến đâu. Ngược lại, `blank_summary` và `duplicate_rows` bị GX bắt nhưng không làm đổi metric, vì các dòng bị ảnh hưởng chỉ rơi vào câu hỏi về tác giả/category, không phải câu hỏi dùng summary.

Kết quả nào khác với kỳ vọng ban đầu?

- **Hit rate = 0.0 ở lần chạy baseline đầu tiên**, dù dữ liệu sạch và quality gate pass. Giả thuyết: test set và index không cùng tập bài. Cách kiểm tra: so `ground_truth_doc_ids` trong `baseline_answers.json` với `paper_id` của `papers_clean.json`. Kết quả không trùng id nào, xác nhận giả thuyết (xem mục 6).
- **Baseline đạt điểm tuyệt đối (1.0 / 1.0 / 5).** Kết quả này cao hơn thực tế vì câu hỏi trích nguyên tiêu đề (exact lookup), câu trả lời trích từ metadata, và judge là heuristic. Con số này là mốc tham chiếu để so sánh, chưa phản ánh chất lượng semantic retrieval.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Artifact được commit phải độc lập với máy chạy. Một đường dẫn tuyệt đối trong manifest đủ để pipeline hỏng trên máy thành viên khác. Dữ liệu có thể build lại (vector DB) không nên đưa vào git.
2. **Data quality/observability:** Quality gate phải chạy trước khi index để chặn dữ liệu hỏng. Ngoài kiểm tra dữ liệu, còn cần kiểm tra tính nhất quán giữa các artifact (test set với dataset), vì "chạy không lỗi" vẫn có thể cho metric sai hoàn toàn.
3. **Ảnh hưởng của data đến RAG agent:** Retrieval chỉ đúng khi tập tài liệu trong index khớp với câu hỏi. Khi dữ liệu nguồn đổi mà test set giữ nguyên, agent trả lời bằng tài liệu sai (F1 ≈ 0) mà không báo lỗi.

### Nếu có thêm thời gian

Sửa lỗi SSL (cài `pip-system-certs`) để LLM Judge thực sự dùng Gemini, và thêm các câu hỏi paraphrase không chứa tiêu đề vào một test set bổ sung. Lý do: hiện hit rate và judge score = 1.0 chủ yếu nhờ exact-title lookup và heuristic. Cách đo: so sánh `retrieval_hit_rate` và `mean_judge_score` trên câu hỏi paraphrase với bộ hiện tại, và kiểm tra `judge.reasoning` trong `baseline_answers.json` không còn là fallback.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Ngô Gia Quốc
**Ngày xác nhận:** [2026-09-25]
