import discord
from discord.ext import commands
from discord import app_commands
import logging
from services.knowledge_service import KnowledgeService

logger = logging.getLogger("knowledge_cog")

class Knowledge(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="knowledge_add", description="[Admin Only] Add or update a server knowledge fact (e.g. rules, FAQ, guide).")
    @app_commands.describe(key="Unique label for the topic (e.g. rules, schedule, events)", value="Details for Nova to memorize")
    @app_commands.default_permissions(administrator=True)
    async def knowledge_add(self, interaction: discord.Interaction, key: str, value: str) -> None:
        """Adds or updates key server context. Only server administrators can invoke this."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be run in a Discord server guild.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await KnowledgeService.add_knowledge(
                guild_id=str(guild.id),
                key=key,
                value=value,
                updated_by=str(interaction.user)
            )
            embed = discord.Embed(
                title="✅ Knowledge Base Updated",
                description=f"Successfully memorized server key: `{key.strip().lower()}`",
                color=discord.Color.green()
            )
            embed.add_field(name="Content Preview", value=value[:1024], inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to add server knowledge key {key}: {e}", exc_info=True)
            await interaction.followup.send("An internal database error occurred while trying to record knowledge.", ephemeral=True)

    @app_commands.command(name="knowledge_remove", description="[Admin Only] Remove a server knowledge key.")
    @app_commands.describe(key="Knowledge label to delete")
    @app_commands.default_permissions(administrator=True)
    async def knowledge_remove(self, interaction: discord.Interaction, key: str) -> None:
        """Removes a server context key. Restricted to administrators."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be run in a Discord server guild.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            removed = await KnowledgeService.remove_knowledge(guild_id=str(guild.id), key=key)
            if removed:
                await interaction.followup.send(f"✅ Successfully deleted key `{key.strip().lower()}` from knowledge database.", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Key `{key.strip().lower()}` does not exist in server knowledge.", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to delete server knowledge key {key}: {e}", exc_info=True)
            await interaction.followup.send("An internal database error occurred while trying to remove knowledge.", ephemeral=True)

    @app_commands.command(name="knowledge_list", description="[Admin Only] List all server knowledge keys taught to Nova.")
    @app_commands.default_permissions(administrator=True)
    async def knowledge_list(self, interaction: discord.Interaction) -> None:
        """Lists all server keys. Restricted to administrators."""
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be run in a Discord server guild.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            items = await KnowledgeService.list_knowledge(str(guild.id))
            if not items:
                await interaction.followup.send("No knowledge records found for this server. Use `/knowledge_add` to add one.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"📚 Server Knowledge Base - {guild.name}",
                description="Below is the custom data Nova has access to when generating responses.",
                color=discord.Color.blue()
            )
            for item in items:
                preview = item["value"]
                if len(preview) > 150:
                    preview = preview[:147] + "..."
                embed.add_field(
                    name=f"🔑 `{item['key']}`",
                    value=f"{preview}\n*Updated by: {item['updated_by']}*",
                    inline=False
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to list server knowledge: {e}", exc_info=True)
            await interaction.followup.send("An internal database error occurred while trying to list knowledge items.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Knowledge(bot))
