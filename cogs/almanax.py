import asqlite
import discord
from discord.ext import commands
from discord import app_commands, Interaction
from datetime import datetime
from bs4 import BeautifulSoup

EMBED_COLOR = 0xebeb33
DOFUSDB_API_URL = "https://api.dofusdb.fr"
ALAMANX_ENDPOINT = "/almanax?date={month}/{day}/{year}"
QUEST_ENDPOINT = "/quest/{quest_id}"
ITEM_ENDPOINT = "/items/{item_id}"

SEARCH_FOR_QUEST_FROM_ALMANAX = "/quests?startCriterion[$regex]=Ad={almanax_id}"

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
headers={'accept-language' :'en-US,en;q=0.9','Cache-Control': 'no-cache','User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'}


class almanax(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    async def cog_app_command_error(self,interaction,error):
        print('Error in {0}: {1}'.format(interaction, error))

    @app_commands.command(name="almanax",description="Get todays or Date specific Almanax Offering, Kamas Reward and Goddess Bonus")
    @app_commands.describe(user_specified_date = "Date Format DD/MM/YYYY")
    @app_commands.rename(user_specified_date="date")
    async def almanax(self,interaction: Interaction, user_specified_date:None |str):
        await interaction.response.defer()
        if user_specified_date is None:
            today = datetime.now()
            day = today.day
            month = today.month
            year = today.year
        else:
            date = user_specified_date.split("/")
            if(len(date[0]) != 2 or len(date[1]) != 2 or len(date[2]) != 4):
                #wrong date format
                await interaction.followup.send("Wrong Dateformat try with DD/MM/YYYY e.g 4/11/2024")
                return
            day = int(date[0])
            month = int(date[1])
            year = int(date[2])
        embed = await self.getAlmanax(month,day,year)
        await interaction.followup.send(embed=embed) 


    async def getAlmanax(self,month:int,day : int, year: int) -> discord.Embed:
        #EVTL AUF discord.py mit voice support wechseln, gerade ohne installiert nicht sicher ob bot funktional!

        almanax_api_object = await self.get_almanax(month,day,year)
        almanax_quest = await self.get_quest_from_almanax_id(almanax_api_object['id'])
        almanax_quest_id = almanax_quest['data'][0]['id']
        almanax_item_id = almanax_quest['data'][0]['steps'][0]['objectives'][0]['need']['generated']['items'][0]
        almanax_item = await self.get_almanax_item_from_id(almanax_item_id)

        #Item Relevant Info
        almanax_item_name = almanax_item['name']['en']
        almanax_item_image = almanax_item['imgset'][-1]['url']
        almanax_item_quantity = almanax_quest['data'][0]['steps'][0]['objectives'][0]['need']['generated']['quantities'][0]

        #Queste relevant Info
        almanax_goddess = almanax_quest['data'][0]['name']['en']
        almanax_bonus = BeautifulSoup(almanax_api_object['desc']['en'],"html.parser").text
        almanax_almoken_quantity = almanax_quest['data'][0]['steps'][0]['rewards'][-1]['itemsReward'][0][1]

        alamanax_embed  = discord.Embed(title=f'Almanax for {day} {month} {year}',url=f"https://dofusdb.fr/en/database/quest/{almanax_quest_id}", type="rich", color=EMBED_COLOR)
        alamanax_embed.set_thumbnail(url=almanax_item_image)
        alamanax_embed.set_author(name='Almanax')
        alamanax_embed.add_field(name="Bonus", value=f"> {almanax_bonus}", inline=False)
        alamanax_embed.add_field(name=almanax_goddess,value=f"{almanax_item_quantity} {almanax_item_name}", inline=False)
        alamanax_embed.add_field(name="Rewards for Level 200", value=f"{almanax_almoken_quantity}x Almoken", inline=False)

        return alamanax_embed

    async def get_almanax(self,month: int, day:int, year: int ) -> dict:
        async with self.bot.web_client.get(DOFUSDB_API_URL+ ALAMANX_ENDPOINT.format(month = month,day = day, year=year )) as res:
            return await res.json()
        
    async def get_quest_from_almanax_id(self,almanax_id:int) -> dict:
        async with self.bot.web_client.get(DOFUSDB_API_URL + SEARCH_FOR_QUEST_FROM_ALMANAX.format(almanax_id=almanax_id)) as res:
            return await res.json()
    async def get_almanax_item_from_id(self, almanax_item_id: int) -> dict:
        async with self.bot.web_client.get(DOFUSDB_API_URL + ITEM_ENDPOINT.format(item_id=almanax_item_id)) as res:
            return await res.json()

async def setup(bot):
    await bot.add_cog(almanax(bot))