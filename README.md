# Local-first AI Policy Helper

A local-first RAG app for product and policy questions. It runs fully offline with a deterministic stub LLM, or can be pointed at a real model when you add a key. The stack is FastAPI (backend), Next.js (frontend), and Qdrant (vector DB).

**Setup**

1. Copy env
```bash
cp .env.example .env
```

2. Run everything
```bash
docker compose up --build
```

3. Open endpoints
- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs
- Qdrant: http://localhost:6333

4. Ingest sample docs
```bash
curl -X POST http://localhost:8000/api/ingest
```

5. Ask a question
```bash
curl -X POST http://localhost:8000/api/ask -H 'Content-Type: application/json' \
  -d '{"query":"What's the shipping SLA to East Malaysia for bulky items?"}'
```

**Architecture**

```
Browser (Next.js)
  |  /api/ask, /api/ingest
  v
FastAPI backend
  |  chunk + embed + store
  |  retrieve + generate
  v
Qdrant (vector DB)
```

Key flows:
- Ingestion: `data/` documents are chunked and embedded, then stored in Qdrant.
- Q&A: the backend retrieves top-k chunks, builds a prompt, and returns an answer plus citations.
- Local-first: when no keys are present, a deterministic stub LLM and built-in embedding keep the app functional offline.

Project layout:
```
backend/app/main.py      FastAPI routes and wiring
backend/app/rag.py       embeddings, retrieval, generation
backend/app/ingest.py    loaders + chunking
frontend/app/page.tsx    main UI
frontend/components/*    chat + admin panel
```

**Trade-offs**

- Hash-based deterministic embeddings for offline use. These vectors are fast and reproducible but not truly semantic, so retrieval quality is limited compared to real embeddings. This is acceptable for small doc sets and local-first demos.
- Deterministic stub LLM for offline use. This guarantees reproducible behavior, but the quality is lower than a real model.
- Fixed-size chunking (default `CHUNK_SIZE=300` tokens). This keeps context windows small and latency predictable, but long documents can lose cross-section context.

**What I'd ship next**

1. Online embeddings (e.g., OpenAI `text-embedding-3-small`) for stronger semantic search.
2. More testing and analysis on the docs to fine-tune chunk size and overlap.
3. Persistent Qdrant storage via a mounted volume.
4. File upload with auto-ingest for non-technical users.
5. Auto-detect network availability and use OpenRouter when online.

**Tests**

```bash
docker compose run --rm backend pytest -q
```
