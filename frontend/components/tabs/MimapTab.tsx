"use client";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";

interface GraphData {
  nodes: Array<{ data: { id: string; label: string; purpose: string } }>;
  edges: Array<{ data: { source: string; target: string } }>;
}

interface Props {
  data: GraphData | null;
}

interface DetailPanel {
  id: string;
  label: string;
  purpose: string;
  role: RoleKey;
  inDegree: number;
  outDegree: number;
  dependsOn: string[];
  dependedBy: string[];
}

type RoleKey =
  | "entry"
  | "api"
  | "ui"
  | "business"
  | "data"
  | "util"
  | "config"
  | "test"
  | "other";

type LayoutKey = "concentric" | "dagre" | "cose" | "grid";

const ROLES: Record<RoleKey, { label: string; color: string; description: string; icon: string }> = {
  entry:    { label: "Giriş Noktası", color: "#ef4444", icon: "▶", description: "main, index, app — uygulamanın başladığı yer" },
  api:      { label: "API / Route",   color: "#3b82f6", icon: "🔌", description: "HTTP endpoint, controller, route" },
  ui:       { label: "Arayüz",        color: "#06b6d4", icon: "🖼",  description: "Sayfa, component, view" },
  business: { label: "İş Mantığı",    color: "#a855f7", icon: "⚙",  description: "Servis, agent, domain logic" },
  data:     { label: "Veri",          color: "#10b981", icon: "💾", description: "Model, schema, repository, DB erişimi" },
  util:     { label: "Yardımcı",      color: "#8b5cf6", icon: "🔧", description: "Util, helper, lib, common" },
  config:   { label: "Yapılandırma",  color: "#f59e0b", icon: "⚙",  description: "Config, settings, env" },
  test:     { label: "Test",          color: "#94a3b8", icon: "✓", description: "Test dosyaları" },
  other:    { label: "Diğer",         color: "#64748b", icon: "•", description: "Sınıflandırılamayan modüller" },
};

function detectRole(id: string): RoleKey {
  const p = id.toLowerCase();
  const base = p.split("/").pop() || "";
  if (/^(main|index|app|server|__main__|run)\.(py|ts|tsx|js|jsx|mjs|java|go|rs|rb|php)$/.test(base)) return "entry";
  if (/(^|\/)tests?\//.test(p) || /\.(test|spec)\.(py|ts|tsx|js|jsx)$/.test(base) || /^test_/.test(base) || /_test\.(go|py|rb)$/.test(base)) return "test";
  if (/(^|\/)(config|settings|env)/.test(p) || /(config|settings)\.(py|ts|js)$/.test(base)) return "config";
  if (/(^|\/)(api|routes?|controllers?|endpoints?|handlers?)\//.test(p)) return "api";
  if (/(^|\/)(components?|pages?|views?|screens?|ui|layouts?)\//.test(p)) return "ui";
  if (/(^|\/)(models?|schemas?|entities?|repositories?|repo|orm|migrations?|db)\//.test(p)) return "data";
  if (/(^|\/)(utils?|helpers?|lib|common|shared|core)\//.test(p)) return "util";
  if (/(^|\/)(services?|agents?|tasks?|jobs?|usecases?|domain|pipeline|business)\//.test(p)) return "business";
  return "other";
}

function topFolder(id: string): string {
  const parts = id.split("/");
  if (parts.length <= 1) return "📂 root";
  return `📂 ${parts[0]}`;
}

// Tarjan SCC ile döngü tespiti (boyutu >1 olan SCC'ler döngüdür)
function detectCycles(nodes: string[], edges: Array<{ source: string; target: string }>): string[][] {
  const adj: Record<string, string[]> = {};
  for (const n of nodes) adj[n] = [];
  for (const e of edges) (adj[e.source] || (adj[e.source] = [])).push(e.target);

  let index = 0;
  const stack: string[] = [];
  const onStack = new Set<string>();
  const ids: Record<string, number> = {};
  const low: Record<string, number> = {};
  const sccs: string[][] = [];

  // İteratif Tarjan — büyük graflarda stack overflow'u engellemek için
  function strongconnect(start: string) {
    const work: Array<{ v: string; iter: number }> = [{ v: start, iter: 0 }];
    while (work.length) {
      const frame = work[work.length - 1];
      const v = frame.v;
      if (frame.iter === 0) {
        ids[v] = index;
        low[v] = index;
        index++;
        stack.push(v);
        onStack.add(v);
      }
      const neighbors = adj[v] || [];
      if (frame.iter < neighbors.length) {
        const w = neighbors[frame.iter];
        frame.iter++;
        if (ids[w] === undefined) {
          work.push({ v: w, iter: 0 });
        } else if (onStack.has(w)) {
          low[v] = Math.min(low[v], ids[w]);
        }
      } else {
        if (low[v] === ids[v]) {
          const comp: string[] = [];
          while (true) {
            const w = stack.pop()!;
            onStack.delete(w);
            comp.push(w);
            if (w === v) break;
          }
          if (comp.length > 1) sccs.push(comp);
        }
        work.pop();
        if (work.length) {
          const parent = work[work.length - 1].v;
          low[parent] = Math.min(low[parent], low[v]);
        }
      }
    }
  }

  for (const n of nodes) if (ids[n] === undefined) strongconnect(n);
  return sccs;
}

let dagreRegistered = false;

export function MimapTab({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const [detail, setDetail] = useState<DetailPanel | null>(null);
  const [search, setSearch] = useState("");
  const [helpOpen, setHelpOpen] = useState(true);
  const [layout, setLayout] = useState<LayoutKey>("concentric");
  const [grouped, setGrouped] = useState(false);
  const [roleFilter, setRoleFilter] = useState<Set<RoleKey>>(new Set());

  // Hesaplanan istatistikler
  const stats = useMemo(() => {
    if (!data) return null;
    const nodeIds = new Set(data.nodes.map((n) => n.data.id));
    const validEdges = data.edges.filter(
      (e) => nodeIds.has(e.data.source) && nodeIds.has(e.data.target)
    );
    const inDeg: Record<string, number> = {};
    const outDeg: Record<string, number> = {};
    const dependsOn: Record<string, string[]> = {};
    const dependedBy: Record<string, string[]> = {};
    const roleCount: Record<RoleKey, number> = {
      entry: 0, api: 0, ui: 0, business: 0, data: 0, util: 0, config: 0, test: 0, other: 0,
    };
    for (const id of nodeIds) {
      inDeg[id] = 0;
      outDeg[id] = 0;
      dependsOn[id] = [];
      dependedBy[id] = [];
    }
    for (const e of validEdges) {
      inDeg[e.data.target]++;
      outDeg[e.data.source]++;
      dependsOn[e.data.source].push(e.data.target);
      dependedBy[e.data.target].push(e.data.source);
    }
    for (const n of data.nodes) {
      roleCount[detectRole(n.data.id)]++;
    }
    const maxIn = Math.max(1, ...Object.values(inDeg));
    const cycles = detectCycles(
      data.nodes.map((n) => n.data.id),
      validEdges.map((e) => ({ source: e.data.source, target: e.data.target })),
    );
    const cycleEdges = new Set<string>();
    for (const scc of cycles) {
      const sccSet = new Set(scc);
      for (const e of validEdges) {
        if (sccSet.has(e.data.source) && sccSet.has(e.data.target)) {
          cycleEdges.add(`${e.data.source}->${e.data.target}`);
        }
      }
    }
    const avgDeg = validEdges.length / Math.max(1, data.nodes.length);
    return {
      validEdges, inDeg, outDeg, dependsOn, dependedBy, maxIn,
      roleCount, cycles, cycleEdges, avgDeg,
    };
  }, [data]);

  // Cytoscape setup + layout uygulama
  useEffect(() => {
    if (!data?.nodes?.length || !containerRef.current || !stats) return;
    let cancelled = false;
    const { validEdges, inDeg, maxIn, cycleEdges } = stats;

    // Rol filtresi: hiç seçili yoksa hepsi göster
    const visibleRoles: Set<RoleKey> | null = roleFilter.size === 0 ? null : roleFilter;

    const visibleNodes = data.nodes.filter((n) => {
      const r = detectRole(n.data.id);
      return !visibleRoles || visibleRoles.has(r);
    });
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.data.id));
    const visibleEdges = validEdges.filter(
      (e) => visibleNodeIds.has(e.data.source) && visibleNodeIds.has(e.data.target)
    );

    // Compound (folder) nodes
    const compoundNodes: any[] = [];
    if (grouped) {
      const folders = new Set<string>();
      for (const n of visibleNodes) folders.add(topFolder(n.data.id));
      for (const f of folders) {
        compoundNodes.push({
          data: { id: f, label: f, isFolder: true },
        });
      }
    }

    const decoratedNodes = visibleNodes.map((n) => {
      const role = detectRole(n.data.id);
      const inD = inDeg[n.data.id] || 0;
      const size = 26 + Math.round((inD / maxIn) * 38);
      return {
        data: {
          id: n.data.id,
          label: n.data.label,
          purpose: n.data.purpose || "",
          role,
          color: ROLES[role].color,
          size,
          inDeg: inD,
          parent: grouped ? topFolder(n.data.id) : undefined,
        },
      };
    });

    const decoratedEdges = visibleEdges.map((e) => ({
      data: {
        ...e.data,
        cycle: cycleEdges.has(`${e.data.source}->${e.data.target}`),
      },
    }));

    (async () => {
      const cytoscapeModule = await import("cytoscape");
      if (cancelled || !containerRef.current) return;
      const cytoscape: any = cytoscapeModule.default;

      // dagre registration (sadece bir kez)
      if (!dagreRegistered) {
        try {
          const dagre = (await import("cytoscape-dagre")).default;
          cytoscape.use(dagre);
          dagreRegistered = true;
        } catch (e) {
          console.warn("dagre yüklenemedi", e);
        }
      }

      if (cyRef.current) {
        try { cyRef.current.destroy(); } catch {}
        cyRef.current = null;
      }

      const isDark = document.documentElement.classList.contains("dark");

      cyRef.current = cytoscape({
        container: containerRef.current,
        elements: [...compoundNodes, ...decoratedNodes, ...decoratedEdges],
        wheelSensitivity: 0.2,
        style: [
          {
            selector: "node[!isFolder]",
            style: {
              label: "data(label)",
              "background-color": "data(color)",
              color: isDark ? "#e2e8f0" : "#0f172a",
              "text-valign": "bottom",
              "text-halign": "center",
              "text-margin-y": 4,
              "font-size": "10px",
              "font-weight": 500,
              "text-wrap": "ellipsis",
              "text-max-width": "120px",
              "text-outline-color": isDark ? "#0f172a" : "#ffffff",
              "text-outline-width": 2,
              width: "data(size)",
              height: "data(size)",
              "border-width": 1,
              "border-color": isDark ? "rgba(226,232,240,0.2)" : "rgba(15,23,42,0.15)",
            },
          },
          {
            selector: "node[isFolder]",
            style: {
              label: "data(label)",
              "background-color": isDark ? "rgba(30,41,59,0.6)" : "rgba(241,245,249,0.7)",
              "background-opacity": 0.5,
              "border-style": "dashed",
              "border-width": 2,
              "border-color": isDark ? "#475569" : "#cbd5e1",
              color: isDark ? "#cbd5e1" : "#475569",
              "font-size": "13px",
              "font-weight": "bold",
              "text-valign": "top",
              "text-halign": "center",
              "text-margin-y": -5,
              padding: "16px",
              shape: "round-rectangle",
            },
          },
          {
            selector: "node:selected",
            style: { "border-width": 3, "border-color": "#1d4ed8" },
          },
          {
            selector: "node.dim",
            style: { opacity: 0.15 },
          },
          {
            selector: "node.highlight",
            style: {
              "border-width": 3,
              "border-color": isDark ? "#f1f5f9" : "#0f172a",
              "z-index": 10,
            },
          },
          {
            selector: "edge",
            style: {
              "curve-style": "bezier",
              "target-arrow-shape": "triangle",
              "arrow-scale": 1,
              "line-color": isDark ? "#475569" : "#cbd5e1",
              "target-arrow-color": isDark ? "#475569" : "#cbd5e1",
              width: 1.5,
              opacity: 0.6,
            },
          },
          {
            selector: "edge[?cycle]",
            style: {
              "line-color": "#dc2626",
              "target-arrow-color": "#dc2626",
              "line-style": "dashed",
              width: 2,
              opacity: 0.95,
              "z-index": 8,
            },
          },
          {
            selector: "edge.dim",
            style: { opacity: 0.05 },
          },
          {
            selector: "edge.highlight",
            style: {
              "line-color": "#1d4ed8",
              "target-arrow-color": "#1d4ed8",
              width: 2.5,
              opacity: 1,
              "z-index": 9,
            },
          },
        ],
        layout: getLayoutConfig(layout),
      });

      cyRef.current.on("tap", "node[!isFolder]", (evt: any) => {
        if (!cyRef.current) return;
        const d = evt.target.data();
        setDetail({
          id: d.id,
          label: d.label,
          purpose: d.purpose,
          role: d.role,
          inDegree: d.inDeg,
          outDegree: stats.outDeg[d.id] || 0,
          dependsOn: stats.dependsOn[d.id] || [],
          dependedBy: stats.dependedBy[d.id] || [],
        });
      });

      cyRef.current.on("mouseover", "node[!isFolder]", (evt: any) => {
        if (!cyRef.current) return;
        const node = evt.target;
        cyRef.current.elements().addClass("dim");
        node.closedNeighborhood().removeClass("dim").addClass("highlight");
      });

      cyRef.current.on("mouseout", "node[!isFolder]", () => {
        if (!cyRef.current) return;
        cyRef.current.elements().removeClass("dim").removeClass("highlight");
      });

      cyRef.current.on("tap", (evt: any) => {
        if (evt.target === cyRef.current) setDetail(null);
      });
    })();

    return () => {
      cancelled = true;
      if (cyRef.current) {
        try { cyRef.current.stop?.(); cyRef.current.destroy(); } catch {}
        cyRef.current = null;
      }
    };
  }, [data, stats, layout, grouped, roleFilter]);

  // Search highlight
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    cy.elements().removeClass("dim").removeClass("highlight");
    if (!search.trim()) return;
    const q = search.toLowerCase();
    const matching = cy.nodes("[!isFolder]").filter((n: any) => n.data("id").toLowerCase().includes(q));
    if (matching.length === 0) return;
    cy.elements().addClass("dim");
    matching.removeClass("dim").addClass("highlight");
    matching.connectedEdges().removeClass("dim");
    matching.neighborhood().removeClass("dim");
  }, [search]);

  // Tema değişince re-render (style güncellemesi için)
  useEffect(() => {
    const obs = new MutationObserver(() => {
      // tetiklemek için layout state'i tazelemek yerine setLayout kendisiyle değiştir
      setLayout((l) => l);
    });
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  const focusNode = useCallback((id: string) => {
    if (!cyRef.current) return;
    const node = cyRef.current.getElementById(id);
    if (!node || node.empty()) return;
    cyRef.current.animate({ center: { eles: node }, zoom: 1.5, duration: 400 });
    cyRef.current.elements().addClass("dim");
    node.closedNeighborhood().removeClass("dim").addClass("highlight");
    setDetail({
      id,
      label: node.data("label"),
      purpose: node.data("purpose") || "",
      role: node.data("role"),
      inDegree: node.data("inDeg"),
      outDegree: stats?.outDeg[id] || 0,
      dependsOn: stats?.dependsOn[id] || [],
      dependedBy: stats?.dependedBy[id] || [],
    });
  }, [stats]);

  const fit = useCallback(() => cyRef.current?.fit(undefined, 30), []);
  const zoomIn = useCallback(() => cyRef.current?.zoom(cyRef.current.zoom() * 1.25), []);
  const zoomOut = useCallback(() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8), []);
  const exportPng = useCallback(() => {
    if (!cyRef.current) return;
    const isDark = document.documentElement.classList.contains("dark");
    const png = cyRef.current.png({ full: true, scale: 2, bg: isDark ? "#0f172a" : "#ffffff" });
    const a = document.createElement("a");
    a.href = png;
    a.download = "mimari-harita.png";
    a.click();
  }, []);

  function toggleRole(role: RoleKey) {
    setRoleFilter((s) => {
      const ns = new Set(s);
      if (ns.has(role)) ns.delete(role); else ns.add(role);
      return ns;
    });
  }

  if (!data?.nodes?.length || !stats) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-8 text-center text-slate-500 dark:text-slate-400">
        Mimari veri henüz hazır değil.
      </div>
    );
  }

  const usedRoles = (Object.keys(stats.roleCount) as RoleKey[]).filter((r) => stats.roleCount[r] > 0);
  const topModules = data.nodes
    .map((n) => ({ id: n.data.id, label: n.data.label, inDeg: stats.inDeg[n.data.id] || 0 }))
    .sort((a, b) => b.inDeg - a.inDeg)
    .slice(0, 5)
    .filter((m) => m.inDeg > 0);

  return (
    <div className="space-y-3">
      {/* İstatistik kartları */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Modül" value={data.nodes.length} accent="blue" />
        <StatCard label="Bağımlılık" value={stats.validEdges.length} accent="emerald" />
        <StatCard
          label="Döngüsel Bağ"
          value={stats.cycles.length}
          accent={stats.cycles.length > 0 ? "red" : "slate"}
          hint={stats.cycles.length > 0 ? "Çözülmesi tavsiye edilir" : "Temiz"}
        />
        <StatCard label="Ort. Bağımlılık" value={stats.avgDeg.toFixed(1)} accent="purple" hint="Modül başına" />
      </div>

      {/* Yardım kutusu */}
      {helpOpen && (
        <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-xl p-4 relative">
          <button onClick={() => setHelpOpen(false)} className="absolute top-2 right-3 text-blue-700 dark:text-blue-300 text-lg" aria-label="Kapat">×</button>
          <h3 className="font-semibold text-blue-800 dark:text-blue-200 text-sm mb-2">Bu haritayı nasıl okumalıyım?</h3>
          <ul className="text-xs text-blue-900 dark:text-blue-100 space-y-1 list-disc list-inside">
            <li><strong>Renk = rol</strong> (API, UI, veri, yardımcı, …). Üstteki kartlardan filtreleyebilirsin.</li>
            <li><strong>Daire büyüklüğü = etkisi</strong> — daha büyükse, daha fazla modül ona bağımlı (projenin "kalbi").</li>
            <li><strong>Kırmızı kesik kenarlar = döngüsel bağımlılık</strong> — temizlenmesi tavsiye edilir.</li>
            <li><strong>Layout</strong> butonlarıyla görünümü değiştir: <em>Hiyerarşik</em> bağımlılık akışını gösterir; <em>Klasör grubu</em> projeyi dosya yapısına göre kümeler.</li>
            <li>Bir düğüme tıkla → detay paneli açılır; orada bağımlı/bağımsız olduğu modülleri tek tıkla gezebilirsin.</li>
          </ul>
        </div>
      )}

      {/* Toolbar: search + layout + actions */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3 flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Modül ara…"
          className="flex-1 min-w-[180px] px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-1 bg-slate-100 dark:bg-slate-900 rounded-lg p-1">
          <LayoutBtn k="concentric" current={layout} setLayout={setLayout} label="Konsantrik" />
          <LayoutBtn k="dagre" current={layout} setLayout={setLayout} label="Hiyerarşik" />
          <LayoutBtn k="cose" current={layout} setLayout={setLayout} label="Organik" />
          <LayoutBtn k="grid" current={layout} setLayout={setLayout} label="Izgara" />
        </div>
        <button
          onClick={() => setGrouped((g) => !g)}
          className={`px-3 py-2 rounded-lg text-xs font-medium ${grouped ? "bg-blue-500 text-white" : "bg-slate-100 dark:bg-slate-900 text-slate-700 dark:text-slate-200"}`}
        >
          📂 Klasör Grubu
        </button>
        <div className="flex gap-1 ml-auto">
          <IconBtn onClick={zoomIn} title="Yakınlaştır">+</IconBtn>
          <IconBtn onClick={zoomOut} title="Uzaklaştır">−</IconBtn>
          <IconBtn onClick={fit} title="Ekrana sığdır">⇲</IconBtn>
          <IconBtn onClick={exportPng} title="PNG indir">⬇</IconBtn>
          {!helpOpen && (
            <button onClick={() => setHelpOpen(true)} className="text-xs text-blue-600 dark:text-blue-400 hover:underline ml-2">
              ? Nasıl okumalı
            </button>
          )}
        </div>
      </div>

      {/* Rol filtre çipleri */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3 flex flex-wrap gap-2 items-center">
        <span className="text-xs text-slate-500 dark:text-slate-400 mr-1">Rol:</span>
        {usedRoles.map((r) => {
          const active = roleFilter.size === 0 || roleFilter.has(r);
          return (
            <button
              key={r}
              onClick={() => toggleRole(r)}
              title={ROLES[r].description}
              className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-all ${
                active
                  ? "border-transparent text-white"
                  : "border-slate-200 dark:border-slate-700 text-slate-400 dark:text-slate-500 bg-transparent"
              }`}
              style={active ? { background: ROLES[r].color } : {}}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: active ? "#fff" : ROLES[r].color }} />
              <span>{ROLES[r].label}</span>
              <span className="opacity-75">{stats.roleCount[r]}</span>
            </button>
          );
        })}
        {roleFilter.size > 0 && (
          <button onClick={() => setRoleFilter(new Set())} className="text-xs text-blue-600 dark:text-blue-400 hover:underline ml-1">
            tümünü göster
          </button>
        )}
        <span className="text-xs text-slate-400 dark:text-slate-500 ml-auto">Daire büyüklüğü = ona bağımlı modül sayısı</span>
      </div>

      {/* Graph + detail panel */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="flex flex-col lg:flex-row">
          <div ref={containerRef} className="cy-container flex-1" style={{ minHeight: 560 }} />

          <div className="lg:w-96 border-t lg:border-t-0 lg:border-l border-slate-100 dark:border-slate-700 p-4 bg-slate-50 dark:bg-slate-900/50 overflow-y-auto" style={{ maxHeight: 560 }}>
            {detail ? (
              <DetailView detail={detail} onNavigate={focusNode} onClose={() => setDetail(null)} />
            ) : (
              <DefaultPanel topModules={topModules} cycles={stats.cycles} onNavigate={focusNode} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Yardımcı componentler ---

function StatCard({ label, value, accent, hint }: { label: string; value: number | string; accent: "blue" | "emerald" | "red" | "purple" | "slate"; hint?: string }) {
  const colors: Record<string, string> = {
    blue: "text-blue-600 dark:text-blue-400",
    emerald: "text-emerald-600 dark:text-emerald-400",
    red: "text-red-600 dark:text-red-400",
    purple: "text-purple-600 dark:text-purple-400",
    slate: "text-slate-600 dark:text-slate-400",
  };
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
      <div className={`text-2xl font-bold ${colors[accent]}`}>{value}</div>
      <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label}</div>
      {hint && <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}

function LayoutBtn({ k, current, setLayout, label }: { k: LayoutKey; current: LayoutKey; setLayout: (l: LayoutKey) => void; label: string }) {
  const active = current === k;
  return (
    <button
      onClick={() => setLayout(k)}
      className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
        active ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm" : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
      }`}
    >
      {label}
    </button>
  );
}

function IconBtn({ onClick, title, children }: { onClick: () => void; title: string; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="w-8 h-8 inline-flex items-center justify-center rounded-lg bg-slate-100 dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 text-base font-bold"
    >
      {children}
    </button>
  );
}

function DetailView({ detail, onNavigate, onClose }: { detail: DetailPanel; onNavigate: (id: string) => void; onClose: () => void }) {
  return (
    <>
      <div className="flex items-start justify-between mb-2 gap-2">
        <span className="font-semibold text-slate-800 dark:text-slate-100 text-sm break-all">{detail.label}</span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 text-lg leading-none">×</button>
      </div>
      <span
        className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full mb-2 font-medium"
        style={{ background: ROLES[detail.role].color + "33", color: ROLES[detail.role].color }}
      >
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: ROLES[detail.role].color }} />
        {ROLES[detail.role].label}
      </span>
      <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1 mb-3 break-all">{detail.id}</p>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-blue-600 dark:text-blue-400">{detail.inDegree}</div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">modül buna<br/>bağımlı</div>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{detail.outDegree}</div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">modüle<br/>bağımlı</div>
        </div>
      </div>

      {detail.purpose ? (
        <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed mb-3">{detail.purpose}</p>
      ) : (
        <p className="text-sm text-slate-400 dark:text-slate-500 italic mb-3">Açıklama yok</p>
      )}

      <NeighborList title="Bağımlı olduğu" items={detail.dependsOn} onNavigate={onNavigate} accent="emerald" empty="Hiçbir şeye bağımlı değil." />
      <NeighborList title="Buna bağımlı olanlar" items={detail.dependedBy} onNavigate={onNavigate} accent="blue" empty="Hiçbir modül buna bağımlı değil." />
    </>
  );
}

function NeighborList({ title, items, onNavigate, accent, empty }: { title: string; items: string[]; onNavigate: (id: string) => void; accent: "blue" | "emerald"; empty: string }) {
  const colors: Record<string, string> = {
    blue: "text-blue-600 dark:text-blue-400",
    emerald: "text-emerald-600 dark:text-emerald-400",
  };
  return (
    <div className="mb-3">
      <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1.5">
        {title} <span className={colors[accent]}>({items.length})</span>
      </h4>
      {items.length === 0 ? (
        <p className="text-xs text-slate-400 dark:text-slate-500 italic">{empty}</p>
      ) : (
        <ul className="space-y-1 max-h-40 overflow-y-auto pr-1">
          {items.slice(0, 30).map((id) => (
            <li key={id}>
              <button
                onClick={() => onNavigate(id)}
                className="w-full text-left text-xs font-mono px-2 py-1 rounded bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 truncate transition-colors"
                title={id}
              >
                {id.split("/").slice(-2).join("/")}
              </button>
            </li>
          ))}
          {items.length > 30 && (
            <li className="text-xs text-slate-400 dark:text-slate-500 px-2 italic">… ve {items.length - 30} fazlası</li>
          )}
        </ul>
      )}
    </div>
  );
}

function DefaultPanel({ topModules, cycles, onNavigate }: { topModules: Array<{ id: string; label: string; inDeg: number }>; cycles: string[][]; onNavigate: (id: string) => void }) {
  return (
    <>
      <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
        Projenin kalbi
      </h4>
      {topModules.length ? (
        <ol className="space-y-1 mb-5">
          {topModules.map((m, i) => (
            <li key={m.id}>
              <button
                onClick={() => onNavigate(m.id)}
                className="w-full text-left flex items-start gap-2 text-sm px-2 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                <span className="text-slate-400 dark:text-slate-500 text-xs font-mono mt-0.5 w-4">{i + 1}.</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-800 dark:text-slate-100 truncate">{m.label}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">{m.inDeg} bağımlılık</div>
                </div>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-sm text-slate-400 dark:text-slate-500 mb-5">İç bağımlılık yok.</p>
      )}

      {cycles.length > 0 && (
        <div className="border-t border-slate-200 dark:border-slate-700 pt-3 mb-3">
          <h4 className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide mb-2">
            Döngüsel Bağımlılıklar ({cycles.length})
          </h4>
          <ul className="space-y-2 max-h-40 overflow-y-auto">
            {cycles.slice(0, 5).map((scc, i) => (
              <li key={i} className="text-xs bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded p-2">
                <div className="font-medium text-red-800 dark:text-red-200 mb-1">Döngü #{i + 1} ({scc.length} modül)</div>
                <div className="space-y-0.5">
                  {scc.slice(0, 4).map((id) => (
                    <button
                      key={id}
                      onClick={() => onNavigate(id)}
                      className="block text-xs font-mono text-red-700 dark:text-red-300 hover:underline truncate w-full text-left"
                    >
                      {id.split("/").slice(-2).join("/")}
                    </button>
                  ))}
                  {scc.length > 4 && <div className="text-xs text-red-500/80 italic">… +{scc.length - 4}</div>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-slate-400 dark:text-slate-500 mt-4 leading-relaxed">
        Bir düğüme tıkla → detayları + bağımlılık listeleri açılır. Hover yap → ilişkileri parlar.
      </p>
    </>
  );
}

// --- Layout config ---
function getLayoutConfig(layout: LayoutKey): any {
  switch (layout) {
    case "concentric":
      return {
        name: "concentric",
        animate: false,
        concentric: (n: any) => n.data("inDeg") || 0,
        levelWidth: () => 1,
        minNodeSpacing: 28,
        padding: 30,
      };
    case "dagre":
      return {
        name: "dagre",
        animate: false,
        rankDir: "TB",
        nodeSep: 30,
        rankSep: 80,
        padding: 30,
      };
    case "cose":
      return {
        name: "cose",
        animate: false,
        idealEdgeLength: () => 100,
        nodeOverlap: 20,
        padding: 30,
        randomize: false,
      };
    case "grid":
      return {
        name: "grid",
        animate: false,
        padding: 30,
        spacingFactor: 1.4,
      };
  }
}
