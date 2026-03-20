export default function Header() {
  return (
    <div className="topbar">
      <div className="brand">
        <div className="brand-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        </div>
        <div className="brand-text">
          <h1>AI Policy Helper</h1>
          <p>Local-first RAG assistant for support teams</p>
        </div>
      </div>
      <div className="status-card">
        <div className="subtle" style={{ marginBottom: 4 }}>System Status</div>
        <div className="status-indicator">
          <span className="pulse"></span>
          Ready to assist
        </div>
      </div>
    </div>
  );
}
