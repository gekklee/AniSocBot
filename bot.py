import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import db
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

def load_allowed_guild_ids() -> set[int]:
    raw_guild_ids = os.getenv('ALLOWED_GUILD_IDS', '')
    return {
        int(guild_id)
        for guild_id in raw_guild_ids.split(',')
        if guild_id.strip().isdigit()
    }


ALLOWED_GUILD_IDS = load_allowed_guild_ids()

if not TOKEN:
    logger.error("DISCORD_TOKEN not found in .env file or environment.")
    exit(1)

class SocietyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    def guild_is_allowed(self, guild_id: int) -> bool:
        return guild_id in ALLOWED_GUILD_IDS

    async def enforce_guild_allowlist(self, guild: discord.Guild):
        if not self.guild_is_allowed(guild.id):
            logger.warning("Leaving unauthorized guild: %s (%s)", guild.name, guild.id)
            await guild.leave()

    async def setup_hook(self):
        await db.init_db()
        
        await self.load_extension('cogs.admin')
        await self.load_extension('cogs.points')
        
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s) globally.")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_guild_join(self, guild: discord.Guild):
        await self.enforce_guild_allowlist(guild)

bot = SocietyBot()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    if not ALLOWED_GUILD_IDS:
        logger.error("ALLOWED_GUILD_IDS is empty in .env; the bot will leave any server it joins.")
    for guild in list(bot.guilds):
        await bot.enforce_guild_allowlist(guild)
    logger.info('------')

if __name__ == '__main__':
    bot.run(TOKEN)