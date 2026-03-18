import Chat from '@/components/Chat';
import AdminPanel from '@/components/AdminPanel';
import Header from '@/components/Header';
import QuickTest from '@/components/QuickTest';

export default function Page() {
  return (
    <div className="page">
      <div className="shell">
        <Header />
        <div className="stack">
          <AdminPanel />
          <Chat />
          <QuickTest />
        </div>
      </div>
    </div>
  );
}
