
import sys
from src.extract import extract_pdf


def chunk_pages(pages: list[dict]) -> list[dict]:
    chunks = []

    chunk_size = 300
    overlap = 50
    step = chunk_size - overlap

    for page in pages:
        words = page["text"].split()

        for start in range(0, len(words), step):
            chunk_words = words[start:start + chunk_size]

            chunks.append({
                "document": page["document"],
                "page": page["page"],
                "chunk_index": len(chunks),
                "text": " ".join(chunk_words)
            })

    return chunks


if __name__ == "__main__":
    pages = extract_pdf(sys.argv[1])
    chunks = chunk_pages(pages)

    print("Total chunks:", len(chunks))
    print("First chunk:", chunks[0]["text"][:300])
