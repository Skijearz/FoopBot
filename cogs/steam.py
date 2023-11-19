from discord.ext import commands, tasks
from discord import app_commands, Interaction
import discord
import config
import asyncio

GET_PLAYER_ACHIEVEMENTS_URL = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid={}&key={}&steamid={}"
GET_OWNED_GAMES_URL ="http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={}&steamid={}&format=json"
#SELECT SteamAccount.SteamID, SteamAccount.DiscordAccountID, WatchedPerfectGames.AppID FROM SteamAccount INNER JOIN WatchedPerfectGames On SteamAccount.SteamID = WatchedPerfectGames.SteamID Where AppID = 730;
class steam(commands.Cog):
    def __init__(self,bot):
        self.bot = bot 
        self.bot.steamwebapikey = config.STEAM_WEB_API_KEY

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        return await super().cog_app_command_error(interaction, error)



    @app_commands.command(name="watchperfectgames", description="Watches your perfect games on Steam and notifies you if a game gets new Achievements")
    async def watchperfectgames(self, interaction: Interaction,steamid: str):
        #Get all owned games of specified steamid
        #discordUser = interaction.user if discordusertomention == None else discordusertomention 
        user = interaction.user
        allOwnedGames = await self.getAllOwnedGamesOfSteamID(steamid)
        perfectGames = await self.getAllPerfectGamesOfOwnedGames(steamid,allOwnedGames)
        if len(perfectGames) >= 1:
            await self.storeSteamUserAccount(steamid,user)
            await self.storePerfectGamesOfSteamAccount(steamid,perfectGames)
            await interaction.response.send_message(user)



    async def storePerfectGamesOfSteamAccount(self,steamid: str,perfectGames: list):
        for _appid in perfectGames:
            async with self.bot.db_client.cursor() as cursor:
                await cursor.execute(''' INSERT OR IGNORE INTO WatchedPerfectGames values(?,?) 
                                    ''', steamid,_appid)
                await self.bot.db_client.commit() 


    async def storeSteamUserAccount(self,steamid: str, discordUser: discord.User | discord.Member):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' INSERT OR IGNORE INTO SteamAccount values(?,?) 
                                ''', steamid,discordUser.id)
            await self.bot.db_client.commit() 


    async def getAllPerfectGamesOfOwnedGames(self, steamid: str,allOwnedGames: list):
        tasks = []
        for _appid in allOwnedGames:
            task = asyncio.ensure_future(self.identifyPerfectGames(_appid,steamid)) 
            tasks.append(task)
        data = await asyncio.gather(*tasks, return_exceptions=True)
        return list(filter(lambda item: item is not None,data))


    async def identifyPerfectGames(self,appid,steamid):
        async with self.bot.web_client.get(GET_PLAYER_ACHIEVEMENTS_URL.format(appid,self.bot.steamwebapikey,steamid)) as res:
            jsonData = await res.json()
            if jsonData['playerstats']['success'] == False:
                return 
            if "achievements" in jsonData['playerstats']:
                for _achievements in jsonData['playerstats']['achievements']:
                    if _achievements['achieved'] == 0:
                        return 
                return appid


    async def getAllOwnedGamesOfSteamID(self, steamid:str):
        async with self.bot.web_client.get(GET_OWNED_GAMES_URL.format(self.bot.steamwebapikey,steamid)) as res:
            jsonData = await res.json()
            allOwnedGames = []
            for _games in jsonData['response']['games']:
                allOwnedGames.append(_games["appid"])
            return allOwnedGames


async def setup(bot):
    await bot.add_cog(steam(bot))