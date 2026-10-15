
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def create_tables():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;

                CREATE TABLE IF NOT EXISTS chunks (
                    id BIGSERIAL PRIMARY KEY,
                    document TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding VECTOR(768)
                );
            """)

    print("Database tables created successfully")


if __name__ == "__main__":
    create_tables()
