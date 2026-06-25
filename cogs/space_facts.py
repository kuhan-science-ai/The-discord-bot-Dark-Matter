import discord
from discord.ext import commands, tasks
import datetime
import logging
from services.ollama_service import OllamaService
import config

logger = logging.getLogger("space_facts")

# IST timezone setup (UTC+5:30)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
DAILY_TIME = datetime.time(hour=9, minute=0, tzinfo=IST)

class SpaceFacts(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ollama_service = OllamaService()
        # Start the background task loop
        self.daily_fact_loop.start()

    def cog_unload(self) -> None:
        """Cancel the loop when the cog is unloaded."""
        self.daily_fact_loop.cancel()

    @tasks.loop(time=DAILY_TIME)
    async def daily_fact_loop(self) -> None:
        """Scheduled task that runs daily at 9:00 AM IST to post a space/cosmic fact."""
        logger.info("Triggered daily space fact generation...")
        
        # System instruction to keep the AI in character
        system_instruction = (
            f"You are {config.BOT_NAME}, a friendly, witty, and emotionally expressive AI companion. "
            "You write casually, using lowercase, abbreviations, and sound exactly like a real human server member."
        )

        prompt = (
            "Generate a mind-blowing, unique, and awesome space or cosmic fact. "
            "Write it in your casual, friendly, and witty personality (Dark-Matter). "
            "Keep it engaging, natural, and relatively short (2-4 sentences). "
            "Make it feel like you just read something cool online and wanted to share it with the server. "
            "Do not use markdown bolding, headings, lists, or headers. "
            "Just write it like a real Discord post, using an emoji naturally."
        )

        try:
            # Query the configured AI model (Ollama)
            fact_text = await self.ollama_service.generate_response(
                system_instruction=system_instruction,
                history=[],
                prompt=prompt
            )

            # Send the fact to all connected servers
            for guild in self.bot.guilds:
                channel = None
                
                # Check for preferred channels
                for name in ["cosmic-facts", "space-facts", "general"]:
                    channel = discord.utils.get(guild.text_channels, name=name)
                    if channel:
                        break
                
                # Fallback to guild default system channel
                if not channel:
                    channel = guild.system_channel

                if not channel:
                    logger.warning(f"Could not find a suitable text channel in guild: {guild.name}")
                    continue

                try:
                    # Create an eye-catching cosmic facts embed
                    embed = discord.Embed(
                        title="🌌 Cosmic Fact of the Day",
                        description=fact_text,
                        color=discord.Color.from_rgb(138, 43, 226)  # Deep Purple theme
                    )
                    avatar_url = self.bot.user.avatar.url if self.bot.user and self.bot.user.avatar else None
                    embed.set_footer(
                        text=f"Brought to you by {config.BOT_NAME} • Daily 9:00 AM IST",
                        icon_url=avatar_url
                    )

                    await channel.send(embed=embed)
                    logger.info(f"Successfully posted daily space fact embed in #{channel.name} of guild: {guild.name}")
                except discord.Forbidden:
                    logger.error(f"Cannot post daily fact in #{channel.name} ({guild.name}): Missing permissions.")
                except Exception as e:
                    logger.error(f"Error posting daily fact in #{channel.name} ({guild.name}): {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to generate daily space fact: {e}", exc_info=True)

    @daily_fact_loop.before_loop
    async def before_daily_fact_loop(self) -> None:
        """Wait for the bot to fully connect to Discord before starting the loop."""
        await self.bot.wait_until_ready()
        logger.info("Daily space facts task loop synchronized and ready.")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SpaceFacts(bot))
