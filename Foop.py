import asyncio
import logging
import logging.handlers
import os
import time
from platform import python_version
import asqlite

from typing import List, Optional

import discord
from discord.ext import commands
from aiohttp import ClientSession


import config

intents = discord.Intents.default()
intents.members = True
__version__ = '0.1.1'
description = 'Anti-Poof'

class Foop(commands.Bot):
    def __init__(
        self,
        *args,
        initial_extensions: List[str],
        web_client: ClientSession,
        testing_guild_id: Optional[int] = None,
        db_client : asqlite.Connection,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.web_client = web_client
        self.db_client = db_client
        self.testing_guild_id = testing_guild_id
        self.initial_extensions = initial_extensions

    async def on_message(self, message: discord.Message, /) -> None:
        if message.author.bot:
            return
        if isinstance(message.channel, discord.DMChannel) and not await self.is_owner(message.author):
            await message.author.send('Der Bot unterstützt keine DMs, bitte nutze den Server dafür!')
            return
        return await super().on_message(message)

    async def on_ready(self):
        self.appInfo = await self.application_info()
        self.time_started = time.time()
        self.youtubeCheckerPing = 0
        self.twitchCheckerPing = 0
        self.bot_version = __version__
        self.description = description
        self.wishesGranted = 0
        self.python_version = python_version()
        self.discordpy_version = discord.__version__
    async def setup_hook(self) -> None:

        for extension in self.initial_extensions:
            await self.load_extension(extension)
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)



async def main():

    if not os.path.isdir("db"):
        os.mkdir("db")


    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename='logs/discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)



    async with ClientSession() as our_client :
        async with asqlite.connect("db/foopDatabase.db") as db_connection:
                db_connection.execute("PRAGMA foreign_keys = ON")
                exts = ['cogs.info','cogs.music','cogs.admin','cogs.almanaxAdmin','cogs.almanax','cogs.youtubeAdmin','cogs.youtube','cogs.twitchAdmin','cogs.twitch','cogs.short','cogs.steam','cogs.steamAdmin']
                async with Foop(commands.when_mentioned_or('!'), web_client=our_client, db_client=db_connection,initial_extensions=exts,intents=intents,testing_guild_id=745495001622118501) as foopBot:

                    await foopBot.start(config.TOKEN)


asyncio.run(main())
