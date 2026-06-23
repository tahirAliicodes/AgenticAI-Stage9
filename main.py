import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents1.thesupervisor_agent1 import Supervisor
from models1.messages1 import AgentMessage
from rich.console import Console
from fastapi.middleware.cors import CORSMiddleware
from tracer.tracer import Tracer
from tracer.storage import save_trace, load_all_traces
from tracer.token_counter import count_response

app = FastAPI(title="Stage 7 — Human-in-the-Loop")
console = Console()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
supervisor = Supervisor()

class UserQuery(BaseModel):
    query: str

@app.post("/orchestrate")
async def orchestrate(request: UserQuery):
    tracer = Tracer(task=request.query)

    tracer.start_span("supervisor")
    msg = AgentMessage(
        from_agent="user",
        to_agent="supervisor",
        task=request.query
    )
    result = await supervisor.run(msg)
    tokens_out = count_response(result.result or "")
    tracer.end_span("supervisor", tokens_in=50, tokens_out=tokens_out)

    trace = tracer.finish()
    save_trace(trace)

    return {
        "query": request.query,
        "success": result.success,
        "result": result.result,
        "agent": result.agent_name,
        "trace_id": trace.trace_id
    }

@app.get("/orchestrate/stream")
async def orchestrate_stream(query: str):
    return StreamingResponse(
        supervisor.stream_orchestrate(query),
        media_type="text/event-stream"
    )

@app.post("/approve/{agent_name}")
async def approve_agent(agent_name: str):
    supervisor.gate.approve(agent_name)
    return {"agent": agent_name, "decision": "approved"}

@app.post("/reject/{agent_name}")
async def reject_agent(agent_name: str):
    supervisor.gate.reject(agent_name)
    return {"agent": agent_name, "decision": "rejected"}

@app.get("/agents")
async def list_agents():
    return {"agents": list(supervisor.agents.keys()), "supervisor": "active"}
@app.get("/traces")
async def get_traces():
    traces = load_all_traces()
    return [t.model_dump(mode="json") for t in traces]

@app.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    from tracer.storage import load_trace
    trace = load_trace(trace_id)
    if not trace:
        return {"error": "trace not found"}
    return trace.model_dump(mode="json")