"""Dedektif Ajan — teknik borç, ölü kod, güvenlik uyarıları."""
from __future__ import annotations
import json
import logging
import subprocess
from pathlib import Path
from app.agents.base import BaseAgent, AgentContext
from app.llm.cerebras import cerebras_client as gemini_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen bir code review uzmanısın. Sana bir projenin static analysis bulguları
verilecek. Görevin: bunları önceliklendirip "sağlık karnesi" üretmek.

Çıktı saf JSON:
{
  "health_score": 72,
  "summary": "Genel olarak temiz, ama X modülünde teknik borç birikmiş.",
  "issues": [
    {
      "severity": "high|medium|low",
      "category": "security|dead_code|tech_debt|outdated_dep",
      "title": "...",
      "description": "...",
      "file_path": "...",
      "line_range": [42, 87]
    }
  ],
  "stats": {
    "todos": 23,
    "dead_functions": 5,
    "outdated_deps": 12,
    "lint_errors": 8
  }
}

Sadece JSON dön, başka metin yazma."""


class DedektifAgent(BaseAgent):
    name = "dedektif"

    async def run(self, ctx: AgentContext) -> dict:
        await self.emit(ctx, "Dedektif ajanı static analiz başlatıyor...", 76)
        repo_path = ctx.repo_path
        lang = ctx.repo_metadata.get("primary_language", "unknown")

        findings: dict = {"lint": [], "todos": [], "outdated_deps": [], "dead_code": []}

        if lang == "python":
            findings["lint"] = _run_ruff(repo_path)
            findings["dead_code"] = _run_vulture(repo_path)
        elif lang in ("javascript", "typescript"):
            findings["lint"] = _run_eslint(repo_path)

        findings["todos"] = _grep_todos(repo_path)
        findings["outdated_deps"] = _check_deps(repo_path, lang)

        await self.emit(ctx, "Dedektif bulguları önceliklendiriyor...", 80)

        user_prompt = json.dumps(
            {
                "metadata": ctx.repo_metadata,
                "findings": findings,
                "plan": ctx.plan.get("agent_plan", {}).get("dedektif", {}),
            },
            ensure_ascii=False,
            indent=2,
        )

        result = await gemini_client.generate_json(SYSTEM_PROMPT, user_prompt)
        await self.emit(ctx, "Dedektif analizi tamamlandı.", 86)
        return result


def _run_ruff(repo_path: str) -> list[dict]:
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", repo_path],
            capture_output=True, text=True, timeout=60,
        )
        import json as j
        data = j.loads(result.stdout or "[]")
        return [
            {
                "file": d.get("filename", ""),
                "line": d.get("location", {}).get("row", 0),
                "code": d.get("code", ""),
                "message": d.get("message", ""),
            }
            for d in data[:50]
        ]
    except Exception as e:
        logger.warning(f"ruff failed: {e}")
        return []


def _run_vulture(repo_path: str) -> list[dict]:
    try:
        result = subprocess.run(
            ["vulture", repo_path, "--min-confidence", "80"],
            capture_output=True, text=True, timeout=60,
        )
        dead = []
        for line in result.stdout.splitlines()[:30]:
            parts = line.split(":")
            if len(parts) >= 3:
                dead.append({"file": parts[0], "line": parts[1], "message": ":".join(parts[2:]).strip()})
        return dead
    except Exception as e:
        logger.warning(f"vulture failed: {e}")
        return []


def _run_eslint(repo_path: str) -> list[dict]:
    try:
        result = subprocess.run(
            ["npx", "eslint", "--format=json", repo_path],
            capture_output=True, text=True, timeout=60, cwd=repo_path,
        )
        import json as j
        data = j.loads(result.stdout or "[]")
        issues = []
        for file_result in data[:20]:
            for msg in file_result.get("messages", [])[:5]:
                issues.append({
                    "file": file_result.get("filePath", ""),
                    "line": msg.get("line", 0),
                    "message": msg.get("message", ""),
                    "severity": "error" if msg.get("severity") == 2 else "warning",
                })
        return issues[:50]
    except Exception as e:
        logger.warning(f"eslint failed: {e}")
        return []


def _grep_todos(repo_path: str) -> list[dict]:
    import re
    todos = []
    root = Path(repo_path)
    EXTS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
        ".java", ".kt", ".scala", ".go", ".rs",
        ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh",
        ".cs", ".rb", ".php", ".swift",
    }
    IGNORE_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "vendor", "target", "build", "dist", "bin", "obj",
    }
    # # ... (Python, Ruby, shell), // ... (C-family, Go, Rust, Java, JS, PHP, C#)
    PATTERNS = [
        re.compile(r"#\s*(TODO|FIXME|HACK|XXX|NOTE)[:\s](.+)", re.IGNORECASE),
        re.compile(r"//\s*(TODO|FIXME|HACK|XXX|NOTE)[:\s](.+)", re.IGNORECASE),
        re.compile(r"/\*+\s*(TODO|FIXME|HACK|XXX|NOTE)[:\s](.+?)\*+/", re.IGNORECASE),
    ]

    for fpath in root.rglob("*"):
        if fpath.suffix.lower() not in EXTS:
            continue
        if any(p in IGNORE_DIRS for p in fpath.parts):
            continue
        try:
            for i, line in enumerate(fpath.read_text(errors="replace").splitlines(), 1):
                for pat in PATTERNS:
                    m = pat.search(line)
                    if m:
                        todos.append({
                            "file": str(fpath.relative_to(root)),
                            "line": i,
                            "type": m.group(1).upper(),
                            "message": m.group(2).strip()[:100],
                        })
                        if len(todos) >= 50:
                            return todos
                        break
        except Exception:
            pass
    return todos


def _check_deps(repo_path: str, lang: str) -> list[str]:
    """Çoklu dil bağımlılık tespiti — manifest dosyalarını okur."""
    root = Path(repo_path)
    outdated: list[str] = []

    # JS/TS — package.json
    pkg = root / "package.json"
    if pkg.exists():
        try:
            import json as j
            data = j.loads(pkg.read_text(errors="replace"))
            all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for name, version in list(all_deps.items())[:30]:
                tag = ""
                if isinstance(version, str) and (version.startswith("^0.") or version.startswith("~0.")):
                    tag = " (pre-1.0)"
                outdated.append(f"npm:{name}@{version}{tag}")
        except Exception:
            pass

    # Python — requirements.txt / pyproject.toml
    for fname in ("requirements.txt", "requirements-dev.txt"):
        req = root / fname
        if req.exists():
            try:
                for line in req.read_text(errors="replace").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        outdated.append(f"pip:{line}")
            except Exception:
                pass
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        try:
            for line in pyproj.read_text(errors="replace").splitlines():
                s = line.strip()
                if s.startswith('"') and "==" in s:
                    outdated.append(f"pyproj:{s.strip(',').strip()}")
        except Exception:
            pass

    # Go — go.mod
    gomod = root / "go.mod"
    if gomod.exists():
        try:
            in_block = False
            for line in gomod.read_text(errors="replace").splitlines():
                s = line.strip()
                if s.startswith("require ("):
                    in_block = True
                    continue
                if in_block and s == ")":
                    in_block = False
                    continue
                if in_block and s and not s.startswith("//"):
                    outdated.append(f"go:{s}")
                elif s.startswith("require ") and not s.endswith("("):
                    outdated.append(f"go:{s[len('require '):]}")
        except Exception:
            pass

    # Rust — Cargo.toml
    cargo = root / "Cargo.toml"
    if cargo.exists():
        try:
            section = ""
            for line in cargo.read_text(errors="replace").splitlines():
                s = line.strip()
                if s.startswith("["):
                    section = s.strip("[]").lower()
                    continue
                if section.endswith("dependencies") and "=" in s and not s.startswith("#"):
                    outdated.append(f"cargo:{s}")
        except Exception:
            pass

    # Java — Maven (pom.xml) / Gradle (build.gradle*)
    pom = root / "pom.xml"
    if pom.exists():
        try:
            import re
            txt = pom.read_text(errors="replace")
            for m in re.finditer(r"<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>", txt):
                outdated.append(f"maven:{m.group(1)}@{m.group(2)}")
        except Exception:
            pass
    for fname in ("build.gradle", "build.gradle.kts"):
        gradle = root / fname
        if gradle.exists():
            try:
                import re
                for m in re.finditer(r"['\"]([\w.-]+:[\w.-]+:[\w.\-+]+)['\"]", gradle.read_text(errors="replace")):
                    outdated.append(f"gradle:{m.group(1)}")
            except Exception:
                pass

    # C# — *.csproj
    for csproj in list(root.rglob("*.csproj"))[:5]:
        try:
            import re
            for m in re.finditer(r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"', csproj.read_text(errors="replace")):
                outdated.append(f"nuget:{m.group(1)}@{m.group(2)}")
        except Exception:
            pass

    # Ruby — Gemfile
    gemfile = root / "Gemfile"
    if gemfile.exists():
        try:
            import re
            for m in re.finditer(r"gem\s+['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?", gemfile.read_text(errors="replace")):
                v = m.group(2) or ""
                outdated.append(f"gem:{m.group(1)}{('@' + v) if v else ''}")
        except Exception:
            pass

    # PHP — composer.json
    composer = root / "composer.json"
    if composer.exists():
        try:
            import json as j
            data = j.loads(composer.read_text(errors="replace"))
            for k, v in {**data.get("require", {}), **data.get("require-dev", {})}.items():
                outdated.append(f"composer:{k}@{v}")
        except Exception:
            pass

    return outdated[:40]
