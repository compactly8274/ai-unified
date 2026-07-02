from __future__ import annotations

import json
import time
from typing import Any

import httpx


class PaperlessTool:
    name = "paperless_search"

    def __init__(
        self,
        base_url: str,
        api_token: str,
        max_results: int = 10,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.max_results = max_results
        self._client = http_client

    def openai_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Search documents in Paperless-NGX. "
                    "Can search by title, content, tag, correspondent, or document type. "
                    "Use document_id to fetch the full content of a specific document."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Full-text search query",
                        },
                        "tag": {
                            "type": "string",
                            "description": "Filter by tag name (optional)",
                        },
                        "correspondent": {
                            "type": "string",
                            "description": "Filter by correspondent name (optional)",
                        },
                        "document_id": {
                            "type": "integer",
                            "description": "Fetch a specific document by ID (optional)",
                        },
                    },
                    "required": [],
                },
            },
        }

    async def execute(
        self,
        query: str = "",
        tag: str | None = None,
        correspondent: str | None = None,
        document_id: int | None = None,
    ) -> str:
        if not self.base_url or not self.api_token:
            return "Paperless-NGX is not configured (missing PAPERLESS_BASE_URL or PAPERLESS_API_TOKEN)."

        headers = {"Authorization": f"Token {self.api_token}"}

        if self._client:
            client = self._client
            should_close = False
        else:
            client = httpx.AsyncClient(timeout=15.0)
            should_close = True

        try:
            if document_id is not None:
                resp = await client.get(
                    f"{self.base_url}/api/documents/{document_id}/",
                    headers=headers,
                    timeout=15.0,
                )
                resp.raise_for_status()
                return self._format_single_doc(resp.json())

            params: dict[str, Any] = {"page_size": self.max_results}
            if query:
                params["query"] = query
            if tag:
                params["tags__name__icontains"] = tag
            if correspondent:
                params["correspondent__name__icontains"] = correspondent

            resp = await client.get(
                f"{self.base_url}/api/documents/",
                headers=headers,
                params=params,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
        finally:
            if should_close:
                await client.aclose()

        docs = data.get("results", [])
        if not docs:
            return "No documents found matching your criteria."

        lines = [f"Found {data.get('count', len(docs))} documents:\n"]
        for doc in docs:
            lines.append(
                f"- [ID {doc['id']}] {doc.get('title', 'Untitled')} "
                f"(created: {doc.get('created', 'unknown')}, "
                f"correspondent: {doc.get('correspondent', 'none')})"
            )
        return "\n".join(lines)

    def _format_single_doc(self, doc: dict) -> str:
        content = (doc.get("content") or "")[:3000]
        return (
            f"Document ID: {doc['id']}\n"
            f"Title: {doc.get('title', 'Untitled')}\n"
            f"Created: {doc.get('created', 'unknown')}\n"
            f"Correspondent: {doc.get('correspondent', 'N/A')}\n"
            f"Tags: {', '.join(str(t) for t in doc.get('tags', []))}\n\n"
            f"Content:\n{content}"
        )