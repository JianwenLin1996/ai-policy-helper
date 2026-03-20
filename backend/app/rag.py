import time, os, math, json, hashlib, logging
import uuid
from typing import List, Dict, Tuple, Optional
import numpy as np
from .settings import settings
from .ingest import chunk_text, doc_hash
from qdrant_client import QdrantClient, models as qm

logger = logging.getLogger(__name__)

# ---- Simple local embedder (deterministic) ----
def _tokenize(s: str) -> List[str]:
    """Lowercase-split a string into tokens."""
    return [t.lower() for t in s.split()]

class LocalEmbedder:
    def __init__(self, dim: int = 384):
        """Initialize the local deterministic embedder."""
        self.dim = dim

    def embed(self, text: str) -> np.ndarray:
        """Create a deterministic pseudo-embedding for text."""
        # Hash-based repeatable pseudo-embedding
        h = hashlib.sha1(text.encode("utf-8")).digest()
        rng_seed = int.from_bytes(h[:8], "big") % (2**32-1)
        rng = np.random.default_rng(rng_seed)
        v = rng.standard_normal(self.dim).astype("float32")
        # L2 normalize
        v = v / (np.linalg.norm(v) + 1e-9)
        return v

# ---- Vector store abstraction ----
class InMemoryStore:
    def __init__(self, dim: int = 384):
        """Initialize an in-memory vector store."""
        self.dim = dim
        self.vecs: List[np.ndarray] = []
        self.meta: List[Dict] = []
        self._hashes = set()

    def upsert(self, vectors: List[np.ndarray], metadatas: List[Dict]):
        """Insert vectors and metadata, skipping duplicate hashes."""
        for v, m in zip(vectors, metadatas):
            h = m.get("hash")
            if h and h in self._hashes:
                continue
            self.vecs.append(v.astype("float32"))
            self.meta.append(m)
            if h:
                self._hashes.add(h)

    def search(self, query: np.ndarray, k: int = 4) -> List[Tuple[float, Dict]]:
        """Search for nearest vectors by cosine similarity."""
        if not self.vecs:
            return []
        A = np.vstack(self.vecs)  # [N, d]
        q = query.reshape(1, -1)  # [1, d]
        # cosine similarity
        sims = (A @ q.T).ravel() / (np.linalg.norm(A, axis=1) * (np.linalg.norm(q) + 1e-9) + 1e-9)
        idx = np.argsort(-sims)[:k]
        return [(float(sims[i]), self.meta[i]) for i in idx]

class QdrantStore:
    def __init__(self, collection: str, dim: int = 384):
        """Initialize a Qdrant-backed vector store."""
        self.client = QdrantClient(url="http://qdrant:6333", timeout=10.0)
        self.collection = collection
        self.dim = dim
        self._ensure_collection()

    def _clean_payload(self, payload: Dict) -> Dict:
        """Ensure payload values are JSON-serializable."""
        cleaned: Dict = {}
        for k, v in payload.items():
            if v is None:
                continue
            if isinstance(v, (np.integer, np.floating)):
                cleaned[k] = v.item()
                continue
            if isinstance(v, np.ndarray):
                cleaned[k] = v.tolist()
                continue
            if isinstance(v, (list, tuple)):
                out = []
                for item in v:
                    if isinstance(item, (np.integer, np.floating)):
                        out.append(item.item())
                    else:
                        out.append(item)
                cleaned[k] = out
                continue
            if isinstance(v, dict):
                cleaned[k] = self._clean_payload(v)
                continue
            cleaned[k] = v
        return cleaned

    def _clean_vector(self, v: np.ndarray) -> List[float]:
        """Convert a vector to a JSON-safe list of floats."""
        # Qdrant rejects NaN/Inf; make the payload JSON-safe
        v = v.astype("float32")
        v = np.where(np.isfinite(v), v, 0.0)
        return v.tolist()

    def _point_id(self, meta: Dict, fallback: int):
        """Derive a Qdrant point id from metadata."""
        # Qdrant point id must be unsigned int or UUID
        raw = meta.get("id") or meta.get("hash")
        if raw is None:
            return fallback
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            try:
                return str(uuid.UUID(raw))
            except Exception:
                # Hash-like strings are not valid UUIDs; derive a stable UUID
                return str(uuid.uuid5(uuid.NAMESPACE_URL, raw))
        return fallback

    def _ensure_collection(self):
        """Create the Qdrant collection if it does not exist."""
        try:
            self.client.get_collection(self.collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=self.dim, distance=qm.Distance.COSINE)
            )

    def upsert(self, vectors: List[np.ndarray], metadatas: List[Dict]):
        """Insert vectors and metadata into Qdrant."""
        points = []
        for i, (v, m) in enumerate(zip(vectors, metadatas)):
            payload = self._clean_payload(m)
            vector = self._clean_vector(v)
            pid = self._point_id(m, i)
            points.append(qm.PointStruct(id=pid, vector=vector, payload=payload))
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query: np.ndarray, k: int = 4) -> List[Tuple[float, Dict]]:
        """Search Qdrant for nearest vectors by cosine similarity."""
        res = self.client.search(
            collection_name=self.collection,
            query_vector=query.tolist(),
            limit=k,
            with_payload=True
        )
        out = []
        for r in res:
            out.append((float(r.score), dict(r.payload)))
        return out

# ---- LLM provider ----
class StubLLM:
    def generate(self, query: str, contexts: List[Dict], history: Optional[List[Dict]] = None) -> str:
        """Return a deterministic stubbed answer from retrieved contexts."""
        lines = [f"Answer (stub):"]
        texts = []
        for c in contexts:
            text = c.get("text", "")
            text = "\n".join([line.lstrip("#").strip() for line in text.splitlines()])
            texts.append(text)
        joined = "\n".join(texts)
        lines.append(joined[:600] + ("..." if len(joined) > 600 else ""))
        return "\n".join(lines)

    def generate_stream(self, query: str, contexts: List[Dict], history: Optional[List[Dict]] = None):
        """Yield a single stubbed answer chunk."""
        yield self.generate(query, contexts, history=history)

class OpenRouterLLM:
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        """Initialize the OpenRouter client and model."""
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = model

    def _guardrail(self, query: str, history: Optional[List[Dict]] = None) -> bool:
        """Return True only if the query is appropriate and policy-related."""
        guardrail_prompt = (
            "You are a policy-query filter for a company policy assistant. "
            "Return JSON only with a single key: allow (boolean). "
            "Allow if the query is about company policies, product rules, returns, shipping, warranties, "
            "or internal support procedures. Also allow short conversational follow-ups that depend on "
            "prior context (e.g., \"what I said just now\", \"again?\") so the conversation can flow. "
            "Allow basic assistant capability questions like \"tell me what you can do\". "
            "Block only clearly unsafe, abusive, sexual, violent, or entirely unrelated requests."
        )
        messages = [{"role": "system", "content": guardrail_prompt}]
        if history:
            for m in history[-6:]:
                role = m.get("role")
                content = m.get("content")
                if role in {"user", "assistant", "system"} and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": query})
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            return bool(data.get("allow", False))
        except Exception:
            logger.exception("Guardrail check failed, defaulting to block")
            return False

    def generate(self, query: str, contexts: List[Dict], history: Optional[List[Dict]] = None) -> str:
        """Generate a grounded answer, with a guardrail check first."""
        if not self._guardrail(query, history=history):
            logger.info("Guardrail blocked request")
            return "Sorry, I can only help with appropriate questions related to company policies and support procedures."
        system_prompt = (
            "You are a helpful company policy assistant. Cite sources by title and section when relevant. "
            "Write a concise, accurate answer grounded in the sources. If unsure, say so."
        )
        sources = "Sources:\n"
        for c in contexts:
            sources += f"- {c.get('title')} | {c.get('section')}\n{c.get('text')[:600]}\n---\n"

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for m in history:
                role = m.get("role")
                content = m.get("content")
                if role in {"user", "assistant", "system"} and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": f"Question: {query}\n{sources}"})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1
        )
        return resp.choices[0].message.content

    def generate_stream(self, query: str, contexts: List[Dict], history: Optional[List[Dict]] = None):
        """Stream a grounded answer, with a guardrail check first."""
        if not self._guardrail(query, history=history):
            logger.info("Guardrail blocked request (stream)")
            yield "Sorry, I can only help with appropriate questions related to company policies and support procedures."
            return
        system_prompt = (
            "You are a helpful company policy assistant. Cite sources by title and section when relevant. "
            "Write a concise, accurate answer grounded in the sources. If unsure, say so."
        )
        sources = "Sources:\n"
        for c in contexts:
            sources += f"- {c.get('title')} | {c.get('section')}\n{c.get('text')[:600]}\n---\n"

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for m in history:
                role = m.get("role")
                content = m.get("content")
                if role in {"user", "assistant", "system"} and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": f"Question: {query}\n{sources}"})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            stream=True,
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0], "delta", None)
            if not delta:
                continue
            content = None
            if isinstance(delta, dict):
                content = delta.get("content")
            else:
                content = getattr(delta, "content", None)
            if content:
                yield content

# ---- RAG Orchestrator & Metrics ----
class Metrics:
    def __init__(self):
        """Initialize latency tracking lists."""
        self.t_retrieval = []
        self.t_generation = []

    def add_retrieval(self, ms: float):
        """Record a retrieval latency in milliseconds."""
        self.t_retrieval.append(ms)

    def add_generation(self, ms: float):
        """Record a generation latency in milliseconds."""
        self.t_generation.append(ms)

    def summary(self) -> Dict:
        """Compute average retrieval and generation latency."""
        avg_r = sum(self.t_retrieval)/len(self.t_retrieval) if self.t_retrieval else 0.0
        avg_g = sum(self.t_generation)/len(self.t_generation) if self.t_generation else 0.0
        return {
            "avg_retrieval_latency_ms": round(avg_r, 2),
            "avg_generation_latency_ms": round(avg_g, 2),
        }

class RAGEngine:
    def __init__(self):
        """Initialize embedder, vector store, LLM, and metrics."""
        self.embedder = LocalEmbedder(dim=384)
        # Vector store selection
        if settings.vector_store == "qdrant":
            try:
                self.store = QdrantStore(collection=settings.collection_name, dim=384)
                logger.info("Vector store: qdrant collection=%s", settings.collection_name)
            except Exception:
                self.store = InMemoryStore(dim=384)
                logger.warning("Qdrant unavailable, falling back to in-memory store")
        else:
            self.store = InMemoryStore(dim=384)
            logger.info("Vector store: in-memory")

        # LLM selection
        if settings.llm_provider == "openrouter" and settings.openrouter_api_key:
            try:
                self.llm = OpenRouterLLM(
                    api_key=settings.openrouter_api_key,
                    model=settings.llm_model,
                )
                self.llm_name = f"openrouter:{settings.llm_model}"
                logger.info("LLM provider: %s", self.llm_name)
            except Exception:
                self.llm = StubLLM()
                self.llm_name = "stub"
                logger.warning("OpenRouter init failed, using stub LLM")
        else:
            self.llm = StubLLM()
            self.llm_name = "stub"
            logger.info("LLM provider: stub")

        self.metrics = Metrics()
        self._doc_titles = set()
        self._chunk_count = 0

    def ingest_chunks(self, chunks: List[Dict]) -> Tuple[int, int]:
        """Embed and store chunks; return counts of new docs and chunks."""
        logger.info("Ingesting chunks count=%s", len(chunks))
        vectors = []
        metas = []
        doc_titles_before = set(self._doc_titles)

        for ch in chunks:
            text = ch["text"]
            h = doc_hash(text)
            meta = {
                "id": h,
                "hash": h,
                "title": ch["title"],
                "section": ch.get("section"),
                "text": text,
            }
            v = self.embedder.embed(text)
            vectors.append(v)
            metas.append(meta)
            self._doc_titles.add(ch["title"])
            self._chunk_count += 1

        self.store.upsert(vectors, metas)
        logger.info("Ingested new_docs=%s new_chunks=%s", len(self._doc_titles) - len(doc_titles_before), len(metas))
        return (len(self._doc_titles) - len(doc_titles_before), len(metas))

    def retrieve(self, query: str, k: int = 4) -> List[Dict]:
        """Retrieve top-k matching chunks for a query."""
        t0 = time.time()
        qv = self.embedder.embed(query)
        results = self.store.search(qv, k=k)
        self.metrics.add_retrieval((time.time()-t0)*1000.0)
        logger.debug("Retrieved k=%s results=%s", k, len(results))
        out = []
        for score, meta in results:
            m = dict(meta)
            m["score"] = float(score)
            out.append(m)
        return out

    def generate(self, query: str, contexts: List[Dict], history: Optional[List[Dict]] = None) -> str:
        """Generate an answer from a query and retrieved contexts."""
        t0 = time.time()
        answer = self.llm.generate(query, contexts, history=history)
        self.metrics.add_generation((time.time()-t0)*1000.0)
        return answer

    def generate_stream(self, query: str, contexts: List[Dict], history: Optional[List[Dict]] = None):
        """Stream an answer from a query and retrieved contexts."""
        t0 = time.time()
        for chunk in self.llm.generate_stream(query, contexts, history=history):
            yield chunk
        self.metrics.add_generation((time.time()-t0)*1000.0)

    def stats(self) -> Dict:
        """Return aggregate stats about the index and latencies."""
        m = self.metrics.summary()
        return {
            "total_docs": len(self._doc_titles),
            "total_chunks": self._chunk_count,
            "embedding_model": settings.embedding_model,
            "llm_model": self.llm_name,
            **m
        }

# ---- Helpers ----
def build_chunks_from_docs(docs: List[Dict], chunk_size: int, overlap: int) -> List[Dict]:
    """Build chunk dicts from document sections."""
    out = []
    for d in docs:
        for ch in chunk_text(d["text"], chunk_size, overlap):
            out.append({"title": d["title"], "section": d["section"], "text": ch})
    return out
