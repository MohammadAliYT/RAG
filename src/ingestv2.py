import hashlib
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastembed import TextEmbedding
from pgvector import Vector
from pgvector.psycopg import register_vector

from src.chunk_chonkie import chunk_text
from src.extract import extract_pdf
from src.pdf_preprocess import remove_repeated_headers

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
DATA_DIR = Path("data")
BATCH_SIZE = 32

MODEL_NAME = "BAAI/bge-small-en-v1.5"
PIPELINE_VERSION = "chonkie-320-50-bge-small-v1"
# PIPELINE_VERSION = "chonkie-320-50-bge-small-safe480-v2"


def file_hash(path: Path) -> str:
    """Calculate SHA-256 to detect changed documents."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def create_tables():
    """Create tables without changing the original RAG index."""
    with (
        psycopg.connect(DATABASE_URL) as conn,
        conn.cursor() as cursor,
    ):
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id BIGSERIAL PRIMARY KEY,
                source_path TEXT NOT NULL UNIQUE,
                sha256 TEXT NOT NULL,
                pipeline_version TEXT NOT NULL,
                indexed_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL
                    REFERENCES documents(id) ON DELETE CASCADE,
                page INT NOT NULL,
                chunk_index INT NOT NULL,
                text TEXT NOT NULL,
                token_count INT NOT NULL,
                embedding VECTOR(384) NOT NULL,

                UNIQUE (document_id, page, chunk_index)
            );
        """)


def ingest_pdf(pdf_path: Path, model: TextEmbedding):
    source_path = pdf_path.relative_to(DATA_DIR).as_posix()
    current_hash = file_hash(pdf_path)

    # Check whether this document is already indexed.
    with (
        psycopg.connect(DATABASE_URL) as conn,
        conn.cursor() as cursor,
    ):
        cursor.execute(
            """
            SELECT sha256, pipeline_version
            FROM documents
            WHERE source_path = %s;
            """,
            (source_path,),
        )

        existing = cursor.fetchone()

        if existing == (current_hash, PIPELINE_VERSION):
            print(f"SKIPPED (unchanged): {source_path}")
            return

    print(f"\nProcessing: {source_path}", flush=True)

    # Extract and preprocess.
    pages = extract_pdf(str(pdf_path))
    pages = remove_repeated_headers(pages)

    records = []

    # Chunk each page using Chonkie.
    for page in pages:
        chunks = chunk_text(page["text"])

        for index, chunk in enumerate(chunks):
            if chunk.token_count > 512:
                raise ValueError(f"Chunk exceeds BGE limit on page {page['page']}")

            records.append(
                (
                    page["page"],
                    index,
                    chunk.text,
                    chunk.token_count,
                )
            )

    print(f"Generated {len(records)} chunks.", flush=True)

    # Save document and embeddings in one transaction.
    # IMPORTANT: Register pgvector on the connection BEFORE creating its cursor.
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (
                    source_path, sha256, pipeline_version
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (source_path)
                DO UPDATE SET
                    sha256 = EXCLUDED.sha256,
                    pipeline_version = EXCLUDED.pipeline_version,
                    indexed_at = NOW()
                RETURNING id;
                """,
                (source_path, current_hash, PIPELINE_VERSION),
            )

            document_id = cursor.fetchone()[0]

            # Remove outdated chunks for changed documents.
            cursor.execute(
                "DELETE FROM document_chunks WHERE document_id = %s;",
                (document_id,),
            )

            for start in range(0, len(records), BATCH_SIZE):
                batch = records[start : start + BATCH_SIZE]
                texts = [record[2] for record in batch]

                # Generate local BGE embeddings.
                embeddings = list(model.embed(texts, batch_size=BATCH_SIZE))

                values = [
                    (
                        document_id,
                        page,
                        chunk_index,
                        text,
                        token_count,
                        Vector(embedding.tolist()),
                    )
                    for (
                        page,
                        chunk_index,
                        text,
                        token_count,
                    ), embedding in zip(batch, embeddings, strict=True)
                ]

                cursor.executemany(
                    """
                    INSERT INTO document_chunks (
                        document_id,
                        page,
                        chunk_index,
                        text,
                        token_count,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    values,
                )

                print(
                    f"Embedded {start + len(batch)}/{len(records)}",
                    flush=True,
                )

    print(f"COMPLETED: {source_path}")


def main():
    create_tables()

    # pdf_files = sorted(
    #     path
    #     for path in DATA_DIR.rglob("*")
    #     if path.is_file() and path.suffix.lower() == ".pdf"
    # )

    pdf_files = sorted(
        path
        for path in DATA_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf" and path.name != "test.pdf"
    )

    print(f"Found {len(pdf_files)} PDF(s).")

    if not pdf_files:
        return

    # Load the embedding model once.
    model = TextEmbedding(model_name=MODEL_NAME)

    for pdf_path in pdf_files:
        ingest_pdf(pdf_path, model)

    print("\nDocument ingestion finished.")


if __name__ == "__main__":
    main()
