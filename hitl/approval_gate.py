import asyncio

class ApprovalGate:
    def __init__(self):
        self._events: dict[str, asyncio.Event] = {}
        self._decisions: dict[str, bool] = {}

    def register(self, agent_name: str):
        self._events[agent_name] = asyncio.Event()
        self._decisions[agent_name] = False

    async def wait_for_approval(self, agent_name: str) -> bool:
        await self._events[agent_name].wait()
        return self._decisions[agent_name]

    def approve(self, agent_name: str):
        self._decisions[agent_name] = True
        self._events[agent_name].set()

    def reject(self, agent_name: str):
        self._decisions[agent_name] = False
        self._events[agent_name].set()

    def reset(self, agent_name: str):
        self._events[agent_name] = asyncio.Event()
        self._decisions[agent_name] = False