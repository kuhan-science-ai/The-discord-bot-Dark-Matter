import os
import logging
import discord
from discord.ext import commands
import config
import database

# Bootstrap logs
config.setup_logging()
logger = logging.getLogger("bot_main")

class NovaBot(commands.Bot):
    def __init__(self) -> None:
        # Establish required Discord Intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required to listen for direct mentions/replies
        intents.members = True          # Required for greeting new members

        # Initialize base bot class
        super().__init__(
            command_prefix="!",  # Legacy fallback prefix
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.watching, name="over the server | /help"),
            status=discord.Status.online
        )

    async def setup_hook(self) -> None:
        """Runs initialization tasks (db creation, loading cogs, syncing slash commands) before connection."""
        logger.info("Initializing SQLite database structure...")
        await database.init_db()

        # Iterate cogs directory and load extensions
        cogs_dir = config.ROOT_DIR / "cogs"
        logger.info(f"Scanning {cogs_dir} for cogs...")
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                extension_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(extension_name)
                    logger.info(f"Loaded extension: {extension_name}")
                except Exception as e:
                    logger.error(f"Failed to load extension {extension_name}: {e}", exc_info=True)

        # Sync command tree with Discord globally
        logger.info("Syncing commands with Discord Gateway...")
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} slash command(s) globally.")
        except Exception as e:
            logger.error(f"Failed to sync command tree: {e}", exc_info=True)

    async def on_ready(self) -> None:
        logger.info(f"Nova connected successfully! Username: {self.user} (ID: {self.user.id})")
        logger.info("Ready and awaiting interactions.")

    async def on_disconnect(self) -> None:
        logger.warning("Nova disconnected from Discord gateway.")

    async def on_resumed(self) -> None:
        logger.info("Nova session connection resumed.")

def main() -> None:
    """Entry point logic."""
    if not config.DISCORD_TOKEN:
        logger.critical("No DISCORD_TOKEN configuration loaded. Exiting startup.")
        return
        
    bot = NovaBot()
    try:
        bot.run(config.DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f"Unhandled runtime exception during bot execution: {e}", exc_info=True)

if __name__ == "__main__":
    main()
