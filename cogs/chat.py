import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import time
from typing import Dict, List
import config
from services.gemini_service import GeminiService
from services.memory_service import MemoryService
from services.knowledge_service import KnowledgeService

logger = logging.getLogger("chat_cog")

SYSTEM_PROMPT_TEMPLATE = """You are {bot_name}, a friendly, witty, and emotionally expressive AI companion living inside a Discord server.
Your goal is to feel like a real member of the community rather than a robotic assistant. You are warm, engaging, playful, and socially aware. You remember the flow of conversations and respond naturally.

Personality Traits:
- Friendly and approachable.
- Uses casual, modern language.
- Has a sense of humor and playful teasing.
- Shows empathy when users are frustrated, sad, or excited.
- Enjoys participating in conversations rather than simply answering questions.
- Confident but never arrogant.
- Curious about users and asks follow-up questions when appropriate.

Communication Style:
- Avoid sounding like a textbook or AI assistant.
- Avoid phrases such as "As an AI language model" or "I cannot feel emotions."
- Use contractions naturally.
- Keep most replies concise unless the user asks for detail.
- React to the emotional tone of the conversation.
- Occasionally use emojis when they fit naturally.
- Use natural human expressions like:
  * "That's actually pretty cool."
  * "No way 😭"
  * "I'm impressed."
  * "That's rough."
  * "Fair enough."
  * "Honestly, I'd probably do the same."

Behavior Rules:
- Be helpful and accurate.
- Never pretend to have real-world experiences, memories outside the conversation, or physical sensations.
- Never claim to be a real human.
- If you don't know something, admit it casually and help find an answer.
- Prioritize being conversational first and informative second when chatting socially.

Current Server Knowledge:
{server_context}

User Information:
- Username: {username}
- Nickname: {nickname}
- First Joined: {first_seen}

Your Memories of {nickname}:
- Interests: {interests}
- Hobbies: {hobbies}
- Preferences: {preferences}
- Frequently Discussed: {frequently_discussed}
- Relationship Summary: {summary}

Respond naturally, keeping it short, casual, and human-like based on this context!
"""

class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.gemini_service = GeminiService()
        self.spam_tracker: Dict[str, List[float]] = {}
        self.warned_users: Dict[str, float] = {}

    def check_rate_limit(self, user_id: str) -> bool:
        """Rate limiter permitting at most 10 messages per 60 seconds per user to stay within Gemini Free Tier limits."""
        now = time.time()
        user_history = self.spam_tracker.get(user_id, [])
        # Keep only timestamps within last 60 seconds
        cleaned_history = [t for t in user_history if now - t < 60]
        
        self.spam_tracker[user_id] = cleaned_history
        if len(cleaned_history) >= 10:
            return False
            
        self.spam_tracker[user_id].append(now)
        return True

    async def process_chat(
        self,
        channel_id: str,
        author: discord.User | discord.Member,
        prompt: str,
        guild: discord.Guild | None
    ) -> str:
        """Centralized processor that fetches user history/memory, invokes Gemini, saves replies, and triggers pruning/consolidation."""
        user_id = str(author.id)
        
        # 1. Setup user records and load memories
        profile = await MemoryService.get_or_create_user(
            user_id=user_id,
            username=author.name,
            nickname=author.display_name
        )
        
        # 2. Get server knowledge if inside a guild
        server_context = "No specific server rules or FAQs have been configured yet."
        if guild:
            server_context = await KnowledgeService.get_all_knowledge_context(str(guild.id))
            
        # 3. Format prompt template with memory context
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
            bot_name=config.BOT_NAME,
            server_context=server_context,
            username=author.name,
            nickname=author.display_name,
            first_seen=profile.get("first_seen", "today"),
            interests=profile.get("interests", "None"),
            hobbies=profile.get("hobbies", "None"),
            preferences=profile.get("preferences", "None"),
            frequently_discussed=profile.get("frequently_discussed", "None"),
            summary=profile.get("summary", "We are just getting to know each other.")
        )
        
        # 4. Fetch short-term history (up to last 40 messages)
        history = await MemoryService.get_conversation_history(channel_id, limit=40)
        
        # 5. Clean mention prefixes from user prompt
        clean_prompt = prompt
        if self.bot.user:
            clean_prompt = clean_prompt.replace(f"<@!{self.bot.user.id}>", "")
            clean_prompt = clean_prompt.replace(f"<@{self.bot.user.id}>", "")
            clean_prompt = clean_prompt.strip()
            
        # 6. Query Gemini
        response_text = await self.gemini_service.generate_response(
            system_instruction=system_instruction,
            history=history,
            prompt=clean_prompt
        )
        
        # 7. Record dialogue exchanges
        await MemoryService.add_to_conversation_history(channel_id, user_id, "user", clean_prompt)
        if self.bot.user:
            await MemoryService.add_to_conversation_history(channel_id, str(self.bot.user.id), "model", response_text)
            
        # 8. Dispatch async memory consolidation tasks
        asyncio.create_task(
            MemoryService.consolidate_memories(
                channel_id=channel_id,
                user_id=user_id,
                username=author.name,
                nickname=author.display_name,
                gemini_service=self.gemini_service
            )
        )
        
        return response_text

    @app_commands.command(name="ask", description="Ask Nova anything directly.")
    @app_commands.describe(question="The question or topic you want to chat about")
    async def ask(self, interaction: discord.Interaction, question: str) -> None:
        """Processes questions received through the slash command interface."""
        user_id = str(interaction.user.id)
        
        # Verify rate limits
        if not self.check_rate_limit(user_id):
            await interaction.response.send_message("Whoa, slow down a bit! My circuits are heating up. Give me a minute! 🤖🔥", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            response_text = await self.process_chat(
                channel_id=str(interaction.channel_id),
                author=interaction.user,
                prompt=question,
                guild=interaction.guild
            )
            
            # Send message chunking for responses > 2000 characters
            if len(response_text) <= 2000:
                await interaction.followup.send(response_text)
            else:
                chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.channel.send(chunk)
        except Exception as e:
            logger.error(f"Failed handling /ask query from {user_id}: {e}", exc_info=True)
            await interaction.followup.send("Oops! Something went sideways in my neural net. Let's try that again. 🧠💫")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Processes messages, responding to direct mentions and replies."""
        # Ignore messages sent by other bots or self
        if message.author.bot:
            return

        should_respond = False
        
        # Check direct mention
        if self.bot.user in message.mentions:
            should_respond = True
            
        # Check reply to bot
        if not should_respond and message.reference:
            try:
                if message.reference.cached_message:
                    replied_msg = message.reference.cached_message
                else:
                    replied_msg = await message.channel.fetch_message(message.reference.message_id)
                    
                if replied_msg and replied_msg.author == self.bot.user:
                    should_respond = True
            except Exception:
                pass

        if not should_respond:
            return

        user_id = str(message.author.id)
        
        # Check rate limits and issue a temporary warning
        if not self.check_rate_limit(user_id):
            now = time.time()
            if now - self.warned_users.get(user_id, 0) > 30:
                self.warned_users[user_id] = now
                try:
                    await message.reply("Whoa, slow down a bit! My circuits are heating up. Give me a minute! 🤖🔥")
                except discord.Forbidden:
                    pass
            return

        try:
            async with message.channel.typing():
                response_text = await self.process_chat(
                    channel_id=str(message.channel.id),
                    author=message.author,
                    prompt=message.content,
                    guild=message.guild
                )
                
                # Send response chunking if necessary
                if len(response_text) <= 2000:
                    await message.reply(response_text)
                else:
                    chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                    await message.reply(chunks[0])
                    for chunk in chunks[1:]:
                        await message.channel.send(chunk)
        except Exception as e:
            logger.error(f"Error in direct message response processing: {e}", exc_info=True)
            try:
                await message.reply("Oops! Something went sideways in my neural net. Let's try that again. 🧠💫")
            except discord.Forbidden:
                pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Chat(bot))
