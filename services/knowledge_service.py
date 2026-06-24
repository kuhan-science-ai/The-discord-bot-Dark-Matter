import logging
from typing import Dict, List, Optional
import database

logger = logging.getLogger("knowledge_service")

class KnowledgeService:
    @staticmethod
    async def add_knowledge(guild_id: str, key: str, value: str, updated_by: str) -> None:
        """Adds or updates a server-specific knowledge item."""
        query = """
            INSERT INTO server_knowledge (guild_id, key, value, updated_by, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id, key) DO UPDATE SET
                value = excluded.value,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
        """
        key_normalized = key.strip().lower()
        await database.execute(query, (guild_id, key_normalized, value.strip(), updated_by))
        logger.info(f"Updated server knowledge key '{key_normalized}' for guild {guild_id} by {updated_by}")

    @staticmethod
    async def remove_knowledge(guild_id: str, key: str) -> bool:
        """Removes a server knowledge key. Returns True if a record was deleted, False otherwise."""
        key_normalized = key.strip().lower()
        row = await database.fetchone(
            "SELECT id FROM server_knowledge WHERE guild_id = ? AND key = ?",
            (guild_id, key_normalized)
        )
        if not row:
            return False
            
        await database.execute(
            "DELETE FROM server_knowledge WHERE guild_id = ? AND key = ?",
            (guild_id, key_normalized)
        )
        logger.info(f"Removed server knowledge key '{key_normalized}' for guild {guild_id}")
        return True

    @staticmethod
    async def list_knowledge(guild_id: str) -> List[Dict[str, str]]:
        """Lists all stored knowledge items for a guild."""
        rows = await database.fetchall(
            "SELECT key, value, updated_by, updated_at FROM server_knowledge WHERE guild_id = ? ORDER BY key ASC",
            (guild_id,)
        )
        return [{"key": r["key"], "value": r["value"], "updated_by": r["updated_by"], "updated_at": r["updated_at"]} for r in rows]

    @staticmethod
    async def get_all_knowledge_context(guild_id: str) -> str:
        """Fetches and formats all knowledge items into a single context string for Gemini."""
        rows = await KnowledgeService.list_knowledge(guild_id)
        if not rows:
            return "No specific server knowledge recorded yet."
            
        context_parts = []
        for r in rows:
            context_parts.append(f"- {r['key']}: {r['value']}")
        return "\n".join(context_parts)
