import re
from collections import Counter

from src.extract import extract_pdf


def normalize_header(line: str) -> str:
    # Remove changing page numbers
    line = re.sub(r"\d+", "", line)

    # Normalize whitespace and capitalization
    return " ".join(line.lower().split()).strip()


def detect_headers(pages, min_occurrences=4):
    counts = Counter()

    for page in pages:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]

        # Inspect only the first two lines
        candidates = {normalize_header(line) for line in lines[:2]}

        counts.update(candidate for candidate in candidates if len(candidate) > 5)

    return [
        (header, count)
        for header, count in counts.most_common()
        if count >= min_occurrences
    ]


def remove_repeated_headers(pages):
    # Detect headers repeated across at least 8 pages
    headers = {header for header, count in detect_headers(pages, min_occurrences=8)}

    cleaned_pages = []

    for page in pages:
        lines = page["text"].splitlines()

        # Find the first two non-empty lines
        first_lines = [i for i, line in enumerate(lines) if line.strip()][:2]

        # Identify repeated header lines
        remove_indices = {
            i for i in first_lines if normalize_header(lines[i]) in headers
        }

        # Remove adjacent page numbers only when a header was detected
        if remove_indices:
            remove_indices.update(i for i in first_lines if lines[i].strip().isdigit())

        cleaned_text = "\n".join(
            line for i, line in enumerate(lines) if i not in remove_indices
        )

        cleaned_pages.append(
            {
                **page,
                "text": clean_pdf_text(cleaned_text),
            }
        )

    return cleaned_pages


def clean_pdf_text(text: str) -> str:
    text = re.sub(r"\u00ad[ \t]*\n[ \t]*", "", text)
    text = text.replace("\u00ad", "")
    return text


if __name__ == "__main__":
    pages = extract_pdf("data/test.pdf")

    headers = detect_headers(pages)

    for header, count in headers[:15]:
        print(f"{count} pages | {header}")
