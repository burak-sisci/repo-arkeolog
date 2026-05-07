from abc import ABC, abstractmethod
from pydantic import BaseModel
from app.utils.progress import push_progress


class AgentContext(BaseModel):
    analysis_id: str
    repo_path: str
    repo_metadata: dict
    plan: dict
    previous_outputs: dict

    class Config:
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, ctx: AgentContext) -> dict:
        """Ajan ana mantığı. Hata durumunda exception fırlatır."""
        ...

    async def emit(self, ctx: AgentContext, message: str, pct: int):
        await push_progress(ctx.analysis_id, self.name, message, pct)
