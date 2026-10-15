
from pathlib import Path
import sys
import pymupdf


def extract_pdf(pdf_path: str) -> list[dict]:
    pages = []

    with pymupdf.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            if text:
                pages.append({
                    "document": Path(pdf_path).name,
                    "page": page_number,
                    "text": text
                })

    return pages


if __name__ == "__main__":
    pdf_path = sys.argv[1]
    pages = extract_pdf(pdf_path)

    print("Pages extracted:", len(pages))

    if pages:
        print("First page:", pages[0]["page"])
        print("Text preview:", pages[0]["text"][:200])
