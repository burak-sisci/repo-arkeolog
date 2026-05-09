const LABELS: Record<string, string> = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  java: "Java",
  go: "Go",
  rust: "Rust",
  c: "C",
  cpp: "C++",
  csharp: "C#",
  ruby: "Ruby",
  php: "PHP",
};

interface Props {
  languages: string[] | undefined | null;
  className?: string;
}

/** Salt okunur — backend uzantılardan otomatik algılanan diller (pastel rozetler) */
export function LanguageBadges({ languages, className = "" }: Props) {
  if (!languages?.length) return null;
  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Algılanan diller</span>
      {languages.map((lang) => (
        <span
          key={lang}
          className="inline-flex select-none items-center rounded-full border border-indigo-200/70 bg-indigo-50/90 px-3 py-1 text-xs font-semibold text-indigo-900 shadow-sm backdrop-blur-sm transition-all duration-300 hover:border-indigo-300 hover:shadow-md dark:border-indigo-800/80 dark:bg-indigo-950/45 dark:text-indigo-100"
          aria-hidden
        >
          {LABELS[lang] ?? lang}
        </span>
      ))}
    </div>
  );
}
