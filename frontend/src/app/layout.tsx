import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AppShell } from '@/components/layout/AppShell';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'Agentic Ads | AI-Powered Advertising Platform',
  description:
    'Autonomous AI multi-agent platform for generating cross-platform ad copy, promotional posters, and video commercials.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 antialiased`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
