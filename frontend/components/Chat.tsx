'use client';
import React from 'react';
import { apiAsk } from '@/lib/api';

type Message = { role: 'user' | 'assistant', content: string, citations?: { title: string, section?: string }[], chunks?: { title: string, section?: string, text: string }[] };

export default function Chat() {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [q, setQ] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const endRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: 'Hi! Ask me anything about company policies or product rules. I will cite the source sections when possible.'
      }]);
    }
  }, [messages.length]);

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async () => {
    if (!q.trim() || loading) return;
    const my = { role: 'user' as const, content: q };
    setMessages(m => [...m, my]);
    setLoading(true);
    try {
      const res = await apiAsk(q);
      const ai: Message = { role: 'assistant', content: res.answer, citations: res.citations, chunks: res.chunks };
      setMessages(m => [...m, ai]);
    } catch (e: any) {
      setMessages(m => [...m, { role: 'assistant', content: 'Connection failed. Please ensure indexing completed and try again.' }]);
    } finally {
      setLoading(false);
      setQ('');
    }
  };

  return (
    <div className="card chat-shell">
      <div className="chat-header">
        <div>
          <div className="chat-title">Policy Assistant</div>
          <div className="subtle">Ask questions, get grounded answers based on indexed docs.</div>
        </div>
        <div className="badge">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 4, display: 'inline-block', verticalAlign: 'text-bottom' }}>
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
          </svg>
          Citations on
        </div>
      </div>

      <div className="messages">
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
        <button onClick={send} disabled={loading || !q.trim()} className="btn" aria-label="Send message">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
        </button>
      </div>
    </div>
  );
}
