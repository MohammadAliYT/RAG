from google.genai import errors

from src.rerank import rerank_chunks
from src.retrieve import retrieve_chunks


def search_chunks(question: str, limit: int = 5):
    try:
        chunks = retrieve_chunks(question, limit)
        return chunks, "semantic"

    except errors.ClientError as error:
        if error.code != 429:
            raise

        print("Gemini embedding quota reached.")
        print("Using keyword search + local reranking.")

        chunks = rerank_chunks(question, limit)
        return chunks, "reranked"
