"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeRepo } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

const DEMO_REPOS = [
  "https://github.com/pallets/flask",
  "https://github.com/tiangolo/fastapi",
  "https://github.com/vercel/next.js",
];

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    try {
      const { analysis_id } = await analyzeRepo(url.trim());
      router.push(`/analysis/${analysis_id}`);
    } catch (err: any) {
      setError(err.message || "Bir hata oluştu.");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-slate-100 to-slate-200 dark:from-slate-900 dark:to-slate-800 px-4 relative">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-2xl text-center">
        <h1 className="text-5xl font-bold text-slate-900 dark:text-white mb-3">RepoArkeolog</h1>
        <p className="text-slate-600 dark:text-slate-300 text-lg mb-10">
          Bir GitHub reposunu çoklu AI ajanıyla <strong className="text-blue-600 dark:text-blue-400">5 dakikada</strong> anla.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/kullanici/repo"
            className="flex-1 px-4 py-3 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-base outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 dark:disabled:bg-blue-800 text-white font-semibold rounded-xl transition-colors"
          >
            {loading ? "Analiz başlatılıyor..." : "Analiz Et"}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/50 border border-red-300 dark:border-red-500 text-red-700 dark:text-red-300 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="mt-8">
          <p className="text-slate-500 dark:text-slate-400 text-sm mb-3">Demo için hazır repolar:</p>
          <div className="flex flex-wrap justify-center gap-2">
            {DEMO_REPOS.map((repo) => (
              <button
                key={repo}
                onClick={() => setUrl(repo)}
                className="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-300 text-sm rounded-lg transition-colors"
              >
                {repo.replace("https://github.com/", "")}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-12 grid grid-cols-3 gap-6 text-center">
          {[
            { title: "Mimari Harita", desc: "Tıklanabilir bağımlılık grafiği" },
            { title: "Git Tarihi", desc: "Projenin evrim hikayesi" },
            { title: "Sağlık Skoru", desc: "Teknik borç ve güvenlik analizi" },
          ].map((f) => (
            <div key={f.title} className="bg-white dark:bg-slate-700/50 border border-slate-200 dark:border-transparent rounded-xl p-4">
              <div className="text-blue-600 dark:text-blue-400 font-semibold mb-1">{f.title}</div>
              <div className="text-slate-600 dark:text-slate-400 text-sm">{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
