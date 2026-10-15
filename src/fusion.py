def reciprocal_rank_fusion(*ranked_lists, k=60, top_k=20):
    scores = {}
    candidates = {}

    for results in ranked_lists:
        for rank, (document, page, text, _) in enumerate(results, start=1):
            # Temporary unique identifier for each chunk
            key = (document, page, text)

            scores[key] = scores.get(key, 0) + 1 / (k + rank)
            candidates[key] = (document, page, text)

    ranked_keys = sorted(scores, key=scores.get, reverse=True)[:top_k]

    return [(*candidates[key], scores[key]) for key in ranked_keys]


def reciprocal_rank_fusion_structured(
    *ranked_lists,
    k: int = 60,
    top_k: int = 20,
):
    if k <= 0:
        raise ValueError("k must be positive")

    if top_k <= 0:
        return []

    scores = {}
    chunks = {}

    for results in ranked_lists:
        seen_in_list = set()

        for rank, chunk in enumerate(results, start=1):
            chunk_id = chunk["chunk_id"]

            # A chunk must contribute only once per retriever
            if chunk_id in seen_in_list:
                continue

            seen_in_list.add(chunk_id)

            # RRF uses ranking positions, not raw similarity scores
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)

            chunks.setdefault(chunk_id, chunk)

    ranked_ids = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )[:top_k]

    return [
        {
            **chunks[chunk_id],
            "rrf_score": scores[chunk_id],
        }
        for chunk_id in ranked_ids
    ]
