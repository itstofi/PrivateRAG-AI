# Changelog

All notable changes follow a simplified Keep a Changelog format.

## Unreleased

### Fixed

- Kept greetings and standalone summary requests out of follow-up query context
- Renamed the citation percentage in the UI to semantic similarity so it is not mistaken for
  answer confidence

## [1.0.0] - 2026-07-23

### Added

- Local PDF, DOCX, TXT, and Markdown ingestion with validation and duplicate detection
- Ollama embeddings, generation, availability checks, and response streaming
- Query preprocessing/decomposition, workspace-filtered Chroma retrieval, MMR, and overlap deduplication
- Context-aligned page citations, source scores, conflict warnings, and insufficient-context handling
- Prompt-injection boundaries and instruction-like source detection
- SQLite workspace, document, chat, and message persistence
- Alembic migrations and embedding-model-specific Chroma collections
- FastAPI endpoints and a polished, offline-resilient Streamlit management interface
- Local privacy controls, defensive deletion, Docker, CI, tests, scripts, release templates, and documentation
- Deterministic offline RAG evaluation dataset with six passing cases

### Fixed

- Offloaded parser, filesystem, and Chroma operations from async request execution
- Prevented citations from referencing chunks omitted by the context budget
- Removed repeated overlapping chunks and invalid model-generated citation numbers
- Deleted document/workspace vectors across every managed embedding collection
- Hardened DOCX archive, UTF-8, cross-platform filename, PDF page, and extracted-text validation
- Corrected sample-loader MIME types and package-style developer script execution
- Returned structured errors when an active response stream fails
