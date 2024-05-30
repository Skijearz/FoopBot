import logging
import discord
from discord.ext import commands
from discord import app_commands, Interaction


class youtubeAdmin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')
        self.bot.loop.create_task(self.create_youtube_tables())
    async def cog_app_command_error(self,interaction,error):
        self.logger.log(logging.ERROR,'Error in {0}: {1}'.format(interaction, error))
 
    @app_commands.command(name="createyoutubetables")
    async def createYoutubeTables(self,interaction: Interaction):
        await self.create_youtube_tables()
        await interaction.response.send_message("Youtube Notifier Tables created!")

    async def create_youtube_tables(self):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute('''CREATE TABLE IF NOT EXISTS YoutubeNotifierChannel(ChannelID PRIMARY KEY UNIQUE,ChannelName Text,NewestVideoURL Text Not Null, PlaylistID Text Not Null)
                                ''') 
            await cursor.execute(''' CREATE TABLE IF NOT EXISTS YoutubeNotifierDiscordChannel(NotifierChannelID Text Not Null ,DiscordGuild Text,DiscordChannel Text  Not Null, DiscordRoleToMention Text Not Null,
                                FOREIGN KEY(NotifierChannelID) REFERENCES YoutubeNotifierChannel(ChannelID), CONSTRAINT unq UNIQUE (NotifierChannelID, DiscordChannel))
                                ''')
            await self.bot.db_client.commit()



async def setup(bot):
    await bot.add_cog(youtubeAdmin(bot),guilds=[discord.Object(id=745495001622118501)])