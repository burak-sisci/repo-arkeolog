import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RepoArkeolog — GitHub Repo Analiz Aracı",
  description: "Bir GitHub reposunu çoklu AI ajanıyla 5 dakikada anlatan araç",
};

// FOUC engelleme: tarayıcıdaki tema React mount olmadan uygulanır.
const themeInit = `
(function(){try{
  var s=localStorage.getItem('theme');
  var p=window.matchMedia('(prefers-color-scheme: dark)').matches;
  if(s? s==='dark' : p){document.documentElement.classList.add('dark');}
}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
