import logging
import json
from typing import Any, Dict, List, Optional
import aiohttp
import config

logger = logging.getLogger("ollama_service")

class OllamaService:
    def __init__(self) -> None:
        """Initializes the Ollama local service."""
        self.model_name = config.OLLAMA_MODEL
        self.url = config.OLLAMA_URL

    async def generate_response(
        self,
        system_instruction: str,
        history: List[Dict[str, str]],
        prompt: str,
        timeout: float = 60.0
    ) -> str:
        """Generates response using local Ollama instance."""
        messages = [{"role": "system", "content": system_instruction}]
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "options": {
                            "temperature": 0.7
                        },
                        "stream": False
                    },
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["message"]["content"]
                    else:
                        logger.error(f"Ollama returned HTTP status {response.status}")
                        return "i'm having trouble thinking straight rn, local ai returned an error"
        except Exception as e:
            logger.error(f"Failed to query local Ollama: {e}", exc_info=True)
            return "my local processors are offline, is ollama running?"

    async def extract_memories(self, conversation_transcript: str) -> Optional[Dict[str, str]]:
        """Extracts long term memory attributes using local Ollama instance."""
        prompt = f"""
Analyze the following conversation transcript between a Discord user and the AI assistant (Nova).
Extract relevant personal details and summaries about the user.

Conversation Transcript:
{conversation_transcript}

Return the results ONLY as a valid JSON object. Do not include markdown codeblocks or backticks. 
Strictly use the following keys:
- "interests": specific topics the user is interested in (comma separated or empty)
- "hobbies": activities/hobbies the user mentions (comma separated or empty)
- "preferences": user's stylistic or usage preferences (comma separated or empty)
- "frequently_discussed": topics discussed multiple times (comma separated or empty)
- "summary": a brief 1-2 sentence description summarizing the relationship/rapport with this user
"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "format": "json",  # Force Ollama to output valid JSON
                        "options": {
                            "temperature": 0.2
                        },
                        "stream": False
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return json.loads(result["response"])
        except Exception as e:
            logger.error(f"Failed to extract memories from Ollama: {e}", exc_info=True)
        return None

    async def consolidate_memories(
        self,
        nickname: str,
        username: str,
        existing_memories: Dict[str, Any],
        transcript: str
    ) -> Optional[Dict[str, str]]:
        """Consolidates old memories and new transcript using local Ollama instance."""
        prompt = f"""
You are a memory consolidation agent for the AI Bot "{config.BOT_NAME}".
Your job is to update the long-term memories for user: {nickname} (username: {username}).

Existing memories:
- Interests: {existing_memories.get('interests', '')}
- Hobbies: {existing_memories.get('hobbies', '')}
- Preferences: {existing_memories.get('preferences', '')}
- Frequently Discussed: {existing_memories.get('frequently_discussed', '')}
- Summary: {existing_memories.get('summary', '')}

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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "format": "json",  # Force Ollama to output valid JSON
                        "options": {
                            "temperature": 0.2
                        },
                        "stream": False
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return json.loads(result["response"])
        except Exception as e:
            logger.error(f"Failed to consolidate memories with Ollama: {e}", exc_info=True)
        return None

