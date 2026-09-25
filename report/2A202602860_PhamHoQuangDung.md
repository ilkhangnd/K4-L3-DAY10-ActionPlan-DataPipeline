# Báo cáo vai trò thành viên — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phạm Hồ Quang Dũng |
| MSSV | 2A202602860 |
| Khóa/Lớp | K4 — L3 Day 10 |
| Tên nhóm |ActionPlan|
| Vai trò chính | Phase 3 — Benchmark Test Set và ChromaDB Vector Index |
| Repository | https://github.com/ilkhangnd/K4-L3-DAY10-ActionPlan-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Benchmark Test Set | `src/evaluation/testset.py`: `build_test_set`, `load_or_create_test_set` | DataFrame sạch từ Phase 2 | `data/eval/test_set.json` gồm 10 câu hỏi chuẩn | Hoàn thành |
| Vector index | Tích hợp và kiểm tra `retrieval/embeddings.py`, `retrieval/index.py` | `text_for_embedding` của 24 bài báo sạch | Collection `papers-baseline` và embedding manifest | Hoàn thành |
| Smoke test retrieval | `LocalEmbeddingIndex.build/load/search` | Câu truy vấn kiểm tra | Hai tài liệu liên quan và metadata đi kèm | Hoàn thành |
| Tính di động của index | `src/retrieval/index.py`, `data/embeddings/papers_embeddings.json` | Đường dẫn ChromaDB local | Manifest dùng đường dẫn tương đối `data/chroma` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra tính tương thích giữa benchmark và corpus | Pipeline integration | Ground-truth document IDs trỏ đúng tài liệu trong collection baseline |
| Xử lý lỗi đường dẫn tuyệt đối | Các thành viên chạy project trên máy khác | Manifest chuyển sang `data/chroma`, không còn phụ thuộc `C:\Users\...` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây dựng benchmark xác định, tái lập được | `src/evaluation/testset.py` | 10 câu hỏi thuộc 4 loại `summary`, `authors`, `date`, `categories` | Đọc `data/eval/test_set.json` và kiểm tra schema |
| Gắn ground truth với tài liệu nguồn | `ground_truth_doc_ids` | Mỗi câu hỏi có DOI ổn định của tài liệu đúng | Đối chiếu ID với `paper_id` trong dữ liệu sạch |
| Tạo vector index | `data/chroma/`, `papers_embeddings.json` | 24 tài liệu trong collection `papers-baseline` | `collection.count()` trả về 24 |
| Kiểm thử semantic retrieval | `LocalEmbeddingIndex.search` | Truy vấn smoke test trả về đủ 2 kết quả | Chạy lệnh kiểm tra Phase 3 |
| Loại bỏ đường dẫn phụ thuộc máy cá nhân | `src/retrieval/index.py` | `persist_path` được lưu là `data/chroma` | Kiểm tra manifest và chạy load/search trên project root |

Commit bàn giao Phase 3 là `c027439` (`Hoan thanh phase 3`). Artifact chính là `data/eval/test_set.json` và `data/embeddings/papers_embeddings.json`. Manifest ghi nhận 24 documents, model `sentence-transformers/all-MiniLM-L6-v2`, collection `papers-baseline` và đường dẫn portable `data/chroma`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phase 3 chuyển dữ liệu sạch thành hai tài sản cần thiết cho việc đánh giá RAG. Thứ nhất là một bộ câu hỏi có đáp án và document ID chuẩn để đo retrieval/answer quality. Thứ hai là vector index cho phép truy vấn ngữ nghĩa trên nội dung tổng hợp của bài báo. Nếu benchmark không ổn định hoặc document ID không khớp corpus, các metrics về sau sẽ không có ý nghĩa. Nếu index lưu đường dẫn tuyệt đối, project sẽ chỉ chạy được trên máy đã tạo artifact.

### Cách triển khai

Benchmark được tạo theo thứ tự ổn định của `paper_id`. Trước khi tạo câu hỏi, dữ liệu được kiểm tra đủ các cột bắt buộc, loại dòng null, khử trùng theo `paper_id`, rồi chọn 10 bài đầu tiên. Bốn loại câu hỏi được phân bổ luân phiên:

- `summary`: ground truth là câu đầu tiên của summary;
- `authors`: ground truth là `authors_joined`;
- `date`: ground truth là ngày `published`;
- `categories`: ground truth là `categories_joined`.

Mỗi câu chứa tiêu đề bài báo trong dấu nháy và DOI trong `ground_truth_doc_ids`. Thiết kế này giúp retrieval vừa tìm kiếm ngữ nghĩa vừa có thể đối chiếu chính xác tài liệu kỳ vọng. `load_or_create_test_set` giữ nguyên bộ benchmark nếu file đã tồn tại, để baseline, corrupted và repaired được đánh giá trên cùng đề thi.

Ở phần vector index, trường `text_for_embedding` được encode bằng `all-MiniLM-L6-v2` với normalized embeddings. ChromaDB dùng cosine distance và lưu metadata gồm DOI, title, ngày xuất bản, tác giả, category, summary và URL. Trước khi build lại collection cùng tên, collection cũ được xóa để thao tác có tính idempotent và tránh ghost vectors.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | DataFrame sạch có `paper_id`, `title`, `summary`, `authors_joined`, `published`, `categories_joined`, `text_for_embedding` |
| Output | `test_set.json`, `papers_embeddings.json`, collection ChromaDB `papers-baseline` |
| Module phụ thuộc | `src/ingestion/cleaning.py`, `src/core/config.py`, `src/core/utils.py` |
| Module sử dụng output | `src/evaluation/metrics.py`, `src/retrieval/qa.py`, `src/pipelines/phase1.py` |
| Điều kiện lỗi cần xử lý | Thiếu cột bắt buộc, dưới 10 tài liệu hợp lệ, ground truth rỗng, benchmark lệch corpus, model chưa được tải, đường dẫn manifest thuộc máy khác |

### Cách xác minh

Tạo hoặc nạp benchmark:

```bash
python -X utf8 -c "from core.config import load_settings; from evaluation.testset import load_or_create_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=load_or_create_test_set(df, s); print('Test set:', len(ts), 'questions')"
```

Build index và smoke test:

```bash
python -X utf8 -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); idx=LocalEmbeddingIndex.build(df, s); res=idx.search('machine learning', top_k=2); print('Documents:', idx.collection.count()); print('Search results:', len(res))"
```

- **Kết quả mong đợi:** 10 câu hỏi, 24 documents và 2 kết quả tìm kiếm.
- **Kết quả thực tế:** 10 câu hỏi, 24 documents và 2 kết quả tìm kiếm.
- **Artifact/log:** `data/eval/test_set.json`, `data/embeddings/papers_embeddings.json`, `data/chroma/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Benchmark phải dùng lại được trong ba trạng thái baseline, corrupted và repaired.
- **Các phương án đã cân nhắc:** Tạo câu hỏi ngẫu nhiên mỗi lần chạy; hoặc tạo bộ câu hỏi xác định và chỉ rebuild khi được yêu cầu hay khi corpus baseline thay đổi.
- **Phương án đã chọn:** Sắp xếp theo `paper_id`, sinh bộ 10 câu cố định và dùng `load_or_create_test_set` để tái sử dụng.
- **Lý do:** Bộ đề cố định loại bỏ biến nhiễu do câu hỏi thay đổi. Khi metrics giảm sau corruption, có thể quy nguyên nhân cho dữ liệu/index thay vì do đổi evaluation set.
- **Bằng chứng quyết định phù hợp:** `test_set.json` chứa ID ổn định; baseline downstream đạt `retrieval_hit_rate = 1.0` và `mean_token_f1 = 1.0` trên 10 mẫu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `papers_embeddings.json` từng chứa `persist_path` dạng tuyệt đối trỏ tới `C:\Users\...\data\chroma`; thành viên khác không thể dùng đúng đường dẫn đó trên máy của họ.
- **Lệnh hoặc bước tái hiện:** Build index trên một máy, commit manifest, sau đó clone/load index trên máy có thư mục project khác.
- **Nguyên nhân gốc:** `str(persist_path)` ghi trực tiếp đường dẫn tuyệt đối vào artifact được chia sẻ.
- **Cách xử lý:** Lưu đường dẫn tương đối bằng `relative_to(project_dir).as_posix()`; khi load, resolve đường dẫn tương đối từ project root và fallback về `settings.paths.chroma_dir` nếu artifact cũ trỏ tới nơi không tồn tại.
- **Cách xác minh sau khi sửa:** Manifest chứa `"persist_path": "data/chroma"`; repository không còn chuỗi đường dẫn tài khoản Windows; index vẫn load và search thành công.
- **Điều học được:** Artifact được commit phải portable. Đường dẫn runtime tuyệt đối chỉ nên tồn tại trong bộ nhớ của tiến trình, không nên ghi vào manifest dùng chung.

## 7. Hiểu biết về luồng end-to-end

1. Crossref cung cấp raw response. Phase 2 chuẩn hóa thành các paper records, làm sạch và tạo `text_for_embedding`. Phase 3 encode trường này thành vector và lưu document cùng metadata vào ChromaDB.
2. Evaluation set chứa câu hỏi, đáp án chuẩn và DOI chuẩn. Khi chạy evaluation, hệ thống kiểm tra DOI kỳ vọng có xuất hiện trong kết quả retrieval hay không, đồng thời so sánh câu trả lời với ground truth bằng Token F1 và judge.
3. Quality checks kiểm tra cấu trúc và nội dung dữ liệu, chẳng hạn null, uniqueness và độ dài summary. Freshness monitoring tập trung vào tuổi dữ liệu và tỷ lệ bản ghi vượt SLA 180 ngày.
4. Cùng một test set phải được dùng cho baseline, corrupted và repaired để phép so sánh công bằng. Nếu đổi câu hỏi giữa các trạng thái thì không thể kết luận metrics thay đổi do corruption.
5. Repair thành công khi dữ liệu/quality/freshness trở về trạng thái hợp lệ, index được rebuild từ nguồn raw đáng tin cậy và các metrics repaired phục hồi gần hoặc bằng baseline trên cùng test set.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | N/A | N/A | Baseline chứng minh 10 ground-truth IDs đều được retrieval tìm thấy |
| `mean_token_f1` | 1.0000 | N/A | N/A | Câu trả lời baseline khớp ground truth của benchmark |
| `judge_accuracy` | 1.0000 | N/A | N/A | Là bằng chứng downstream; không phải module tôi sở hữu |
| `mean_judge_score` | 5.0000 | N/A | N/A | Là bằng chứng downstream; không phải module tôi sở hữu |
| Quality checks | PASS | N/A | N/A | Quality thuộc Phase 2, được dùng làm điều kiện đầu vào cho Phase 3 |
| Freshness status | PASS | N/A | N/A | Freshness thuộc Phase 2, không phải deliverable của tôi |

### Kết luận từ số liệu

Tại thời điểm hoàn thành báo cáo cá nhân này, tôi chỉ nhận ownership Phase 3 và repository chưa có đủ artifact corrupted/repaired để tôi đưa ra chuỗi nhân quả định lượng cho hai trạng thái đó. Tôi không điền số liệu giả định.

Với baseline, chuỗi bằng chứng là: dữ liệu sạch có 24 paper IDs → benchmark chọn 10 IDs thuộc đúng corpus → ChromaDB index đủ 24 documents → retrieval tìm đúng 10/10 ground-truth documents → `retrieval_hit_rate = 1.0`.

Corruption có khả năng ảnh hưởng rõ nhất tới Phase 3 là drop records hoặc làm sai `paper_id`, vì ground-truth document biến mất trực tiếp khỏi index và retrieval hit sẽ chuyển từ đúng sang sai. Kết luận thực tế về mức giảm chỉ được đưa ra sau khi Phase corruption tạo `corrupted_metrics.json` trên chính test set này.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Vector index chỉ đáng tin khi document identity ổn định và metadata có thể truy vết về nguồn.
2. Benchmark phải cố định và khớp corpus; một test set cũ trỏ tới DOI không còn trong index có thể làm Hit Rate bằng 0 dù retrieval code không lỗi.
3. Artifact kỹ thuật cũng là một phần của data contract: đường dẫn tuyệt đối trong manifest có thể làm pipeline hỏng trên máy khác dù code Python đúng.

### Nếu có thêm thời gian

Tôi sẽ bổ sung pytest cho test-set schema, kiểm tra tất cả `ground_truth_doc_ids` tồn tại trong baseline corpus, kiểm tra build index idempotent và chạy load/search trong một thư mục project tạm khác. Cải thiện được đo bằng việc các test này pass trên CI và không cần Chroma artifact được tạo từ máy cá nhân.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Hồ Quang Dũng  
**Ngày xác nhận:** 2026-09-25
