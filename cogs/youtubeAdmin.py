import discord
from discord.ext import commands
from discord import app_commands, Interaction


class youtubeAdmin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    
    async def cog_app_command_error(self,interaction,error):
        print('Error in {0}: {1}'.format(interaction, error))

    @app_commands.command(name="createyoutubetables")
    async def createYoutubeTables(self,interaction: Interaction):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute('''CREATE TABLE IF NOT EXISTS YoutubeNotifierChannel(ChannelID PRIMARY KEY UNIQUE,ChannelName Text,NewestVideoURL Text Not Null, PlaylistID Text Not Null)
                                ''') 
            await cursor.execute(''' CREATE TABLE IF NOT EXISTS YoutubeNotifierDiscordChannel(NotifierChannelID Text Not Null ,DiscordGuild Text,DiscordChannel Text  Not Null, DiscordRoleToMention Text Not Null,
                                FOREIGN KEY(NotifierChannelID) REFERENCES YoutubeNotifierChannel(ChannelID), CONSTRAINT unq UNIQUE (NotifierChannelID, DiscordChannel))
                                ''')
            await self.bot.db_client.commit()
        await interaction.response.send_message("Youtube Notifier Tables created!")



async def setup(bot):
    await bot.add_cog(youtubeAdmin(bot),guilds=[discord.Object(id=745495001622118501)])