import Chat from '@/components/Chat';
import AdminPanel from '@/components/AdminPanel';
import Header from '@/components/Header';
import QuickTest from '@/components/QuickTest';

export default function Page() {
  return (
    <div className="page">
      <div className="shell">
        <Header />

        <div className="layout">
          <div>
            <Chat />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <AdminPanel />
            <QuickTest />
          </div>
        </div>
      </div>
    </div>
  );
}
