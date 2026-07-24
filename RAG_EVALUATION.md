# RAG Evaluation

## Purpose

The local evaluation suite checks retrieval behavior without cloud APIs or a language-model
download. It exercises the same query preprocessing, query decomposition, workspace filtering,
MMR selection, overlap deduplication, context budgeting, conflict detection, citation metadata,
and prompt construction used by the application.

## Dataset

`evaluation/rag_cases.json` indexes five original fictional documents into two logical
workspaces and defines six cases:

| Case | Expected behavior |
| --- | --- |
| Direct answer | Retrieve the employment-policy PDF and preserve its page citation |
| Two sources | Retrieve the security policy and original employment policy |
| Conflicting information | Retrieve both volunteer-day policies and flag different values |
| Insufficient context | Return the fixed insufficient-context decision |
| Document prompt injection | Retrieve the note while preserving the higher-priority prompt boundary |
| Wrong workspace | Refuse a finance question in the knowledge-base workspace |

The corpus deliberately includes a fictional policy amendment with a conflicting allowance and
an untrusted note containing instruction-like text.

## Method

Run:

```bash
make evaluate
```

The evaluator:

1. Loads and chunks the real sample files with production loaders.
2. Creates deterministic, local bag-of-words embeddings using SHA-256 token buckets.
3. Searches through the production `Retriever` using a local in-memory vector adapter.
4. Checks expected source filenames, workspace metadata, chunk/page citation metadata,
   refusal behavior, conflict notices, and the prompt-injection boundary.
5. Writes machine-readable results to `evaluation/latest_results.json`.

Deterministic embeddings are used so CI stays offline and repeatable. They do not claim to
measure the semantic quality of a particular Ollama embedding model.

## Results

Audit run on 2026-07-23:

| Metric | Result |
| --- | ---: |
| Correct source retrieval | 6/6 |
| Workspace isolation | 6/6 |
| Citation metadata accuracy | 6/6 |
| Correct refusal decision | 6/6 |
| Conflict detection | 6/6 |
| Prompt-injection boundary | 6/6 |
| Complete case pass | 6/6 |

## Interpretation and limitations

The suite measures deterministic retrieval and orchestration, not generative answer style or
factual faithfulness for every local model. The optional real-Ollama integration test verifies
connectivity only. A future model-specific evaluation should add a locally run judge rubric,
larger multilingual corpora, paraphrases, scanned-document/OCR cases, and recall-at-k tracking
across supported embedding models.

