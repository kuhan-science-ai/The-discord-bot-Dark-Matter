import discord
from discord.ext import commands
from discord import app_commands
import logging
import config
from services.memory_service import MemoryService

logger = logging.getLogger("memory_cog")

class Memory(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description=f"Show your basic profile information stored by {config.BOT_NAME}.")
    async def profile(self, interaction: discord.Interaction) -> None:
        """Displays user profile details such as database ID and first join date."""
        user_id = str(interaction.user.id)
        username = interaction.user.name
        nickname = interaction.user.display_name
        
        await interaction.response.defer()
        try:
            profile_data = await MemoryService.get_or_create_user(user_id, username, nickname)
            
            embed = discord.Embed(
                title=f"👤 User Profile - {nickname}",
                color=discord.Color.blue()
            )
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
                
            embed.add_field(name="User ID", value=user_id, inline=True)
            embed.add_field(name="Username", value=username, inline=True)
            embed.add_field(name="Nickname", value=nickname, inline=True)
            embed.add_field(name="First Met", value=profile_data.get("first_seen", "Unknown"), inline=True)
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to fetch profile for {user_id}: {e}", exc_info=True)
            await interaction.followup.send("An internal database error occurred while loading your profile.")

    @app_commands.command(name="memory", description=f"Show personal long-term memories that {config.BOT_NAME} has stored about you.")
    async def memory(self, interaction: discord.Interaction) -> None:
        """Displays the consolidated long term traits, preferences and summaries learned about the user."""
        user_id = str(interaction.user.id)
        username = interaction.user.name
        nickname = interaction.user.display_name
        
        await interaction.response.defer()
        try:
            profile_data = await MemoryService.get_or_create_user(user_id, username, nickname)
            
            embed = discord.Embed(
                title=f"🧠 Memory Log - {nickname}",
                description=f"This is the consolidated memory {config.BOT_NAME} uses to personalize conversations with you.",
                color=discord.Color.teal()
            )
            
            interests = profile_data.get("interests", "")
            hobbies = profile_data.get("hobbies", "")
            prefs = profile_data.get("preferences", "")
            freq = profile_data.get("frequently_discussed", "")
            summary = profile_data.get("summary", "")
            
            embed.add_field(name="🎨 Interests", value=interests if interests else "None recorded yet.", inline=False)
            embed.add_field(name="🎮 Hobbies", value=hobbies if hobbies else "None recorded yet.", inline=False)
            embed.add_field(name="⚡ Preferences", value=prefs if prefs else "None recorded yet.", inline=False)
            embed.add_field(name="💬 Frequently Discussed", value=freq if freq else "None recorded yet.", inline=False)
            embed.add_field(name="📝 Relationship Summary", value=summary if summary else "No summary yet. Chat with me more to build rapport!", inline=False)
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to fetch memory for {user_id}: {e}", exc_info=True)
            await interaction.followup.send("An internal database error occurred while loading your memory logs.")

    @app_commands.command(name="clear_memory", description=f"Wipe all personal long-term memories that {config.BOT_NAME} has stored about you.")
    async def clear_memory(self, interaction: discord.Interaction) -> None:
        """Wipes the database memory attributes associated with the requesting user."""
        user_id = str(interaction.user.id)
        nickname = interaction.user.display_name
        
        await interaction.response.defer(ephemeral=True)
        try:
            await MemoryService.clear_user_memory(user_id)
            await interaction.followup.send(f"✅ Hey {nickname}, I've wiped my memory logs of our past talks. Let's start fresh!", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to clear memory for {user_id}: {e}", exc_info=True)
            await interaction.followup.send("An internal database error occurred. Your memory logs could not be cleared.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Memory(bot))

