"""PageRank and Personalized PageRank over the vault's wikilink graph."""
import networkx as nx


class PageRankRanker:
    def __init__(self):
        self.graph: nx.DiGraph | None = None
        self.scores: dict[str, float] = {}

    def build_graph(self, link_graph: dict[str, set[str]]):
        self.graph = nx.DiGraph()
        for source, targets in link_graph.items():
            self.graph.add_node(source)
            for target in targets:
                self.graph.add_edge(source, target)

    def compute_global(self, alpha: float = 0.85) -> dict[str, float]:
        if not self.graph or self.graph.number_of_nodes() == 0:
            return {}
        try:
            self.scores = nx.pagerank(self.graph, alpha=alpha)
        except nx.PowerIterationFailedConvergence:
            self.scores = {n: 1.0 / self.graph.number_of_nodes() for n in self.graph.nodes}
        return self.scores

    def personalized_search(self, seed_docs: list[str], top_k: int = 50) -> list[tuple[str, float]]:
        if not self.graph or not seed_docs:
            return []

        personalization = {}
        valid_seeds = [d for d in seed_docs if d in self.graph]
        if not valid_seeds:
            return [(doc, self.scores.get(doc, 0)) for doc in sorted(self.scores, key=self.scores.get, reverse=True)[:top_k]]

        weight = 1.0 / len(valid_seeds)
        for doc in valid_seeds:
            personalization[doc] = weight

        try:
            ppr = nx.pagerank(self.graph, alpha=0.85, personalization=personalization)
        except nx.PowerIterationFailedConvergence:
            ppr = self.scores

        ranked = sorted(ppr.items(), key=lambda kv: -kv[1])[:top_k]
        return ranked

    def get_score(self, rel_path: str) -> float:
        return self.scores.get(rel_path, 0.0)
