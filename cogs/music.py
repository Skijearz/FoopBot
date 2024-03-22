import discord
from discord.ext import commands
import random
import asyncio
import itertools
import sys
import traceback
from async_timeout import timeout
from functools import partial

import yt_dlp
from yt_dlp import YoutubeDL 
import os

from discord import app_commands, Interaction

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda:''

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    'before_options': '-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)


class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')
        self.duration = data.get('duration')

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, interaction: Interaction, search: str, *, loop, download=False):

        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        embed = discord.Embed(title="", description=f"Queued [{data['title']}]({data['webpage_url']}) [{interaction.user.mention}]", color=discord.Color.green())
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.defer()
            await interaction.followup.send(embed=embed)

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': interaction.user, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source,**ffmpegopts), data=data, requester=interaction.user)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url'],**ffmpegopts), data=data, requester=requester)


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self,bot, interaction,cog):
        self.bot = bot
        self._guild = interaction.guild
        self._channel = interaction.channel
        self._cog = cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        self.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            embed = discord.Embed(title="Now playing", description=f"[{source.title}]({source.web_url}) [{source.requester.mention}]", color=discord.Color.green())
            self.np = await self._channel.send(embed=embed)
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            # source.cleanup()
            self.current = None

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass



    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, interaction):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[interaction.guild_id]
        except KeyError:
            player = MusicPlayer(self.bot,interaction,self)
            self.players[interaction.guild_id] = player

        return player

    @app_commands.command(name='join', description="connects to voice")
    async def connect_(self, interaction: Interaction, *, channel: discord.VoiceChannel=None):
        await self.selfConnect(interaction,channel)

    async def selfConnect(self,interaction: Interaction,channel: discord.VoiceChannel=None):
        """Connect to voice.
        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
            will be made.
        This command also handles moving the bot to different channels.
        """
        if not channel:
            try:
                channel = interaction.user.voice.channel
            except AttributeError:
                embed = discord.Embed(title="", description="No channel to join. Please call `,join` from a voice channel.", color=discord.Color.green())
                await interaction.response.send_message(embed=embed)
                raise InvalidVoiceChannel('No channel to join. Please either specify a valid channel or join one.')

        vc = interaction.guild.voice_client
        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')
        await interaction.response.send_message(f'**Joined `{channel}`**')
        if (random.randint(0, 1) == 0):
            message = await interaction.original_response()
            await message.add_reaction('👍')


    @app_commands.command(name='play', description="streams music")
    async def play_(self, interaction: Interaction, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search and retrieve a song.
        Parameters
        ------------
        search: str [Required]
            The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """
        #if "youtube" not in search:
        #    return await interaction.response.send_message("```Other links than Youtube links arent supported!```")
        vc = interaction.guild.voice_client

        if not vc:
            await self.selfConnect(interaction)

        player = self.get_player(interaction)

        # If download is False, source will be a dict which will be used later to regather the stream.
        # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
        source = await YTDLSource.create_source(interaction, search, loop=self.bot.loop, download=False)

        await player.queue.put(source)
        
    @app_commands.command(name='pause', description="pauses music")
    async def pause_(self,interaction: Interaction):
        """Pause the currently playing song."""
        vc = interaction.guild.voice_client

        if not vc or not vc.is_playing():
            embed = discord.Embed(title="", description="I am currently not playing anything", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)
        elif vc.is_paused():
            return

        vc.pause()
        await interaction.response.send_message("Paused ⏸️")

    @app_commands.command(name='resume', description="resumes music")
    async def resume_(self,interaction: Interaction):
        """Resume the currently paused song."""
        vc = interaction.guild.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)
        elif not vc.is_paused():
            return

        vc.resume()
        await interaction.response.send_message("Resuming ⏯️")

    @app_commands.command(name='skip', description="skips to next song in queue")
    async def skip_(self,interaction: Interaction,):
        """Skip the song."""
        vc = interaction.guild.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        embed = discord.Embed(title="", description="**{0}** just skipped the song!".format(interaction.user), color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name='remove', description="removes specified song from queue")
    async def remove_(self,interaction:Interaction, pos : int=None):
        """Removes specified song from queue"""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)

        player = self.get_player(interaction)
        if pos == None:
            player.queue._queue.pop()
        else:
            try:
                s = player.queue._queue[pos-1]
                del player.queue._queue[pos-1]
                embed = discord.Embed(title="", description=f"Removed [{s['title']}]({s['webpage_url']}) [{s['requester'].mention}]", color=discord.Color.green())
                await interaction.response.send_message(embed=embed)
            except:
                embed = discord.Embed(title="", description=f'Could not find a track for "{pos}"', color=discord.Color.green())
                await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name='clear',  description="clears entire queue")
    async def clear_(self,interaction: Interaction):
        """Deletes entire queue of upcoming songs."""

        vc = interaction.guild.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)

        player = self.get_player(interaction)
        player.queue._queue.clear()
        await interaction.response.send_message('**Cleared**')

    @app_commands.command(name='queue', description="shows the queue")
    async def queue_info(self, interaction: Interaction):
        """Retrieve a basic queue of upcoming songs."""
        vc = interaction.guild.voice_client
        print(vc.is_connected())


        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)

        player = self.get_player(interaction)
        if player.queue.empty():
            embed = discord.Embed(title="", description="queue is empty", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)

        seconds = vc.source.duration % (24 * 3600) 
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        if hour > 0:
            duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
        else:
            duration = "%02dm %02ds" % (minutes, seconds)

        # Grabs the songs in the queue...
        upcoming = list(itertools.islice(player.queue._queue, 0, int(len(player.queue._queue))))
        fmt = '\n'.join(f"`{(upcoming.index(_)) + 1}.` [{_['title']}]({_['webpage_url']}) | ` {duration} Requested by: {_['requester']}`\n" for _ in upcoming)
        fmt = f"\n__Now Playing__:\n[{vc.source.title}]({vc.source.web_url}) | ` {duration} Requested by: {vc.source.requester}`\n\n__Up Next:__\n" + fmt + f"\n**{len(upcoming)} songs in queue**"
        embed = discord.Embed(title=f'Queue for {interaction.guild.name}', description=fmt, color=discord.Color.green())
        embed.set_footer(text=f"{interaction.user.display_name}", icon_url=interaction.user.avatar)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='np', description="shows the current playing song")
    async def now_playing_(self,interaction: Interaction):
        """Display information about the currently playing song."""
        vc = interaction.guild.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)

        player = self.get_player(interaction)
        if not player.current:
            embed = discord.Embed(title="", description="I am currently not playing anything", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)
        
        seconds = vc.source.duration % (24 * 3600) 
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        if hour > 0:
            duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
        else:
            duration = "%02dm %02ds" % (minutes, seconds)

        embed = discord.Embed(title="", description=f"[{vc.source.title}]({vc.source.web_url}) [{vc.source.requester.mention}] | `{duration}`", color=discord.Color.green())
        embed.set_author(icon_url=self.bot.user.avatar, name=f"Now Playing 🎶")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='volume', description="changes Kermit's volume")
    async def change_volume(self,interaction: Interaction, *, vol: float=None):
        """Change the player volume.
        Parameters
        ------------
        volume: float or int [Required]
            The volume to set the player to in percentage. This must be between 1 and 100.
        """
        vc = interaction.guild.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I am not currently connected to voice", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)
        
        if not vol:
            embed = discord.Embed(title="", description=f"🔊 **{(vc.source.volume)*100}%**", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)

        if not 0 < vol < 101:
            embed = discord.Embed(title="", description="Please enter a value between 1 and 100", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)

        player = self.get_player(interaction)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        embed = discord.Embed(title="", description=f'**`{interaction.user}`** set the volume to **{vol}%**', color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='leave', description="stops music and disconnects from voice")
    async def leave_(self,interaction: Interaction):
        """Stop the currently playing song and destroy the player.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = interaction.guild.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=discord.Color.green())
            return await interaction.response.send_message(embed=embed)
        await interaction.response.send_message('**Successfully disconnected**')
        if (random.randint(0, 1) == 0):
            message = await interaction.original_response()
            await message.add_reaction('👋')
        
        await self.cleanup(interaction.guild)


async def setup(bot):
    await bot.add_cog(Music(bot))