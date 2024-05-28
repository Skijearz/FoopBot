import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging

class admin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')

    async def cog_app_command_error(self,interaction,error):
        self.logger.log(logging.ERROR,'Error in {0}: {1}'.format(interaction, error))

    async def cog_check(self,ctx):
        return await ctx.bot.is_owner(ctx.author)

    @app_commands.command(name='testdb',description="Test if Database is available")
    async def testDB(self,interaction: Interaction)-> None:
        await interaction.response.send_message("Database is {0}".format("avaiable" if self.bot.db_client is not None else "not available" ))
    
    @app_commands.command(name="sync", description="Syncs all Commands to all Guilds")
    async def sync(self,interaction: Interaction) -> None:
        synced = await self.bot.tree.sync()
        await interaction.response.send_message(
            f"Synced {len(synced)} commands globally "
        )
    @app_commands.command(name="stop", description="stops the bot")
    async def stop(self,interaction: Interaction) -> None:
        await interaction.response.send_message("Foop will now go to sleep!")
        await self.bot.close()

    @app_commands.command(name="audit", description="test")
    async def audit(self,interaction: Interaction, guildid: str) -> None:
        guild = self.bot.get_guild(int(guildid))
        async for entry in guild.audit_logs(limit=100):
            await interaction.response.send_message(f'{entry.user} did {entry.action} to {entry.target} reason: {entry.reason}')

async def setup(bot):
    await bot.add_cog(admin(bot), guilds=[discord.Object(id=745495001622118501)])
