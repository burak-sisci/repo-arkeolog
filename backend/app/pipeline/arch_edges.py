"""Repo içi dosya düzeyinde kenar (import) ve ana sembol çıkarımı — LLM çıktısından bağımsız deterministik."""
from __future__ import annotations

import ast
import re
from pathlib import Path

IGNORE_DIRS = frozenset(
    {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "coverage",
        ".mypy_cache",
        ".pytest_cache",
        ".idea",
        ".vscode",
    }
)

CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx"}


def _norm_rel(root: Path, p: Path) -> str:
    return str(p.relative_to(root)).replace("\\", "/")


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def _under_root(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _iter_code_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in CODE_EXT:
            continue
        if _is_ignored(p):
            continue
        out.append(p)
    return out


def _resolve_abs_py_import(root: Path, module: str) -> list[Path]:
    if not module:
        return []
    parts = module.split(".")
    out: list[Path] = []
    p = root.joinpath(*parts).with_suffix(".py")
    if p.is_file():
        out.append(p)
    pkg_init = root.joinpath(*parts) / "__init__.py"
    if pkg_init.is_file():
        out.append(pkg_init)
    return out


def _resolve_rel_py_import(from_file: Path, root: Path, level: int, module: str | None) -> list[Path]:
    base = from_file.parent
    if level > 0:
        for _ in range(level - 1):
            base = base.parent
    if not module:
        return []
    parts = module.split(".")
    out: list[Path] = []
    p = base.joinpath(*parts).with_suffix(".py")
    if p.is_file() and _under_root(p, root):
        out.append(p)
    pkg_init = base.joinpath(*parts) / "__init__.py"
    if pkg_init.is_file() and _under_root(pkg_init, root):
        out.append(pkg_init)
    return out


def _python_import_targets(from_file: Path, root: Path) -> list[Path]:
    targets: list[Path] = []
    try:
        src = from_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src, filename=str(from_file))
    except (SyntaxError, OSError, UnicodeError):
        return targets

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            lvl = getattr(node, "level", 0) or 0
            mod = node.module
            if lvl == 0:
                hits = _resolve_abs_py_import(root, mod or "")
            else:
                hits = _resolve_rel_py_import(from_file, root, lvl, mod)
            for h in hits:
                if h.is_file():
                    targets.append(h)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if len(top) <= 1:
                    continue
                if top in {"sys", "os", "re", "json", "typing", "logging", "asyncio", "pathlib", "datetime"}:
                    continue
                for h in _resolve_abs_py_import(root, alias.name):
                    if h.is_file():
                        targets.append(h)
                for h in _resolve_abs_py_import(root, top):
                    if h.is_file():
                        targets.append(h)

    return targets


_JS_REL_IMPORT = re.compile(
    r"""(?:from\s+['"](\.[^'"]+)['"]|import\s*\(?['"](\.[^'"]+)['"])""",
    re.MULTILINE,
)


def _resolve_js_relative(spec: str, from_file: Path, root: Path) -> list[Path]:
    out: list[Path] = []
    if not spec.startswith("."):
        return out
    raw = (from_file.parent / spec).resolve()

    candidates: list[Path] = []
    if raw.suffix in CODE_EXT:
        candidates.append(raw)
    else:
        for ext in (".ts", ".tsx", ".js", ".jsx"):
            candidates.append(Path(str(raw) + ext))
        candidates.append(raw / "index.ts")
        candidates.append(raw / "index.tsx")
        candidates.append(raw / "index.js")

    for c in candidates:
        try:
            if c.is_file() and _under_root(c, root):
                out.append(c)
                return out
        except OSError:
            continue
    return out


def _js_import_targets(from_file: Path, root: Path) -> list[Path]:
    targets: list[Path] = []
    try:
        content = from_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return targets
    for m in _JS_REL_IMPORT.finditer(content):
        spec = m.group(1) or m.group(2)
        if spec:
            targets.extend(_resolve_js_relative(spec, from_file, root))
    return targets


def _extract_python_symbols(from_file: Path) -> list[str]:
    try:
        tree = ast.parse(from_file.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return []
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            names.append(f"class {node.name}")
        elif isinstance(node, ast.AsyncFunctionDef):
            names.append(f"async def {node.name}(…)")
        elif isinstance(node, ast.FunctionDef):
            names.append(f"def {node.name}(…)")
    return names[:14]


_JS_EXPORT_FN = re.compile(
    r"(?:export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)|export\s+class\s+(\w+))",
)
_JS_FN = re.compile(r"(?:^|\n)\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(")
_JS_CLASS = re.compile(r"(?:^|\n)\s*(?:export\s+)?class\s+(\w+)\b")


def _extract_js_symbols(from_file: Path) -> list[str]:
    try:
        content = from_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    names: list[str] = []
    for pat in (_JS_EXPORT_FN, _JS_FN, _JS_CLASS):
        for m in pat.finditer(content):
            g = m.group(1) or m.group(2)
            if g:
                names.append(g)
    seen: set[str] = set()
    uniq: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq[:14]


def build_architecture_graph_metadata(repo_path: str | Path, *, max_edges: int = 1200) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
    root = Path(repo_path).resolve()
    edges_set: set[tuple[str, str]] = set()
    symbols: dict[str, list[str]] = {}

    for fpath in _iter_code_files(root):
        if len(edges_set) >= max_edges:
            break
        rel = _norm_rel(root, fpath)
        if fpath.suffix == ".py":
            symbols.setdefault(rel, _extract_python_symbols(fpath))
            targets = _python_import_targets(fpath, root)
        else:
            symbols.setdefault(rel, _extract_js_symbols(fpath))
            targets = _js_import_targets(fpath, root)

        for t in targets:
            if len(edges_set) >= max_edges:
                break
            tr = _norm_rel(root, t)
            if tr != rel:
                edges_set.add((rel, tr))

    return sorted(edges_set), symbols


def merge_edges_with_llm_modules(
    static_edges: list[tuple[str, str]],
    modules: list[dict],
) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []

    def add_edge(src: str, tgt: str, idx: int, kind: str) -> None:
        src = src.replace("\\", "/")
        tgt = tgt.replace("\\", "/")
        key = (src, tgt)
        if key in seen or src == tgt:
            return
        seen.add(key)
        out.append({"id": f"e-{idx}", "source": src, "target": tgt, "kind": kind})

    idx = 0
    for src, tgt in static_edges:
        add_edge(src, tgt, idx, "static_import")
        idx += 1

    node_paths = {str(m.get("path", "")).replace("\\", "/") for m in modules if isinstance(m, dict) and m.get("path")}
    for mod in modules:
        if not isinstance(mod, dict):
            continue
        src = str(mod.get("path", "")).replace("\\", "/")
        if not src:
            continue
        for dep in mod.get("depends_on") or []:
            if not dep:
                continue
            tgt = str(dep).replace("\\", "/")
            if tgt in node_paths:
                add_edge(src, tgt, idx, "llm_inferred")
                idx += 1

    return out


def enrich_modules_with_symbols(modules: list[dict], symbols: dict[str, list[str]]) -> None:
    key_map = {k.replace("\\", "/"): v for k, v in symbols.items()}
    for mod in modules:
        if not isinstance(mod, dict):
            continue
        p = str(mod.get("path", "")).replace("\\", "/")
        if not p:
            continue
        syms = key_map.get(p)
        if syms:
            mod.setdefault("key_symbols", syms)
