import os
import sys
import time
import psycopg

from dotenv import load_dotenv
from src.extract import extract_pdf
from src.chunk import chunk_pages
from src.embed import embed_text
from src.store import store_chunk

load_dotenv()


def ingest_book(pdf_path: str):
    pages = extract_pdf(pdf_path)
    chunks = chunk_pages(pages)

    print(f"Total chunks: {len(chunks)}")

    # Find chunks already stored
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT chunk_index FROM chunks
                WHERE document = %s
                """,
                (pages[0]["document"],),
            )
            completed = {row[0] for row in cursor.fetchall()}

    print(f"Already stored: {len(completed)} chunks")

    # Process remaining chunks
    for i, chunk in enumerate(chunks, start=1):
        if chunk["chunk_index"] in completed:
            continue

        # Retry temporary API failures
        for attempt in range(5):
            try:
                vector = embed_text(chunk["text"])
                store_chunk(chunk, vector)

                print(f"[{i}/{len(chunks)}] Stored page {chunk['page']}")

                time.sleep(1.2)
                break

            except Exception as error:
                status = getattr(error, "code", None)

                if status not in (429, 503):
                    raise

                if attempt == 4:
                    print(f"Stopped at chunk {i}: {error}")
                    print("Run again to resume.")
                    return

                # Respect rate limits and retry server errors
                wait = 60 if status == 429 else min(60, 5 * (2**attempt))

                print(f"API error {status}. Retrying in {wait}s...")
                time.sleep(wait)

    print("Ingestion completed!")


if __name__ == "__main__":
    ingest_book(sys.argv[1])
