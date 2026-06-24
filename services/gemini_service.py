import asyncio
import logging
import json
from typing import Any, Dict, List, Optional
import aiohttp
import config

# Import google client conditionally to avoid errors if API keys are missing on local mode
if config.AI_PROVIDER == "gemini":
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
else:
    genai = None
    types = None
    APIError = Exception

logger = logging.getLogger("gemini_service")

class GeminiService:
    def __init__(self) -> None:
        """Initializes the AI client based on the provider configuration."""
        if config.AI_PROVIDER == "gemini":
            self.client = genai.Client(api_key=config.GEMINI_API_KEY)
            self.model_name = "gemini-2.5-flash"
        else:
            self.client = None
            self.model_name = config.OLLAMA_MODEL

    async def generate_response(
        self,
        system_instruction: str,
        history: List[Dict[str, str]],
        prompt: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        initial_backoff: float = 2.0
    ) -> str:
        """Generates response using the configured AI provider (Gemini or Ollama)."""
        if config.AI_PROVIDER == "gemini":
            # Convert short term database history to SDK structures
            contents = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )
            
            # Append latest user input
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)]
                )
            )

            config_args = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=1500,
            )

            backoff = initial_backoff
            for attempt in range(1, max_retries + 1):
                try:
                    # Wrap SDK call with timeout
                    response = await asyncio.wait_for(
                        self.client.aio.models.generate_content(
                            model=self.model_name,
                            contents=contents,
                            config=config_args
                        ),
                        timeout=timeout
                    )
                    
                    if response.text:
                        return response.text
                    else:
                        logger.warning("Gemini returned empty text response.")
                        return "I'm drawing a blank right now. What were we saying?"
                        
                except asyncio.TimeoutError:
                    logger.error(f"Gemini API call timed out on attempt {attempt}/{max_retries}.")
                    if attempt == max_retries:
                        raise
                except APIError as e:
                    logger.error(f"Gemini APIError on attempt {attempt}/{max_retries}: {e}")
                    if attempt == max_retries:
                        raise
                    # Exponential backoff for rate limits or server errors
                    if hasattr(e, "code") and e.code in [429, 500, 503, 504]:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Unexpected error in Gemini API call (attempt {attempt}/{max_retries}): {e}")
                    if attempt == max_retries:
                        raise
                    await asyncio.sleep(backoff)
                    backoff *= 2

            raise RuntimeError("Failed to obtain response from Gemini API.")
            
        else:
            # Query Local Ollama Instance
            messages = [{"role": "system", "content": system_instruction}]
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                messages.append({"role": role, "content": msg["content"]})
            messages.append({"role": "user", "content": prompt})

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{config.OLLAMA_URL}/api/chat",
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
        """Extracts long term memory attributes using the configured AI provider."""
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
        if config.AI_PROVIDER == "gemini":
            config_args = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=512,
                response_mime_type="application/json"
            )
            
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config_args
                )
                if response.text:
                    return json.loads(response.text)
            except Exception as e:
                logger.error(f"Failed to extract memories using Gemini: {e}", exc_info=True)
                
            return None
            
        else:
            # Query Local Ollama with JSON constraints
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{config.OLLAMA_URL}/api/generate",
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
