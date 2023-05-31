import  discord
from discord.ext import commands

class removeYoutubeSubDropDown(discord.ui.Select):
    def __init__(self,bot):
        self.bot = bot
        options= [
        ]
        super().__init__(placeholder="Choose the Channel you want to remove from the notifier",max_values=1,options=options)

    async def callback(self,interaction:discord.Interaction):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' DELETE FROM YoutubeNotifierDiscordChannel WHERE DiscordGuild=? AND NotifierChannelID =?
                                ''',(interaction.guild_id,self.values[0]))
            await self.bot.db_client.commit()
            url = f"https://www.youtube.com/channel/{self.values[0]}"
        await self.checkIfChannelRemove(self.values[0])
        await interaction.response.send_message(f"Unsubscribed: {url}")
        await interaction.followup.delete_message(interaction.message.id)
        

    async def checkIfChannelRemove(self,channelID: str):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' SELECT COUNT(*) FROM YoutubeNotifierDiscordChannel WHERE NotifierChannelID =?
                                ''',(channelID))
            result = await cursor.fetchone()
            if result[0] == 0:
                await cursor.execute(''' DELETE FROM YoutubeNotifierChannel WHERE ChannelID =?
                                    ''',(channelID))
                await self.bot.db_client.commit()


class removeYoutubeSubView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.timeout = 30
    async def on_timeout(self) -> None:
        self.stop()
        return await super().on_timeout()