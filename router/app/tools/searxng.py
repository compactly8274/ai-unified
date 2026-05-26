import httpx


class SearXNGTool:
    name = "web_search"

    def __init__(self, base_url: str, max_results: int = 5, categories: list = None):
        self.base_url = base_url.rstrip("/")
        self.max_results = max_results
        self.categories = categories or ["general"]

    def openai_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Search the web using SearXNG. Returns titles, URLs, and snippets. "
                    "Use for current events, facts, or anything requiring live data."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (1-10)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    async def execute(self, query: str, num_results: int = None) -> str:
        n = min(num_results or self.max_results, 10)
        params = {
            "q": query,
            "format": "json",
            "categories": ",".join(self.categories),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])[:n]
        if not results:
            return "No results found."

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   URL: {r.get('url', '')}\n"
                f"   {r.get('content', '')}"
            )
        return "\n\n".join(lines)
