# Stage9/models1/trace_models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid

class Span(BaseModel):
    """One agent's work within a run."""
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str                          # which run this belongs to
    agent_name: str                        # "researcher", "writer", etc.
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None   # filled when span closes
    tokens_in: int = 0                    # prompt tokens
    tokens_out: int = 0                   # completion tokens
    status: str = "running"               # running | ok | error
    error: Optional[str] = None
    metadata: dict = Field(default_factory=dict)  # anything extra

    def close(self, status: str = "ok", error: str = None):
        self.ended_at = datetime.utcnow()
        self.duration_ms = (
            self.ended_at - self.started_at
        ).total_seconds() * 1000
        self.status = status
        if error:
            self.error = error

class Trace(BaseModel):
    """One full run — contains many spans."""
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    task: str                              # the user's original request
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    spans: list[Span] = []
    status: str = "running"               # running | ok | error
    eva_score: Optional[float] = None     # hook for your Stage8 EVA

    def close(self, status: str = "ok"):
        self.ended_at = datetime.utcnow()
        self.total_duration_ms = (
            self.ended_at - self.started_at
        ).total_seconds() * 1000
        self.status = status

    @property
    def total_tokens(self) -> int:
        return sum(s.tokens_in + s.tokens_out for s in self.spans)