from fastapi import FastAPI, HTTPException
from typing import List
from fastapi.responses import StreamingResponse
import json
from fastapi.middleware.cors import CORSMiddleware
from .models import IngestResponse, AskRequest, AskResponse, MetricsResponse, Citation, Chunk, SessionResponse, MessageResponse
from .settings import settings
from .ingest import load_documents
from .rag import RAGEngine, build_chunks_from_docs
from .db import SessionLocal, init_db, Message, Retrieval, ChatSession

app = FastAPI(title="AI Policy & Product Helper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = RAGEngine()

@app.on_event("startup")
def _init_db():
    init_db()

@app.get("/api/health")
def health():
    """Simple health check endpoint."""
    return {"status": "ok"}

@app.get("/api/metrics", response_model=MetricsResponse)
def metrics():
    """Return aggregated retrieval and generation metrics."""
    s = engine.stats()
    return MetricsResponse(**s)

@app.post("/api/ingest", response_model=IngestResponse)
def ingest():
    """Ingest documents from the configured data directory into the vector store."""
    docs = load_documents(settings.data_dir)
    chunks = build_chunks_from_docs(docs, settings.chunk_size, settings.chunk_overlap)
    new_docs, new_chunks = engine.ingest_chunks(chunks)
    return IngestResponse(indexed_docs=new_docs, indexed_chunks=new_chunks)

@app.post("/api/sessions", response_model=SessionResponse)
def create_session():
    """Create a new chat session and return its id."""
    with SessionLocal() as db:
        session = ChatSession()
        db.add(session)
        db.commit()
        db.refresh(session)
        return SessionResponse(id=session.id, created_at=session.created_at)

@app.get("/api/sessions", response_model=List[SessionResponse])
def list_sessions():
    """List all chat sessions (newest first)."""
    with SessionLocal() as db:
        sessions = (
            db.query(ChatSession)
            .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
            .all()
        )
        return [SessionResponse(id=s.id, created_at=s.created_at) for s in sessions]

@app.get("/api/sessions/{session_id}/messages", response_model=List[MessageResponse])
def list_messages(session_id: int, limit: int = 20):
    """Return the latest messages for a session in chronological order."""
    with SessionLocal() as db:
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        msgs = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
            .all()
        )
        msgs = list(reversed(msgs))
        return [
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in msgs
        ]

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: int):
    """Delete a session and its messages."""
    with SessionLocal() as db:
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        db.delete(session)
        db.commit()
    return {"status": "ok"}

@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    """Answer a user query using retrieval-augmented generation."""
    ctx = engine.retrieve(req.query, k=req.k or 4)
    history = []
    with SessionLocal() as db:
        chat_session = db.get(ChatSession, req.session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
        recent = (
            db.query(Message)
            .filter(Message.session_id == chat_session.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(10)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in reversed(recent)]
    answer = engine.generate(req.query, ctx, history=history)
    citations = [Citation(title=c.get("title"), section=c.get("section")) for c in ctx]
    chunks = [Chunk(title=c.get("title"), section=c.get("section"), text=c.get("text")) for c in ctx]
    stats = engine.stats()
    # Persist chat to SQLite
    with SessionLocal() as db:
        try:
            chat_session = db.get(ChatSession, req.session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")
            user_msg = Message(session_id=chat_session.id, role="user", content=req.query)
            db.add(user_msg)
            db.flush()
            assistant_msg = Message(session_id=chat_session.id, role="assistant", content=answer)
            db.add(assistant_msg)
            db.flush()
            retrievals = []
            for c in ctx:
                doc_id = c.get("id") or c.get("hash")
                retrieval = Retrieval(
                    message_id=assistant_msg.id,
                    document_id=str(doc_id) if doc_id is not None else None,
                    chunk_text=c.get("text") or "",
                    score=c.get("score"),
                )
                retrievals.append(retrieval)
            db.add_all(retrievals)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    return AskResponse(
        query=req.query,
        answer=answer,
        citations=citations,
        chunks=chunks,
        metrics={
            "retrieval_ms": stats["avg_retrieval_latency_ms"],
            "generation_ms": stats["avg_generation_latency_ms"],
        }
    )

@app.post("/api/ask/stream")
def ask_stream(req: AskRequest):
    """Stream an answer using retrieval-augmented generation."""
    ctx = engine.retrieve(req.query, k=req.k or 4)
    citations = [Citation(title=c.get("title"), section=c.get("section")) for c in ctx]
    chunks = [Chunk(title=c.get("title"), section=c.get("section"), text=c.get("text")) for c in ctx]
    stats = engine.stats()

    history = []
    with SessionLocal() as db:
        chat_session = db.get(ChatSession, req.session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
        recent = (
            db.query(Message)
            .filter(Message.session_id == chat_session.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(10)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in reversed(recent)]

    def event_stream():
        answer_parts = []
        try:
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            for part in engine.generate_stream(req.query, ctx, history=history):
                answer_parts.append(part)
                yield f"data: {json.dumps({'type': 'chunk', 'content': part})}\n\n"
            answer = "".join(answer_parts)
            # Persist chat to SQLite
            with SessionLocal() as db:
                chat_session = db.get(ChatSession, req.session_id)
                if not chat_session:
                    raise HTTPException(status_code=404, detail="Session not found")
                user_msg = Message(session_id=chat_session.id, role="user", content=req.query)
                db.add(user_msg)
                db.flush()
                assistant_msg = Message(session_id=chat_session.id, role="assistant", content=answer)
                db.add(assistant_msg)
                db.flush()
                retrievals = []
                for c in ctx:
                    doc_id = c.get("id") or c.get("hash")
                    retrieval = Retrieval(
                        message_id=assistant_msg.id,
                        document_id=str(doc_id) if doc_id is not None else None,
                        chunk_text=c.get("text") or "",
                        score=c.get("score"),
                    )
                    retrievals.append(retrieval)
                db.add_all(retrievals)
                db.commit()
            payload = {
                "type": "final",
                "answer": answer,
                "citations": [c.model_dump() for c in citations],
                "chunks": [c.model_dump() for c in chunks],
                "metrics": {
                    "retrieval_ms": stats["avg_retrieval_latency_ms"],
                    "generation_ms": stats["avg_generation_latency_ms"],
                },
            }
            yield f"data: {json.dumps(payload)}\n\n"
        except Exception as e:
            err = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(err)}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream; charset=utf-8", headers=headers)
