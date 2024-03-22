from discord.ext import commands, tasks
from discord import app_commands, Interaction
import discord

class steamAdmin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot 

    async def cog_app_command_error(self,interaction,error):
        print('Error in {0}: {1}'.format(interaction, error))

    @app_commands.command(name="createsteamdb",description="creates db table for watchperfect games")
    async def createsteamdb(self,interaction: discord.Interaction):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute('''CREATE TABLE IF NOT EXISTS SteamAccount(SteamID PRIMARY KEY UNIQUE,DiscordAccountID Text, CONSTRAINT unqq UNIQUE(SteamID, DiscordAccountID))
                                ''') 
            await cursor.execute(''' CREATE TABLE IF NOT EXISTS WatchedPerfectGames(AppID PRIMARY KEY UNIQUE,NumberAchievementes Text Not Null)
                                ''')
            await cursor.execute('''
                                 CREATE TABLE IF NOT EXISTS R_Games_Account(SteamID,AppID,FOREIGN KEY(SteamID) REFERENCES SteamAccount(SteamID) ON DELETE CASCADE, FOREIGN KEY(AppID) REFERENCES WatchedPerfectGames(AppID) ON DELETE CASCADE, CONSTRAINT uniq UNIQUE(SteamID,AppID))
                                 ''')
            await self.bot.db_client.commit()
        await interaction.response.send_message("Steam Tables created!")



async def setup(bot):
    await bot.add_cog(steamAdmin(bot),guilds=[discord.Object(id=745495001622118501)])