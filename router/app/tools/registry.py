from .memory import MemoryTool
from .paperless import PaperlessTool
from .searxng import SearXNGTool


class ToolRegistry:
    def __init__(self, tools: list):
        self._tools = {t.name: t for t in tools}

    def get_openai_definitions(self) -> list[dict]:
        return [t.openai_definition() for t in self._tools.values()]

    async def execute(self, tool_name: str, arguments: dict) -> str:
        tool = self._tools.get(tool_name)
        if tool is None:
            return f"Error: unknown tool '{tool_name}'"
        try:
            return await tool.execute(**arguments)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"


def build_tool_registry(tools_config: dict, settings) -> ToolRegistry:
    tc = tools_config.get("tools", {})
    tools = []

    if tc.get("searxng", {}).get("enabled", True):
        cfg = tc.get("searxng", {})
        tools.append(SearXNGTool(
            base_url=settings.searxng_base_url,
            max_results=cfg.get("max_results", 5),
            categories=cfg.get("categories", ["general"]),
        ))

    if tc.get("paperless", {}).get("enabled", True):
        cfg = tc.get("paperless", {})
        tools.append(PaperlessTool(
            base_url=settings.paperless_base_url,
            api_token=settings.paperless_api_token,
            max_results=cfg.get("max_results", 10),
        ))

    if tc.get("memory", {}).get("enabled", True):
        tools.append(MemoryTool(
            sqlite_path=settings.sqlite_path,
            max_turns=settings.memory_max_turns,
        ))

    return ToolRegistry(tools)
