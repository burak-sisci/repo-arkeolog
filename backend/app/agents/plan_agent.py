import json
from app.agents.base import BaseAgent, AgentContext
from app.llm.cerebras import cerebras_client as gemini_client

SYSTEM_PROMPT = """Sen bir senior yazılım mimarısın. Görevin: verilen repo metadata'sına bakarak,
3 uzman ajanın (Mimar, Tarihçi, Dedektif) yapacağı analizleri planlamak.

Çıktın saf JSON olmalı, şu yapıda:
{
  "summary": "Bu repo X teknolojisiyle yazılmış Y türünde bir projedir.",
  "agent_plan": {
    "mimar": {
      "sub_tasks": ["...", "..."],
      "focus_areas": ["src/auth", "src/api"],
      "expected_output": "..."
    },
    "tarihci": {
      "sub_tasks": ["..."],
      "interesting_periods": ["last_6_months", "initial_commits"]
    },
    "dedektif": {
      "sub_tasks": ["..."],
      "priority_checks": ["security", "dead_code"]
    }
  },
  "estimated_complexity": "low|medium|high"
}

Sadece JSON dön, başka metin yazma."""


class PlanAgent(BaseAgent):
    name = "planning"

    async def run(self, ctx: AgentContext) -> dict:
        await self.emit(ctx, "Plan ajanı repo'yu inceliyor...", 33)
        user_prompt = json.dumps(ctx.repo_metadata, ensure_ascii=False, indent=2)
        result = await gemini_client.generate_json(SYSTEM_PROMPT, user_prompt)
        await self.emit(ctx, "Plan tamamlandı.", 40)
        return result
