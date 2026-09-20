# Kịch bản demo — Lab 07, nhóm sieunhandienquang

7 phút + hỏi đáp. Trang trình chiếu: `demo.html` (mở sẵn trong trình duyệt, không cần mạng).

## Chuẩn bị trước khi lên

```bash
python scripts/build_demo.py     # sinh lại demo.html từ kết quả mới nhất
python bench.py                  # làm nóng cache, ~2 giây
```

- Mở `demo.html` ở tab 1, terminal ở tab 2. Phóng font terminal lên cỡ 18–20pt.
- Kiểm `python scripts/check_cp2.py` chạy được — đây là lệnh mở màn.
- Cache embedding đã có sẵn nên `bench.py` chạy lại mất 2 giây, không phụ thuộc mạng lúc demo.

---

## 0:00–1:00 · Chủ đề và bộ tài liệu — *Thái*

Mở phần đầu `demo.html`.

> "Nhóm làm truy xuất chính sách trả hàng của Shopee. Chọn nguồn này vì hai lý do. Một, `help.shopee.vn` cho phép crawl tự động — `robots.txt` ghi `Allow: /`. Hai, quan trọng hơn, Shopee tách sẵn nội dung thành hai cổng: `portal/4` cho người mua và `portal/1` cho người bán. Nhờ vậy nhóm có được các tài liệu **cùng chủ đề, cùng từ vựng, nhưng khác đối tượng** — đúng thứ cần để chứng minh tác dụng của metadata filter."

Chuyển sang terminal, chạy:

```bash
python scripts/check_cp2.py
```

> "10 tài liệu, đủ metadata, `sources.csv` khớp một-một, và phân bố `audience` là 6 người mua / 3 người bán / 1 chung."

---

## 1:00–3:00 · Ba chiến lược — *mỗi người 40 giây*

Cuộn tới mục **02** của `demo.html`. Mỗi người nói đúng ba ý: chọn gì, vì sao hợp với văn bản chính sách, ra bao nhiêu chunk.

**Tùng — `HeadingChunker(600)`, 107 chunk**
> "Văn bản chính sách đã được người soạn chia sẵn theo mục — `A.`, `B.`, hoặc heading Markdown. Mỗi mục là một đơn vị ngữ nghĩa trọn vẹn nên mình cắt theo đó. Mục nào dài quá thì hạ xuống recursive, và **gắn lại tiêu đề vào từng mảnh con** để mảnh thứ hai trở đi không mất ngữ cảnh."

**Thái — `FixedSizeChunker(300, 50)`, 199 chunk**
> "Mình chọn cắt cố định kèm cửa sổ trượt. 300 ký tự để một điều khoản không bị pha loãng bởi nội dung lân cận, và overlap 50 vì văn bản chính sách hay đặt con số ngay sát ranh giới mục — `60×60×60 cm`, `5.000.000Đ`. Không có overlap thì con số đó chỉ có đúng một cơ hội nằm trọn trong một chunk."

**Cường — `RecursiveChunker(300)`, 210 chunk**
> "Mình thử ranh giới thô trước là đoạn, mảnh nào còn dài thì hạ dần xuống dòng, câu, rồi từ. Ưu điểm là không cần biết trước tài liệu có định dạng tiêu đề hay không."

---

## 3:00–6:00 · So sánh và kết luận — *Thái dẫn, cả nhóm bổ sung*

Phần ăn điểm nặng nhất (15đ). Cuộn lại mục **01**.

> "Ba chiến lược cho số chunk chênh gần gấp đôi — 107, 199, 210 — và độ dài trung bình chênh hơn gấp đôi. Nhưng điểm truy xuất trên cùng nền mock là 1, 2, 1 trên 10. Gần như không đổi.
>
> Ban đầu nhóm tưởng chiến lược chunking không quan trọng. Rồi nhóm chạy lại **đúng một chiến lược đó, đúng corpus đó, đúng 5 câu hỏi đó**, chỉ đổi mô hình nhúng từ `MockEmbedder` sang `gemini-embedding-001`. Kết quả lên 9 trên 10.
>
> Bài học là: khi nền đo là nhiễu thì mọi so sánh chiến lược đều vô nghĩa. Bước chọn embedder phải làm **trước** bước tinh chỉnh chunking, không phải sau."

Chuyển sang terminal, chạy hai lệnh:

```bash
python bench.py
```
```bash
EMBEDDING_PROVIDER=mock python bench.py
```

Chỉ vào hai dòng cuối: `9 / 10` so với `2 / 10`.

Rồi kết luận chiến lược:

> "Trong ba chiến lược, nhóm chọn `FixedSizeChunker(300, 50)` là hợp nhất với chủ đề này. Không phải vì nó hơn 1 điểm trên mock — chênh lệch đó là nhiễu, không chứng minh được gì. Mà vì nó là chiến lược **duy nhất có overlap**, và độ dài chunk 294 nằm giữa 448 của heading (quá gộp) và 215 của recursive (quá vụn)."

---

## 6:00–7:00 · Demo metadata filter

Cuộn tới mục **03** của `demo.html` — hai cột đặt cạnh nhau.

> "Câu hỏi 5 chạy hai lần trên cùng một kho vector, chỉ khác tham số `metadata_filter`. Không lọc thì top-3 toàn tài liệu người mua — trả lời sai đối tượng. Lọc `audience=seller` thì chuyển hẳn sang tài liệu người bán."

Rồi nói luôn phần giới hạn, đừng giấu:

> "Nhưng khi chạy lại bằng embedder thật, hai lần cho kết quả **giống hệt nhau**. Vì câu hỏi có chứa cụm 'Kênh Quản Lý Shop' vốn chỉ xuất hiện trong tài liệu người bán, nên embedding tốt đã tự tìm đúng chỗ mà không cần lọc. Theo tiêu chí của đề thì câu hỏi này **chưa thực sự cần filter** — nó chỉ cần khi embedding yếu. Nếu làm lại, nhóm sẽ đặt câu hỏi không nêu manh mối về đối tượng, kiểu 'Sau khi hàng hoàn trả về thì cần làm gì tiếp theo?'"

---

## Hỏi đáp — ba câu hay gặp

**Chuyển sang chủ đề khác thì chiến lược nào còn dùng được?**
> `FixedSize` và `Recursive` không phụ thuộc định dạng, bê sang dữ liệu nào cũng chạy. `HeadingChunker` cần văn bản có tiêu đề rõ ràng; gặp dữ liệu không cấu trúc thì nó suy biến thành recursive, mất hết lợi thế.

**Metadata filter giúp ở đâu và làm mất kết quả ở đâu?**
> Giúp ở câu 5 như vừa demo. Làm mất: lọc `audience=seller` sẽ loại luôn tài liệu gắn `both` như `shopee-dieu-khoan-dich-vu`, dù nó có thể chứa điều khoản áp dụng cho cả hai bên. Đó là đánh đổi precision lấy recall.

**Nhóm học được gì từ nhóm khác?**
> *(điền sau khi nghe các nhóm khác trình bày)*

---

## Lá bài dự phòng

Nếu bị hỏi sâu về embedding, cuộn tới mục **05** của `demo.html`:

> "Nhóm đo 5 cặp câu bằng `compute_similarity`. Cặp 'Đơn hàng đã được giao thành công' và 'Đơn hàng giao không thành công' — **trái nghĩa nhau** — vẫn đạt 0.8379. Cặp đổi chủ thể từ người mua sang người bán đạt 0.8600. Cosine mã hoá chủ đề, không mã hoá phủ định hay chủ thể. Đó chính là lý do kỹ thuật vì sao những khác biệt đó **buộc phải** đưa vào metadata thay vì tin vào độ tương tự."

## Nếu có sự cố

- **Mất mạng:** `demo.html` tự chứa, chỉ font Google là tải từ mạng — mất mạng thì rơi về font hệ thống, nội dung vẫn đủ. `bench.py` chạy hoàn toàn bằng cache.
- **Cache embedding bị xoá:** `bench.py` sẽ gọi API 199 lần, mất khoảng 3 phút. Đừng chạy live — chỉ chiếu `ket_qua_benchmark.txt` đã có sẵn.
- **Quá giờ:** bỏ mục 05 và phần hỏi đáp dự phòng, giữ nguyên mục 01 và 03.
