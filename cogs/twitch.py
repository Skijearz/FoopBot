import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import config
import asyncio
from datetime import datetime, timedelta,timezone
from views.removeTwitchSub import removeTwitchSubView,removeTwitchSubDropDown
import time
import random
from typing import cast

OAUTH_URL = 'https://id.twitch.tv/oauth2/token?client_id={}&client_secret={}&grant_type=client_credentials'

TWITCH_API_STREAMS_ID = 'https://api.twitch.tv/helix/streams?user_id={}'
TWITCH_API_USERS_LOGIN = 'https://api.twitch.tv/helix/users?login={}'
TWITCH_API_USERS_ID = "https://api.twitch.tv/helix/users?id={}"



EMBED_COLOR = 0x9146ff

class twitch(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.authToken = None
        self.expiresIn = None
        self.tokenType = None
        self.createOAuthToken.start()
        self.taskTwitchStream.start()
    
    async def cog_app_command_error(self,interaction,error):
        print('Error in {0}: {1}'.format(interaction, error))
    
    async def cog_check(self,ctx):
        member = cast(discord.Member, ctx.author)
        return (member.guild_permissions.administrator)
    
    async def interaction_check(self,interaction: Interaction):
        if interaction.user == self.bot.appInfo.owner:
            return True
        member = cast(discord.Member, interaction.user)
        if not member.guild_permissions.administrator:
           await interaction.response.send_message("You dont have the required Permissions",ephemeral=True)
           return False
        return True
    @tasks.loop(seconds = 10)
    async def createOAuthToken(self):
        async with self.bot.web_client.post(OAUTH_URL.format(config.TWITCH_API_CHANNEL_ID,config.TWITCH_API_TOKEN)) as r:
            jsonData = await r.json()
            self.authToken = jsonData["access_token"]
            self.expiresIn = jsonData["expires_in"] - 300
            self.tokenType = jsonData["token_type"]
            self.createOAuthToken.change_interval(seconds = self.expiresIn)


    @app_commands.command(name="subtwitch",description="Subscribe to a Twitch Channel, getting a Notification when that channel goes Live!")
    async def subTwitchChannel(self,interaction:Interaction, twitchchannel : str, textchannel: discord.TextChannel ,role: discord.Role):
        if "twitch.tv" not in twitchchannel:
            return await interaction.response.send_message("Please provide a valid https://www.twitch.tv URL")
        username = twitchchannel.split("/")[-1]
        jsonDataProfile = await self.getTwitchProfileInfo(username)
        broadcasterID = jsonDataProfile['data'][0]['id']
        jsonDataStream = await self.getStreamInfo(broadcasterID)
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' INSERT OR IGNORE INTO TwitchNotifierChannel values(?,?,?) 
                                ''',broadcasterID,jsonDataProfile['data'][0]['login'],jsonDataStream['data'][0]['started_at'] if jsonDataStream != None else "Offline")
            await cursor.execute(''' INSERT OR IGNORE INTO TwitchNotifierDiscordChannel values(?,?,?,?)
                                ''',broadcasterID,interaction.guild_id,textchannel.id,role.id)
            await self.bot.db_client.commit() 
        await interaction.response.send_message(f"Subscribed to Twitch-Channel: {twitchchannel}")


    @app_commands.command(name="twitchsublist", description="Show all Twitch-Channels Subscribed on this Discord-Server")
    async def twitchSubList(self,interaction: Interaction):
        async with self.bot.db_client.cursor()as cursor:
            await cursor.execute(''' SELECT TwitchNotifierChannel.ChannelName FROM TwitchNotifierChannel INNER JOIN TwitchNotifierDiscordChannel ON TwitchNotifierChannel.BroadcasterID = TwitchNotifierDiscordChannel.NotifierBroadcasterID where DiscordGuild =?
                                ''',(interaction.guild_id))
            result = await cursor.fetchall()
            embed = discord.Embed(title=f'Subscribed Twitch-Channels ', type="rich", color=EMBED_COLOR)
            value: str = ""
            if len(result) == 0:
                return await interaction.response.send_message("No Twitch-Channel Subscribed")
            for channel in result:
                name = channel[0]
                value += "```" + name + "```\n" 
            embed.add_field(name="",value=value)
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="removetwitchsub", description="removes the selcted Twitch-Channel from the notifier list")
    async def removeTwitchSub(self,interaction: Interaction):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute('''SELECT TwitchNotifierChannel.BroadcasterID, TwitchNotifierChannel.ChannelName FROM  TwitchNotifierChannel INNER JOIN TwitchNotifierDiscordChannel ON TwitchNotifierChannel.BroadcasterID = TwitchNotifierDiscordChannel.NotifierBroadcasterID WHERE TwitchNotifierDiscordChannel.DiscordGuild = ?
                                ''',(interaction.guild_id))
            result = await cursor.fetchall()
            if len(result) == 0:
                return await interaction.response.send_message("No Twitch-Channel Subscribed")
            view = removeTwitchSubView()
            select = removeTwitchSubDropDown(self.bot)
            for channel in result:
                select.add_option(label=channel[1],value=channel[0])
            view.add_item(select)
        
        await interaction.response.send_message(view=view,ephemeral=True)

    @tasks.loop(seconds=300)
    async def taskTwitchStream(self):
        startTime = time.time()
        tasks = []
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' SELECT * FROM TwitchNotifierChannel
                                ''')
            result = await cursor.fetchall()
            if len(result) == 0:
                return
            for channel in result:
                if channel[2] != 'Offline':
                    datetime_obj = datetime.strptime(channel[2],'%Y-%m-%dT%H:%M:%S%z')
                    lastStreamedDelay_obj = (datetime.now(tz=timezone.utc) - timedelta(hours=2))
                    if datetime_obj > lastStreamedDelay_obj:
                        ## Stream was/is online 2H ago, no need to check it on the API side.
                        continue
                result = (channel[0],channel[1],channel[2])
                task = asyncio.ensure_future(self.checkForLiveStream(result))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
        self.bot.twitchCheckerPing = time.time() - startTime

    @taskTwitchStream.before_loop
    async def waitTillBotReady(self):
        print('Waiting for bot..')
        await self.bot.wait_until_ready()
    
    async def checkForLiveStream(self,resultSet):
        header = await self.getHeader()
        tasksNotify = []
        tasksLastStreamed = []
        async with self.bot.web_client.get(TWITCH_API_STREAMS_ID.format(resultSet[0]),headers = header) as r:
            result = await r.json()
            if len(result['data']) == 0:
                #Offline!
                return
            jsonData = result['data'][0]

            #Already Posted the Stream:
            if resultSet[2] == jsonData['started_at']:
                return
            resultSetStream = (jsonData['user_id'],jsonData['user_name'],jsonData['game_name'],jsonData['title'],jsonData['viewer_count'],jsonData['started_at'],jsonData['thumbnail_url'])
            async with self.bot.db_client.cursor() as cursor :
                await cursor.execute(''' SELECT * FROM TwitchNotifierDiscordChannel WHERE NotifierBroadcasterID =?
                                    ''',resultSet[0])
                result = await cursor.fetchall()
                for discordChannel in result:
                    resultDiscord=(discordChannel[1],discordChannel[2],discordChannel[3])
                    taskNotify = asyncio.ensure_future(self.notifyLiveStream(resultSetStream,resultDiscord))
                    taskLastStreamed = asyncio.ensure_future(self.updateLastStreamed(resultSetStream))
                    tasksNotify.append(taskNotify)
                    tasksLastStreamed.append(taskLastStreamed)
        await asyncio.gather(*tasksNotify,return_exceptions=True)
        await asyncio.gather(*tasksLastStreamed,return_exceptions=True)

    async def notifyLiveStream(self,resultSetStream,discordResultSet):
        header = await self.getHeader()
        async with self.bot.web_client.get(TWITCH_API_USERS_ID.format(resultSetStream[0]),headers=header) as r:
            jsonData = await r.json()
            streamUrl= f"https://www.twitch.tv/{resultSetStream[1]}"
            thumbnail =f'{resultSetStream[6]}?r={random.randint(1,100000000)}'
            profileImage = jsonData['data'][0]['profile_image_url']
            channel = self.bot.get_channel(int(discordResultSet[1]))
            embed = discord.Embed(title=resultSetStream[3],url=streamUrl, type="rich", color=EMBED_COLOR)
            embed.set_author(name=resultSetStream[1])
            embed.set_thumbnail(url = profileImage)
            embed.add_field(name="Game",value=resultSetStream[2], inline=True)
            embed.add_field(name="Viewers",value=resultSetStream[4])
            embed.set_image(url=thumbnail.format(width=320,height=180))
            await channel.send(f'<@&{discordResultSet[2]}> {resultSetStream[1]} is now live! go check it out: {streamUrl} ',embed=embed)


    async def updateLastStreamed(self,resultLastStreamed):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' UPDATE TwitchNotifierChannel SET TimeStreamStarted =? WHERE BroadcasterID =?
                                ''',resultLastStreamed[5],resultLastStreamed[0])
            await self.bot.db_client.commit()


    
    async def getStreamInfo(self,channelID):
        header = await self.getHeader()
        async with self.bot.web_client.get(TWITCH_API_STREAMS_ID.format(channelID), headers = header) as r:
            jsonData = await r.json()
            if len(jsonData['data']) != 0:
                return jsonData
            return None
    
    async def getTwitchProfileInfo(self,username = None,id = None):
        header = await self.getHeader()
        if id != None:
            url = TWITCH_API_USERS_ID
        else:
            url = TWITCH_API_USERS_LOGIN
        async with self.bot.web_client.get(url.format(id if id else username), headers = header) as r:
            return await r.json()

    async def getHeader(self):
        return {'Client-Id': config.TWITCH_API_CHANNEL_ID, 'Authorization' : "Bearer " +str(self.authToken)}

async def setup(bot):
    await bot.add_cog(twitch(bot))