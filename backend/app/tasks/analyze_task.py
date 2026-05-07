import asyncio
import logging
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.pipeline.miner import mine_repo
from app.agents.plan_agent import PlanAgent
from app.agents.mimar_agent import MimarAgent
from app.agents.tarihci_agent import TarihciAgent
from app.agents.dedektif_agent import DedektifAgent
from app.agents.onboarding_agent import OnboardingAgent
from app.agents.base import AgentContext
from app.db import SessionLocal
from app.models import Analysis
from app.utils.progress import push_progress

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="analyze_repo")
def analyze_repo_task(self, analysis_id: str, repo_url: str, branch: str = "main"):
    asyncio.run(_run(analysis_id, repo_url, branch))


async def _run(analysis_id: str, repo_url: str, branch: str):
    db = SessionLocal()
    try:
        _update_status(db, analysis_id, "running")

        # 1. Mining
        repo_path, metadata = await mine_repo(analysis_id, repo_url, branch)

        ctx = AgentContext(
            analysis_id=analysis_id,
            repo_path=repo_path,
            repo_metadata=metadata,
            plan={},
            previous_outputs={},
        )

        # 2. Plan Agent
        await push_progress(analysis_id, "planning", "Plan hazırlanıyor...", 32)
        plan = await PlanAgent().run(ctx)
        ctx.plan = plan
        _save_field(db, analysis_id, "plan_output", plan)

        # 3. Skill agents sequentially (Gemini rate limit)
        agents = [
            (MimarAgent, "mimar_output", "mimar", "Mimar ajanı çalışıyor...", 45),
            (TarihciAgent, "tarihci_output", "tarihci", "Tarihçi ajanı çalışıyor...", 60),
            (DedektifAgent, "dedektif_output", "dedektif", "Dedektif ajanı çalışıyor...", 75),
        ]
        for agent_cls, field, stage, msg, pct in agents:
            await push_progress(analysis_id, stage, msg, pct)
            try:
                output = await agent_cls().run(ctx)
                ctx.previous_outputs[agent_cls.name] = output
                _save_field(db, analysis_id, field, output)
            except Exception as e:
                logger.error(f"{agent_cls.name} failed: {e}")
                _save_field(db, analysis_id, field, {"error": str(e), "status": "failed"})

        # 4. Onboarding (stretch)
        await push_progress(analysis_id, "onboarding", "Yol haritası yazılıyor...", 88)
        try:
            onboarding = await OnboardingAgent().run(ctx)
            _save_field(db, analysis_id, "onboarding_output", onboarding)
        except Exception as e:
            logger.warning(f"Onboarding agent failed: {e}")

        # 5. Done
        await push_progress(analysis_id, "done", "Analiz tamamlandı!", 100)
        _mark_done(db, analysis_id)

    except Exception as e:
        logger.exception(f"Analysis {analysis_id} failed: {e}")
        await push_progress(analysis_id, "error", f"Hata: {e}", 0)
        _mark_failed(db, analysis_id, str(e))
    finally:
        db.close()


def _update_status(db, analysis_id: str, status: str):
    db.query(Analysis).filter(Analysis.id == analysis_id).update({"status": status})
    db.commit()


def _save_field(db, analysis_id: str, field: str, value: dict):
    db.query(Analysis).filter(Analysis.id == analysis_id).update({field: value})
    db.commit()


def _mark_done(db, analysis_id: str):
    db.query(Analysis).filter(Analysis.id == analysis_id).update(
        {"status": "done", "completed_at": datetime.utcnow()}
    )
    db.commit()


def _mark_failed(db, analysis_id: str, error: str):
    db.query(Analysis).filter(Analysis.id == analysis_id).update(
        {"status": "failed", "error": error, "completed_at": datetime.utcnow()}
    )
    db.commit()
