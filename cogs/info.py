from discord.ext import commands, tasks
from discord import app_commands, Interaction
import time
import discord
import random
import math

EMBED_COLOR = 0x4aa3f2

class info(commands.Cog):
    def __init__(self,bot):
        self.bot = bot 
        self.bot.timeSinceStart = time.time()
        self.changeStatus.start()
    
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: Interaction, command: discord.app_commands.Command):
        self.bot.wishesGranted += 1

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        return await super().cog_app_command_error(interaction, error)

    @app_commands.command(name="info", description="Show some Information about Foop")
    async def info(self, interaction: Interaction):
        print(f' yt :{self.bot.youtubeCheckerPing}')
        hours, rem = divmod(time.time()- self.bot.timeSinceStart,3600)
        minutes, seconds = divmod(rem,60)
        botOwner = self.bot.appInfo.owner
        amountGuilds = len(self.bot.guilds)
        embed = discord.Embed(title=f'{self.bot.user.name} Stats', type="rich", color=EMBED_COLOR)
        #embed.set_thumbnail(url=self.bot.appInfo.icon.url)
        embed.add_field(name="Anti-Fairly Oddparent of: ",value=botOwner,inline=False)
        embed.add_field(name="#Server im watching: ",value=amountGuilds,inline=True)
        embed.add_field(name="#User im watching", value=len(self.bot.users),inline=True)
        embed.add_field(name="Bot-Version",value=self.bot.bot_version, inline=True)
        embed.add_field(name="Python Version",value=self.bot.python_version, inline=True)
        embed.add_field(name="Discordpy Version",value=discord.__version__, inline=True)
        embed.add_field(name="YT-Announcer Ping",value=str(math.ceil(self.bot.youtubeCheckerPing*100))+" ms",inline=True)
        embed.add_field(name="Twitch-Announcer Ping", value=str(math.ceil(self.bot.twitchCheckerPing*100))+" ms",inline=True)
        embed.add_field(name="Wishes granted", value=self.bot.wishesGranted,inline=True)
        embed.add_field(name="I've been alive for", value='{:0>2}h{:0>2}m{:02.0f}s'.format(int(hours),int(minutes),seconds),inline = False)
        embed.set_footer(text="There's a new sheriff in town and his name, unfortunately, is Foop!")
        await interaction.response.send_message(embed=embed)

    @tasks.loop(seconds=300)
    async def changeStatus(self):
        await self.bot.wait_until_ready()
        with open('quotes.txt') as quotes:
            lines = quotes.readlines()
            quote_count = len(lines)
            random_number = random.randint(1,quote_count)
            line= lines[random_number-1]
            game = discord.Game(line)
            await self.bot.change_presence(status=discord.Status.online, activity=game)


async def setup(bot):
    await bot.add_cog(info(bot))