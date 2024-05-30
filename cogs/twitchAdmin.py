import logging
import discord
from discord.ext import commands
from discord import app_commands, Interaction


class twitchAdmin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.logger = logging.getLogger('discord')
        self.bot.loop.create_task(self.create_twitch_tables())
    
    async def cog_app_command_error(self,interaction,error):
        self.logger.log(logging.ERROR,'Error in {0}: {1}'.format(interaction, error))

    @app_commands.command(name="createtwitchtables")
    async def createTwitchTables(self,interaction: Interaction):
        await self.create_twitch_tables()
        await interaction.response.send_message("Twitch Notifier Tables created!")

    async def create_twitch_tables(self):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute('''CREATE TABLE IF NOT EXISTS TwitchNotifierChannel(BroadcasterID PRIMARY KEY UNIQUE,ChannelName Text,TimeStreamStarted Text)
                                ''') 
            await cursor.execute(''' CREATE TABLE IF NOT EXISTS TwitchNotifierDiscordChannel(NotifierBroadcasterID Text Not Null ,DiscordGuild Text,DiscordChannel Text  Not Null, DiscordRoleToMention Text Not Null,
                                FOREIGN KEY(NotifierBroadcasterID) REFERENCES TwitchNotifierChannel(BroadcasterID), CONSTRAINT unq UNIQUE (NotifierBroadcasterID, DiscordChannel))
                                ''')
            await self.bot.db_client.commit()



async def setup(bot):
    await bot.add_cog(twitchAdmin(bot),guilds=[discord.Object(id=745495001622118501)])