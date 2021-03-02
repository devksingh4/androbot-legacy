
import asyncio
import functools
import itertools
import math
import random

import discord
import youtube_dl
from async_timeout import timeout
from discord.ext import commands

from playlist import getPlaylistLinks, isYTPlaylist

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''
class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass

class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 1):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester', 'url')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester
        self.url = self.source.url

    def create_embed(self, title="Now Playing"):
        if not self.source.duration:
            self.source.duration = 'LIVE'
        embed = (discord.Embed(title=title,
                            description='```css\n{0.source.title}\n```'.format(self),
                            color=discord.Color.blurple())
                .add_field(name='Duration', value=self.source.duration)
                .add_field(name='Requested by', value=self.requester.mention)
                .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                .add_field(name='URL', value='[Click]({0.url})'.format(self))
                .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx
        self.exists = True
        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 1
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    self.exists = False
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}
    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state or not state.exists:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    def write_user_song(self, author, song):
        try:
            with open(f'playlists/{author}.txt', "a") as f:
                f.write(f'{song}\n')
            return True
        except:
            return False
    def overwrite_user_songs(self, author, songs):
        try:
            with open(f'playlists/{author}.txt', "w") as f:
                f.writelines(songs)
                f.writelines(['\n'])
            return True
        except:
            return False
    def get_user_playlist(self, author):
        try:
            with open(f'playlists/{author}.txt', "r") as f:
                return list(map(lambda x: x.strip(), f.readlines()))
        except:
            return False

    def remove_user_playlist(self, author, index):
        try:
            playlist = self.get_user_playlist(author=author)
            playlist.pop(index)
            self.overwrite_user_songs(author, playlist)
            return True
        except:
            return False

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='summon')
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume')
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='now', aliases=['current', 'playing', 'np'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""
        try:
            realembed = ctx.voice_state.current.create_embed()
            await ctx.send(embed=realembed)
        except AttributeError:
            embed = (discord.Embed(title='Nothing playing',
                               description='Add a song with ?play',
                               color=discord.Color.red()))
            await ctx.send(embed=embed)

    @commands.command(name='pause')
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester or ("dj" in [y.name.lower() for y in ctx.message.author.roles]):
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()
        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 2:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/2**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            embed = (discord.Embed(title='Nothing in the queue',
                description='Add a song with ?play',
                color=discord.Color.red()))
            return await ctx.send(embed=embed)

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            try:
                queue += '`{0}.` [**{1.source.title}**]({1.url})\n'.format(i + 1, song)
            except:
                queue += '`{0}.` {1.source.title}\n'.format(i + 1, song)
        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, max(pages, 1))))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')
        
    @commands.command(name='move')
    async def _move(self, ctx: commands.Context, old: int, new: int):
        """Removes a song from the queue at a given index."""
        lenq = len(ctx.voice_state.songs)
        if lenq == 0:
            return await ctx.send('Empty queue.')
        if lenq < old or lenq < new or old < 1 or new < 1:
            return await ctx.send('Index too large.')
        temp = list(ctx.voice_state.songs)
        temp.insert(new - 1, temp.pop(old -1))
        tempqueue = SongQueue()
        for item in temp:
            tempqueue.put_nowait(item)    
        ctx.voice_state.songs = tempqueue
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.
        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')
    @commands.command(name='save')
    async def _addToSaved(self, ctx: commands.Context, *, song_query: str):
        """Add a song to your saved playlist."""
        author = ctx.message.author.id
        if isYTPlaylist(song_query):
            links = getPlaylistLinks(song_query)
            for query in links:
                rval = self.write_user_song(author, query)
                if rval:
                    if ctx.voice_state.voice:
                        await ctx.voice_state.songs.put(query)
                    return
                else:
                    return await ctx.send(f'"{song_query}" could not be added to your playlist. Please, try again.')
            return await ctx.send(f"Enqueued {len(links)} songs.")
        else:
            try:
                source = await YTDLSource.create_source(ctx, song_query, loop=False)
                song = Song(source)
            except Exception as e:
                print(e)
                return await ctx.send(f'"{song_query}" could not be added to your playlist. Please, try again.')
            rval = self.write_user_song(author, song_query)
            if rval:
                await ctx.send(embed=song.create_embed(title="Song added to playlist"))
                if ctx.voice_state.voice:
                    await ctx.voice_state.songs.put(song)
                return
            else:
                return await ctx.send(f'"{song_query}" could not be added to your playlist. Please, try again.')

    @commands.command(name='playSaved')
    async def _playFromSaved(self, ctx: commands.Context):
        """Add songs from your saved to the current playlist."""
        author = ctx.message.author.id
        if not ctx.voice_state.voice:
            try:
                await ctx.invoke(self._join)
            except AttributeError:
                raise commands.CommandError('You are not connected to any voice channel.')
        async with ctx.typing():
            songs = self.get_user_playlist(author)
            await ctx.send(f'Enqueued {str(len(songs))} songs!')
            for search in songs:
                try:
                    source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
                except YTDLError as e:
                    await ctx.send(f'"{search}" could not be added to the queue.')
                else:
                    song = Song(source)
                    await ctx.voice_state.songs.put(song)
        return

    @commands.command(name='showSaved')
    async def _showSaved(self, ctx: commands.Context, *, page: int = 1):
        """Show saved songs."""
        await ctx.message.add_reaction('✅')
        author = ctx.message.author.id
        songs = self.get_user_playlist(author)

        if len(songs) == 0:
            embed = (discord.Embed(title='Nothing saved for you',
                description='Add a song with ?addToSaved',
                color=discord.Color.red()))
            return await ctx.send(embed=embed)

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(songs, start=start):
            try:
                source = await YTDLSource.create_source(ctx, song, loop=False)
                song1 = Song(source)
            except:
                pass
            try:
                queue += '`{0}.` [**{1.source.title}**]({1.url})\n'.format(i + 1, song1)
            except:
                queue += '`{0}.` {1.source.title}\n'.format(i + 1, song1)
        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, max(pages, 1))))
        return await ctx.send(embed=embed)

    @commands.command(name='removeSaved')
    async def _removeFromSaved(self, ctx: commands.Context, *, index: int):
        """Removed a song that is saved."""
        index = index - 1
        numinlist = len(self.get_user_playlist(author=ctx.message.author.id))
        if numinlist <= index:
            return await ctx.send(f'Cannot remove song at {index +1} because there are only {numinlist} songs saved!')
        rval = self.remove_user_playlist(author=ctx.message.author.id, index=index)
        if rval:
            return await ctx.message.add_reaction('✅')
        else: 
            return await ctx.send("Could not remove song. Please, try again.")

    @commands.command(name='play')
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        if search.lower().find("soran bushi") != -1  or search.lower().startswith("https://www.youtube.com/watch?v=dqSygB92584"):   
            await ctx.send("<@225326981862916107> is a WEEEEEEEEEEEEEEB!")
        if isYTPlaylist(search):
            # invoke playlist handling
            links = getPlaylistLinks(search)
            await ctx.send('Enqueuing {} songs'.format(len(links)))
            for search in links:
                try:
                    source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
                except YTDLError as e:
                    await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
                    break
                else:
                    song = Song(source)
                ctx.voice_state.songs.put_nowait(song)
        else:
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                song = Song(source)

                ctx.voice_state.songs.put_nowait(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')
def setup(bot):
    bot.add_cog(Music(bot))
