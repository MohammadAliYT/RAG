from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()

response = client.interactions.create(
    model="gemini-3.8-flash",
    input="Reply with exactly: Gemini API works",
    store=False,
)

print(response.output_text)