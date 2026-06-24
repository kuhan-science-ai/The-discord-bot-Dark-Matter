import logging
import json
from typing import Any, Dict, List, Optional
from google.genai import types
import database

logger = logging.getLogger("memory_service")

class MemoryService:
    @staticmethod
    async def get_or_create_user(user_id: str, username: str, nickname: Optional[str] = None) -> Dict[str, Any]:
        """Ensures the user and their corresponding memory profile exists in the database."""
        try:
            user = await database.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
            if not user:
                await database.execute(
                    "INSERT INTO users (user_id, username, nickname) VALUES (?, ?, ?)",
                    (user_id, username, nickname)
                )
                await database.execute(
                    "INSERT INTO user_memories (user_id) VALUES (?)",
                    (user_id,)
                )
                logger.info(f"Registered new user {username} ({user_id}) and created memory slot.")
            else:
                # Keep nickname synchronized
                if nickname != user["nickname"]:
                    await database.execute(
                        "UPDATE users SET nickname = ? WHERE user_id = ?",
                        (nickname, user_id)
                    )
            
            return await MemoryService.get_user_profile_context(user_id)
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_user_profile_context(user_id: str) -> Dict[str, Any]:
        """Retrieves user details alongside their long-term memories."""
        query = """
            SELECT u.user_id, u.username, u.nickname, u.first_seen,
                   m.interests, m.hobbies, m.preferences, m.frequently_discussed, m.summary
            FROM users u
            LEFT JOIN user_memories m ON u.user_id = m.user_id
            WHERE u.user_id = ?
        """
        row = await database.fetchone(query, (user_id,))
        return row if row else {}

    @staticmethod
    async def add_to_conversation_history(channel_id: str, user_id: str, role: str, content: str) -> None:
        """Appends a single dialogue message (from user or model) to the channel's short-term history."""
        await database.execute(
            "INSERT INTO conversation_history (channel_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (channel_id, user_id, role, content)
        )

    @staticmethod
    async def get_conversation_history(channel_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieves the latest messages from channel history, sorted chronologically."""
        query = """
            SELECT user_id, role, content, timestamp 
            FROM conversation_history 
            WHERE channel_id = ? 
            ORDER BY id DESC 
            LIMIT ?
        """
        rows = await database.fetchall(query, (channel_id, limit))
        rows.reverse()
        return rows

    @staticmethod
    async def clear_conversation_history(channel_id: str) -> None:
        """Deletes all short-term conversation logs for a channel."""
        await database.execute("DELETE FROM conversation_history WHERE channel_id = ?", (channel_id,))

    @staticmethod
    async def clear_user_memory(user_id: str) -> None:
        """Clears long-term profile data for a specific user."""
        await database.execute(
            """
            UPDATE user_memories 
            SET interests = '', hobbies = '', preferences = '', frequently_discussed = '', summary = '', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (user_id,)
        )
        logger.info(f"Cleared long-term memory for user {user_id}")

    @staticmethod
    async def consolidate_memories(
        channel_id: str,
        user_id: str,
        username: str,
        nickname: str,
        gemini_service: Any
    ) -> None:
        """
        Triggers memory update by passing short-term transcript to Gemini to extract interests/summaries,
        updating long-term storage and pruning old records to manage size.
        """
        try:
            # Fetch message transcript for consolidation
            history = await database.fetchall(
                "SELECT role, content FROM conversation_history WHERE channel_id = ? AND user_id = ? ORDER BY id ASC",
                (channel_id, user_id)
            )
            
            # Require at least 20 messages to consolidate
            if len(history) < 20:
                return
                
            mem = await MemoryService.get_user_profile_context(user_id)
            if not mem:
                return

            transcript_lines = []
            for h in history:
                speaker = nickname if h["role"] == "user" else "Nova"
                transcript_lines.append(f"{speaker}: {h['content']}")
            transcript = "\n".join(transcript_lines)

            prompt = f"""
You are a memory consolidation agent for the AI Bot "Nova".
Your job is to update the long-term memories for user: {nickname} (username: {username}).

Existing memories:
- Interests: {mem.get('interests', '')}
- Hobbies: {mem.get('hobbies', '')}
- Preferences: {mem.get('preferences', '')}
- Frequently Discussed: {mem.get('frequently_discussed', '')}
- Summary: {mem.get('summary', '')}

Recent Chat Logs:
{transcript}

Analyze the logs. Merge any new information into the existing categories. Deduplicate entry lists.
Update the relationship summary to capture new bonding or facts.
Return the results ONLY as a valid JSON object. Do not include markdown codeblocks or backticks. 
Use these exact keys:
- "interests": updated comma-separated list of interests (or empty)
- "hobbies": updated comma-separated list of hobbies (or empty)
- "preferences": updated comma-separated list of preferences (or empty)
- "frequently_discussed": updated comma-separated list of frequently discussed topics (or empty)
- "summary": updated 1-2 sentence relationship summary
"""
            config_args = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=512,
                response_mime_type="application/json"
            )
            
            response = await gemini_service.client.aio.models.generate_content(
                model=gemini_service.model_name,
                contents=prompt,
                config=config_args
            )
            
            if response.text:
                # Sanitize markdown code blocks if the model wrapped the JSON output
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

                try:
                    data = json.loads(raw_text)
                    await database.execute(
                        """
                        UPDATE user_memories
                        SET interests = ?, hobbies = ?, preferences = ?, frequently_discussed = ?, summary = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                        """,
                        (
                            data.get("interests", ""),
                            data.get("hobbies", ""),
                            data.get("preferences", ""),
                            data.get("frequently_discussed", ""),
                            data.get("summary", ""),
                            user_id
                        )
                    )
                    logger.info(f"Consolidated and updated memories for user {username} ({user_id}).")
                except json.JSONDecodeError as je:
                    logger.error(f"Incomplete or malformed JSON returned during memory consolidation: {je}. Raw output: {raw_text}")
                
                # Prune history to avoid database bloat and token waste
                all_ids = await database.fetchall(
                    "SELECT id FROM conversation_history WHERE channel_id = ? ORDER BY id DESC",
                    (channel_id,)
                )
                if len(all_ids) > 15:
                    keep_ids = [str(r["id"]) for r in all_ids[:15]]
                    placeholders = ", ".join("?" for _ in keep_ids)
                    await database.execute(
                        f"DELETE FROM conversation_history WHERE channel_id = ? AND id NOT IN ({placeholders})",
                        (channel_id, *keep_ids)
                    )
                    logger.info(f"Pruned message history for channel {channel_id}, kept {len(keep_ids)} records.")
        except Exception as e:
            logger.error(f"Error consolidating memory for {user_id}: {e}", exc_info=True)
