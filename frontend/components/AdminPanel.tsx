'use client';
import React from 'react';
import { apiIngest, apiMetrics } from '@/lib/api';

export default function AdminPanel() {
  const [metrics, setMetrics] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);

  const refresh = async () => {
    try {
      const m = await apiMetrics();
      setMetrics(m);
    } catch {
      // Backend might be unavailable
    }
  };

  const ingest = async () => {
    setBusy(true);
    try {
      await apiIngest();
      await refresh();
    } catch (e) {
      console.error(e);
      alert('Ingest API not available. Make sure the backend is running.');
    } finally {
      setBusy(false);
    }
  };

  React.useEffect(() => { refresh(); }, []);

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#6366F1' }}>
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
        <h2 style={{ margin: 0 }}>Admin Data</h2>
      </div>

      <div className="subtle" style={{ marginBottom: 16 }}>Manage the knowledge base and monitor latency metrics.</div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        <button onClick={ingest} disabled={busy} className="btn secondary" style={{ height: 44 }}>
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
          {busy ? 'Indexing...' : 'Ingest sample docs'}
        </button>
        <button onClick={refresh} className="btn secondary" style={{ height: 44 }}>
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 2v6h6" /><path d="M21 12A9 9 0 0 0 6 5.3L3 8" /><path d="M21 22v-6h-6" /><path d="M3 12a9 9 0 0 0 15 6.7l3-2.7" /></svg>
          Refresh
        </button>
      </div>

      {metrics ? (
        <div className="code">
          <pre style={{ margin: 0 }}>{JSON.stringify(metrics, null, 2)}</pre>
        </div>
      ) : (
        <div className="code" style={{ color: '#94A3B8' }}>
          <pre style={{ margin: 0 }}>No metrics available.
            Ensure API backend is running.</pre>
        </div>
      )}
    </div>
  );
}
