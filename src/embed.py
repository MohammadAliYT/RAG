
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()

def embed_text(text: str) -> list[float]:
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        )
    )
    return response.embeddings[0].values

if __name__ == "__main__":
    vector = embed_text("Python is a programming language.")
    print("Dimensions:", len(vector))
    print("First 5 values:", vector[:5])
