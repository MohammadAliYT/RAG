import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from src.cache import get_question_embedding

load_dotenv()


def retrieve_chunks(question: str, limit: int = 3):
    # Convert the question into an embedding
    embedding = get_question_embedding(question)

    # Connect to PostgreSQL
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        register_vector(conn)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT document, page, text,
                       embedding <=> %s AS distance
                FROM chunks
                WHERE embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT %s;
                """,
                (embedding, limit),
            )
            return cursor.fetchall()


if __name__ == "__main__":
    # question = "What rights does an option contract give its holder?"
    question = "How does implied volatility affect option prices?"

    results = retrieve_chunks(question)

    for document, page, text, distance in results:
        print(f"\nDocument: {document}")
        print(f"Page: {page}")
        print(f"Cosine distance: {distance:.4f}")
        print(f"Text: {text}")
