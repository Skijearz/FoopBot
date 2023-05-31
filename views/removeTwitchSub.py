import  discord
from discord.ext import commands

class removeTwitchSubDropDown(discord.ui.Select):
    def __init__(self,bot):
        self.bot = bot
        options= [
        ]
        super().__init__(placeholder="Choose the Twitch-Channel you want to remove from the notifier",max_values=1,options=options)

    async def callback(self,interaction:discord.Interaction):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' DELETE FROM TwitchNotifierDiscordChannel WHERE DiscordGuild=? AND NotifierBroadcasterID =?
                                ''',(interaction.guild_id,self.values[0]))
            await self.bot.db_client.commit()
        for option in self.options:
            if option.value == self.values[0]:
                title = option.label
        url = f"https://www.twitch.tv/{title}"
        await self.checkIfChannelRemove(self.values[0])
        await interaction.response.send_message(f"Unsubscribed: {url}")
        await interaction.followup.delete_message(interaction.message.id)
        

    async def checkIfChannelRemove(self,channelID: str):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' SELECT COUNT(*) FROM TwitchNotifierDiscordChannel WHERE NotifierBroadcasterID =?
                                ''',(channelID))
            result = await cursor.fetchone()
            if result[0] == 0:
                await cursor.execute(''' DELETE FROM TwitchNotifierChannel WHERE BroadcasterID =?
                                    ''',(channelID))
                await self.bot.db_client.commit()


class removeTwitchSubView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.timeout = 30
    async def on_timeout(self) -> None:
        self.stop()
        return await super().on_timeout()