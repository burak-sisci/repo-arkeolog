"use client";
import { useEffect, useRef } from "react";

interface Milestone {
  date: string;
  commit_sha: string;
  title: string;
  description: string;
}

interface HotFile {
  path: string;
  change_count: number;
  note?: string;
}

interface ContributorSummary {
  total: number;
  active_last_3_months: number;
  top_contributors?: string[];
}

interface TimelineData {
  story_summary?: string;
  milestones?: Milestone[];
  hot_files?: HotFile[];
  contributor_summary?: ContributorSummary;
  summary_note?: string;
}

interface Props {
  data: TimelineData | null;
}

export function TimelineTab({ data }: Props) {
  const tlRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<any>(null);

  useEffect(() => {
    if (!data?.milestones?.length || !tlRef.current) return;

    import("vis-timeline/standalone").then(({ Timeline, DataSet }) => {
      const items = new DataSet(
        data.milestones!.map((m, i) => ({
          id: i,
          content: `<strong>${m.title}</strong><br/><span style="font-size:11px">${m.commit_sha}</span>`,
          start: m.date,
          title: m.description,
        }))
      );

      if (timelineRef.current) {
        timelineRef.current.destroy();
      }
      timelineRef.current = new Timeline(tlRef.current!, items, {
        height: "300px",
        locale: "en",
        showCurrentTime: false,
        tooltip: { followMouse: true },
      });
    });

    return () => {
      if (timelineRef.current) {
        timelineRef.current.destroy();
        timelineRef.current = null;
      }
    };
  }, [data]);

  if (!data) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-8 text-center text-slate-500 dark:text-slate-400">
        Timeline verisi henüz hazır değil.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {data.summary_note && (
        <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300 text-sm p-3 rounded-lg">
          {data.summary_note}
        </div>
      )}

      {/* Story */}
      {data.story_summary && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="font-semibold text-slate-800 dark:text-slate-100 mb-2">Proje Hikayesi</h2>
          <p className="text-slate-700 dark:text-slate-200 leading-relaxed">{data.story_summary}</p>
        </div>
      )}

      {/* vis-timeline */}
      {data.milestones?.length ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-200">
            Önemli Dönüm Noktaları
          </div>
          <div ref={tlRef} className="vis-timeline-container" />
        </div>
      ) : null}

      {/* Milestone list */}
      {data.milestones?.length ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h2 className="font-semibold text-slate-800 dark:text-slate-100 mb-3">Kilometre Taşları</h2>
          <ol className="relative border-l border-slate-200 dark:border-slate-600 ml-2 space-y-4">
            {data.milestones.map((m, i) => (
              <li key={i} className="ml-6">
                <span className="absolute -left-2.5 w-5 h-5 rounded-full bg-blue-500 border-2 border-white dark:border-slate-800 flex items-center justify-center text-white text-xs">
                  {i + 1}
                </span>
                <div className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">{m.date} · {m.commit_sha}</div>
                <div className="font-medium text-slate-800 dark:text-slate-100">{m.title}</div>
                <div className="text-sm text-slate-600 dark:text-slate-300">{m.description}</div>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Hot files */}
        {data.hot_files?.length ? (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="font-semibold text-slate-800 dark:text-slate-100 mb-3">En Çok Değişen Dosyalar</h2>
            <div className="space-y-2">
              {data.hot_files.slice(0, 10).map((f, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-slate-600 dark:text-slate-300 truncate max-w-xs">{f.path}</span>
                  <span className="text-blue-600 dark:text-blue-400 font-semibold ml-2">{f.change_count}x</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {/* Contributors */}
        {data.contributor_summary && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <h2 className="font-semibold text-slate-800 dark:text-slate-100 mb-3">Katkıcılar</h2>
            <div className="text-4xl font-bold text-blue-600 dark:text-blue-400 mb-1">
              {data.contributor_summary.total}
            </div>
            <div className="text-sm text-slate-500 dark:text-slate-400">toplam katkıcı</div>
            <div className="text-sm text-slate-700 dark:text-slate-200 mt-2">
              Son 3 ayda aktif: <strong>{data.contributor_summary.active_last_3_months}</strong>
            </div>
            {data.contributor_summary.top_contributors?.length ? (
              <div className="mt-3">
                <div className="text-xs text-slate-400 dark:text-slate-500 mb-1">En aktif:</div>
                <div className="flex flex-wrap gap-1">
                  {data.contributor_summary.top_contributors.slice(0, 5).map((c, i) => (
                    <span key={i} className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
