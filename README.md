
# RAG SYS

**A modular, document-grounded Retrieval-Augmented Generation (RAG) engine built with Python, PostgreSQL/pgvector, local embeddings, hybrid search, reranking, and Google Gemini.**

RAG SYS lets users ingest PDF documents and ask questions against their content. It supports searching across an entire document collection or limiting retrieval to a specific PDF.

**Project status:** Core RAG pipeline implemented and tested. FastAPI, React, and deployment are planned next.

## Why this project?

The goal is to understand and implement the components of a RAG system directly, rather than relying on orchestration frameworks such as LangChain.

This project explores document extraction, chunking, embedding, retrieval, fusion, reranking, context construction, grounding, and evaluation as separate, testable stages.

The system is designed to work with multiple PDFs across different domains.

## Features

- **PDF ingestion:** Page-level text extraction using PyMuPDF.
- **Text preprocessing:** Repeated-header cleanup and text normalization.
- **Token-aware chunking:** Chonkie sentence chunking with fallback splitting for oversized passages.
- **Local embeddings:** BAAI/bge-small-en-v1.5 via FastEmbed.
- **Vector database:** PostgreSQL with pgvector and cosine similarity.
- **Hybrid retrieval:** Combines semantic search and PostgreSQL full-text search.
- **Reciprocal Rank Fusion:** Combines ranked retrieval candidates.
- **Neural reranking:** FlashRank reranks retrieved passages.
- **Context expansion:** Retrieves neighboring chunks for additional context.
- **Token budgeting:** Controls the amount of evidence passed to the language model.
- **Answer generation:** Google Gemini generates document-grounded answers with source references.
- **Document filtering:** Search all PDFs or restrict retrieval to one selected document.
- **Incremental indexing:** Uses SHA-256 hashes and pipeline versions to avoid unnecessary reprocessing.
- **Retrieval evaluation:** Initial benchmarks for Hit@K, MRR, and document isolation.

## Architecture

```text
PDF Documents
      |
      v
PyMuPDF Text Extraction
      |
      v
Text Preprocessing
      |
      v
Chonkie Sentence Chunking
      |
      v
FastEmbed (BGE-small-en-v1.5)
      |
      v
PostgreSQL + pgvector
      |
      |
User Question + Optional Document Filter
      |
      +--------------------------+
      |                          |
      v                          v
Semantic Vector Search     PostgreSQL Keyword Search
      |                          |
      +------------+-------------+
                   |
                   v
          Reciprocal Rank Fusion
                   |
                   v
             FlashRank Reranking
                   |
                   v
            Context Expansion
                   |
                   v
             Token Budgeting
                   |
                   v
              Google Gemini
                   |
                   v
         Answer + Source References
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13 |
| PDF Extraction | PyMuPDF |
| Chunking | Chonkie |
| Embedding Model | BGE-small-en-v1.5 |
| Embedding Runtime | FastEmbed |
| Vector Database | PostgreSQL + pgvector |
| Database Driver | psycopg 3 |
| Keyword Search | PostgreSQL Full-Text Search |
| Rank Fusion | Reciprocal Rank Fusion |
| Reranking | FlashRank |
| LLM | Google Gemini |
| Database Runtime | Docker |
| Backend API (planned) | FastAPI |
| Frontend (planned) | React + TypeScript |

The RAG pipeline is implemented directly in Python without LangChain.

## Project Structure

```text
rag-cli/
├── src/
│   ├── extract.py
│   ├── pdf_preprocess.py
│   ├── chunk_chonkie.py
│   ├── ingestv2.py
│   ├── retrieve_local.py
│   ├── retrieve_keyword.py
│   ├── fusion.py
│   ├── context_expand.py
│   ├── context_assemble.py
│   ├── generate.py
│   ├── rag_pipeline.py
│   └── evaluate_retrieval.py
├── data/
├── .env
├── .gitignore
└── README.md
```

## Retrieval Configuration

| Parameter | Default |
|-----------|---------|
| Chunk size | 320 tokens |
| Chunk overlap | 50 tokens |
| Embedding dimensions | 384 |
| Semantic candidates | 20 |
| Keyword candidates | 20 |
| RRF candidates | 30 |
| Reranked passages | 5 |
| Context expansion | 1 neighboring chunk on each side |
| Maximum context budget | Approximately 4,000 tokens |

These are current experimental defaults, not universally optimal configurations.

## Getting Started

### Prerequisites

- Python 3.13
- Docker
- PostgreSQL with pgvector
- Google Gemini API key

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Replace the repository URL with your own GitHub URL.

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Once dependency specifications are available:

```bash
pip install -r requirements.txt
```

### 3. Start PostgreSQL

Example development database:

```bash
docker run -d \
  --name rag-postgres \
  -e POSTGRES_USER=raguser \
  -e POSTGRES_PASSWORD=change-this-password \
  -e POSTGRES_DB=rag \
  -p 5433:5432 \
  pgvector/pgvector:pg17
```

Enable pgvector:

```bash
docker exec rag-postgres \
  psql -U raguser -d rag \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

**Note:** A fresh database also requires the application's `documents` and `document_chunks` schema. Reproducible schema initialization and migrations are planned.

### 4. Environment variables

Create a `.env` file:

```dotenv
DATABASE_URL=postgresql://raguser:change-this-password@localhost:5433/rag
GEMINI_API_KEY=your_api_key
```

Never commit the `.env` file.

### 5. Ingest documents

Place PDF files inside `data/`.

```bash
python -m src.ingestv2
```

The ingestion pipeline:

1. Discovers PDF files.
2. Extracts and preprocesses text.
3. Divides content into token-aware chunks.
4. Generates local embeddings.
5. Stores chunks and vectors in PostgreSQL.
6. Skips previously indexed documents when appropriate.

**Note:** During development, `test.pdf` was excluded from ingestion discovery to preserve its existing index. Remove that local exclusion for a fresh installation.

### 6. Query all documents

```python
from src.rag_pipeline import ask_document

result = ask_document(
    "Explain delta hedging."
)

print(result["answer"])
print(result["sources"])
```

### 7. Query a specific document

```python
from src.rag_pipeline import ask_document

result = ask_document(
    "What is implied volatility?",
    document="JC Hull.pdf"
)

print(result["answer"])
```

The document parameter restricts both semantic and keyword retrieval before rank fusion.

## Initial Evaluation Results

The retrieval pipeline was evaluated using a small collection of questions across three indexed PDFs.

| Metric | Result |
|--------|--------|
| Hit@5 | 100% (5/5) |
| MRR@5 | 0.900 |
| Document isolation | 3/3 tests passed |
| Retrieval regression | 5/5 tests passed |
| Citation provenance | 4/4 parsed citations valid |
| Unsupported-question abstention | Passed sampled tests |

**Evaluation limitation:** These are preliminary results from a small, provisional benchmark. They are not representative accuracy guarantees. Reference-page labels still require broader independent validation.

### Retrieval Improvement

An initial cross-document comparison failed to retrieve a relevant passage from one financial textbook.

Investigation showed that:

- Semantic retrieval found the passage at rank 16.
- RRF with a top-20 cutoff discarded it.
- Increasing the fusion candidate pool to 30 allowed FlashRank to evaluate it.
- FlashRank subsequently ranked the passage first.

This demonstrates the importance of evaluating individual stages rather than treating retrieval as a black box.

## Known Limitations

- Complex PDF layouts, tables, and mathematical equations can lose formatting during extraction.
- Strict keyword retrieval may miss long natural-language questions.
- Global retrieval can return irrelevant passages from unrelated documents.
- Source citations do not guarantee that every generated claim is supported.
- Citation provenance has been tested, but comprehensive claim-level verification is not implemented.
- Automatic contradiction detection remains experimental.
- Similarity scores have not been calibrated into reliable answerability thresholds.
- The application currently has no user authentication or multi-user access-control enforcement.

## Development Roadmap

### Phase 1: Core RAG Engine

- [x] PDF extraction
- [x] Text preprocessing
- [x] Token-aware chunking
- [x] Local embedding generation
- [x] PostgreSQL + pgvector
- [x] Semantic retrieval
- [x] Keyword retrieval
- [x] Reciprocal Rank Fusion
- [x] Neural reranking
- [x] Context expansion
- [x] Gemini integration
- [x] Multi-document retrieval
- [x] Document-scoped search

### Phase 2: Evaluation and Reliability

- [x] Initial retrieval benchmark
- [x] Multi-document retrieval testing
- [x] Document-isolation tests
- [x] Citation provenance experiment
- [x] Abstention experiments
- [x] Retrieval regression tests
- [ ] Comprehensive claim-level verification
- [ ] Reliable automatic contradiction detection
- [ ] Expanded independently labeled benchmark

### Phase 3: Full-Stack Application

- [ ] FastAPI backend
- [ ] Document upload API
- [ ] Document management endpoints
- [ ] React + TypeScript frontend
- [ ] Chat interface
- [ ] Document selection
- [ ] Source citations
- [ ] Loading and error handling

### Phase 4: Deployment

- [ ] Dockerized application services
- [ ] Reproducible database migrations
- [ ] Automated tests
- [ ] CI/CD
- [ ] Production configuration
- [ ] Security improvements
- [ ] Deployment and monitoring

## Privacy and Security

Embedding generation runs locally.

However, retrieved document context is transmitted to the Google Gemini API for answer generation.

Do not upload sensitive documents unless this data flow is acceptable.

The repository should not contain private CVs, licensed books, personal records, API keys, or credentials.

Document-scoped retrieval is not a substitute for user-level access control.

## Future Improvements

- DOCX and PPTX ingestion
- Table-aware document extraction
- Conversation history
- Streaming responses
- Semantic caching
- Improved citation verification
- Automated RAG evaluation
- Configurable retrieval strategies
- Multi-user document collections

## Project Status

**Core RAG engine: Operational**

**Current focus: Building a full-stack application with FastAPI and React.**
