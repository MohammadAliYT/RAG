import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]


def expand_context(chunks, before=1, after=1):
    if not chunks:
        return []

    if before < 0 or after < 0:
        raise ValueError("Neighbor counts cannot be negative")

    chunk_ids = list(dict.fromkeys(chunk["chunk_id"] for chunk in chunks))
    matched_ids = set(chunk_ids)

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
                WITH seeds AS (
                    SELECT id, document_id, page, chunk_index
                    FROM document_chunks
                    WHERE id = ANY(%s)
                ),
                selected AS (
                    -- Original retrieved chunks
                    SELECT id FROM seeds

                    UNION ALL

                    -- Preceding chunks within the same document
                    SELECT previous.id
                    FROM seeds s
                    CROSS JOIN LATERAL (
                        SELECT c.id
                        FROM document_chunks c
                        WHERE c.document_id = s.document_id
                          AND (c.page, c.chunk_index)
                              < (s.page, s.chunk_index)
                        ORDER BY c.page DESC, c.chunk_index DESC
                        LIMIT %s
                    ) previous

                    UNION ALL

                    -- Following chunks within the same document
                    SELECT following.id
                    FROM seeds s
                    CROSS JOIN LATERAL (
                        SELECT c.id
                        FROM document_chunks c
                        WHERE c.document_id = s.document_id
                          AND (c.page, c.chunk_index)
                              > (s.page, s.chunk_index)
                        ORDER BY c.page, c.chunk_index
                        LIMIT %s
                    ) following
                )
                SELECT
                    c.id,
                    c.document_id,
                    d.source_path,
                    c.page,
                    c.chunk_index,
                    c.text
                FROM document_chunks c
                JOIN (
                    SELECT DISTINCT id FROM selected
                ) selected_chunks
                    ON selected_chunks.id = c.id
                JOIN documents d
                    ON d.id = c.document_id
                ORDER BY
                    c.document_id, c.page, c.chunk_index;
                """,
            (chunk_ids, before, after),
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
            "matched": row[0] in matched_ids,
        }
        for row in rows
    ]
