import discord
from discord.ext import commands
import logging
import config

logger = logging.getLogger("moderation")

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Fires when a new user joins a guild. Sends a friendly welcome greeting."""
        logger.info(f"New member joined: {member.name} ({member.id}) in guild {member.guild.name}")
        
        guild = member.guild
        channel = None
        
        # 1. Look for a channel explicitly named "welcome"
        channel = discord.utils.get(guild.text_channels, name="welcome")
        
        # 2. Look for "general" channel
        if not channel:
            channel = discord.utils.get(guild.text_channels, name="general")
            
        # 3. Fallback to guild's designated system channel
        if not channel:
            channel = guild.system_channel
            
        if not channel:
            logger.warning(f"Could not find a suitable welcome channel in guild {guild.name}.")
            return
            
        welcome_text = (
            f"👋 Welcome to the server, {member.mention}! We're thrilled to have you here.\n\n"
            f"I'm **{config.BOT_NAME}**, the server's AI companion. If you want to ask me anything or chat, "
            f"just mention me (@{config.BOT_NAME}) or use `/ask`. Have a great time! ✨"
        )
        
        try:
            await channel.send(welcome_text)
            logger.info(f"Sent welcome message to {member.name} in #{channel.name}")
        except discord.Forbidden:
            logger.error(f"Cannot send welcome message: lack Send Messages permissions in #{channel.name} ({guild.name})")
        except Exception as e:
            logger.error(f"Error handling welcome message: {e}", exc_info=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
