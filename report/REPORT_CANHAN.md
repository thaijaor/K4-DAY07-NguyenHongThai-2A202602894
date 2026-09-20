# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Hồng Thái (2A202602894)
**Nhóm:** sieunhandienquang (lớp 3B)
**Ngày:** 2026-09-20

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector chỉ về cùng một hướng trong không gian embedding, tức hai đoạn văn bản nói về cùng một chủ đề. Giá trị chạy từ -1 đến 1, càng gần 1 thì càng gần nghĩa.

**Ví dụ có độ tương tự CAO:**
- Câu A: Tôi muốn trả lại đơn hàng bị lỗi.
- Câu B: Làm sao để yêu cầu hoàn tiền cho sản phẩm hỏng?
- Tại sao tương đồng: cùng nói về quy trình trả hàng/hoàn tiền, chung nhóm từ vựng "trả lại", "hoàn tiền", "lỗi/hỏng".

**Ví dụ có độ tương tự THẤP:**
- Câu A: Tôi muốn trả lại đơn hàng bị lỗi.
- Câu B: Phí vận chuyển nội thành là bao nhiêu?
- Tại sao khác: một câu hỏi về đổi trả, một câu hỏi về cước vận chuyển, không chung chủ đề lẫn từ vựng.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ đo góc nên bỏ qua độ lớn vector, vốn tỉ lệ với độ dài văn bản. Nhờ vậy một câu hỏi ngắn vẫn so sánh công bằng được với một đoạn chính sách dài cùng chủ đề, trong khi Euclid sẽ phạt cặp đó chỉ vì chênh lệch độ dài.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Bước nhảy giữa hai chunk liên tiếp: step = chunk_size - overlap = 500 - 50 = 450.
> Chunk đầu phủ ký tự 0–499, mỗi chunk sau dịch thêm 450 ký tự.
> Số chunk = ceil((10000 - 500) / 450) + 1 = ceil(9500 / 450) + 1 = ceil(21.11) + 1 = 22 + 1.
> **Đáp án: 23 chunk**, trong đó chunk cuối chỉ dài 100 ký tự.
> Kiểm chứng: `FixedSizeChunker(chunk_size=500, overlap=50).chunk("a" * 10000)` trả về 23 chunk.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Bước nhảy còn 400 nên số chunk tăng lên 25. Overlap lớn giúp một câu nằm vắt qua ranh giới chunk vẫn xuất hiện trọn vẹn trong ít nhất một chunk, tránh mất thông tin ở mép cắt; đổi lại tốn thêm chi phí lưu trữ và embedding.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Cắt bằng regex `(?<=[.!?])\s+`. Lookbehind khớp vị trí *sau* dấu câu mà không nuốt nó, nên dấu chấm vẫn dính vào câu vừa kết thúc; `\s+` gom được cả `". "` lẫn `".\n"` mà đề liệt kê riêng. Edge case: text rỗng hoặc toàn khoảng trắng trả `[]`, và phải lọc phần tử rỗng sinh ra khi chuỗi kết thúc bằng `". "`.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> `_split` có ba base case: text rỗng trả `[]`; text ngắn hơn hoặc bằng `chunk_size` giữ nguyên; hết separator (hoặc gặp `""`) thì cắt cứng theo độ dài. Thân đệ quy thử separator đầu tiên, nếu nó không xuất hiện thì gọi lại chính nó với danh sách separator còn lại, mảnh nào vẫn dài quá thì đệ quy tiếp. Tôi thêm bước gom các mảnh nhỏ liền kề lại tới sát `chunk_size`: không có bước này thì `"word " * 200` với `chunk_size=100` ra 200 chunk 4 ký tự, vẫn pass test nhưng vô dụng cho retrieval.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `_make_record` chuẩn hoá mỗi document thành một dict gồm `content`, `metadata`, `embedding`, và tự gán `metadata["doc_id"]` mặc định bằng `doc.id` — đây là khoá mà `delete_document` và metadata filter dựa vào. Embedding tính ngay lúc nạp chứ không tính lúc search, vì đó là phần đắt nhất. `search` gọi `_search_records`: embed query một lần, tính cosine với mọi record, sort giảm dần rồi cắt `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Lọc metadata **trước** rồi mới xếp hạng trên tập đã lọc; lọc sau (lấy top-k rồi bỏ cái không khớp) sẽ trả về ít hơn `top_k` kết quả hoặc rỗng. `delete_document` quét ra danh sách khớp `metadata["doc_id"]` trước để biết có gì để xoá và trả `False` nếu rỗng, rồi mới dựng lại danh sách, không xoá tại chỗ khi đang lặp.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba bước: `store.search()` lấy top-k, ghép các chunk thành khối NGỮ CẢNH kèm `doc_id` và score, rồi gọi `llm_fn(prompt)`. Prompt đặt ba ràng buộc: chỉ dùng thông tin trong ngữ cảnh, không đủ thì nói rõ là không tìm thấy trong tài liệu, và dẫn số hiệu đoạn `[1]` để truy được câu trả lời dựa trên chunk nào.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

### Kết Quả Kiểm Thử (Test Results)

```
$ pytest tests/ -v

tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED          [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED    [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.07s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Chưa hoàn thành. Cột **Dự đoán** phải điền trước khi chạy `compute_similarity()`, và cần bật embedder thật: `MockEmbedder` băm MD5 nên điểm số là nhiễu, không phản ánh ngữ nghĩa.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | | | cao / thấp | | |
| 2 | | | cao / thấp | | |
| 3 | | | cao / thấp | | |
| 4 | | | cao / thấp | | |
| 5 | | | cao / thấp | | |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> *(điền sau khi chạy)*

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

> Chưa hoàn thành. Chờ nhóm chốt 5 câu hỏi đánh giá (CP5) và dựng `bench.py`.

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của tôi trong gói `src`. 5 câu hỏi này trùng với các thành viên cùng nhóm (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** __ / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *(điền sau demo)*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | / 5 |
| Kết quả truy xuất của tôi (Competition Results) | / 10 |
| **Tổng phần cá nhân** | **45 / 60** |
