import discord
from discord.ext import commands
from discord import app_commands, Interaction


class admin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    async def cog_app_command_error(self,interaction,error):
        print('Error in {0}: {1}'.format(interaction, error))

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

async def setup(bot):
    await bot.add_cog(admin(bot), guilds=[discord.Object(id=745495001622118501)])