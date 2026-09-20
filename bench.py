"""
Benchmark script for K4-L3B: E-commerce Policy Retrieval.
Strategy: FixedSizeChunker (chunk_size=300, overlap=50) — Chiến lược 3.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
from dotenv import load_dotenv

from src.chunking import FixedSizeChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore


class CachedEmbedder:
    """Bọc một embedder thật: cache theo hash nội dung + giãn nhịp gọi API.

    Không liên quan tới chiến lược chunking — đây chỉ là hạ tầng để chạy được
    trên free tier Gemini (giới hạn 100 request/phút) và để chạy lại không tốn
    thêm quota. Cache lưu ở .embed_cache.json, đã gitignore.
    """

    def __init__(self, inner, cache_path: str = ".embed_cache.json", min_interval: float = 0.65) -> None:
        self._inner = inner
        self._backend_name = f"{getattr(inner, '_backend_name', type(inner).__name__)} (cached)"
        self._path = Path(cache_path)
        self._min_interval = min_interval
        self._last_call = 0.0
        self._cache = {}
        if self._path.exists():
            try:
                self._cache = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}
        self._hits = 0
        self._misses = 0

    def __call__(self, text: str) -> list[float]:
        key = hashlib.md5(text.encode("utf-8")).hexdigest()
        if key in self._cache:
            self._hits += 1
            return self._cache[key]

        for attempt in range(6):
            wait = self._min_interval - (time.time() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            try:
                vec = self._inner(text)
                self._last_call = time.time()
                break
            except Exception as exc:
                self._last_call = time.time()
                delay = 20.0
                m = re.search(r"retry in ([0-9.]+)s", str(exc))
                if m:
                    delay = float(m.group(1)) + 1.0
                if "429" not in str(exc) and "RESOURCE_EXHAUSTED" not in str(exc):
                    raise
                print(f"  [rate limit] cho {delay:.0f}s roi thu lai ({attempt + 1}/6)...", flush=True)
                time.sleep(delay)
        else:
            raise RuntimeError("Het so lan thu lai voi Gemini API")

        self._misses += 1
        self._cache[key] = vec
        if self._misses % 25 == 0:
            self.flush()
        return vec

    def flush(self) -> None:
        self._path.write_text(json.dumps(self._cache), encoding="utf-8")


# Định nghĩa 5 Benchmark Queries chuẩn cho biến thể K4-L3B
BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Quy định về kích thước và trọng lượng tối đa của kiện hàng đối với dịch vụ SPX Instant là bao nhiêu?",
        "gold_answer": "Dài <= 60 cm, Rộng <= 60 cm, Cao <= 60 cm; Trọng lượng tối đa <= 30kg sau khi đóng gói.",
        "expected_doc": "ecom-shopee-co-check",
        "keywords": ["60 cm", "30kg", "SPX Instant"],
        "filter": None,
    },
    {
        "id": 2,
        "query": "Người mua cần lưu ý gì khi đóng gói hàng hóa hoàn trả có chứa chất lỏng hoặc dễ vỡ?",
        "gold_answer": "Đóng chặt nắp chai, cho vào thùng vừa với kích cỡ, sử dụng vật liệu đệm (bong bóng, màng co, xốp) để giảm va đập và luôn ghi hình lại quá trình đóng gói.",
        "expected_doc": "shopee-dong-goi-don-hoan-tra",
        "keywords": ["chất lỏng", "đóng chặt nắp", "bong bóng", "xốp"],
        "filter": None,
    },
    {
        "id": 3,
        "query": "Người bán cần làm gì khi đơn vị vận chuyển hoàn trả hàng về kho thành công và hàng còn nguyên vẹn?",
        "gold_answer": "Tại mục Trả hàng thành công, chọn Xác nhận Nhận hàng -> chọn 'Nhập lại hàng vào kho' -> nhập số lượng thực tế và nhấn 'Nhập tồn kho nhanh'.",
        "expected_doc": "shopee-seller-quan-ly-don-tra-hang",
        "keywords": ["Nhập lại hàng vào kho", "Nhập tồn kho nhanh"],
        "filter": None,
    },
    {
        "id": 4,
        "query": "Giá trị đơn hàng tối đa áp dụng cho phương thức thanh toán COD khi sử dụng dịch vụ SPX Instant là bao nhiêu?",
        "gold_answer": "Giá trị đơn hàng tối đa đối với phương thức thanh toán COD là 5.000.000Đ (các phương thức khác là 10.000.000Đ).",
        "expected_doc": "ecom-shopee-co-check",
        "keywords": ["5.000.000Đ", "COD", "SPX Instant"],
        "filter": None,
    },
    {
        # Câu hỏi bắt buộc của L3B cần metadata_filter={"audience": "seller"}
        "id": 5,
        "query": "Quy trình xử lý đơn trả hàng và quản lý hàng hoàn trả tại Kênh Quản Lý Shop được thực hiện như thế nào?",
        "gold_answer": "Người bán theo dõi trạng thái tại Kênh Quản Lý Shop. Nếu hàng nguyên vẹn thì chọn Nhập lại hàng vào kho; nếu hàng thất lạc/hư hỏng thì chọn Thêm chi phí để được Shopee đền bù.",
        "expected_doc": "shopee-seller-quan-ly-don-tra-hang",
        "keywords": ["Kênh Quản Lý Shop", "Nhập lại hàng vào kho", "Thêm chi phí"],
        "filter": {"audience": "seller"},
    },
]


def load_and_chunk_corpus(data_dir: Path, chunker) -> list[Document]:
    md_files = sorted(data_dir.glob("*.md"))
    all_docs: list[Document] = []

    for file_path in md_files:
        content = file_path.read_text(encoding="utf-8")
        if "---" in content:
            parts = content.split("---", 2)
            frontmatter_raw = parts[1]
            body_content = parts[2] if len(parts) > 2 else ""
        else:
            frontmatter_raw = ""
            body_content = content

        # Parse YAML frontmatter đơn giản
        metadata = {}
        for line in frontmatter_raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip()] = v.strip().strip('"').strip("'").split("#")[0].strip()

        doc_id = metadata.get("doc_id", file_path.stem)
        metadata["doc_id"] = doc_id

        # Chunk nội dung phần thân
        chunks = chunker.chunk(body_content)
        for idx, ch in enumerate(chunks):
            chunk_doc = Document(
                id=f"{doc_id}#{idx}",
                content=ch,
                metadata={**metadata, "chunk_index": idx, "doc_id": doc_id},
            )
            all_docs.append(chunk_doc)

    return all_docs


def run_benchmark(output_file: Path | None = None) -> None:
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            embedder = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "openai":
        try:
            embedder = OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    elif provider == "gemini":
        try:
            embedder = GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
        except Exception:
            embedder = _mock_embed
    else:
        embedder = _mock_embed

    if embedder is not _mock_embed:
        embedder = CachedEmbedder(embedder)

    data_dir = Path("data/ecommerce")
    # Chiến lược cá nhân (Chiến lược 3): cắt cố định + cửa sổ trượt.
    # chunk_size=300 giữ chunk đủ nhỏ để một điều khoản không bị pha loãng
    # bởi nội dung lân cận; overlap=50 để câu nằm vắt qua mép cắt vẫn xuất
    # hiện trọn vẹn trong ít nhất một chunk.
    chunker = FixedSizeChunker(chunk_size=300, overlap=50)
    docs = load_and_chunk_corpus(data_dir, chunker)

    store = EmbeddingStore("ecommerce_benchmark", embedding_fn=embedder)
    store.add_documents(docs)

    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("K4-L3B BENCHMARK RETRIEVAL REPORT")
    lines.append("Chiến lược: FixedSizeChunker (Cắt cố định 300 ký tự, cửa sổ trượt overlap 50)")
    lines.append(f"Mô hình nhúng (Embedder): {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")
    lines.append(f"Số lượng chunk đã nạp vào Vector Store: {store.get_collection_size()} chunks")
    lines.append("=" * 80)
    lines.append("")

    total_score = 0
    max_score = len(BENCHMARK_QUERIES) * 2

    for item in BENCHMARK_QUERIES:
        q_id = item["id"]
        q_text = item["query"]
        expected = item["expected_doc"]
        keywords = item["keywords"]
        m_filter = item["filter"]

        lines.append(f"Query {q_id}: {q_text}")
        lines.append(f"Câu trả lời chuẩn (Gold): {item['gold_answer']}")
        if m_filter:
            lines.append(f"Metadata filter áp dụng: {m_filter}")
            results = store.search_with_filter(q_text, top_k=3, metadata_filter=m_filter)
        else:
            results = store.search(q_text, top_k=3)

        # Đánh giá 2 mức (doc_id và nội dung chứa từ khóa)
        top1_doc = results[0]["metadata"].get("doc_id") if results else None
        top_docs = [r["metadata"].get("doc_id") for r in results]
        
        has_relevant_content = False
        gold_at_top1 = (top1_doc == expected)
        gold_in_top3 = (expected in top_docs)

        for r in results:
            if any(kw.lower() in r["content"].lower() for kw in keywords):
                has_relevant_content = True
                break

        if gold_at_top1 and has_relevant_content:
            score = 2
        elif gold_in_top3 or has_relevant_content:
            score = 1
        else:
            score = 0

        total_score += score
        lines.append(f"Điểm đánh giá câu này: {score}/2 đ")
        lines.append("Top-3 Chunks tìm thấy:")
        for rank, r in enumerate(results, start=1):
            chunk_doc_id = r["metadata"].get("doc_id")
            score_val = r["score"]
            preview = r["content"].replace("\n", " ")[:110]
            lines.append(f"  [{rank}] Score: {score_val:.4f} | Doc: {chunk_doc_id} | Preview: {preview}...")
        lines.append("-" * 80)

    # Thử nghiệm A/B trên Query 5 (So sánh Không filter vs Có filter)
    lines.append("")
    lines.append("=== THỬ NGHIỆM A/B: HIỆU QUẢ CỦA METADATA FILTERING TRÊN QUERY 5 ===")
    q5 = BENCHMARK_QUERIES[4]["query"]
    res_no_filter = store.search(q5, top_k=3)
    res_filtered = store.search_with_filter(q5, top_k=3, metadata_filter={"audience": "seller"})

    lines.append(f"Query: {q5}")
    lines.append("1. Khi KHÔNG dùng filter:")
    for rank, r in enumerate(res_no_filter, start=1):
        lines.append(f"   [{rank}] Doc: {r['metadata'].get('doc_id')} (audience: {r['metadata'].get('audience')})")

    lines.append("2. Khi CÓ filter {'audience': 'seller'}:")
    for rank, r in enumerate(res_filtered, start=1):
        lines.append(f"   [{rank}] Doc: {r['metadata'].get('doc_id')} (audience: {r['metadata'].get('audience')})")

    lines.append("")
    lines.append("=" * 80)
    lines.append(f"TỔNG KẾT ĐIỂM TRUY XUẤT (RETRIEVAL QUALITY): {total_score} / {max_score}")
    lines.append("=" * 80)

    if isinstance(embedder, CachedEmbedder):
        embedder.flush()
        lines.append(f"Cache embedding: {embedder._hits} hit / {embedder._misses} goi API moi")

    output_content = "\n".join(lines)
    print(output_content)

    if output_file:
        output_file.write_text(output_content, encoding="utf-8")
        print(f"\nĐã xuất toàn bộ kết quả vào: {output_file}")


if __name__ == "__main__":
    out_path = Path("ket_qua_benchmark.txt")
    run_benchmark(out_path)
