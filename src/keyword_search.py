import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()


def keyword_search(question: str, limit: int = 5):

    phrase = question.lower().strip()

    phrase = phrase.removeprefix("what is ")

    phrase = phrase.rstrip("?.! ")

    with (
        psycopg.connect(os.environ["DATABASE_URL"]) as conn,
        conn.cursor() as cursor,
    ):
        cursor.execute(
            """
                SELECT
                    document,
                    page,
                    text,
                    ts_rank(
                        to_tsvector('english', text),
                        websearch_to_tsquery('english', %s)
                    )
                    +
                    CASE
                        WHEN POSITION(%s IN LOWER(LEFT(text, 250))) > 0
                        THEN 0.2
                        ELSE 0
                    END
                    +
                    CASE
                        WHEN LOWER(text) LIKE %s
                        OR LOWER(text) LIKE %s
                        THEN 2.0
                        ELSE 0
                    END AS rank
                FROM chunks
                WHERE to_tsvector('english', text)
                    @@ websearch_to_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s;
                """,
            (
                question,
                phrase,
                f"%{phrase} is %",
                f"%{phrase} represents %",
                question,
                limit,
            ),
        )

        return cursor.fetchall()


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    results = keyword_search(question)

    for document, page, text, rank in results:
        print(f"\nDocument: {document}")
        print(f"Page: {page}")
        print(f"Rank: {rank:.4f}")
        print(f"Text: {text[:300]}")
