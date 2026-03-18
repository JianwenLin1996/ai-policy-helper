'use client';
import React from 'react';
import { apiAskStream, apiCreateSession, apiDeleteSession, apiGetMessages, apiListSessions } from '@/lib/api';

type Message = { role: 'user' | 'assistant', content: string, citations?: { title: string, section?: string }[], chunks?: { title: string, section?: string, text: string }[] };
type SessionInfo = { id: number, created_at: string };

export default function Chat() {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [q, setQ] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [sessionId, setSessionId] = React.useState<number | null>(null);
  const [creatingSession, setCreatingSession] = React.useState(false);
  const [sessions, setSessions] = React.useState<SessionInfo[]>([]);
  const [loadingSessions, setLoadingSessions] = React.useState(false);
  const [loadingMessages, setLoadingMessages] = React.useState(false);
  const [sessionsCollapsed, setSessionsCollapsed] = React.useState(false);
  const endRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: 'Hi! Ask me anything about company policies or product rules. I will cite the source sections when possible.'
      }]);
    }
  }, [messages.length]);

  const loadSessions = React.useCallback(async () => {
    setLoadingSessions(true);
    try {
      const res = await apiListSessions();
      setSessions(res);
      return res as SessionInfo[];
    } catch {
      return [];
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  const loadMessages = React.useCallback(async (id: number) => {
    setLoadingMessages(true);
    try {
      const res = await apiGetMessages(id, 20);
      const msgs: Message[] = res.map((m: any) => ({
        role: m.role,
        content: m.content,
      }));
      setMessages(msgs);
    } catch {
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  React.useEffect(() => {
    let active = true;
    const init = async () => {
      const list = await loadSessions();
      if (!active) return;
      if (list.length === 0) {
        setCreatingSession(true);
        try {
          const res = await apiCreateSession();
          if (!active) return;
          setSessionId(res.id);
          await loadSessions();
          await loadMessages(res.id);
        } finally {
          if (active) setCreatingSession(false);
        }
        return;
      }
      setSessionId(list[0].id);
      await loadMessages(list[0].id);
    };
    init();
    return () => { active = false; };
  }, [loadMessages, loadSessions]);

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const newChat = async () => {
    if (creatingSession || loading) return;
    setMessages([]);
    setQ('');
    setCreatingSession(true);
    try {
      const res = await apiCreateSession();
      setSessionId(res.id);
      await loadSessions();
      await loadMessages(res.id);
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: 'Could not create a new session. Please try again.' }]);
    } finally {
      setCreatingSession(false);
    }
  };

  const openSession = async (id: number) => {
    if (loading || creatingSession || loadingMessages) return;
    setSessionId(id);
    await loadMessages(id);
  };

  const removeSession = async (id: number) => {
    if (loading || creatingSession || loadingMessages) return;
    const ok = window.confirm(`Delete session ${id}? This cannot be undone.`);
    if (!ok) return;
    try {
      await apiDeleteSession(id);
      const list = await loadSessions();
      if (id === sessionId) {
        if (list.length > 0) {
          setSessionId(list[0].id);
          await loadMessages(list[0].id);
        } else {
          await newChat();
        }
      }
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: 'Could not delete session. Please try again.' }]);
    }
  };

  const send = async () => {
    if (!q.trim() || loading || creatingSession || loadingMessages) return;
    const activeSessionId = sessionId;
    if (activeSessionId === null) return;
    const my = { role: 'user' as const, content: q };
    setMessages(m => [...m, my]);
    setQ('');
    setLoading(true);
    try {
      setMessages(m => [...m, { role: 'assistant', content: '' }]);
      const stream = await apiAskStream(q, activeSessionId as number);
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          const line = part.split('\n').find(l => l.startsWith('data: '));
          if (!line) continue;
          const payload = JSON.parse(line.replace('data: ', ''));
          if (payload.type === 'chunk') {
            setMessages(m => {
              const next = [...m];
              const lastIdx = next.length - 1;
              if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
                next[lastIdx] = { ...next[lastIdx], content: next[lastIdx].content + payload.content };
              }
              return next;
            });
          } else if (payload.type === 'final') {
            setMessages(m => {
              const next = [...m];
              const lastIdx = next.length - 1;
              if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
                next[lastIdx] = {
                  ...next[lastIdx],
                  content: payload.answer,
                  citations: payload.citations,
                  chunks: payload.chunks,
                };
              }
              return next;
            });
          } else if (payload.type === 'error') {
            throw new Error(payload.message || 'Stream error');
          }
        }
      }
    } catch (e: any) {
      setMessages(m => [...m, { role: 'assistant', content: 'Connection failed. Please ensure indexing completed and try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`chat-layout${sessionsCollapsed ? ' collapsed' : ''}`}>
      {sessionsCollapsed && (
        <button
          className="sessions-toggle"
          onClick={() => setSessionsCollapsed(false)}
          aria-label="Show sessions"
        >
          Show sessions
        </button>
      )}
      <div className="card session-card">
        <div className="session-header">
          <div className="chat-title">Sessions</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setSessionsCollapsed(c => !c)}
              className="btn secondary"
              aria-label={sessionsCollapsed ? 'Expand sessions' : 'Collapse sessions'}
            >
              {sessionsCollapsed ? 'Show' : 'Hide'}
            </button>
            <button onClick={newChat} disabled={loading || creatingSession || loadingMessages} className="btn secondary" aria-label="Start new chat">
              New chat
            </button>
          </div>
        </div>
        <div className="session-list">
          {loadingSessions && <div className="subtle">Loading sessions…</div>}
          {!loadingSessions && sessions.length === 0 && (
            <div className="subtle">No sessions yet.</div>
          )}
          {!loadingSessions && sessions.map((s) => (
            <button
              key={s.id}
              className={`session-item${sessionId === s.id ? ' active' : ''}`}
              onClick={() => openSession(s.id)}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <div className="session-id">Session {s.id}</div>
                <button
                  className="session-delete"
                  onClick={(e) => { e.stopPropagation(); removeSession(s.id); }}
                  aria-label={`Delete session ${s.id}`}
                >
                  Delete
                </button>
              </div>
              <div className="session-time">{new Date(s.created_at).toLocaleString()}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="card chat-shell">
      <div className="chat-header">
        <div>
          <div className="chat-title">Policy Assistant</div>
          <div className="subtle">Ask questions, get grounded answers based on indexed docs.</div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div className="badge">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 4, display: 'inline-block', verticalAlign: 'text-bottom' }}>
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
            </svg>
            Citations on
          </div>
        </div>
      </div>

      <div className="messages">
        {loadingMessages && (
          <div className="subtle" style={{ padding: '8px 0 12px 0' }}>Loading messages…</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <div className="avatar">
              {m.role === 'user' ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8V4H8" /><rect width="16" height="12" x="4" y="8" rx="2" /><path d="M2 14h2" /><path d="M20 14h2" /><path d="M15 13v2" /><path d="M9 13v2" /></svg>
              )}
            </div>
            <div style={{ maxWidth: 'calc(100% - 48px)' }}>
              <div className="meta">{m.role === 'user' ? 'You' : 'AI Assistant'}</div>
              <div className="bubble">{m.content}</div>

              {m.citations && m.citations.length > 0 && (
                <div className="sources">
                  {m.citations.map((c, idx) => (
                    <span key={idx} className="badge badge-citation" title={c.section || ''}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h6v6" /><path d="M10 14 21 3" /><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /></svg>
                      {c.title}
                    </span>
                  ))}
                </div>
              )}

              {m.chunks && m.chunks.length > 0 && (
                <details className="chunks">
                  <summary>View supporting extracted text</summary>
                  <div className="chunk-list">
                    {m.chunks.map((c, idx) => (
                      <div key={idx} className="chunk-card">
                        <div style={{ fontWeight: 600, color: '#4F46E5', marginBottom: 4 }}>{c.title}{c.section ? ' — ' + c.section : ''}</div>
                        <div style={{ whiteSpace: 'pre-wrap', color: '#64748B' }}>{c.text}</div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="avatar">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8V4H8" /><rect width="16" height="12" x="4" y="8" rx="2" /><path d="M2 14h2" /><path d="M20 14h2" /><path d="M15 13v2" /><path d="M9 13v2" /></svg>
            </div>
            <div>
              <div className="meta">AI Assistant</div>
              <div className="bubble" style={{ padding: '16px 20px' }}>
                <span className="typing">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </span>
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="input-wrap">
        <textarea
          className="textarea"
          placeholder="Ask about refunds, shipping, warranties, or product eligibility…"
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
        />
        <button onClick={send} disabled={loading || creatingSession || loadingMessages || !q.trim()} className="btn" aria-label="Send message">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
        </button>
      </div>
      </div>
    </div>
  );
}
