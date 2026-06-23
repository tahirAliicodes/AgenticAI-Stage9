# Stage9/tracer/tracer.py

from datetime import datetime
from models1.trace_models import Span, Trace


class Tracer:
    """Manages one Trace (full run) and its Spans (per agent)."""

    def __init__(self, task: str):
        self.trace = Trace(task=task)
        self._active_spans: dict[str, Span] = {}  # agent_name → open span

    def start_span(self, agent_name: str, metadata: dict = {}) -> Span:
        """Call this when an agent starts working."""
        span = Span(
            trace_id=self.trace.trace_id,
            agent_name=agent_name,
            started_at=datetime.utcnow(),
            metadata=metadata
        )
        self._active_spans[agent_name] = span
        self.trace.spans.append(span)
        print(f"[tracer] ▶ {agent_name} started")
        return span

    def end_span(
        self,
        agent_name: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        status: str = "ok",
        error: str = None
    ):
        """Call this when an agent finishes."""
        span = self._active_spans.pop(agent_name, None)
        if not span:
            print(f"[tracer] ⚠ no active span for {agent_name}")
            return

        span.tokens_in = tokens_in
        span.tokens_out = tokens_out
        span.close(status=status, error=error)
        print(f"[tracer] ■ {agent_name} done in {span.duration_ms:.0f}ms")

    def finish(self, status: str = "ok"):
        """Call this when the entire run is done."""
        self.trace.close(status=status)
        print(f"[tracer] ✅ trace {self.trace.trace_id} finished in {self.trace.total_duration_ms:.0f}ms")
        return self.trace