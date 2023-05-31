import discord
from discord.ext import commands
from discord import app_commands, Interaction
import bs4
import calendar



URL = "https://dofuswiki.fandom.com/wiki/Almanax/Offerings"


class almanaxAdmin(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    

    async def cog_app_command_error(self,interaction,error):
        print('Error in {0}: {1}'.format(interaction, error))

    
    @app_commands.command(name="createalmanaxtable",description="re-creates the alamanx rewards/offering database")
    async def createAlmanaxTable(self,interaction: Interaction):
        async with self.bot.web_client.get(URL) as res:
            html = await res.text()
            soup = bs4.BeautifulSoup(html,"lxml")
            table = soup.find_all("table")


            async with self.bot.db_client.cursor() as cursor:
                #monthnumber = i+1
                tasks= []
                for i, tableMonths in enumerate(table):
                    monthName = calendar.month_name[i+1]

                    await cursor.execute('''CREATE TABLE IF NOT EXISTS {month}(
                                        Day PRIMARY KEY NOT NULL UNIQUE , Goddess Text NOT NULL,Offering Text NOT NULL, Kamas Integer NOT NULL, GoddessBonus Text NOT NULL
                                        )'''.format(month=monthName))

                    days = tableMonths.find_all("tr")
                    for i, days in enumerate(days[1:]):
                        day = i +1
                        data = days.find_all("td")
                        goddess = data[1].text
                        offering = data[2]
                        kamas = data[3].text
                        bonus = data[4].text

                        await cursor.execute('''INSERT OR IGNORE INTO {month} values(?,?,?,?,?)
                                            '''.format(month=monthName),day,goddess,offering.text,kamas,bonus)
                await self.bot.db_client.commit()
        await interaction.response.send_message("Almanax-Database Created")




async def setup(bot):
    await bot.add_cog(almanaxAdmin(bot),guilds=[discord.Object(id=745495001622118501)])