from chonkie import SentenceChunker, TokenChunker
from tokenizers import Tokenizer

from src.extract import extract_pdf
from src.pdf_preprocess import remove_repeated_headers

tokenizer = Tokenizer.from_pretrained("BAAI/bge-small-en-v1.5")

chunker = SentenceChunker(
    tokenizer=tokenizer,
    chunk_size=320,
    chunk_overlap=50,
)

MAX_CHUNK_TOKENS = 480

fallback_chunker = TokenChunker(
    tokenizer=tokenizer,
    chunk_size=MAX_CHUNK_TOKENS,
    chunk_overlap=40,
)


def chunk_text(text: str):
    sentence_chunks = chunker(text)
    safe_chunks = []

    for chunk in sentence_chunks:
        if chunk.token_count <= MAX_CHUNK_TOKENS:
            safe_chunks.append(chunk)
        else:
            # Split oversized chunks using token boundaries
            smaller_chunks = fallback_chunker(chunk.text)
            safe_chunks.extend(smaller_chunks)

    # Validate before sending anything for embedding
    for chunk in safe_chunks:
        if chunk.token_count > MAX_CHUNK_TOKENS:
            raise ValueError(f"Oversized chunk: {chunk.token_count} tokens")

    return safe_chunks


if __name__ == "__main__":
    pages = extract_pdf("data/test.pdf")
    pages = remove_repeated_headers(pages)

    total_chunks = 0
    max_tokens = 0

    for page in pages:
        if not page["text"].strip():
            continue

        chunks = chunk_text(page["text"])

        total_chunks += len(chunks)

        for chunk in chunks:
            max_tokens = max(max_tokens, chunk.token_count)

        if page["page"] == 105:
            print("\nPDF page 105:")
            for chunk in chunks:
                print(f"Tokens: {chunk.token_count}")
                print(f"Text: {chunk.text[:150]}\n")

    print(f"Pages processed: {len(pages)}")
    print(f"Total chunks: {total_chunks}")
    print(f"Maximum chunk tokens: {max_tokens}")
