import logging
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import discord
import config
import asyncio

GET_PLAYER_ACHIEVEMENTS_URL = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid={}&key={}&steamid={}"
GET_OWNED_GAMES_URL ="http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={}&steamid={}&format=json&include_played_free_games=true"
STEAM_PROFILE_URL = "https://steamcommunity.com/profiles/{}"
GAME_INFO_URL ="https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key={}&appid={}"
GAME_STORE_SITE ="https://store.steampowered.com/app/{}"
#SELECT SteamAccount.SteamID, SteamAccount.DiscordAccountID, WatchedPerfectGames.AppID FROM SteamAccount INNER JOIN WatchedPerfectGames On SteamAccount.SteamID = WatchedPerfectGames.SteamID Where AppID = 730;
class steam(commands.Cog):
    def __init__(self,bot):
        self.bot = bot 
        self.bot.steamwebapikey = config.STEAM_WEB_API_KEY
        self.check_perfect_games.start()
        self.check_unused_games.start()
        self.logger = logging.getLogger('discord')

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        return await super().cog_app_command_error(interaction, error)



    @app_commands.command(name="watchperfectgames", description="Watches your perfect games on Steam and notifies you if a game gets new Achievements")
    async def watchperfectgames(self, interaction: Interaction,steamid: str):
        #Get all owned games of specified steamid
        #discordUser = interaction.user if discordusertomention == None else discordusertomention 
        user = interaction.user
        await interaction.response.defer()
        allOwnedGames = await self.getAllOwnedGamesOfSteamID(steamid)
        perfectGames = await self.getAllPerfectGamesOfOwnedGames(steamid,allOwnedGames)
        if len(perfectGames) >= 1:
            await self.storeSteamUserAccount(steamid,user)
            await self.storePerfectGamesOfSteamAccount(steamid,perfectGames)
            await interaction.followup.send("Now Watching perfect Games for: " + STEAM_PROFILE_URL.format(steamid))
        else:
            await interaction.followup.send("No PerfectGames found for " + STEAM_PROFILE_URL.format(steamid))
        
        
    @app_commands.command(name="stopwatchingperfectgames", description="Bot stops watching your perfect games")
    async def stopwatchingperfectgames(self,interaction: Interaction):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' DELETE FROM SteamAccount WHERE DiscordAccountID =? 
                                ''',(interaction.user.id))
            await self.bot.db_client.commit()
        await self.check_unused_games()
        await interaction.response.send_message("Stopping to watch your perfect games on Steam!")



        

    async def storePerfectGamesOfSteamAccount(self,steamid: str,perfectGames: list):
        for games in perfectGames:
            appid = games[0]
            number_achievements = games[1]
            async with self.bot.db_client.cursor() as cursor:
                await cursor.execute(''' INSERT OR IGNORE INTO WatchedPerfectGames values(?,?) 
                                    ''', appid,number_achievements)
                await cursor.execute('''
                                     INSERT OR IGNORE INTO R_Games_Account values(?,?)
                                     ''', steamid,appid)
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
                number_achievements: int
                for number_achievements,_achievements in enumerate(jsonData['playerstats']['achievements']):
                    if _achievements['achieved'] == 0:
                        return 
                return (appid,number_achievements+1)


    async def getAllOwnedGamesOfSteamID(self, steamid:str):
        async with self.bot.web_client.get(GET_OWNED_GAMES_URL.format(self.bot.steamwebapikey,steamid)) as res:
            jsonData = await res.json()
            allOwnedGames = []
            for _games in jsonData['response']['games']:
                #remove games with playtime_forever:0 as they didnt play that game 
                allOwnedGames.append(_games["appid"])
            return allOwnedGames

    @tasks.loop(seconds=18000)
    async def check_perfect_games(self):
        try:
            async with self.bot.db_client.cursor() as cursor:
                await cursor.execute(''' SELECT * FROM WatchedPerfectGames
                                    ''')
                result = await cursor.fetchall()
                if len(result) > 0:
                    tasks = []
                    changed_games: list
                    for games in result:
                        appid = games[0]
                        number_achievements = games[1]
                        task = asyncio.ensure_future(self.get_all_games_with_new_achievements(appid,number_achievements)) 
                        tasks.append(task)
                        changed_games = await asyncio.gather(*tasks, return_exceptions=True)
                    changed_games = list(filter(lambda item: item is not None,changed_games))
                    if len(changed_games) > 0:
                        await self.notify_users(changed_games)
                        await self.delete_perfect_game(changed_games)
        except Exception as e:
            self.logger.log(logging.ERROR, e)

    @tasks.loop(hours=24)
    async def check_unused_games(self):
        try:
            async with self.bot.db_client.cursor() as cursor:
                await cursor.execute(''' SELECT * FROM WatchedPerfectGames WHERE AppID NOT IN (SELECT AppID FROM R_Games_Account)
                                    ''')
                result = await cursor.fetchall()
                if len(result) > 0:
                    for game in result:
                        appid = game[0]
                        await cursor.execute(''' DELETE FROM WatchedPerfectGames WHERE AppID=? 
                                    ''',(appid))
                        await self.bot.db_client.commit()
        except Exception as e:
            self.logger.log(logging.ERROR, e)


    @check_perfect_games.before_loop
    async def waitTillBotReady(self):
        await self.bot.wait_until_ready()


    async def delete_perfect_game(self,changed_games:list)-> None:
        for game in changed_games:
            async with self.bot.db_client.cursor() as cursor:
                await cursor.execute(''' DELETE FROM WatchedPerfectGames WHERE AppID=? 
                                    ''',(game))
                await self.bot.db_client.commit()

    async def notify_users(self,changed_games:list):
        for game in changed_games:
            async with self.bot.db_client.cursor() as cursor:
                await cursor.execute(''' SELECT SteamAccount.DiscordAccountID, SteamAccount.SteamID, R_Games_Account.AppID FROM R_Games_Account INNER JOIN SteamAccount on R_Games_Account.SteamID = SteamAccount.SteamID WHERE R_Games_Account.AppID =?

                                    ''',game)
                result = await cursor.fetchall()
                tasks = []
                for user in result:
                    task = asyncio.ensure_future(self.send_dm(user))
                    tasks.append(task)
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
    async def send_dm(self,user):
        discord_user = self.bot.get_user(int(user[0]))
        await discord_user.send("Game: " +GAME_STORE_SITE.format(user[2]) + " got new Achievements!")


    async def get_all_games_with_new_achievements(self,appid: str, number_achievments:int):
        async with self.bot.web_client.get(GAME_INFO_URL.format(self.bot.steamwebapikey,appid)) as result:
            game = await result.json()
            total_achievements :int = int(len(game['game']['availableGameStats']['achievements']))
            if int(number_achievments) != int(total_achievements):
                return appid


async def setup(bot):
    await bot.add_cog(steam(bot))
