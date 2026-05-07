"""Tarihçi Ajan — Git geçmişinden projenin evrim hikayesini çıkarır."""
from __future__ import annotations
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from app.agents.base import BaseAgent, AgentContext
from app.llm.cerebras import cerebras_client as groq_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen yazılım tarihçisisin. Sana bir projenin commit istatistikleri verilecek.
Görevin: bu projenin evrim hikayesini timeline olarak çıkarmak.

Çıktı saf JSON:
{
  "story_summary": "Proje 2022'de başladı, ilk 6 ay X üzerine yoğunlaştı...",
  "milestones": [
    {
      "date": "2023-04-15",
      "commit_sha": "abc123",
      "title": "Auth katmanı eklendi",
      "description": "Bu noktada proje monolit yapıdan ayrılmaya başladı."
    }
  ],
  "hot_files": [
    {"path": "src/api.py", "change_count": 47, "note": "En sık değişen dosya"}
  ],
  "contributor_summary": {
    "total": 8,
    "active_last_3_months": 3,
    "top_contributors": ["alice@example.com"]
  },
  "summary_note": ""
}

Sadece JSON dön, başka metin yazma."""


class TarihciAgent(BaseAgent):
    name = "tarihci"

    async def run(self, ctx: AgentContext) -> dict:
        await self.emit(ctx, "Tarihçi ajanı git geçmişini okuyor...", 61)
        import git

        repo = git.Repo(ctx.repo_path)
        all_commits = list(repo.iter_commits())

        summary_note = ""
        if len(all_commits) > 150:
            summary_note = f"Bu repo {len(all_commits)} commit içeriyor — Tarihçi temsili 150 commit üzerinden hikaye çıkardı."
            selected = _select_significant_commits(all_commits, max_commits=150)
        else:
            selected = all_commits

        await self.emit(ctx, f"Tarihçi ajanı {len(selected)} commit analiz ediyor...", 64)

        commit_data = _serialize_commits(selected)
        hot_files = _find_hot_files(all_commits)

        user_prompt = json.dumps(
            {
                "commit_count_total": len(all_commits),
                "commits": commit_data,
                "hot_files": hot_files[:20],
                "plan": ctx.plan.get("agent_plan", {}).get("tarihci", {}),
            },
            ensure_ascii=False,
            indent=2,
        )

        result = await groq_client.generate_json(SYSTEM_PROMPT, user_prompt)
        if summary_note:
            result["summary_note"] = summary_note

        await self.emit(ctx, "Tarih analizi tamamlandı.", 72)
        return result


def _select_significant_commits(commits: list, max_commits: int = 150) -> list:
    selected = set()
    selected.update(id(c) for c in commits[-10:])   # oldest
    selected.update(id(c) for c in commits[:30])    # newest
    selected.update(id(c) for c in commits if len(c.parents) > 1)  # merges

    # Largest diffs
    def _size(c):
        try:
            return c.stats.total.get("lines", 0)
        except Exception:
            return 0

    by_size = sorted(commits, key=_size, reverse=True)
    selected.update(id(c) for c in by_size[: max_commits // 5])

    # Monthly samples
    monthly: dict[str, object] = {}
    for c in commits:
        key = datetime.fromtimestamp(c.committed_date).strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = c
    selected.update(id(c) for c in monthly.values())

    result = [c for c in commits if id(c) in selected]
    result.sort(key=lambda c: c.committed_date)
    return result[:max_commits]


def _serialize_commits(commits: list) -> list[dict]:
    out = []
    for c in commits:
        try:
            stats = c.stats.total
        except Exception:
            stats = {}
        out.append(
            {
                "sha": c.hexsha[:8],
                "date": datetime.fromtimestamp(c.committed_date).strftime("%Y-%m-%d"),
                "author": c.author.email,
                "message": c.message.strip()[:200],
                "insertions": stats.get("insertions", 0),
                "deletions": stats.get("deletions", 0),
                "files_changed": stats.get("files", 0),
                "is_merge": len(c.parents) > 1,
            }
        )
    return out


def _find_hot_files(commits: list) -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for c in commits[:500]:  # cap for performance
        try:
            for f in c.stats.files:
                counts[f] += 1
        except Exception:
            pass
    return [
        {"path": k, "change_count": v}
        for k, v in sorted(counts.items(), key=lambda x: -x[1])[:30]
    ]
