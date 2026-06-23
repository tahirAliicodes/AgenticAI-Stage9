import asyncio
import json
from agents1.base_agent1 import BaseAgent
from agents1.reasearch_agent1 import ResearchAgent
from agents1.analysis_agent1 import AnalysisAgent
from agents1.writer_agent1 import WriterAgent
from models1.messages1 import AgentMessage, AgentResult, SupervisorPlan
from hitl.approval_gate import ApprovalGate
from eva.eva import Evaluator
from rich.console import Console
from rich.panel import Panel
from tracer.tracer import Tracer
from tracer.storage import save_trace
from tracer.token_counter import count_response
console = Console()


class Supervisor(BaseAgent):
    def __init__(self):
        super().__init__(name="supervisor")
        self.agents = {
            "research": ResearchAgent(),
            "analysis": AnalysisAgent(),
            "writer": WriterAgent(),
        }
        self.gate = ApprovalGate()
        self.evaluator = Evaluator()

    def _build_system_prompt(self) -> str:
        return """You are a supervisor agent that coordinates a team of specialists.
Available agents:
- research: searches the web and finds facts
- analysis: critiques, compares, and reasons about information
- writer: produces polished final responses

Your job: given a user query, decide which agents are needed and in what order.
Respond ONLY with valid JSON matching this schema:
{
  "reasoning": "why you chose these agents",
  "agents_needed": ["research", "analysis", "writer"],
  "tasks": {
    "research": "specific instruction for research agent",
    "analysis": "specific instruction for analysis agent",
    "writer": "specific instruction for writer agent"
  },
  "final_synthesis_needed": true
}

Be minimal. Only add agents that are strictly necessary.
- Simple creative tasks (poems, jokes, rewrites) → writer only
- Factual questions → research + writer
- Complex analysis → research + analysis + writer

Only include agents that are actually needed."""

    async def run(self, message: AgentMessage) -> AgentResult:

        user_query = message.task
        console.print(Panel(f"[bold yellow]Supervisor received:[/bold yellow] {user_query}"))

        plan = await self._plan(user_query)
        console.print(f"[bold yellow][Supervisor][/bold yellow] Plan: {plan.agents_needed}")
        console.print(f"[dim]Reasoning: {plan.reasoning}[/dim]")

        results: dict[str, AgentResult] = {}
        accumulated_context = ""

        for agent_name in plan.agents_needed:
            agent = self.agents[agent_name]
            task_instruction = plan.tasks.get(agent_name, user_query)

            msg = AgentMessage(
                from_agent="supervisor",
                to_agent=agent_name,
                task=task_instruction,
                payload={
                    "context": accumulated_context,
                    "all_results": accumulated_context,
                    "original_query": user_query
                }
            )

            result = await agent.run(msg)
            results[agent_name] = result

            if result.success:
                accumulated_context += f"\n\n[{agent_name.upper()} AGENT]:\n{result.result}"
            else:
                console.print(f"[red][{agent_name}] failed: {result.error}[/red]")

        final_result = (
            results.get("writer") or
            next((r for r in reversed(list(results.values())) if r.success), None)
        )

        if not final_result:
            return AgentResult(agent_name="supervisor", task=user_query,
                               result="All agents failed to produce a result.", success=False)

        return AgentResult(agent_name="supervisor", task=user_query,
                           result=final_result.result, success=True)

    async def stream_orchestrate(self, query: str):
        yield f"data: {json.dumps({'agent': 'supervisor', 'status': 'planning', 'msg': f'Planning for: {query}'})}\n\n"
        tracer = Tracer(task=query)
        tracer.start_span("supervisor")

        plan = await self._plan(query)

        yield f"data: {json.dumps({'agent': 'supervisor', 'status': 'plan_ready', 'msg': f'Agents: {plan.agents_needed}', 'reasoning': plan.reasoning})}\n\n"

        results: dict[str, AgentResult] = {}
        accumulated_context = ""

        for agent_name in plan.agents_needed:
            agent = self.agents[agent_name]
            task_instruction = plan.tasks.get(agent_name, query)

            self.gate.register(agent_name)
            yield f"data: {json.dumps({'agent': agent_name, 'status': 'awaiting_approval', 'msg': task_instruction})}\n\n"

            approved = await self.gate.wait_for_approval(agent_name)

            if not approved:
                yield f"data: {json.dumps({'agent': agent_name, 'status': 'skipped', 'msg': 'Rejected by user'})}\n\n"
                continue

            yield f"data: {json.dumps({'agent': agent_name, 'status': 'started', 'msg': task_instruction})}\n\n"
            tracer.start_span(agent_name)

            msg = AgentMessage(
                from_agent="supervisor",
                to_agent=agent_name,
                task=task_instruction,
                payload={
                    "context": accumulated_context,
                    "all_results": accumulated_context,
                    "original_query": query
                }
            )

            result = await agent.run(msg)
            results[agent_name] = result
            self.gate.reset(agent_name)

            if result.success:
                accumulated_context += f"\n\n[{agent_name.upper()} AGENT]:\n{result.result}"
                tokens_out = count_response(result.result or "")
                tracer.end_span(agent_name, tokens_out=tokens_out, status="ok")
                eval_result = await self.evaluator.evaluate(task_instruction, result.result)
                yield f"data: {json.dumps({'agent': agent_name, 'status': 'done', 'msg': result.result[:150], 'score': eval_result['score'], 'reason': eval_result['reason']})}\n\n"
            else:
                tracer.end_span(agent_name, status="error", error=result.error)
                yield f"data: {json.dumps({'agent': agent_name, 'status': 'error', 'msg': result.error})}\n\n"

        final_result = (
            results.get("writer") or
            next((r for r in reversed(list(results.values())) if r.success), None)
        )

        # close skipped spans
        # close skipped spans
        for agent_name in plan.agents_needed:
            if agent_name not in results:
                tracer.end_span(agent_name, status="error", error="skipped by user")

        if final_result:
            tracer.end_span("supervisor", status="ok")
            trace = tracer.finish()
            save_trace(trace)
            yield f"data: {json.dumps({'agent': 'supervisor', 'status': 'final', 'msg': final_result.result})}\n\n"
        else:
            tracer.end_span("supervisor", status="error")
            trace = tracer.finish(status="error")
            save_trace(trace)
            yield f"data: {json.dumps({'agent': 'supervisor', 'status': 'error', 'msg': 'All agents failed'})}\n\n"

    async def _plan(self, query: str) -> SupervisorPlan:
        raw = await asyncio.to_thread(self._llm, query)

        try:
            clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(clean)
            return SupervisorPlan(**data)
        except Exception:
            console.print("[yellow][Supervisor] Plan parsing failed, using default.[/yellow]")
            return SupervisorPlan(
                reasoning="Fallback: couldn't parse LLM plan",
                agents_needed=["research", "writer"],
                tasks={"research": query, "writer": query}
            )