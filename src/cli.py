from src.generate import generate_answer
from src.search import search_chunks


def main():
    print("RAG CLI started. Type 'exit' to quit.")

    while True:
        question = input("\nAsk a question: ").strip()

        if question.lower() in ("exit", "quit"):
            break

        if not question:
            continue

        # Step 1: Retrieve relevant chunks
        chunks, mode = search_chunks(question, limit=5)

        if not chunks:
            print("No relevant documents found.")
            continue

        # Step 2: Generate an answer
        answer = generate_answer(question, chunks)

        # Step 3: Display answer
        print("\n" + "=" * 60)
        print("ANSWER")
        print("=" * 60)
        print(answer)

        # Step 4: Display retrieval sources
        print(f"\nRetrieval mode: {mode}")
        print("\nSOURCES")
        print("-" * 60)

        for document, page, text, score in chunks:
            if mode == "semantic":
                metric = f"Cosine similarity: {1 - score:.1%}"
            else:
                metric = f"Reranker rank: {score:.4f}"

            print(f"{document} | Page {page} | {metric}")

        print("=" * 60)


if __name__ == "__main__":
    main()
