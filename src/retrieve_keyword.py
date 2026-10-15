import os
import re
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]


def retrieve_keyword(question: str, top_k: int = 20):
    # Extract search terms from the question
    terms = re.findall(r"\b\w+\b", question)

    if not terms:
        return []

    # PostgreSQL websearch syntax supports OR.
    # Quote each term so it is interpreted as a search term.
    broad_question = " OR ".join(f'"{term}"' for term in terms)

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                d.source_path,
                c.page,
                c.text,
                ts_rank_cd(
                    to_tsvector('english', c.text),
                    websearch_to_tsquery('english', %s)
                ) AS keyword_score
            FROM document_chunks c
            JOIN documents d
                ON d.id = c.document_id
            WHERE
                to_tsvector('english', c.text)
                @@ websearch_to_tsquery('english', %s)
            ORDER BY keyword_score DESC
            LIMIT %s;
            """,
            (question, question, top_k),
        )

        return cursor.fetchall()


def retrieve_keyword_relaxed(question: str, top_k: int = 20):
    # First try the original strict search
    results = retrieve_keyword(question, top_k=top_k)

    if results:
        return results

    # Remove common question words
    stopwords = {
        "what",
        "why",
        "how",
        "is",
        "are",
        "do",
        "does",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "to",
        "for",
        "and",
        "or",
        "between",
        "with",
        "you",
    }

    words = re.findall(r"\b\w+\b", question.lower())
    terms = [word for word in words if word not in stopwords]

    if len(terms) < 2:
        return []

    # Generate adjacent two-term search queries
    queries = [f"{terms[i]} {terms[i + 1]}" for i in range(len(terms) - 1)]

    # Search each query and collect unique candidates
    candidate_lists = [
        retrieve_keyword(query, top_k=5) for query in dict.fromkeys(queries)
    ]

    unique_results = []
    seen = set()

    # Round-robin merging prevents one query
    # from dominating the candidate list
    for position in range(5):
        for candidates in candidate_lists:
            if position >= len(candidates):
                continue

            result = candidates[position]
            document, page, text, score = result

            key = (document, page, text)

            if key not in seen:
                seen.add(key)
                unique_results.append(result)

            if len(unique_results) >= top_k:
                return unique_results

    return unique_results


def retrieve_keyword_structured(
    question: str,
    top_k: int = 20,
    document: str | None = None,
):
    if not question.strip() or top_k <= 0:
        return []

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
                SELECT
                    c.id,
                    c.document_id,
                    d.source_path,
                    c.page,
                    c.chunk_index,
                    c.text,
                    ts_rank_cd(
                        to_tsvector('english', c.text),
                        websearch_to_tsquery('english', %s)
                    ) AS score
                FROM document_chunks c
                JOIN documents d
                    ON d.id = c.document_id
                WHERE
                    to_tsvector('english', c.text)
                    @@ websearch_to_tsquery('english', %s)
                    AND (%s::text IS NULL OR d.source_path = %s)
                ORDER BY score DESC, c.id
                LIMIT %s;
                """,
            (question, question, document, document, top_k),
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


def retrieve_keyword_relaxed_structured(
    question: str,
    top_k: int = 20,
    document: str | None = None,
):
    if not question.strip() or top_k <= 0:
        return []

    # First try strict PostgreSQL full-text search
    # results = retrieve_keyword_structured(question, top_k)
    results = retrieve_keyword_structured(
        question,
        top_k=top_k,
        document=document,
    )

    if results:
        return results

    # Remove common question words
    stopwords = {
        "what",
        "why",
        "how",
        "is",
        "are",
        "do",
        "does",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "to",
        "for",
        "and",
        "or",
        "between",
        "with",
        "you",
    }

    words = re.findall(r"\b\w+\b", question.lower())
    terms = [word for word in words if word not in stopwords]

    if len(terms) < 2:
        return []

    # Generate unique adjacent-term queries
    queries = list(
        dict.fromkeys(f"{terms[i]} {terms[i + 1]}" for i in range(len(terms) - 1))
    )

    # candidate_lists = [retrieve_keyword_structured(query, top_k=5) for query in queries]
    candidate_lists = [
        retrieve_keyword_structured(
            query,
            top_k=5,
            document=document,
        )
        for query in queries
    ]

    unique_results = []
    seen_ids = set()

    # Combine candidates using round-robin selection
    for position in range(5):
        for candidates in candidate_lists:
            if position >= len(candidates):
                continue

            chunk = candidates[position]
            chunk_id = chunk["chunk_id"]

            if chunk_id in seen_ids:
                continue

            seen_ids.add(chunk_id)
            unique_results.append(chunk)

            if len(unique_results) >= top_k:
                return unique_results

    return unique_results
