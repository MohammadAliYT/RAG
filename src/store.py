
import os
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from src.embed import embed_text

load_dotenv()


def store_chunk(chunk: dict, embedding: list[float]) -> int:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        register_vector(conn)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chunks
                    (document, page, chunk_index, text, embedding)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    chunk["document"],
                    chunk["page"],
                    chunk["chunk_index"],
                    chunk["text"],
                    embedding
                )
            )

            return cursor.fetchone()[0]


if __name__ == "__main__":
    chunk = {
        "document": "test.txt",
        "page": 1,
        "chunk_index": 0,
        "text": "An option gives the holder the right, but not the obligation, to buy or sell an asset."
    }

    vector = embed_text(chunk["text"])
    record_id = store_chunk(chunk, vector)

    print("Inserted record ID:", record_id)
