def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_sessions_crud(client):
    r = client.post("/api/sessions")
    assert r.status_code == 200
    session = r.json()
    assert "id" in session

    r2 = client.get("/api/sessions")
    assert r2.status_code == 200
    assert any(s["id"] == session["id"] for s in r2.json())

    r3 = client.get(f"/api/sessions/{session['id']}/messages")
    assert r3.status_code == 200
    assert r3.json() == []

    r4 = client.delete(f"/api/sessions/{session['id']}")
    assert r4.status_code == 200

    r5 = client.get(f"/api/sessions/{session['id']}/messages")
    assert r5.status_code == 404

def test_ingest_and_ask(client):
    r = client.post("/api/ingest")
    assert r.status_code == 200
    session = client.post("/api/sessions").json()
    # Ask a deterministic question
    r2 = client.post("/api/ask", json={"query":"What is the refund window for small appliances?", "session_id": session["id"]})
    assert r2.status_code == 200
    data = r2.json()
    assert "citations" in data and len(data["citations"]) > 0
    assert "answer" in data and isinstance(data["answer"], str)

def test_ask_stream(client):
    session = client.post("/api/sessions").json()
    with client.stream("POST", "/api/ask/stream", json={"query": "Tell me about return policy", "session_id": session["id"]}) as r:
        assert r.status_code == 200
        final_seen = False
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("data: "):
                payload = line.replace("data: ", "")
                if "\"type\": \"final\"" in payload:
                    final_seen = True
                    break
        assert final_seen
