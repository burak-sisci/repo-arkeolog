const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export async function analyzeRepo(repoUrl: string, branch = "main") {
  return apiFetch("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl, branch }),
  });
}

export async function getAnalysis(analysisId: string) {
  return apiFetch(`/api/analysis/${analysisId}`);
}
