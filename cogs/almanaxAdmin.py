import logging
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import bs4
import calendar



URL = "https://dofuswiki.fandom.com/wiki/Almanax/Offerings"


class almanaxAdmin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')
        self.bot.loop.create_task(self.create_almanax_tables())

    async def cog_app_command_error(self,interaction,error):
        self.logger.log(logging.ERROR,'Error in {0}: {1}'.format(interaction, error))

    
    @app_commands.command(name="createalmanaxtable",description="re-creates the alamanx discorchannel table")
    async def prepare_almanax_tables(self,interaction: Interaction):
        await self.create_almanax_tables()
        await interaction.response.send_message("Almanax-Database Created")

    async def create_almanax_tables(self):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute('''CREATE TABLE IF NOT EXISTS AlmanaxChannel(
                                DiscordChannel Text NOT NULL UNIQUE
                                )''')
        await self.bot.db_client.commit()


async def setup(bot):
    await bot.add_cog(almanaxAdmin(bot),guilds=[discord.Object(id=745495001622118501)])