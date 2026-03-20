import './globals.css';
import { Poppins, Open_Sans } from 'next/font/google';

const sans = Open_Sans({ subsets: ['latin'], variable: '--font-sans' });
const serif = Poppins({ subsets: ['latin'], weight: ['400', '500', '600', '700'], variable: '--font-serif' });

export const metadata = { title: 'AI Policy Helper', description: 'Local-first RAG assistant for support teams. Grounded answers with citations.' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${serif.variable}`}>
        {children}
      </body>
    </html>
  );
}
