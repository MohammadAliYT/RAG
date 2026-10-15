from functools import lru_cache
from time import perf_counter

from flashrank import Ranker, RerankRequest

from src.context_assemble import assemble_context
from src.context_expand import expand_context
from src.fusion import reciprocal_rank_fusion_structured
from src.generate import generate_answer_from_context
from src.retrieve_keyword import retrieve_keyword_relaxed_structured
from src.retrieve_local import retrieve_local_structured


@lru_cache(maxsize=1)
def get_ranker():
    """Load FlashRank once and reuse it."""
    return Ranker(
        model_name="ms-marco-MiniLM-L-12-v2",
        cache_dir=".models",
    )


def ask_document(
    question: str,
    retrieval_k: int = 20,
    final_k: int = 5,
    max_context_tokens: int = 4000,
    document: str | None = None,
    fusion_k: int = 30,
) -> dict:
    """Run the complete document-grounded RAG pipeline."""

    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty")

    if retrieval_k <= 0 or final_k <= 0 or fusion_k <= 0:
        raise ValueError("Retrieval, fusion, and final limits must be positive")

    start = perf_counter()

    # 1. Semantic retrieval
    semantic = retrieve_local_structured(
        question,
        top_k=retrieval_k,
        document=document,
    )

    # 2. Keyword retrieval
    keyword = retrieve_keyword_relaxed_structured(
        question,
        top_k=retrieval_k,
        document=document,
    )

    # 3. Reciprocal Rank Fusion
    hybrid = reciprocal_rank_fusion_structured(
        semantic,
        keyword,
        top_k=fusion_k,
    )

    if not hybrid:
        return {
            "question": question,
            "answer": "No relevant context found.",
            "sources": [],
            "context_tokens": 0,
            "stats": {
                "semantic": len(semantic),
                "keyword": len(keyword),
                "hybrid": 0,
                "elapsed_seconds": round(perf_counter() - start, 2),
            },
        }

    # 4. FlashRank reranking
    passages = [
        {
            "id": chunk["chunk_id"],
            "text": chunk["text"],
        }
        for chunk in hybrid
    ]

    ranked = get_ranker().rerank(
        RerankRequest(
            query=question,
            passages=passages,
        )
    )

    chunks_by_id = {chunk["chunk_id"]: chunk for chunk in hybrid}

    top_chunks = [chunks_by_id[item["id"]] for item in ranked[:final_k]]

    # 5. Neighboring-chunk expansion
    expanded = expand_context(
        top_chunks,
        before=1,
        after=1,
    )

    # 6. Context assembly
    assembled = assemble_context(
        top_chunks,
        expanded,
        max_tokens=max_context_tokens,
    )

    # 7. Gemini answer generation
    answer = generate_answer_from_context(
        question=question,
        context=assembled["context"],
    )

    # Unique source documents and PDF pages
    source_pairs = sorted(
        {(chunk["document"], chunk["page"]) for chunk in assembled["chunks"]}
    )

    sources = [{"document": document, "page": page} for document, page in source_pairs]

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "context_tokens": assembled["token_count"],
        "stats": {
            "semantic": len(semantic),
            "keyword": len(keyword),
            "hybrid": len(hybrid),
            "reranked": len(top_chunks),
            "expanded": len(expanded),
            "selected": len(assembled["chunks"]),
            "elapsed_seconds": round(perf_counter() - start, 2),
        },
    }
