from discord.ext import commands
from discord import app_commands, Interaction
import discord


SHORTENER_URL = "https://short.skijearz.xyz"
CREATE_ENDPOINT ="/url"
DELETE_ENDPOINT ="/admin/{secret_key}"
INFO_ENDPOINT ="/admin/{secret_key}"
EMBED_COLOR = 0x9146ff
class short(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        return await super().cog_app_command_error(interaction, error)

    @app_commands.command(name="shorturl", description="Short your URL")
    async def shorturl(self, interaction: Interaction, url: str):
        async with self.bot.web_client.post(SHORTENER_URL+CREATE_ENDPOINT, json={'target_url' : url}) as r:
            if r.status == 200:
                jsonData = await r.json()
                short_url = jsonData['url']
                secret_key = jsonData['secret_key']
                embed = discord.Embed(title="",type="rich", color=EMBED_COLOR)
                embed.add_field(name="Shortened URL ",value=short_url,inline=False)
                embed.set_footer(text=f"Your secret key: {secret_key} keep it secret! You can use it to delete the shortened url or get some infos about your shortened url")
                await interaction.response.send_message(embed=embed,ephemeral=True)

            else:
                await interaction.response.send_message(f"{url} is not a valid URL, please try again with a valid URL")

    @app_commands.command(name="deleteurl", description="Delete your Shortened URL")
    async def deleteurl(self,interaction: Interaction, secret_key:str):
        async with self.bot.web_client.delete(SHORTENER_URL+DELETE_ENDPOINT.format(secret_key=secret_key)) as r:
            if r.status == 200:
                await interaction.response.send_message("Shortened URL deleted!")
            else:
                await interaction.response.send_message("Secretkey is wrong!")


async def setup(bot):
    await bot.add_cog(short(bot))
