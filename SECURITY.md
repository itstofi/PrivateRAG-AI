# Security and Privacy

## Privacy model

PrivateRAG AI has no cloud AI integration, analytics, advertising, tracking pixels, remote
logging, or crash reporting. Ollama inference and embeddings, SQLite chat history, Chroma
vectors, and uploaded files remain local. Streamlit usage collection is disabled, and the Chroma
client explicitly sets `anonymized_telemetry=False`.

The configured Ollama URL can point to another machine. If changed from localhost, the operator is responsible for the network's confidentiality and trust.

## Local data locations

By default:

- Uploads: `data/uploads/`
- Vectors and chunk excerpts: `data/vector_store/`
- Metadata and chats: `data/database/private_rag.db`
- Logs: standard output only unless redirected by the operator

Deleting a document removes its vectors, file, and database row. Deleting a workspace performs those actions for every associated document and cascades chats/messages. Filesystem recovery may still be possible on unencrypted media; use full-disk encryption and secure deletion controls appropriate to your OS.

## Threat model

Protected against:

- Accidental cloud disclosure through an AI provider
- Basic path traversal and unsafe stored filenames
- Oversized, empty, extension-mismatched, malformed, and oversized-expansion DOCX files
- Duplicate indexing in a workspace
- Cross-workspace retrieval through missing metadata filters
- SQL injection through ORM-generated parameterized statements
- Prompt injection in documents through context-as-data boundaries, explicit instruction-like
  content warnings, and higher-priority grounding rules
- Deletion outside the configured application upload directory

Not protected against:

- A compromised operating system, Ollama process, Python dependency, or administrator account
- Other local users who can read the data directory
- Network attackers when the API/UI/Ollama are exposed beyond localhost
- Denial of service from authorized uploads within configured limits
- Malicious documents exploiting an unknown parser vulnerability
- Highly persuasive prompt injection defeating the local model despite defensive prompting

## Upload protections

The server accepts only PDF, DOCX, TXT, and Markdown. It checks both slash styles and control
characters in basenames, extension, declared MIME, PDF/ZIP signatures, UTF-8 text, emptiness, and
configurable bytes before persistence. DOCX archives must contain required parts and stay within
entry-count and uncompressed-size limits. PDF page count and extracted text are capped. Stored
names are UUIDs. SHA-256 prevents duplicates per workspace. Parsers run without shell commands
or macros.

Run the application as an unprivileged user. For higher-risk content, add OS/container sandboxing and malware scanning that does not send files to a cloud service.

## API and network

CORS defaults to the local Streamlit origin. No credentialed cross-origin requests are enabled. This version intentionally has no authentication and must not be exposed to an untrusted network. Bind ports to loopback when operating outside Docker or adjust Compose bindings for your environment.

## Logging policy

JSON logs include timestamps, levels, module names, document IDs, and exception diagnostics. Code must never log raw uploads, extracted chunks, prompts, questions, answers, or full request bodies. User-facing errors omit internal details and stack traces.

## Secrets

No AI keys are needed. `.env` is ignored. Do not put secrets in tracked configuration or Ollama URLs.

## Known risks

Chroma stores chunk text alongside vectors. SQLite stores chat contents in plaintext. Backups and
filesystem snapshots may retain deleted information. Defensive prompting reduces but cannot
guarantee elimination of prompt injection or model hallucination. DOCX/PDF parsing relies on
third-party native and Python libraries; keep pinned dependencies updated after reviewing release
notes and running tests.

The v1.0.0 dependency audit reports `CVE-2026-45829` against ChromaDB 1.5.9's unauthenticated
network server collection-creation endpoint. No fixed PyPI release was available during this
audit. PrivateRAG AI does not start or expose the Chroma FastAPI server: it uses the embedded
`PersistentClient` against a local directory and never accepts Chroma model-repository
configuration from API users. Do not add a network Chroma server until a patched release is
pinned and reviewed.

## Reporting

Do not open a public issue containing a sensitive document, local path, chat transcript, or exploit details. Contact the repository maintainer privately through the security contact configured on the hosting platform.
