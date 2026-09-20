"""Server demo cuc bo — hoi truc tiep kho tri thuc bang chinh src/ cua lab.

    python demo_server.py        # rồi mở http://localhost:8000

Server nap corpus data/ecommerce, chunk bang chien luoc ca nhan
(FixedSizeChunker 300/50), dung EmbeddingStore + KnowledgeBaseAgent trong
src/, va sinh cau tra loi qua endpoint OpenAI-compatible cua Gemini.

API key chi nam trong .env phia server, khong bao gio gui xuong trinh duyet.
Trang demo.html tu roi ve danh sach cau hoi dung san neu khong goi duoc server.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=ROOT / ".env", override=False)

from bench import CachedEmbedder, load_and_chunk_corpus  # noqa: E402
from src import FixedSizeChunker, GeminiEmbedder, KnowledgeBaseAgent, EmbeddingStore  # noqa: E402

PORT = int(os.getenv("DEMO_PORT", "8000"))
CHIEN_LUOC = "FixedSizeChunker(chunk_size=300, overlap=50)"

_state: dict = {}


def make_llm_fn():
    """Sinh cau tra loi qua thu vien openai tro toi endpoint OpenAI-compatible."""
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    model = os.getenv("OPENAI_MODEL", "gemini-3.5-flash-lite")

    def llm_fn(prompt: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()

    return llm_fn


def boot() -> None:
    print("Nap corpus va dung vector store...", flush=True)
    embedder = CachedEmbedder(GeminiEmbedder())
    docs = load_and_chunk_corpus(
        ROOT / "data" / "ecommerce",
        FixedSizeChunker(chunk_size=300, overlap=50),
    )
    store = EmbeddingStore("demo", embedding_fn=embedder)
    store.add_documents(docs)
    embedder.flush()

    _state["store"] = store
    _state["embedder"] = embedder
    _state["agent"] = KnowledgeBaseAgent(store=store, llm_fn=make_llm_fn())
    print(
        f"San sang: {store.get_collection_size()} chunk | {CHIEN_LUOC} | "
        f"{embedder._backend_name}\n  http://localhost:{PORT}\n",
        flush=True,
    )


def hoi(cau_hoi: str, loc: str | None, top_k: int = 3) -> dict:
    store: EmbeddingStore = _state["store"]
    agent: KnowledgeBaseAgent = _state["agent"]

    metadata_filter = {"audience": loc} if loc else None
    if metadata_filter:
        ket_qua = store.search_with_filter(cau_hoi, top_k=top_k, metadata_filter=metadata_filter)
    else:
        ket_qua = store.search(cau_hoi, top_k=top_k)

    try:
        tra_loi = agent.answer(cau_hoi, top_k=top_k)
    except Exception as exc:  # LLM loi thi van tra ve chunk da truy xuat
        tra_loi = f"(Không gọi được LLM: {exc.__class__.__name__}) — phần truy xuất vẫn chạy."

    return {
        "cau_hoi": cau_hoi,
        "loc": metadata_filter,
        "chien_luoc": CHIEN_LUOC,
        "tra_loi": tra_loi,
        "top": [
            {
                "doc_id": r["metadata"].get("doc_id"),
                "audience": r["metadata"].get("audience"),
                "category": r["metadata"].get("category"),
                "score": round(r["score"], 4),
                "content": r["content"].strip(),
            }
            for r in ket_qua
        ],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # bot log moi request cho gon khi demo
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("/", "/demo.html"):
            f = ROOT / "demo.html"
            if not f.exists():
                self._send(404, "Chưa có demo.html — chạy: python scripts/build_demo.py".encode(),
                           "text/plain; charset=utf-8")
                return
            self._send(200, f.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/health":
            self._send(200, json.dumps({"ok": True, "chien_luoc": CHIEN_LUOC,
                                        "chunks": _state["store"].get_collection_size()}).encode(),
                       "application/json; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if self.path.split("?")[0] != "/api/ask":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            cau_hoi = (data.get("cau_hoi") or "").strip()
            if not cau_hoi:
                raise ValueError("Câu hỏi rỗng")
            loc = data.get("loc") or None
            ket_qua = hoi(cau_hoi, loc)
            _state["embedder"].flush()
            body = json.dumps(ket_qua, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except Exception as exc:
            body = json.dumps({"loi": f"{exc.__class__.__name__}: {exc}"},
                              ensure_ascii=False).encode("utf-8")
            self._send(500, body, "application/json; charset=utf-8")


def main() -> int:
    if not (ROOT / "demo.html").exists():
        print("Thieu demo.html — chay truoc: python scripts/build_demo.py")
        return 1
    boot()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nDa dung server.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
