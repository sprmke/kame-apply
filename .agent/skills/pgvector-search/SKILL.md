---
name: pgvector-search
description: "pgvector + pg_trgm search in Postgres: embeddings with fastembed, hybrid ranking, workspace-scoped queries."
---

# pgvector search

- Embeddings from `fastembed` (`bge-small-en-v1.5`; `multilingual-e5-small` for non-English). Store in `vector(384)` columns with an HNSW index.
- Hybrid: trigram/FTS candidate set + vector rerank. Tune in the matching phase against a golden set, not by feel.
- Queries are workspace-scoped through RLS; shared job-corpus tables are the only unscoped reads and are read-only to the app role.
- Re-embed on model change via a DBOS workflow; keep `embedding_model` on the row.
