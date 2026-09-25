# Kịch bản nhập Chatbot bằng tiếng Việt

Chọn **Baseline (clean)** trước để demo câu trả lời chính xác. Để chatbot xác định đúng paper, giữ nguyên **title tiếng Anh trong dấu nháy đơn**.

| Mục tiêu | Câu nhập vào chatbot | Kết quả mong đợi |
| --- | --- | --- |
| Hỏi tóm tắt | `Tóm tắt nội dung chính của bài báo 'JADE-Plus: A Multimodal Agentic Retrieval-Augmented Generation Large Language Framework for Diagnostic Support in Jawbone Lesions: Development and Technical Validation Study' là gì?` | Trả câu tóm tắt đầu tiên và liệt kê DOI nguồn. |
| Hỏi tác giả | `Ai là tác giả của bài báo 'Retrieval-Augmented Large Language Model Agents for Automated Scientific Literature Review Generation'?` | Hiện nhãn `Tác giả:` kèm danh sách tác giả. |
| Hỏi ngày | `Bài báo 'Speculative Retrieval-Augmented Generation for Cost-Efficient Large Language Model Inference' được công bố khi nào?` | Hiện nhãn `Ngày công bố:` và ngày ISO. |
| Hỏi lĩnh vực | `Bài báo 'A large language model-driven scientific literature surveys generation framework based on multi-agents and retrieval-augmented generation' thuộc lĩnh vực nào?` | Hiện nhãn `Lĩnh vực:` và categories của record. |
| So sánh silent failure | Nhập lại một câu ở trên sau khi chọn **Corrupted**. | Chatbot vẫn có thể trả lời, nhưng Sources/metrics ở dashboard cho thấy chất lượng retrieval đã giảm. |
| Chứng minh phục hồi | Nhập lại câu đó sau khi chọn **Repaired**. | Kết quả và metrics quay về tương đương Baseline. |

## Lưu ý về tiếng Việt

Chatbot hiện hỗ trợ trực tiếp các mẫu câu tiếng Việt về **tóm tắt, tác giả, ngày công bố và lĩnh vực**. Các metadata gốc do Crossref cung cấp chủ yếu là tiếng Anh, vì vậy phần nội dung câu trả lời có thể là tiếng Anh dù câu hỏi là tiếng Việt.

Với câu hỏi hoàn toàn tự do bằng tiếng Việt mà không nêu title, model embedding hiện tại (`all-MiniLM-L6-v2`) tối ưu cho tiếng Anh nên kết quả semantic search có thể kém hơn. Khi demo, dùng title trong dấu nháy đơn là lựa chọn chính xác và ổn định nhất.
