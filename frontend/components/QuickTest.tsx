const QUICK_TESTS = [
  'Can a customer return a damaged blender after 20 days?',
  'What’s the shipping SLA to East Malaysia for bulky items?',
  'Is a used laptop eligible for a partial refund?'
];

export default function QuickTest() {
  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#6366F1' }}>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
        <h3 style={{ margin: 0 }}>Quick test</h3>
      </div>
      <div className="subtle" style={{ marginBottom: 16 }}>Try these prompts after indexing documents.</div>
      <div style={{ display: 'grid', gap: 10 }}>
        {QUICK_TESTS.map((prompt) => (
          <div key={prompt} className="quick-test-card">
            <svg className="quick-test-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
            {prompt}
          </div>
        ))}
      </div>
    </div>
  );
}
