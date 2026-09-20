from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    NO_CONTEXT = "(khong tim thay tai lieu lien quan trong kho tri thuc)"

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        prompt = self._build_prompt(question, results)
        return self.llm_fn(prompt)

    def _build_prompt(self, question: str, results: list[dict]) -> str:
        if results:
            context = "\n\n".join(
                f"[{i}] (nguon: {r['metadata'].get('doc_id', r['id'])}, score={r['score']:.3f})\n{r['content']}"
                for i, r in enumerate(results, start=1)
            )
        else:
            context = self.NO_CONTEXT

        return (
            "Ban la tro ly tra loi dua tren tai lieu duoc cung cap.\n"
            "Chi dung thong tin trong phan NGU CANH. Neu ngu canh khong du de tra loi, "
            "hay noi ro la khong tim thay trong tai lieu, khong duoc suy doan.\n"
            "Khi tra loi, dan so hieu doan da dung, vi du [1].\n\n"
            f"NGU CANH:\n{context}\n\n"
            f"CAU HOI: {question}\n\n"
            "TRA LOI:"
        )
