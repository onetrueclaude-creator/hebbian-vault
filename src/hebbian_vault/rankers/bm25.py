"""BM25 keyword ranking using bm25s."""
import re
import bm25s


class BM25Ranker:
    def __init__(self):
        self.retriever = None
        self.doc_ids: list[str] = []

    def build_index(self, documents: dict[str, str]):
        self.doc_ids = list(documents.keys())
        corpus = [documents[did] for did in self.doc_ids]
        corpus_tokens = bm25s.tokenize(corpus, stopwords="en")
        self.retriever = bm25s.BM25()
        self.retriever.index(corpus_tokens)

    def search(self, query: str, top_k: int = 50) -> list[tuple[str, float]]:
        if not self.retriever or not self.doc_ids:
            return []
        query_tokens = bm25s.tokenize([query], stopwords="en")
        results, scores = self.retriever.retrieve(query_tokens, k=min(top_k, len(self.doc_ids)))

        ranked = []
        for idx, score in zip(results[0], scores[0]):
            if score > 0 and idx < len(self.doc_ids):
                ranked.append((self.doc_ids[idx], float(score)))
        return ranked
