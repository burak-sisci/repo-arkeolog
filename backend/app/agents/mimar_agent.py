"""Mimar Ajan — mimari harita, modül bağımlılıkları, tasarım pattern'ları."""
from __future__ import annotations
import json
import logging
from pathlib import Path
from app.agents.base import BaseAgent, AgentContext
from app.llm.cerebras import cerebras_client as gemini_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen bir senior software architect'sin. Sana bir projenin klasör yapısı ve
modül bağımlılık grafiği verilecek. Görevin:

1. Üst düzey mimari pattern'ı tespit et (MVC, monorepo, mikroservis, layered, vb.)
2. Her ana modülün bir cümlelik amacını yaz
3. Dikkat çekici bağımlılıklar veya circular dependencies varsa belirt

Çıktı saf JSON:
{
  "architecture_pattern": "...",
  "modules": [
    {
      "path": "src/auth",
      "purpose": "...",
      "depends_on": ["src/db", "src/utils"],
      "dependents": ["src/api"]
    }
  ],
  "warnings": ["..."],
  "summary": "..."
}

Sadece JSON dön, başka metin yazma."""


class MimarAgent(BaseAgent):
    name = "mimar"

    async def run(self, ctx: AgentContext) -> dict:
        await self.emit(ctx, "Mimar ajanı klasör yapısını analiz ediyor...", 46)

        folder_tree = _build_folder_tree(ctx.repo_path)
        import_graph = _build_import_graph(ctx.repo_path)

        user_prompt = json.dumps(
            {
                "metadata": ctx.repo_metadata,
                "folder_structure": folder_tree,
                "import_graph": import_graph,
                "plan": ctx.plan.get("agent_plan", {}).get("mimar", {}),
            },
            ensure_ascii=False,
            indent=2,
        )

        await self.emit(ctx, "Mimar ajanı modül bağımlılıklarını çözümlüyor...", 50)
        result = await gemini_client.generate_json(SYSTEM_PROMPT, user_prompt)
        await self.emit(ctx, "Mimari analiz tamamlandı.", 58)
        return result


def _build_folder_tree(repo_path: str, max_depth: int = 4) -> dict:
    """Klasör ağacını dict olarak döner."""
    root = Path(repo_path)
    IGNORE = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", ".next"}

    def _walk(path: Path, depth: int) -> dict | None:
        if depth > max_depth:
            return None
        if path.name in IGNORE:
            return None
        if path.is_file():
            return path.name
        result = {}
        try:
            for child in sorted(path.iterdir()):
                sub = _walk(child, depth + 1)
                if sub is not None:
                    result[child.name] = sub
        except PermissionError:
            pass
        return result

    return _walk(root, 0) or {}


def _build_import_graph(repo_path: str) -> dict[str, list[str]]:
    """Basit import graph — sadece kendi dosya referanslarını yakalar."""
    import re
    root = Path(repo_path)
    graph: dict[str, list[str]] = {}
    EXTS = {".py", ".js", ".ts", ".jsx", ".tsx"}

    for fpath in root.rglob("*"):
        if fpath.suffix not in EXTS:
            continue
        if any(p in {"node_modules", ".git", "__pycache__"} for p in fpath.parts):
            continue
        rel = str(fpath.relative_to(root))
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        imports = []
        # Python: from . import / import x
        for m in re.findall(r"^from\s+([\.\w/]+)\s+import", content, re.MULTILINE):
            imports.append(m)
        # JS/TS: import ... from '...'
        for m in re.findall(r"""(?:import|require)\s*\(?['"]([^'"]+)['"]\)?""", content):
            if m.startswith("."):
                imports.append(m)

        if imports:
            graph[rel] = imports[:30]  # cap per file

    return graph
