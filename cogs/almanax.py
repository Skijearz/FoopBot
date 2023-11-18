import asqlite
import discord
from discord.ext import commands
from discord import app_commands, Interaction
from datetime import datetime
import calendar
from lxml import html
EMBED_COLOR = 0xebeb33
ALMANAX_URL = "https://www.krosmoz.com/en/almanax"
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
headers={'accept-language' :'en-US,en;q=0.9','Cache-Control': 'no-cache','User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'}


class almanax(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    async def cog_app_command_error(self,interaction,error):
        print('Error in {0}: {1}'.format(interaction, error))

    @app_commands.command(name="almanax",description="Get todays Almanax Offering, Kamas Reward and Goddess Bonus")
    async def almanax(self,interaction: Interaction):
        today = datetime.now()
        day = today.day
        month = today.month
        monthName = calendar.month_name[month]
        await self.getAlmanax(interaction,day,monthName) 


    async def getAlmanax(self,interaction: Interaction,day : int, monthName: str):
        async with self.bot.db_client.cursor() as cursor:
            await cursor.execute(''' SELECT * FROM {month} where day =?
                                '''.format(month=monthName),(day))
            almanaxToday = await cursor.fetchall()
            
            embed = discord.Embed(title=f'Almanax for {monthName} {day} :calendar_spiral: ', type="rich", color=EMBED_COLOR)
            for rows in almanaxToday:
                goddess = rows[1]
                offering = rows[2]
                kamas = rows[3]
                goddessBonus = rows[4]
                img_url = None
                async with self.bot.web_client.get(ALMANAX_URL) as res:
                    print(await res.text())
                    tree = html.fromstring(await res.text())
                    img_url = tree.xpath('//*[@class="more-infos-content"]/img/@src')
                    print(img_url)
                    print(img_url[0])
                embed.add_field(name=f"Offering for {goddess}", value=offering,inline=False)
                embed.add_field(name="Kamas Reward", value=kamas,inline=False)
                embed.add_field(name="Bonus", value=goddessBonus)
                #embed.set_thumbnail(url=img_url[0])
            await interaction.response.send_message(embed=embed) 


async def setup(bot):
    await bot.add_cog(almanax(bot))