import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastembed import TextEmbedding
from pgvector import Vector
from pgvector.psycopg import register_vector

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]

# Load the embedding model once
model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def retrieve_local_structured(
    question: str,
    top_k: int = 5,
    document: str | None = None,
) -> list[dict]:

    if not question.strip() or top_k <= 0:
        return []

    # Generate the query embedding
    embedding = next(model.embed([question]))
    query_vector = Vector(embedding.tolist())

    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.document_id,
                    d.source_path,
                    c.page,
                    c.chunk_index,
                    c.text,
                    1 - (c.embedding <=> %s) AS similarity

                FROM document_chunks c

                JOIN documents d
                    ON d.id = c.document_id

                WHERE (%s::text IS NULL OR d.source_path = %s)

                ORDER BY c.embedding <=> %s, c.id
                LIMIT %s;
                """,
                (
                    query_vector,
                    document,
                    document,
                    query_vector,
                    top_k,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "chunk_id": row[0],
            "document_id": row[1],
            "document": row[2],
            "page": row[3],
            "chunk_index": row[4],
            "text": row[5],
            "score": row[6],
        }
        for row in rows
    ]
