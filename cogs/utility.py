import discord
from discord.ext import commands
from discord import app_commands
import config

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's response latency.")
    async def ping(self, interaction: discord.Interaction) -> None:
        """Responds with the bot's websocket latency in milliseconds."""
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: **{latency}ms**",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Display information about this server.")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        """Displays key server metrics and characteristics."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be used inside a Discord server.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🏰 {guild.name} Info",
            color=discord.Color.purple()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner or "Unknown", inline=True)
        embed.add_field(name="MembersCount", value=guild.member_count, inline=True)
        embed.add_field(name="Created On", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
        embed.add_field(name="Verification Level", value=guild.verification_level.name, inline=True)
        embed.add_field(name="Roles Count", value=len(guild.roles), inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description=f"Show all commands and features of {config.BOT_NAME}.")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """Presents detailed information about bot capabilities and slash commands."""
        embed = discord.Embed(
            title=f"👋 Hello, I'm {config.BOT_NAME}!",
            description=(
                f"I am a friendly, social AI companion powered by local Ollama AI. "
                f"I chat, answer questions, help with programming, or just hang out. "
                f"Talk to me by **mentioning me (@{config.BOT_NAME})** or **replying to my messages**!\n\n"
                f"Here are the slash commands available:"
            ),
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🤖 Chat & Info Commands",
            value=(
                "**/ask <question>** - Ask me anything directly.\n"
                "**/ping** - View my response latency.\n"
                "**/serverinfo** - View information about this Discord server.\n"
                "**/help** - Display this menu."
            ),
            inline=False
        )
        
        embed.add_field(
            name="🧠 Memory Commands",
            value=(
                "**/profile** - View user profile information stored.\n"
                "**/memory** - Inspect the long-term memories saved for you.\n"
                "**/clear_memory** - Reset and clear your long-term memories."
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Admin Commands (Server Knowledge)",
            value=(
                "**/knowledge_add <key> <value>** - Teach me something about this server (rules, FAQs, events).\n"
                "**/knowledge_remove <key>** - Remove a piece of server knowledge.\n"
                "**/knowledge_list** - List all custom knowledge configured for this server."
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Developed with care • Powered by Ollama ({config.OLLAMA_MODEL})")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
