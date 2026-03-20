export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function apiAsk(query: string, sessionId: number, k: number = 4) {
  const r = await fetch(`${API_BASE}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k, session_id: sessionId })
  });
  if (!r.ok) throw new Error('Ask failed');
  return r.json();
}

export async function apiAskStream(query: string, sessionId: number, k: number = 4) {
  const r = await fetch(`${API_BASE}/api/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k, session_id: sessionId })
  });
  if (!r.ok || !r.body) throw new Error('Ask stream failed');
  return r.body;
}

export async function apiCreateSession() {
  const r = await fetch(`${API_BASE}/api/sessions`, { method: 'POST' });
  if (!r.ok) throw new Error('Create session failed');
  return r.json();
}

export async function apiListSessions() {
  const r = await fetch(`${API_BASE}/api/sessions`);
  if (!r.ok) throw new Error('List sessions failed');
  return r.json();
}

export async function apiGetMessages(sessionId: number, limit: number = 20) {
  const r = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages?limit=${limit}`);
  if (!r.ok) throw new Error('Get messages failed');
  return r.json();
}

export async function apiDeleteSession(sessionId: number) {
  const r = await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: 'DELETE' });
  if (!r.ok) throw new Error('Delete session failed');
  return r.json();
}

export async function apiIngest() {
  const r = await fetch(`${API_BASE}/api/ingest`, { method: 'POST' });
  if (!r.ok) throw new Error('Ingest failed');
  return r.json();
}

export async function apiMetrics() {
  const r = await fetch(`${API_BASE}/api/metrics`);
  if (!r.ok) throw new Error('Metrics failed');
  return r.json();
}
