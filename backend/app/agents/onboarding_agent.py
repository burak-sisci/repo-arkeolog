"""Onboarding Ajan — 3 ajanın çıktısını sentezler, yeni geliştirici için yol haritası."""
import json
from app.agents.base import BaseAgent, AgentContext
from app.llm.cerebras import cerebras_client as gemini_client

SYSTEM_PROMPT = """Sen experienced bir tech lead'sın. Sana bir projenin mimari analizi, tarihi
ve sağlık raporu verilecek. Bu projeye yeni katılan bir geliştirici için
"ilk hafta yol haritası" hazırla.

Çıktı saf JSON:
{
  "intro": "Bu projeye hoş geldin! Burası X yapan bir Y projesi.",
  "day_1": ["README oku", "Şu modülü incele: ..."],
  "day_2": ["..."],
  "day_3": ["..."],
  "first_pr_suggestion": {
    "title": "...",
    "rationale": "Bu küçük issue, kodbase'i tanıman için ideal."
  },
  "people_to_ask": [
    {"name": "Alice", "expertise": "auth modülü", "from_commits": true}
  ],
  "key_files_to_read": ["src/main.py", "README.md"],
  "things_to_avoid": ["X nedeniyle Y dosyasına dokunma"]
}

Sadece JSON dön, başka metin yazma."""


class OnboardingAgent(BaseAgent):
    name = "onboarding"

    async def run(self, ctx: AgentContext) -> dict:
        await self.emit(ctx, "Onboarding ajanı yol haritası hazırlıyor...", 89)

        user_prompt = json.dumps(
            {
                "metadata": ctx.repo_metadata,
                "architecture": ctx.previous_outputs.get("mimar", {}),
                "history": ctx.previous_outputs.get("tarihci", {}),
                "health": ctx.previous_outputs.get("dedektif", {}),
                "plan_summary": ctx.plan.get("summary", ""),
            },
            ensure_ascii=False,
            indent=2,
        )

        result = await gemini_client.generate_json(SYSTEM_PROMPT, user_prompt)
        await self.emit(ctx, "Onboarding kılavuzu hazır.", 95)
        return result
