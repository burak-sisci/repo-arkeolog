"""Repo klonlama, metadata çıkarma, chunk ve embed."""
from __future__ import annotations
import logging
import os
import shutil
import tempfile
from pathlib import Path

import git

from app.pipeline.chunker import chunk_repo, LANG_EXTENSIONS
from app.pipeline.embedder import embed_chunks
from app.config import settings
from app.utils.progress import push_progress

logger = logging.getLogger(__name__)


async def mine_repo(analysis_id: str, repo_url: str, branch: str = "main") -> tuple[str, dict]:
    await push_progress(analysis_id, "mining", "Repo indiriliyor (smart clone)...", 5)

    tmp_dir = tempfile.mkdtemp(prefix=f"repo_{analysis_id}_")
    # Smart clone:
    #   --depth 50         : sadece son 50 commit (Tarihçi için yeterli, history şişmez)
    #   --filter=blob:limit=1m : >1MB blob'lar (binary, LFS, doc dump) lazy fetch — disk korunur
    #   --single-branch    : sadece hedef branch
    multi_options = ["--filter=blob:limit=1m"]

    def _try_clone(target_dir: str, br: str | None, with_filter: bool):
        kwargs = dict(depth=50, single_branch=True)
        if br:
            kwargs["branch"] = br
        if with_filter:
            kwargs["multi_options"] = multi_options
        return git.Repo.clone_from(repo_url, target_dir, **kwargs)

    repo = None
    last_err: Exception | None = None
    # 1) Hedef branch + filter, 2) hedef branch + filter yok, 3) varsayılan branch (HEAD) + filter, 4) HEAD + filter yok
    attempts = [(branch, True), (branch, False), (None, True), (None, False)]
    for br, with_filter in attempts:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir = tempfile.mkdtemp(prefix=f"repo_{analysis_id}_")
        try:
            repo = _try_clone(tmp_dir, br, with_filter)
            break
        except git.exc.GitCommandError as e:
            last_err = e
            continue
    if repo is None:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"Repo klonlanamadı: {last_err}") from last_err

    await push_progress(analysis_id, "mining", "Metadata çıkarılıyor...", 10)
    metadata = _extract_metadata(repo, tmp_dir)

    await push_progress(analysis_id, "mining", "Kod parse ediliyor...", 15)
    chunks = chunk_repo(tmp_dir)

    # Çok büyük repo'larda chunk sayısını sınırla — LLM prompt patlamasını engeller.
    MAX_CHUNKS = 5000
    if len(chunks) > MAX_CHUNKS:
        logger.warning(f"Chunk sayısı {len(chunks)} → {MAX_CHUNKS}'a sınırlandırılıyor")
        # Sınıf > fonksiyon > modül önceliği, sonra kısa dosya yolları (kök yakını) önce.
        order = {"class": 0, "function": 1, "module": 2}
        chunks.sort(key=lambda c: (order.get(c.chunk_type, 3), len(c.file_path)))
        chunks = chunks[:MAX_CHUNKS]

    # Embedding adımı: yalnız QDRANT_URL set edilmişse ve Gemini key varsa çalışır.
    if settings.qdrant_url and settings.gemini_api_key:
        await push_progress(analysis_id, "mining", f"{len(chunks)} chunk embed ediliyor...", 20)
        try:
            await embed_chunks(analysis_id, chunks)
        except Exception as e:
            logger.warning(f"Embedding atlandı (chat/RAG kapanır): {e}")
    else:
        logger.info("QDRANT_URL veya GEMINI_API_KEY yok — embedding atlanıyor (chat/RAG kapalı).")

    await push_progress(analysis_id, "mining", "Kazı tamamlandı.", 30)
    return tmp_dir, metadata


def _extract_metadata(repo: git.Repo, path: str) -> dict:
    root = Path(path)
    all_files = [f for f in root.rglob("*") if f.is_file()]

    lang_counts: dict[str, int] = {}
    for f in all_files:
        lang = LANG_EXTENSIONS.get(f.suffix)
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    primary_lang = max(lang_counts, key=lambda k: lang_counts[k]) if lang_counts else "unknown"

    commits = list(repo.iter_commits())
    contributors = len(set(c.author.email for c in commits))

    frameworks = _detect_frameworks(root)

    return {
        "languages": lang_counts,
        "primary_language": primary_lang,
        "file_count": len(all_files),
        "commit_count": len(commits),
        "contributors": contributors,
        "frameworks": frameworks,
        "repo_name": Path(path).name,
        "latest_commit_sha": commits[0].hexsha if commits else "",
        "latest_commit_date": commits[0].committed_datetime.isoformat() if commits else "",
    }


def _detect_frameworks(root: Path) -> list[str]:
    frameworks = []
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:
                frameworks.append("Next.js")
            if "react" in deps:
                frameworks.append("React")
            if "express" in deps:
                frameworks.append("Express")
            if "vue" in deps:
                frameworks.append("Vue")
            if "svelte" in deps:
                frameworks.append("Svelte")
        except Exception:
            pass

    for fname in ["requirements.txt", "pyproject.toml", "setup.py"]:
        req_file = root / fname
        if req_file.exists():
            content = req_file.read_text(errors="replace").lower()
            if "fastapi" in content:
                frameworks.append("FastAPI")
            if "django" in content:
                frameworks.append("Django")
            if "flask" in content:
                frameworks.append("Flask")
            if "pytorch" in content or "torch" in content:
                frameworks.append("PyTorch")

    return list(set(frameworks))
