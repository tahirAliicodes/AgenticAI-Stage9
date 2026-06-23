import asyncio
from ollama import Client

client = Client()

class Evaluator:
    def __init__(self):
        self.model = "llama3.1"

    def _build_prompt(self, task: str, output: str) -> str:
        return f"""You are a HARSH critic. Be strict. Most responses deserve 5-6.
    Only give 8+ if the response is exceptional.
    Give 3-4 if it's vague or generic.
    Penalize heavily for: missing specifics, vague language, no concrete examples.

    Task given to agent:
    {task}

    Agent output:
    {output}

    Evaluate on:
    1. Relevance — did it answer the task?
    2. Accuracy — does it seem factual?
    3. Conciseness — is it to the point?

    Respond ONLY in this exact JSON format:
    {{
      "score": <number 1-10>,
      "reason": "<one sentence explanation>"
    }}"""

    def _evaluate(self, task: str, output: str) -> dict:
        prompt = self._build_prompt(task, output)
        response = client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.message.content.strip()

        try:
            import json
            clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
            print(f"EVA RAW: {raw}")
            print(f"EVA CLEAN: {clean}")
            return json.loads(clean)
        except Exception as e:
            print(f"EVA PARSE ERROR: {e}")
            print(f"EVA RAW WAS: {raw}")
            return {"score": 0, "reason": "Evaluation parsing failed"}
    async def evaluate(self, task: str, output: str) -> dict:
        return await asyncio.to_thread(self._evaluate, task, output)