"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getAnalysis } from "@/lib/api";
import { ProgressBar } from "@/components/ProgressBar";
import { SummaryTab } from "@/components/tabs/SummaryTab";
import { MimapTab } from "@/components/tabs/MimapTab";
import { TimelineTab } from "@/components/tabs/TimelineTab";
import { ChatTab } from "@/components/tabs/ChatTab";
import { HealthBadge } from "@/components/HealthBadge";
import { ThemeToggle } from "@/components/ThemeToggle";

type TabId = "summary" | "mimap" | "timeline" | "chat";

const TABS: { id: TabId; label: string }[] = [
  { id: "summary", label: "Ozet" },
  { id: "mimap", label: "Mimari Harita" },
  { id: "timeline", label: "Timeline" },
  { id: "chat", label: "Repoyla Konuş" },
];

export default function AnalysisPage() {
  const params = useParams();
  const analysisId = params.id as string;
  const [analysis, setAnalysis] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<TabId>("summary");
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!analysisId) return;
    let interval: NodeJS.Timeout;

    async function fetchAnalysis() {
      try {
        const data = await getAnalysis(analysisId);
        setAnalysis(data);
        if (data.status === "done" || data.status === "failed") {
          setDone(true);
          clearInterval(interval);
        }
      } catch {}
    }

    fetchAnalysis();
    interval = setInterval(fetchAnalysis, 3000);
    return () => clearInterval(interval);
  }, [analysisId]);

  if (!analysis) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="text-slate-600 dark:text-slate-300 text-lg">Yükleniyor...</div>
      </div>
    );
  }

  const healthScore = analysis.results?.health_report?.health_score;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <a href="/" className="text-sm text-blue-600 dark:text-blue-400 hover:underline mr-3">← Ana Sayfa</a>
            <span className="font-semibold text-slate-800 dark:text-slate-100 truncate max-w-md">
              {analysis.repo_url}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {healthScore != null && <HealthBadge score={healthScore} />}
            <UsageStatusDot />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Progress bar (shown while running) */}
      {!done && (
        <div className="max-w-7xl mx-auto px-6 mt-4">
          <ProgressBar analysisId={analysisId} />
        </div>
      )}

      {analysis.status === "failed" && (
        <div className="max-w-7xl mx-auto px-6 mt-4">
          <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 p-4 rounded-xl">
            Analiz başarısız: {analysis.error}
          </div>
        </div>
      )}

      {/* Tabs */}
      {(done || analysis.results) && (
        <div className="max-w-7xl mx-auto px-6 mt-6">
          <div className="flex gap-1 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-1 mb-6 w-fit">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "bg-blue-500 text-white"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="pb-12">
            {activeTab === "summary" && (
              <SummaryTab
                plan={analysis.results?.summary}
                mimar={analysis.results?.mimar}
                health={analysis.results?.health_report}
                onboarding={analysis.results?.onboarding_guide}
                metadata={{}}
              />
            )}
            {activeTab === "mimap" && (
              <MimapTab data={analysis.results?.architecture_graph} />
            )}
            {activeTab === "timeline" && (
              <TimelineTab data={analysis.results?.timeline} />
            )}
            {activeTab === "chat" && (
              <ChatTab analysisId={analysisId} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function UsageStatusDot() {
  const [status, setStatus] = useState<"green" | "yellow" | "red">("green");

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/usage`
        );
        const data = await res.json();
        const worst =
          data.gemini_status === "red" || data.groq_status === "red"
            ? "red"
            : data.gemini_status === "yellow" || data.groq_status === "yellow"
            ? "yellow"
            : "green";
        setStatus(worst);
      } catch {}
    }
    fetchStatus();
    const t = setInterval(fetchStatus, 30000);
    return () => clearInterval(t);
  }, []);

  const colors = { green: "bg-green-400", yellow: "bg-yellow-400", red: "bg-red-400" };
  const labels = { green: "Sistem Saglikli", yellow: "Yüksek tüketim", red: "Kota dolmak üzere" };
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
      <span className={`w-2 h-2 rounded-full ${colors[status]}`} />
      {labels[status]}
    </div>
  );
}
