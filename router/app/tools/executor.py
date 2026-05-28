import json

from .registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute_all(self, tool_calls: list[dict]) -> list[dict]:
        results = []
        for tc in tool_calls:
            # Ollama format: {"function": {"name": ..., "arguments": {...}}}
            # OpenAI format adds "id" and arguments is a JSON string
            func = tc.get("function", tc)
            name = func.get("name", "")
            arguments = func.get("arguments", {})

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            tool_call_id = tc.get("id", f"call_{name}_{id(tc)}")
            result_content = await self.registry.execute(name, arguments)

            results.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_content,
            })

        return results
