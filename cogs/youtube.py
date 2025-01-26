import logging
import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import config
import asqlite
from views.removeYTSub import removeYoutubeSubView,removeYoutubeSubDropDown
import asyncio
from datetime import datetime, timedelta
import time

URL_VIDEO = "https://www.googleapis.com/youtube/v3/videos?part=snippet&id={videoID}&key={API_KEY}"
URL_PLAYLIST_ID = "https://youtube.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={PLAYLIST_ID}&key={API_KEY}"
URL_CHANNEL = "https://youtube.googleapis.com/youtube/v3/channels?part=snippet%2CcontentDetails&id={CHANNEL_ID}&key={API_KEY}"
EMBED_COLOR = 0xff0000
user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
headers={'accept-language' :'en-US,en;q=0.9','Cache-Control': 'no-cache','User-Agent' : user_agent}

class youtube(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.taskYoutubeNotifier.start()
        self.logger = logging.getLogger('discord')
    async def cog_app_command_error(self,interaction,error):
        self.logger.log(logging.ERROR,'Error in {0}: {1}'.format(interaction, error))

    async def interaction_check(self,interaction: Interaction):
        if interaction.user == self.bot.appInfo.owner:
            return True
        if not interaction.user.guild_permissions.administrator:
           await interaction.response.send_message("You dont have the required Permissions",ephemeral=True)
           return False
        return True

    @app_commands.command(name="subyt", description="Subscribes to a YT-Channel to notify when a new Video gets released")
    async def subscribeYtChannel(self,interaction:Interaction, youtubechannelvideo: str ,channel: discord.TextChannel,role : discord.Role):
        channelID = await self.getChannelIDfromURL(youtubechannelvideo)
        if channelID is None:
            return await interaction.response.send_message("Could not retrieve ChannelID, please provide a valid Youtube Video URL")
        channelName = await self.getChannelName(channelID)
        if channelName is None:
            return await interaction.response.send_message("Could not retrieve Channel Name")
        playlistID = await self.getPlayListID(channelID)
        if playlistID is None:
            return await interaction.response.send_message("Could not retrieve PlaylistID")
        newestVideoID = (await self.getNewestVideo(playlistID))[0]
        if newestVideoID is None:
            return await interaction.response.send_message("Could not retrieve newest video")
        
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' INSERT OR IGNORE INTO YoutubeNotifierChannel values(?,?,?,?)
                                ''',(channelID,channelName,newestVideoID,playlistID))
            await cursor.execute(''' INSERT OR IGNORE INTO YoutubeNotifierDiscordChannel values(?,?,?,?)
                                ''',(channelID,interaction.guild_id,channel.id,role.id))
            await self.bot.db_client.commit()
        url = "https://www.youtube.com/channel/{CHANNEL_ID}"
        await interaction.response.send_message("Subscribed to: " + url.format(CHANNEL_ID=channelID))

    @app_commands.command(name="youtubesublist", description="Show all YoutubeChannels Subscribed on this Discord-Server")
    async def youtubeSubList(self,interaction: Interaction):
        async with self.bot.db_client.cursor()as cursor:
            await cursor.execute(''' SELECT * FROM YoutubeNotifierDiscordChannel where DiscordGuild =?
                                ''',(interaction.guild_id))
            result = await cursor.fetchall()
            embed = discord.Embed(title=f'Subscribed Youtube Channels ', type="rich", color=EMBED_COLOR)
            value: str = ""
            if len(result) == 0:
                return await interaction.response.send_message("No Youtube Channel Subscribed")
            for channel in result:
                name = await self.getChannelName(channel[0])
                value += name+"\n"
            embed.add_field(name="",value=value)
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="removeytsub", description="removes the selcted channel from the notifier list")
    async def removeYoutubeSub(self,interaction: Interaction):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute('''SELECT YoutubeNotifierChannel.ChannelID, YoutubeNotifierChannel.ChannelName FROM  YoutubeNotifierChannel INNER JOIN YoutubeNotifierDiscordChannel ON YoutubeNotifierChannel.ChannelID = YoutubeNotifierDiscordChannel.NotifierChannelID WHERE YoutubeNotifierDiscordChannel.DiscordGuild = ?
                                ''',(interaction.guild_id))
            result = await cursor.fetchall()
            if len(result) == 0:
                return await interaction.response.send_message("No Youtube Channel Subscribed")
            view = removeYoutubeSubView()
            select = removeYoutubeSubDropDown(self.bot)
            for channel in result:
                select.add_option(label=channel[1],value=channel[0])
            view.add_item(select)
        
        await interaction.response.send_message(view=view,ephemeral=True)

    @tasks.loop(seconds=300)
    async def taskYoutubeNotifier(self):
        startTime = time.time()
        tasks = []
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' SELECT * FROM YoutubeNotifierChannel
                                ''')
            result = await cursor.fetchall()
            if len(result) == 0:
                return
            for channel in result:
                channelID = channel[0]
                newestVideo = channel[2]
                playlistID = channel[3]
                resultList=(channelID,newestVideo,playlistID)
                task = asyncio.ensure_future(self.checkForNewVideo(resultList))
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
        self.bot.youtubeCheckerPing = time.time() - startTime
        

    async def checkForNewVideo(self,resultList):
        result  = await self.getNewestVideo(resultList[2])
        newestVideo = result[0]
        publishedAt = result[1]
        if newestVideo == resultList[1]:
            return
        await self.storeNewVideo(resultList[0],newestVideo)
        d2 = datetime.today()
        enddate = d2 - timedelta(days=5)
        enddate = enddate.strftime('%Y-%m-%dT%H:%M:%SZ')
        if enddate > publishedAt:
            return
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' SELECT YoutubeNotifierChannel.ChannelID, YoutubeNotifierDiscordChannel.DiscordChannel,YoutubeNotifierDiscordChannel.DiscordRoleTomention 
                                    FROM YoutubeNotifierChannel 
                                    INNER JOIN YoutubeNotifierDiscordChannel 
                                    ON YoutubeNotifierChannel.ChannelID = YoutubeNotifierDiscordChannel.NotifierChannelID WHERE YoutubeNotifierDiscordChannel.NotifierChannelID =?
                                ''',(resultList[0]))
            result = await cursor.fetchall()
            if len(result) == 0:
                return
            tasks=[]
            for channel in result:
                channelid = resultList[0]
                discordChannel = channel[1]
                discordRoleToMention = channel[2]
                resultlist= (channelid,discordChannel,discordRoleToMention,newestVideo)
                task = asyncio.ensure_future(self.postNewVideo(resultlist))
                tasks.append(task)
            await asyncio.gather(*tasks,return_exceptions=True)

    @taskYoutubeNotifier.before_loop
    async def waitTillBotReady(self):
        await self.bot.wait_until_ready()

    async def postNewVideo(self,resultlist):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(int(resultlist[1]))
        url = f"https://www.youtube.com/watch?v={resultlist[3]}"
        if await self.isVideoShort(resultlist[3]):
            return
        await channel.send(f"<@&{resultlist[2]}> New Video just got released! {url}")

        
    
############################################################################################## HELPER FUNCTIONS ###################################################
    async def isVideoShort(self,videoID):
        url = f'https://www.youtube.com/shorts/{videoID}'
        async with self.bot.web_client.head(url,headers=headers,cookies={"SOCS": "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg"}) as r:
            return r.status == 200
            
    async def getChannelName(self,ChannelID):
        async with self.bot.web_client.get(URL_CHANNEL.format(CHANNEL_ID=ChannelID,API_KEY=config.YOUTUBE_API_TOKEN),headers=headers) as r:
            if r.status == 200:
                jsonData = await r.json()
                return jsonData['items'][0]['snippet']['title']
    async def storeNewVideo(self,ChannelID,url):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' UPDATE YoutubeNotifierChannel SET NewestVideoURL =? WHERE ChannelID =?
                                ''',(url,ChannelID))
            await self.bot.db_client.commit()
    async def getNewestVideo(self,playlistID):
        async with self.bot.web_client.get(URL_PLAYLIST_ID.format(PLAYLIST_ID=playlistID,API_KEY=config.YOUTUBE_API_TOKEN),headers=headers) as r:
            if r.status == 200:
                jsonData = await r.json()
                return (jsonData['items'][0]['contentDetails']['videoId'],jsonData['items'][0]['contentDetails']['videoPublishedAt'])
            return None
    async def getPlayListID(self,ChannelID):
        async with self.bot.web_client.get(URL_CHANNEL.format(CHANNEL_ID=ChannelID,API_KEY=config.YOUTUBE_API_TOKEN),headers=headers) as r:
            if r.status == 200:
                jsonData = await r.json()
                return jsonData['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            return None

    async def getChannelIDfromURL(self,url):
        if "watch" in url:
            videoId = url.split("/")[-1].split("=")[-1]
            async with self.bot.web_client.get(URL_VIDEO.format(videoID=videoId,API_KEY=config.YOUTUBE_API_TOKEN),headers=headers) as r:
                if r.status == 200:
                    jsonData = await r.json()
                    return jsonData['items'][0]['snippet']['channelId']
                return None
        else:
            return None

async def setup(bot):
    await bot.add_cog(youtube(bot))
