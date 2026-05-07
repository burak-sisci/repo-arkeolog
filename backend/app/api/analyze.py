import hashlib
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.db import get_db
from app.models import Analysis
from app.schemas import AnalyzeRequest, AnalyzeResponse, AnalysisResult
from app.utils.github import validate_repo_url, get_repo_size_mb

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def start_analysis(req: AnalyzeRequest, db: Session = Depends(get_db)):
    repo_url = str(req.repo_url).rstrip("/")

    # Validate URL format and repo existence
    repo_info = await validate_repo_url(repo_url)
    if repo_info.get("private"):
        raise HTTPException(
            status_code=401,
            detail="Demo modunda yalnızca public repo destekleniyor.",
        )
    if repo_info.get("not_found"):
        raise HTTPException(status_code=404, detail="Repo bulunamadı.")

    # Size check — GitHub size_kb tüm history+LFS toplamı; smart clone ile çoğu atlanır.
    size_mb = repo_info.get("size_kb", 0) / 1024
    HARD_LIMIT_MB = 2048  # 2 GB tavan
    if size_mb > HARD_LIMIT_MB:
        raise HTTPException(
            status_code=413,
            detail=f"Repo çok büyük ({size_mb:.0f}MB). Üst sınır {HARD_LIMIT_MB}MB.",
        )

    # Language check — chunker'ın tanıdığı diller
    primary_lang = (repo_info.get("language") or "").lower()
    supported = {
        "python", "javascript", "typescript",
        "java", "go", "rust",
        "c", "c++", "cpp", "c#", "csharp",
        "ruby", "php",
    }
    if primary_lang and primary_lang not in supported:
        # Sert reddetme yerine uyarı: alt dosyalar yine de chunklanabilir
        logger.info(f"Primary language '{primary_lang}' tam desteklenmiyor; alt diller varsa devam edilecek.")

    # Branch'i çöz: kullanıcı varsayılanı 'main' gönderiyorsa repo'nun gerçek default'una geç.
    default_branch = repo_info.get("default_branch") or "main"
    effective_branch = req.branch if req.branch and req.branch != "main" else default_branch

    # Cache check — same repo+branch
    repo_hash = hashlib.sha256(f"{repo_url}:{effective_branch}".encode()).hexdigest()[:64]
    cached = (
        db.query(Analysis)
        .filter(Analysis.repo_hash == repo_hash, Analysis.status == "done")
        .order_by(Analysis.created_at.desc())
        .first()
    )
    if cached:
        return AnalyzeResponse(analysis_id=cached.id, status="done", cached=True)

    # Create new analysis record
    analysis = Analysis(
        repo_url=repo_url,
        repo_hash=repo_hash,
        status="pending",
        progress={},
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Enqueue Celery task
    from app.tasks.analyze_task import analyze_repo_task
    analyze_repo_task.delay(analysis.id, repo_url, effective_branch)

    return AnalyzeResponse(analysis_id=analysis.id, status="pending")


@router.get("/analysis/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı.")

    results = None
    if analysis.status == "done":
        results = {
            "summary": analysis.plan_output,
            "architecture_graph": _to_cytoscape(analysis.mimar_output),
            "mimar": analysis.mimar_output,
            "timeline": analysis.tarihci_output,
            "health_report": analysis.dedektif_output,
            "onboarding_guide": analysis.onboarding_output,
        }

    return AnalysisResult(
        analysis_id=analysis.id,
        status=analysis.status,
        repo_url=analysis.repo_url,
        progress=analysis.progress or {},
        results=results,
        error=analysis.error,
        created_at=analysis.created_at.isoformat(),
        completed_at=analysis.completed_at.isoformat() if analysis.completed_at else None,
    )


def _to_cytoscape(mimar_output: dict | None) -> dict:
    if not mimar_output or "modules" not in mimar_output:
        return {"nodes": [], "edges": []}

    nodes = []
    edges = []
    for mod in mimar_output.get("modules", []):
        nodes.append({"data": {"id": mod["path"], "label": mod["path"].split("/")[-1], "purpose": mod.get("purpose", "")}})
        for dep in mod.get("depends_on", []):
            edges.append({"data": {"source": mod["path"], "target": dep}})

    return {"nodes": nodes, "edges": edges}
