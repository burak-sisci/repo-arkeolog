"use client";

interface Props {
  plan: any;
  mimar: any;
  health: any;
  onboarding: any;
  metadata: any;
}

export function SummaryTab({ plan, mimar, health, onboarding, metadata }: Props) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Project Summary */}
      {plan?.summary && (
        <Card title="Proje Özeti">
          <p className="text-slate-700 dark:text-slate-200 leading-relaxed">{plan.summary}</p>
          {plan.estimated_complexity && (
            <div className="mt-3">
              <Badge label={`Karmaşıklık: ${plan.estimated_complexity}`} />
            </div>
          )}
        </Card>
      )}

      {/* Architecture */}
      {mimar && (
        <Card title="Mimari">
          <p className="font-medium text-blue-600 dark:text-blue-400 mb-2">{mimar.architecture_pattern}</p>
          {mimar.summary && <p className="text-sm text-slate-600 dark:text-slate-300 mb-3">{mimar.summary}</p>}
          {mimar.warnings?.length > 0 && (
            <div className="mt-2">
              {mimar.warnings.map((w: string, i: number) => (
                <div key={i} className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded p-2 mb-1">
                  {w}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Health Report */}
      {health && (
        <Card title="Saglik Raporu">
          <div className="text-3xl font-bold mb-2" style={{ color: scoreColor(health.health_score) }}>
            {health.health_score}/100
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-300 mb-3">{health.summary}</p>
          {health.stats && (
            <div className="grid grid-cols-3 gap-2 text-center text-sm">
              <Stat label="TODO" value={health.stats.todos} />
              <Stat label="Lint Hatası" value={health.stats.lint_errors} />
              <Stat label="Eski Paket" value={health.stats.outdated_deps} />
            </div>
          )}
        </Card>
      )}

      {/* Onboarding Guide */}
      {onboarding && (
        <Card title="Ilk Hafta Yol Haritası">
          {onboarding.intro && <p className="text-sm text-slate-700 dark:text-slate-200 mb-3 italic">{onboarding.intro}</p>}
          {["day_1", "day_2", "day_3"].map((day, i) =>
            onboarding[day]?.length ? (
              <div key={day} className="mb-2">
                <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-1">Gün {i + 1}</div>
                <ul className="list-disc list-inside text-sm text-slate-600 dark:text-slate-300 space-y-0.5">
                  {onboarding[day].map((item: string, j: number) => (
                    <li key={j}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null
          )}
          {onboarding.first_pr_suggestion && (
            <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-lg text-sm">
              <span className="font-medium text-green-700 dark:text-green-300">Ilk PR Önerisi: </span>
              <span className="text-slate-700 dark:text-slate-200">{onboarding.first_pr_suggestion.title}</span>
            </div>
          )}
        </Card>
      )}

      {/* Issues */}
      {health?.issues?.length > 0 && (
        <div className="lg:col-span-2">
          <Card title="Tespit Edilen Sorunlar">
            <div className="space-y-2">
              {health.issues.slice(0, 10).map((issue: any, i: number) => (
                <div key={i} className={`p-3 rounded-lg border text-sm ${severityStyle(issue.severity)}`}>
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-semibold">{issue.title}</span>
                    <span className="text-xs opacity-70">[{issue.category}]</span>
                  </div>
                  <p className="opacity-80">{issue.description}</p>
                  {issue.file_path && (
                    <p className="text-xs mt-1 font-mono opacity-60">{issue.file_path}</p>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <h2 className="font-semibold text-slate-800 dark:text-slate-100 mb-3">{title}</h2>
      {children}
    </div>
  );
}

function Badge({ label }: { label: string }) {
  return (
    <span className="inline-block px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs rounded">
      {label}
    </span>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-2">
      <div className="text-xl font-bold text-slate-800 dark:text-slate-100">{value}</div>
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
    </div>
  );
}

function scoreColor(score: number) {
  if (score >= 80) return "#16a34a";
  if (score >= 60) return "#d97706";
  return "#dc2626";
}

function severityStyle(severity: string) {
  if (severity === "high") return "bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-700 dark:text-red-300";
  if (severity === "medium") return "bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/30 dark:border-yellow-700 dark:text-yellow-300";
  return "bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-700/50 dark:border-slate-600 dark:text-slate-200";
}
