from flashrank import RerankRequest

from src.fusion import reciprocal_rank_fusion_structured
from src.rag_pipeline import get_ranker
from src.retrieve_keyword import retrieve_keyword_relaxed_structured
from src.retrieve_local import retrieve_local_structured

# Provisional reference pages based on earlier experiments.
# Verify these against the actual PDF text before treating
# benchmark scores as ground-truth quality measurements.
TEST_CASES = [
    {
        "question": "What is implied volatility?",
        "document": "test.pdf",
        "reference_pages": [105, 532],
    },
    {
        "question": "Explain delta hedging.",
        "document": "JC Hull.pdf",
        "reference_pages": [426, 445],
    },
    {
        "question": "What programming languages and frameworks are listed?",
        "document": "Mohammad_Ali_CV.pdf",
        "reference_pages": [1, 2],
    },
    {
        "question": "What is an iron condor?",
        "document": "test.pdf",
        "reference_pages": [280, 563],
    },
    {
        "question": "How does Hull define implied volatility?",
        "document": "JC Hull.pdf",
        "reference_pages": [363],
    },
]


def retrieve_ranked(
    question,
    document=None,
    retrieval_k=20,
    final_k=5,
    fusion_k=30,
):
    semantic = retrieve_local_structured(
        question,
        top_k=retrieval_k,
        document=document,
    )

    keyword = retrieve_keyword_relaxed_structured(
        question,
        top_k=retrieval_k,
        document=document,
    )

    hybrid = reciprocal_rank_fusion_structured(
        semantic,
        keyword,
        top_k=fusion_k,
    )

    if not hybrid:
        return []

    passages = [{"id": chunk["chunk_id"], "text": chunk["text"]} for chunk in hybrid]

    ranked = get_ranker().rerank(RerankRequest(query=question, passages=passages))

    by_id = {chunk["chunk_id"]: chunk for chunk in hybrid}

    return [by_id[item["id"]] for item in ranked[:final_k]]


def main():
    hits = 0
    reciprocal_ranks = []

    for index, case in enumerate(TEST_CASES, 1):
        results = retrieve_ranked(
            case["question"],
            document=case["document"],
        )

        relevant_pages = set(case["reference_pages"])

        # First relevant result determines reciprocal rank.
        first_relevant_rank = None

        for rank, chunk in enumerate(results, 1):
            if (
                chunk["document"] == case["document"]
                and chunk["page"] in relevant_pages
            ):
                first_relevant_rank = rank
                break

        hit = first_relevant_rank is not None

        hits += int(hit)
        reciprocal_ranks.append(1 / first_relevant_rank if hit else 0)

        # Scope isolation must hold for every returned chunk.
        assert all(chunk["document"] == case["document"] for chunk in results), (
            f"Document leakage in test {index}"
        )

        print(f"\nTest {index}: {case['question']}")
        print(f"Document: {case['document']}")
        print(f"Hit@5: {hit}")
        print(f"First relevant rank: {first_relevant_rank}")

        print("Top results:")
        for rank, chunk in enumerate(results, 1):
            print(f"  {rank}. {chunk['document']} | Page {chunk['page']}")

    count = len(TEST_CASES)

    print("\n" + "=" * 50)
    print("RETRIEVAL EVALUATION")
    print("=" * 50)
    print(f"Questions: {count}")
    print(f"Hit@5: {hits / count:.1%}")
    print(f"MRR@5: {sum(reciprocal_ranks) / count:.3f}")
    print("Document isolation: PASS")


if __name__ == "__main__":
    main()
