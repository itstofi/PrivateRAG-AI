# Architecture

## Components

The Streamlit process is a replaceable API client. FastAPI owns validation and orchestration. Services implement workspace, document, and chat use cases. The ingestion and RAG packages contain model-independent document and retrieval logic. SQLite stores relational state; ChromaDB stores vectors and chunk metadata; the filesystem stores original uploads under generated names.

## Ingestion flow

1. FastAPI reads the bounded upload and validates filename, extension, MIME, signature, and size.
2. The service computes SHA-256 and checks for a duplicate in the selected workspace.
3. It writes the file under a generated UUID filename and inserts a pending database record.
4. A format loader extracts cleaned, page-aware text.
5. The chunker splits each page with configurable overlap and skips empty chunks.
6. Ollama creates embeddings in batches while parser, file, and Chroma operations run off the
   async event loop.
7. Chroma upserts vectors with document, workspace, page, chunk, and embedding-model metadata.
8. SQLite records indexed/failed status, pages, chunks, and a sanitized processing error.

One malformed document moves to `failed`; it does not interrupt management of other files.

## Query flow

The question is normalized and multi-part questions are decomposed into focused variants. Each
variant is embedded locally, and every Chroma search receives the mandatory `workspace_id`
filter. Results are merged, similarity-thresholded, stripped of repeated overlapping chunks, and
optionally diversified with MMR. Follow-up questions can include the previous user turn for
retrieval.

Only chunks that fit the context budget become citations. The prompt labels those sources,
wraps source text and conversation history as untrusted data, marks instruction-like content,
and includes potential numeric conflicts between documents. Ollama streams the answer; citations,
conflicts, and retrieval settings are saved with the assistant message. Invalid model-generated
source numbers are replaced with an explicit unsupported-citation marker before persistence.

When no context meets the threshold, the application returns its fixed insufficient-context response without calling the chat model.

## Storage choices

- SQLite fits a local, single-user workload and provides transactions, foreign keys, indexes, and portable backups. WAL improves responsiveness.
- ChromaDB provides durable cosine search and metadata filtering without a separate server.
  Each embedding-model name maps to a separate collection, preventing dimension collisions after
  model changes. Document/workspace deletion scans all managed collections.
- Original uploads remain available for reindexing. Database rows never store full extracted text.

All paths derive from `DATA_DIR`. Deletions are checked against the resolved upload root.
Alembic owns relational schema upgrades; startup upgrades to the current revision and stamps the
pre-migration v1 schema safely before applying later migrations.

## Model abstraction

`OllamaService` owns REST transport, availability checks, generation, streaming, and embeddings. `EmbeddingService` adds batching. `Generator` and `Retriever` keep orchestration testable with fakes. No cloud model provider is present.

## Workspace isolation

Workspace IDs are foreign keys in SQLite and required filters in every vector search. Chat
continuation validates workspace ownership. Workspace deletion removes vectors from every
managed embedding collection, confined upload files, and cascading relational records.

## Error handling

Known failures use typed application exceptions mapped to stable JSON errors. Unexpected exceptions are logged locally with stack traces while clients receive a generic message. Logs contain IDs and diagnostics, not document text or prompts.

Streaming failures after headers are sent end the NDJSON stream; the UI shows a local connection error without losing already rendered tokens.

## Trade-offs

- In-process ingestion makes initial deployment simple but holds an API request open for embedding. A local job queue is a future scaling option.
- Character chunking is language-agnostic and lightweight, but tokenizer-aware splitting may pack context more precisely.
- Conflict detection is deliberately conservative and numeric; it signals potential conflicts
  for the model and user rather than claiming legal or semantic resolution.
- Runtime settings are process-local by design. Environment variables remain the auditable persistent configuration.
- Chroma and SQLite are appropriate for a personal application, not a high-concurrency multi-tenant service.

## Future scaling

The service boundaries allow a background job runner, PostgreSQL, a remote self-hosted vector database, OCR, reranking, or a React frontend without rewriting loaders and prompt logic. Multi-user deployment would additionally require identity, authorization, encryption-key management, audit logging, and network hardening.
