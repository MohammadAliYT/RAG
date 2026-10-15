import os

import psycopg
from dotenv import load_dotenv
from fastembed import TextEmbedding
from pgvector.psycopg import register_vector

load_dotenv()

BATCH_SIZE = 10


def embed_local_chunks():
    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    with (
        psycopg.connect(os.environ["DATABASE_URL"]) as conn,
        conn.cursor() as cursor,
    ):
        register_vector(conn)

        cursor.execute(
            """
            SELECT id, text
            FROM chunks
            WHERE embedding_local IS NULL
            ORDER BY id
            LIMIT %s;
            """,
            (BATCH_SIZE,),
        )

        rows = cursor.fetchall()

        if not rows:
            print("No chunks need local embeddings.")
            return

        texts = [row[1] for row in rows]

        embeddings = list(model.embed(texts))

        for (chunk_id, _), embedding in zip(rows, embeddings, strict=True):
            cursor.execute(
                """
                UPDATE chunks
                SET embedding_local = %s
                WHERE id = %s;
                """,
                (embedding, chunk_id),
            )

        print(f"Stored {len(embeddings)} local embeddings.")


if __name__ == "__main__":
    embed_local_chunks()
