from flashrank import Ranker, RerankRequest

from src.keyword_search import keyword_search

ranker = Ranker(
    model_name="ms-marco-MiniLM-L-12-v2",
    cache_dir=".models",
)


def rerank_chunks(question: str, limit: int = 5):
    # Retrieve 100 candidates from PostgreSQL
    candidates = keyword_search(question, limit=100)

    if not candidates:
        return []

    # Prepare passages for the reranking model
    passages = [{"id": i, "text": chunk[2]} for i, chunk in enumerate(candidates)]

    # Score passages against the original question
    request = RerankRequest(
        query=question,
        passages=passages,
    )

    ranked = ranker.rerank(request)

    results = []

    for item in ranked[:limit]:
        original = candidates[item["id"]]

        results.append(
            (
                original[0],  # Document
                original[1],  # Page
                original[2],  # Text
                float(item["score"]),
            )
        )

    return results


if __name__ == "__main__":
    question = "What is a put option?"

    results = rerank_chunks(question, limit=10)

    for position, (document, page, text, score) in enumerate(results, start=1):
        print(f"{position}. Page {page} | Reranker score: {score:.4f}")
        print(text[:120])
        print()
