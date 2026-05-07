"use client";
import { useEffect, useState } from "react";
import { createProgressSocket } from "@/lib/socket";

interface ProgressState {
  stage: string;
  message: string;
  progress_pct: number;
}

const STAGE_LABELS: Record<string, string> = {
  mining: "Repo kazılıyor",
  planning: "Plan hazırlanıyor",
  mimar: "Mimar ajanı çalışıyor",
  tarihci: "Tarihçi ajanı çalışıyor",
  dedektif: "Dedektif ajanı çalışıyor",
  onboarding: "Yol haritası yazılıyor",
  done: "Tamamlandı",
  error: "Hata",
};

export function ProgressBar({ analysisId }: { analysisId: string }) {
  const [progress, setProgress] = useState<ProgressState>({
    stage: "starting",
    message: "Analiz başlatılıyor...",
    progress_pct: 0,
  });

  useEffect(() => {
    const ws = createProgressSocket(analysisId, setProgress);
    return () => ws.close();
  }, [analysisId]);

  const pct = Math.min(100, Math.max(0, progress.progress_pct));

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 mb-2">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
          {STAGE_LABELS[progress.stage] || progress.stage}
        </span>
        <span className="text-sm text-slate-500 dark:text-slate-400">{pct}%</span>
      </div>
      <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">{progress.message}</p>
    </div>
  );
}
