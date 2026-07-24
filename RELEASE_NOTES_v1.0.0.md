# PrivateRAG AI v1.0.0

PrivateRAG AI is a local-first document question-answering application built around Ollama. It
organizes private files into isolated workspaces, retrieves relevant local evidence, streams a
grounded answer, and exposes page-aware source citations.

## Main features

- Fully local Ollama chat inference and embeddings
- PDF, DOCX, TXT, and Markdown ingestion
- SHA-256 duplicate detection and generated stored filenames
- Workspace-filtered ChromaDB retrieval
- Query decomposition, similarity thresholds, MMR, overlap deduplication, and context budgets
- Page-aware citations with excerpts and semantic similarity
- Conflict warnings and defensive prompt-injection boundaries
- SQLite chat history with resume, rename, delete, and Markdown export
- FastAPI/OpenAPI backend and professional Streamlit interface
- Alembic database migrations, Docker Compose, GitHub Actions, and offline RAG evaluation

## Privacy model

Documents, extracted chunks, embeddings, model requests, and conversations stay within the
configured local environment. There is no cloud AI fallback, tracking, advertising, or remote
application logging. Chroma telemetry is explicitly disabled and Streamlit usage collection is
disabled.

## Installation summary

```bash
cp .env.example .env
make install
make setup
ollama pull llama3.2:3b
ollama pull nomic-embed-text
make run-api
make run-ui
```

Models are never downloaded automatically.

## Known limitations

- Designed for one trusted local user; no authentication or multi-user authorization
- Scanned PDFs need OCR before upload
- DOCX page numbers are unavailable
- The offline evaluator does not judge model prose or hallucinations
- Changing embedding models requires reindexing documents into the new active collection
- No guarantee against every parser exploit or prompt-injection technique
- ChromaDB 1.5.9 has a published network-server advisory; this release uses only the embedded
  local client and must not expose a Chroma server

## Planned next features

- Local OCR
- Hybrid keyword/vector retrieval and local reranking
- Encrypted workspace import/export
- Model-specific local faithfulness evaluation
- Replaceable React client using the existing API
