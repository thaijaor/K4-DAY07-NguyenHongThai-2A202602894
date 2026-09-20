# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** sieunhandienquang (lớp 3B)
**Thành viên:** Nguyễn Hồng Thái (2A202602894), Trần Mạnh Tùng (2A202602879), Nguyễn Mạnh Cường (2A202602650)
**Ngày:** 2026-09-20

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách trả hàng / hoàn tiền và quy định người mua – người bán trên sàn Shopee.

**Tại sao nhóm chọn chủ đề này?**
> Trung tâm trợ giúp Shopee cho phép truy cập tự động (`robots.txt`: `User-Agent:* / Allow: /`) và tách sẵn nội dung theo hai cổng: `portal/4` dành cho người mua, `portal/1` dành cho người bán. Nhờ đó nhóm có được các tài liệu **cùng chủ đề, cùng từ vựng nhưng khác đối tượng** — điều kiện cần để chứng minh tác dụng của `metadata_filter` theo yêu cầu riêng của L3B.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu (`doc_id`) | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | ecom-shopee-co-check | https://help.shopee.vn/portal/4/article/79262 | 2026-09-20 / 2024 | 3.690 | audience=buyer, category=help, language=vi |
| 2 | return-refund-policy | https://example.com/policy/returns | 2026-09-18 / not-stated | 628 | audience=buyer, category=returns-policy, language=vi |
| 3 | seller-warranty-policy | https://example.com/policy/seller-warranty | 2026-09-18 / not-stated | 512 | audience=seller, category=warranty-policy, language=vi |
| 4 | shopee-bang-chung-tra-hang | https://help.shopee.vn/portal/4/article/79467 | 2026-09-20 / not-stated | 3.491 | audience=buyer, category=tra-hang-hoan-tien, language=vi |
| 5 | shopee-cam-nang-tra-hang-hoan-tien | https://help.shopee.vn/portal/4/article/79258 | 2026-09-20 / not-stated | 2.235 | audience=buyer, category=tra-hang-hoan-tien, language=vi |
| 6 | shopee-chinh-sach-van-chuyen | https://help.shopee.vn/portal/4/article/77250 | 2026-09-20 / not-stated | 24.597 | audience=buyer, category=van-chuyen, language=vi |
| 7 | shopee-dieu-khoan-dich-vu | https://help.shopee.vn/portal/4/article/77242 | 2026-09-20 / not-stated | 1.398 | audience=both, category=dieu-khoan, language=vi |
| 8 | shopee-dong-goi-don-hoan-tra | https://help.shopee.vn/portal/4/article/79508 | 2026-09-20 / not-stated | 3.639 | audience=buyer, category=tra-hang-hoan-tien, language=vi |
| 9 | shopee-seller-don-giao-khong-thanh-cong | https://help.shopee.vn/portal/1/article/102523 | 2026-09-20 / not-stated | 5.003 | audience=seller, category=van-chuyen, language=vi |
| 10 | shopee-seller-quan-ly-don-tra-hang | https://help.shopee.vn/portal/1/article/102521 | 2026-09-20 / not-stated | 3.842 | audience=seller, category=tra-hang-hoan-tien, language=vi |

Tổng 10 tài liệu, 49.035 ký tự. Phân bố `audience`: buyer 6 / seller 3 / both 1. Kiểm kê đầy đủ tại `data/ecommerce/sources.csv`.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

Ghi chú minh bạch: tài liệu **#2 và #3 là file mẫu đi kèm repo gốc**, `source_url` trỏ tới `example.com` chứ không phải nguồn thật. Nhóm giữ lại để corpus đủ 10 tài liệu và để `audience=seller` có thêm mẫu, nhưng **không dùng chúng làm gold answer** cho bất kỳ câu benchmark nào. Tám tài liệu còn lại đều thu thập từ `help.shopee.vn` bằng `scripts/fetch_public_pages.py` (kiểm `robots.txt`, giãn ≥1 giây giữa các request).

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | enum | `buyer` / `seller` / `both` | Cùng một nghiệp vụ trả hàng nhưng quy trình và đáp án khác nhau theo đối tượng. Trường bắt buộc của L3B, là khoá cho `search_with_filter`. |
| `category` | enum | `tra-hang-hoan-tien`, `van-chuyen`, `dieu-khoan` | Thu hẹp theo nhóm nghiệp vụ; 4 tài liệu cùng `tra-hang-hoan-tien` nhưng khác `audience`. |
| `language` | mã | `vi` | Corpus hiện thuần Việt; để sẵn cho trường hợp bổ sung nguồn tiếng Anh. |
| `document_version` | chuỗi | `2024`, `not-stated` | Đối chiếu độ mới của chính sách khi kiểm gold answer. |
| `source_url` | URL | `https://help.shopee.vn/portal/4/article/79508` | Truy vết câu trả lời về trang gốc. |
| `retrieved_at` | ngày | `2026-09-20` | Ghi nhận thời điểm chụp nội dung. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

`ChunkingStrategyComparator().compare(chunk_size=300)`, chạy trên phần thân bài sau khi đã bỏ front matter:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| shopee-cam-nang-tra-hang-hoan-tien | FixedSizeChunker (`fixed_size`) | 9 | 293 | Trung bình — cắt giữa câu |
| shopee-cam-nang-tra-hang-hoan-tien | SentenceChunker (`by_sentences`) | 8 | 271 | Tốt — trọn câu |
| shopee-cam-nang-tra-hang-hoan-tien | RecursiveChunker (`recursive`) | 9 | 247 | Tốt — ưu tiên ranh giới đoạn |
| shopee-seller-quan-ly-don-tra-hang | FixedSizeChunker | 16 | 287 | Trung bình |
| shopee-seller-quan-ly-don-tra-hang | SentenceChunker | 5 | 766 | Kém — chunk phình to, vượt xa `chunk_size` |
| shopee-seller-quan-ly-don-tra-hang | RecursiveChunker | 16 | 238 | Tốt |
| shopee-chinh-sach-van-chuyen | FixedSizeChunker | 99 | 298 | Trung bình |
| shopee-chinh-sach-van-chuyen | SentenceChunker | 65 | 373 | Không ổn định |
| shopee-chinh-sach-van-chuyen | RecursiveChunker | 124 | 196 | Tốt nhưng chunk vụn |

Nhận xét: `SentenceChunker` **không tôn trọng `chunk_size`** vì nó đếm số câu chứ không đếm ký tự — văn bản chính sách có nhiều câu dài nên chunk phình tới 766 ký tự. `RecursiveChunker` cho chunk ngắn và đều nhất nhưng dễ vụn ở tài liệu dài.

### Chiến lược của từng thành viên

**Thành viên 1 — Trần Mạnh Tùng**
- **Loại chiến lược:** custom — `HeadingChunker(max_chunk_size=600)`
- **Mô tả & lý do chọn cho chủ đề này:** Tách trước mỗi dòng tiêu đề Markdown (`#`, `##`) hoặc đề mục dạng `A.`, `B.` của văn bản chính sách; mỗi mục thành một chunk, mục nào dài quá ngưỡng thì hạ xuống `RecursiveChunker` và **gắn lại tiêu đề vào từng mảnh con** (header inheritance) để không mất ngữ cảnh. Lý do: điều khoản chính sách đã được người soạn chia sẵn theo mục, mỗi mục là một đơn vị ngữ nghĩa trọn vẹn. Đây cũng là chiến lược bắt buộc phải có người nhận theo `K4_VARIANT.md`.
- **Kết quả:** 107 chunk, dài trung bình ~448 ký tự.

**Thành viên 2 — Nguyễn Hồng Thái**
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=300, overlap=50)`
- **Mô tả & lý do chọn:** Cắt cố định kèm cửa sổ trượt. `chunk_size=300` giữ chunk đủ nhỏ để một điều khoản không bị pha loãng bởi nội dung lân cận; `overlap=50` để câu nằm vắt qua mép cắt vẫn xuất hiện trọn vẹn trong ít nhất một chunk — chính là điểm yếu lớn nhất của hai chiến lược còn lại, vốn không có overlap.
- **Kết quả:** 199 chunk, dài trung bình ~294 ký tự.

**Thành viên 3 — Nguyễn Mạnh Cường**
- **Loại chiến lược:** `RecursiveChunker(chunk_size=300)` với separator mặc định `["\n\n", "\n", ". ", " ", ""]`
- **Mô tả & lý do chọn:** Thử ranh giới thô trước (đoạn), mảnh nào còn dài thì hạ dần xuống dòng, câu, từ. Bám theo cấu trúc tự nhiên của văn bản mà không cần biết trước định dạng tiêu đề.
- **Kết quả:** 210 chunk, dài trung bình ~215 ký tự.

### So Sánh Giữa Các Thành Viên

Đo trên cùng corpus, cùng 5 câu hỏi, cùng `MockEmbedder` để ba kết quả so sánh được với nhau:

| Thành viên | Chiến lược (Strategy) | Số chunk | Dài TB | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|---------|--------|----------------------|-----------|----------|
| Trần Mạnh Tùng | HeadingChunker(600) | 107 | ~448 | 1 | Chunk trùng khít một điều khoản, đọc ra là hiểu trọn vẹn | Chunk to nên một chunk chứa nhiều ý; các mục trong cùng tài liệu điểm gần bằng nhau, khó tách top-3 |
| Nguyễn Hồng Thái | FixedSizeChunker(300, 50) | 199 | ~294 | 2 | Duy nhất có overlap nên không mất thông tin ở mép cắt; độ dài đều | Cắt giữa câu, chunk có thể mở đầu bằng một mẩu từ cụt |
| Nguyễn Mạnh Cường | RecursiveChunker(300) | 210 | ~215 | 1 | Bám ranh giới tự nhiên, chunk gọn và đều | Chunk vụn nhất (có chunk chỉ 1 ký tự); không overlap nên thông tin ở mép cắt chỉ có một cơ hội lọt top-k |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Trên `MockEmbedder`, cả ba gần như ngang nhau (1–2/10) và **chênh lệch đó không chứng minh được gì** — mock băm MD5 nên điểm số là nhiễu. Vì vậy nhóm kết luận dựa trên các chỉ số không phụ thuộc embedding.
> Xét như vậy, `FixedSizeChunker(300, 50)` phù hợp nhất với chủ đề: nó là chiến lược duy nhất có **overlap**, mà văn bản chính sách hay đặt con số và điều kiện ngay sát ranh giới mục (ví dụ "60 × 60 × 60 cm", "5.000.000Đ") — không overlap thì những chi tiết đó chỉ có đúng một cơ hội nằm trong một chunk. Độ dài chunk ~294 ký tự cũng cân bằng giữa `HeadingChunker` (448, quá gộp) và `RecursiveChunker` (215, quá vụn).
> Kiểm chứng bổ sung: khi chạy lại đúng chiến lược này bằng embedder thật `gemini-embedding-001`, điểm truy xuất lên **9/10** (xem `ket_qua_benchmark.txt` của Nguyễn Hồng Thái). Điều đó cho thấy thứ hạn chế kết quả của nhóm là chất lượng embedding, không phải thiết kế chunking.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Quy định về kích thước và trọng lượng tối đa của kiện hàng đối với dịch vụ SPX Instant là bao nhiêu? | Dài ≤ 60 cm, Rộng ≤ 60 cm, Cao ≤ 60 cm; trọng lượng tối đa ≤ 30 kg sau khi đóng gói. | `ecom-shopee-co-check` |
| 2 | Người mua cần lưu ý gì khi đóng gói hàng hóa hoàn trả có chứa chất lỏng hoặc dễ vỡ? | Đóng chặt nắp chai, cho vào thùng vừa kích cỡ, dùng vật liệu đệm (bong bóng, màng co, xốp) để giảm va đập, và luôn ghi hình lại quá trình đóng gói. | `shopee-dong-goi-don-hoan-tra` |
| 3 | Người bán cần làm gì khi đơn vị vận chuyển hoàn trả hàng về kho thành công và hàng còn nguyên vẹn? | Tại mục Trả hàng thành công, chọn Xác nhận Nhận hàng → "Nhập lại hàng vào kho" → nhập số lượng thực tế và nhấn "Nhập tồn kho nhanh". | `shopee-seller-quan-ly-don-tra-hang` |
| 4 | Giá trị đơn hàng tối đa áp dụng cho phương thức thanh toán COD khi sử dụng dịch vụ SPX Instant là bao nhiêu? | 5.000.000Đ với COD (các phương thức khác là 10.000.000Đ). | `ecom-shopee-co-check` |
| 5 | Quy trình xử lý đơn trả hàng và quản lý hàng hoàn trả tại Kênh Quản Lý Shop được thực hiện như thế nào? *(cần `metadata_filter={"audience": "seller"}`)* | Người bán theo dõi trạng thái tại Kênh Quản Lý Shop; hàng nguyên vẹn thì chọn Nhập lại hàng vào kho, hàng thất lạc/hư hỏng thì chọn Thêm chi phí để được Shopee đền bù. | `shopee-seller-quan-ly-don-tra-hang` |

Cách chấm áp dụng **hai mức** như `docs/SCORING.md` yêu cầu: vừa kiểm `doc_id` của tài liệu gold có trong top-3, vừa kiểm chuỗi từ khoá đặc trưng có thật trong ngữ cảnh truy xuất được. Chỉ kiểm `doc_id` sẽ thổi phồng kết quả, vì các mục trong cùng một tài liệu có điểm gần bằng nhau nên việc mục nào lọt top-3 gần như ngẫu nhiên.

### Tổng hợp chất lượng truy xuất của nhóm

Bảng dưới đo trên `MockEmbedder` (nền chung của cả ba thành viên):

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Kích thước/trọng lượng SPX Instant | không chiến lược nào | Không | Cả ba đều trả về chunk từ `shopee-chinh-sach-van-chuyen` — đúng chủ đề vận chuyển nhưng không chứa con số |
| 2 | Đóng gói hàng hoàn trả dễ vỡ | không chiến lược nào | Không | Tài liệu vận chuyển 24.597 ký tự lấn át vì chiếm phần lớn số chunk |
| 3 | Người bán xử lý hàng hoàn về kho | FixedSize, Recursive | Một phần | Cường và Thái được 1/2, Tùng 0/2 |
| 4 | Giá trị đơn tối đa COD | không chiến lược nào | Không | Cùng nguyên nhân với câu 1 |
| 5 | Quy trình tại Kênh Quản Lý Shop | Heading, FixedSize | Có | Nhờ `metadata_filter` thu hẹp về nhóm tài liệu seller |
| | **Tổng** | | | Tùng 1/10 · Thái 2/10 · Cường 1/10 |

Đối chứng: cùng corpus và cùng 5 câu hỏi, chạy `FixedSizeChunker(300, 50)` với `gemini-embedding-001` đạt **9/10** (4 câu 2/2, câu 3 được 1/2). Nói cách khác, cả 5 câu hỏi đều **trả lời được** từ corpus này; điểm thấp ở bảng trên hoàn toàn do `MockEmbedder`.

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, ở Query 5, và bằng chứng rõ nhất nằm ở phép A/B chạy trên `MockEmbedder`: **không filter** thì top-3 là `shopee-cam-nang-tra-hang-hoan-tien`, `shopee-bang-chung-tra-hang`, `ecom-shopee-co-check` — cả ba đều `audience=buyer`, tức trả lời sai đối tượng. **Có filter** `{"audience": "seller"}` thì top-3 chuyển hẳn sang `shopee-seller-don-giao-khong-thanh-cong` và `shopee-seller-quan-ly-don-tra-hang`.
> Tuy nhiên nhóm ghi nhận một giới hạn của chính câu hỏi này: khi chạy lại bằng `gemini-embedding-001`, **hai lần A/B cho kết quả giống hệt nhau** — embedding tốt đã tự tìm đúng tài liệu seller mà không cần lọc, vì câu hỏi có chứa cụm "Kênh Quản Lý Shop" vốn chỉ xuất hiện trong tài liệu seller. Theo đúng tiêu chí của đề, như vậy Query 5 **chưa thực sự "cần" filter**; nó chỉ cần filter khi embedding yếu. Câu hỏi đạt yêu cầu cần đặt **không nêu manh mối về đối tượng**, ví dụ "Sau khi hàng hoàn trả về, cần làm gì tiếp theo?" — lúc đó tài liệu buyer và seller cùng khớp và chỉ `audience` mới tách được.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. **Chất lượng embedding chi phối kết quả mạnh hơn chiến lược chunking.** Cùng corpus, cùng câu hỏi, cùng `FixedSizeChunker(300, 50)`: `MockEmbedder` cho 2/10, `gemini-embedding-001` cho 9/10. Trong khi đó ba chiến lược chunking khác nhau chạy trên cùng mock chỉ chênh nhau 1 điểm.
> 2. **Cosine không mã hoá phủ định và không phân biệt chủ thể.** Đo bằng `compute_similarity` với embedder thật: "Đơn hàng đã được giao thành công" và "Đơn hàng giao không thành công" đạt 0.8379 dù trái nghĩa; "Người mua yêu cầu trả hàng hoàn tiền" và "Người bán xử lý đơn trả hàng hoàn tiền" đạt 0.8600. Đây chính là lý do kỹ thuật vì sao phải đưa `audience` vào metadata thay vì tin vào độ tương tự.
> 3. **Một tài liệu quá dài có thể nuốt cả corpus.** `shopee-chinh-sach-van-chuyen` chiếm 24.597 / 49.035 ký tự (50%) nên nó áp đảo số chunk, và trên mock nó chiếm top-3 của gần như mọi câu hỏi kể cả những câu nó không chứa đáp án.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng corpus và cùng câu hỏi, ba chiến lược cho số chunk chênh nhau gần gấp đôi (107 / 199 / 210) và độ dài trung bình chênh hơn gấp đôi (448 / 294 / 215) — nhưng điểm truy xuất trên mock gần như không đổi. Điều đó dạy nhóm rằng khi nền đo bị nhiễu thì **mọi so sánh chiến lược đều vô nghĩa**, và bước chọn embedder phải làm trước bước tinh chỉnh chunking chứ không phải sau.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Ba điều. Một, **bật embedder thật từ đầu buổi** để mọi số liệu so sánh có nghĩa. Hai, **không để một tài liệu chiếm 50% corpus** — nên tách `shopee-chinh-sach-van-chuyen` thành các mục nhỏ theo `category` hoặc bỏ bớt phần không liên quan tới trả hàng. Ba, **thay hai file mẫu `example.com`** bằng nguồn Shopee thật, và thiết kế câu hỏi số 5 sao cho nó thực sự mơ hồ về đối tượng thì phép A/B mới chứng minh được tác dụng của `metadata_filter` kể cả khi embedding tốt.

### Phân tích lỗi (Failure Analysis)

**Câu hỏi nào truy xuất thất bại?** Query 1 — "Kích thước và trọng lượng tối đa của kiện hàng SPX Instant", trên cả ba chiến lược khi chạy `MockEmbedder` (0/2).

**Tại sao?** Hai nguyên nhân chồng lên nhau. Thứ nhất, `MockEmbedder` băm MD5 nên điểm số không phản ánh ngữ nghĩa. Thứ hai — và đây là lỗi thật sự đáng học — top-3 đều rơi vào `shopee-chinh-sach-van-chuyen`, tài liệu **đúng chủ đề vận chuyển nhưng không chứa con số cần tìm**. Đáp án "60 × 60 × 60 cm, 30 kg" nằm trong `ecom-shopee-co-check`. Đây đúng hiện tượng *chunk giống chủ đề thắng chunk chứa đáp án*: cosine đo độ gần chủ đề chứ không đo mật độ thông tin trả lời được.

**Đề xuất cải thiện.** (1) Bật embedder thật — riêng việc này đã đưa Query 1 từ 0/2 lên 2/2. (2) Giảm ảnh hưởng của tài liệu dài bằng cách gán `category` mịn hơn rồi lọc trước khi xếp hạng, thay vì để nó cạnh tranh trên toàn corpus. (3) Ở tầng chấm, luôn kiểm chuỗi từ khoá trong nội dung chứ không chỉ kiểm `doc_id`, vì cách chấm chỉ theo `doc_id` sẽ báo "đạt" cho chính những trường hợp hỏng kiểu này.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 8 / 10 |
| Thiết kế chiến lược (Strategy Design) | 14 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10 |
| Thuyết trình (Demo) | / 5 |
| **Tổng phần nhóm** | **30 / 40** (chưa tính Demo) |
