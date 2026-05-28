import time

import aiosqlite


async def init_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT NOT NULL,
                turn_index       INTEGER NOT NULL,
                role             TEXT NOT NULL,
                content          TEXT NOT NULL,
                created_at       REAL NOT NULL,
                PRIMARY KEY (conversation_id, turn_index)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_id
            ON conversations(conversation_id, turn_index DESC)
        """)
        await db.commit()


class MemoryTool:
    name = "memory_recall"

    def __init__(self, sqlite_path: str, max_turns: int = 20):
        self.sqlite_path = sqlite_path
        self.max_turns = max_turns

    def openai_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Recall previous messages or notes from this conversation's memory. "
                    "Returns the most recent stored turns."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conversation_id": {
                            "type": "string",
                            "description": "The conversation identifier",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max number of turns to return",
                            "default": 10,
                        },
                    },
                    "required": ["conversation_id"],
                },
            },
        }

    async def execute(self, conversation_id: str, limit: int = 10) -> str:
        rows = await self.get_turns(conversation_id, limit)
        if not rows:
            return "No memory found for this conversation."
        return "\n---\n".join(f"{role.upper()}: {content}" for role, content in rows)

    async def get_turns(self, conversation_id: str, limit: int = None) -> list[tuple]:
        n = limit or self.max_turns
        async with aiosqlite.connect(self.sqlite_path) as db:
            cursor = await db.execute(
                """
                SELECT role, content FROM conversations
                WHERE conversation_id = ?
                ORDER BY turn_index ASC
                LIMIT ?
                """,
                (conversation_id, n),
            )
            return await cursor.fetchall()

    async def append_turn(self, conversation_id: str, role: str, content: str):
        async with aiosqlite.connect(self.sqlite_path) as db:
            cursor = await db.execute(
                "SELECT COALESCE(MAX(turn_index), -1) + 1 FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = await cursor.fetchone()
            next_index = row[0]

            await db.execute(
                "INSERT INTO conversations VALUES (?, ?, ?, ?, ?)",
                (conversation_id, next_index, role, content, time.time()),
            )

            # Prune old turns beyond max_turns
            await db.execute(
                """
                DELETE FROM conversations
                WHERE conversation_id = ?
                  AND turn_index < (
                    SELECT MAX(turn_index) - ? + 1
                    FROM conversations WHERE conversation_id = ?
                  )
                """,
                (conversation_id, self.max_turns, conversation_id),
            )
            await db.commit()
