import './global.css';
import { RootProvider } from 'fumadocs-ui/provider';
import { Inter } from 'next/font/google';
import type { ReactNode } from 'react';

const inter = Inter({
  subsets: ['latin'],
});

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.className} suppressHydrationWarning>
      <head>
        <link rel="icon" href="/docs/favicon.ico" sizes="any" />
      </head>
      <body className="flex min-h-screen flex-col">
        <RootProvider search={{ options: { api: '/docs/api/search' } }}>
          {children}
        </RootProvider>
      </body>
    </html>
  );
}
