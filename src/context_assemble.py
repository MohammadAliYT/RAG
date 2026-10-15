from src.chunk_chonkie import tokenizer


def assemble_context(matches, expanded, max_tokens=4000):
    """
    Build a source-attributed context within a token budget.

    Prioritize matched chunks, then nearby context.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")

    selected = []
    seen_ids = set()
    total_tokens = 0

    def add_chunk(chunk):
        nonlocal total_tokens

        chunk_id = chunk["chunk_id"]

        if chunk_id in seen_ids:
            return

        header = (
            f"[Document: {chunk['document']} | "
            f"PDF page: {chunk['page']} | "
            f"Chunk: {chunk['chunk_index']}]\n"
        )

        block = header + chunk["text"].strip()

        token_count = len(tokenizer.encode(block).ids)

        if total_tokens + token_count > max_tokens:
            return

        selected.append(
            {
                **chunk,
                "token_count": token_count,
                "formatted_text": block,
            }
        )

        seen_ids.add(chunk_id)
        total_tokens += token_count

    # Priority 1: Keep the highest-ranked evidence
    for chunk in matches:
        add_chunk(chunk)

    # Priority 2: Add nearby chunks for each ranked match
    for match in matches:
        neighbors = [
            chunk
            for chunk in expanded
            if chunk["document_id"] == match["document_id"]
            and chunk["chunk_id"] not in seen_ids
            and (
                (
                    chunk["page"] == match["page"]
                    and abs(chunk["chunk_index"] - match["chunk_index"]) == 1
                )
                or abs(chunk["page"] - match["page"]) == 1
            )
        ]

        # Prefer same-page neighbors, then adjacent pages
        neighbors.sort(
            key=lambda chunk: (
                abs(chunk["page"] - match["page"]),
                abs(chunk["chunk_index"] - match["chunk_index"]),
            )
        )

        for neighbor in neighbors:
            add_chunk(neighbor)

    context = "\n\n---\n\n".join(chunk["formatted_text"] for chunk in selected)

    return {
        "context": context,
        "chunks": selected,
        "token_count": total_tokens,
    }
