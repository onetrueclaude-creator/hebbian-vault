"""Reciprocal Rank Fusion — merges multiple ranked lists without weight tuning."""


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
    top_n: int = 20,
) -> list[tuple[str, float]]:
    """Merge multiple ranked lists using RRF.

    Each input is a list of (doc_id, score) tuples, ordered by score descending.
    Output is a merged list of (doc_id, rrf_score) tuples.

    RRF formula: score(d) = sum(1 / (k + rank_i(d))) for each ranker i
    """
    rrf_scores: dict[str, float] = {}

    for ranked_list in ranked_lists:
        for rank, (doc_id, _score) in enumerate(ranked_list):
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
            rrf_scores[doc_id] += 1.0 / (k + rank + 1)

    merged = sorted(rrf_scores.items(), key=lambda kv: -kv[1])
    return merged[:top_n]
