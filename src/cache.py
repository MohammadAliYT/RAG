import os

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from src.embed import embed_text

load_dotenv()

MODEL = "gemini-embedding-2"


def get_question_embedding(question: str) -> np.ndarray:
    # Step 1: Check whether the question is cached
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        register_vector(conn)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT embedding
                FROM question_embedding_cache
                WHERE question = %s AND model = %s
                """,
                (question, MODEL),
            )

            result = cursor.fetchone()

            if result is not None:
                print("CACHE HIT: Using stored embedding")
                return result[0]

    # Step 2: Generate embedding when not cached
    print("CACHE MISS: Calling Gemini API")

    embedding = np.array(embed_text(question), dtype=np.float32)

    # Step 3: Save the embedding for future use
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        register_vector(conn)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO question_embedding_cache
                    (question, model, embedding)
                VALUES (%s, %s, %s)
                ON CONFLICT (question, model) DO NOTHING
                """,
                (question, MODEL, embedding),
            )

    return embedding
