import asyncio
import string
import youtube_dl
import discord
import re
from difflib import SequenceMatcher
from requests_html import AsyncHTMLSession, HTMLSession
from random import shuffle
from utils import song_added_embed

asession = AsyncHTMLSession()
session = HTMLSession()

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '/tmp/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class MusicPlayer:
    def __init__(self, bot):
        self.current = None
        self.bot = bot
        self.queue = []
        self.voice = bot.voice_client
        self.play_next_song = True
        self.now_playing_channel = None
        self.queue_channel = None
        self.song_request_channel = None
        self.song_request_queue_channel = None
        self.bot_cmd_channel = None
        self.playlist_queue_channel = None
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())
        self.auto_playlist_loop = self.bot.loop.create_task(self.create_auto_playlist())
        self.volume = 0.5
        self.request_queue = []
        self.auto_playlist = []
        self.is_pause = False
        self.autoplay = True
        self.queue_length = 0

    def is_playing(self):
        return self.voice.is_playing()

    def skip(self):
        self.voice.stop()
        self.play_next_song = True
        self.is_pause = False

    def pause(self):
        if self.is_playing():
            self.voice.pause()
            self.is_pause = True

    def resume(self):
        if not self.is_playing():
            self.voice.resume()
            self.is_pause = False

    def clear(self):
        self.voice.stop()
        self.queue = []
        self.is_pause = False
        self.play_next_song = True
        self.current = None

    def set_volume(self, volume):
        self.volume = volume / 100
        if self.current:
            self.current.volume = volume / 100

    def progress(self):
        # return round(self.voice._player.loops * 0.02)
        if self.current:
            return self.current.song_progress
        else:
            self.bot.logger.warning("Player Progress is called without a song")
            return 0

    def toggle_play_next_song(self):
        self.play_next_song = True
        self.is_pause = False

    async def add(self, song, play_now=False):
        if play_now:
            self.queue.insert(0, song)
        else:
            if len(self.queue) >= 20 and song.requester:
                await self.bot_cmd_channel.send(f"<{song.requester.mention}> Queue is full, try again in bit :x: ")
                return False
            self.queue.append(song)
        await self.bot_cmd_channel.send(embed=song_added_embed(self.bot, song))

    async def request(self, song):
        song.user_request = await self.song_request_queue_channel.send(
            f"{song.requester.mention} Requested {song.song_webpage_url}")
        self.bot.logger.info(f"Song Request from {song.requester} ({song.song_webpage_url})\n {song.user_request}")
        self.request_queue.append(song)

    async def create_auto_playlist(self):
        while True:
            self.auto_playlist = []
            if self.playlist_queue_channel:
                async for message in self.playlist_queue_channel.history(limit=None):
                    message = message.content.strip()
                    self.auto_playlist.append(message)
                await asyncio.sleep(300)
            else:
                await asyncio.sleep(1)

    async def audio_player_task(self):
        while True:
            if self.queue and self.play_next_song and (not self.is_playing() and not self.is_pause):
                self.current = self.queue.pop(0)
                self.current.volume = self.volume
                try:
                    activity = discord.Game(f"{self.current.song_name} by {self.current.song_uploader}")
                    await self.bot.change_presence(status=discord.Status.online, activity=activity)
                except Exception as e:
                    self.bot.logger.error("Unable to Change Bot Activity")
                    self.bot.logger.exception(e)

                try:
                    if self.current.is_a_request:
                        self.song_request_channel.send(
                            f"Now Playing {self.current.user_request.mention}'s Request\n{self.current.song_name} by {self.current.song_uploader}")
                except Exception as e:
                    self.bot.logger.error("Error while mentioning requested user")
                    self.bot.logger.exception(e)

                # Some kind of a weird bug in after argument require to pass toggle like this
                try:
                    self.voice.play(self.current,
                                    after=lambda
                                        e_: self.toggle_play_next_song() if e_ else self.toggle_play_next_song())
                except Exception as e:
                    self.bot.logger.critical(f"Can't Play {self.current.song_webpage_url}")
                    self.bot.logger.exception(e)

                self.play_next_song = False

            else:
                await asyncio.sleep(0.01)


class Song(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.song_name = None
        self.song_uploader = None
        self.song_thumbnail = None
        self.song_url = None
        self.song_duration = None
        self.song_is_live = False
        self.song_extractor = None
        self.song_playlist = None
        self.song_playlist_index = None
        self.song_playlist_size = None
        self.requester = None
        self.song_webpage_url = None
        self.user_request = None
        self.video_name = None
        self.song_progress = 0
        self.update_metadata(data)

    @classmethod
    async def stream(cls, url, author, bot):
        loop = bot.loop or asyncio.get_event_loop()
        # noinspection PyBroadException
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except Exception as e:
            bot.logger.error(f"Error While Streaming {url}")
            bot.logger.exception(e)
            return None

        if 'entries' in data:
            data = data['entries'][0]

        data['requester'] = author

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data)

    @classmethod
    async def download(cls, url, author, bot, playlist=False):
        loop = bot.loop or asyncio.get_event_loop()
        bot.logger.info(f"Downloading {url}")
        try:
            if playlist:
                await bot.MusicPlayer.bot_cmd_channel.send(
                    ':robot: I am Processing the Playlist this may take few minutes')
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
        except Exception as e:
            bot.logger.error(f"Error While Downloading {url}")
            bot.logger.exception(e)
            return None

        if playlist and 'entries' in data and data['entries'][0]['playlist'] != '':
            shuffle(data['entries'])
            for entry in data['entries']:
                entry['requester'] = author
                entry['path'] = ytdl.prepare_filename(entry)
                a = await bot.MusicPlayer.add(cls(discord.FFmpegPCMAudio(entry['url'], **ffmpeg_options), data=entry))
                if not a:
                    return True
            return True

        if 'entries' in data:
            data = data['entries'][0]

        data['requester'] = author
        data['path'] = ytdl.prepare_filename(data)

        return cls(discord.FFmpegPCMAudio(data['path'], **ffmpeg_options), data=data)

    @classmethod
    async def podcast(cls, url, author, bot):
        try:
            data = {'title': None, 'thumbnail': None, 'webpage_url': url, 'url': None, 'extractor': 'Podcasts',
                    'uploader': 'Rathumakara FM'}
            r = await asession.get(url)
            await r.html.arender()
            data['thumbnail'] = r.html.find('#podcast_logo', first=True).attrs['src']
            if data['thumbnail'].startswith('/'):
                data['thumbnail'] = 'http://www.podcasts.com' + data['thumbnail']
            audio_file = r.html.find('source', first=True).attrs['src']
            if not audio_file:
                return None
            data['url'] = 'http://www.podcasts.com' + audio_file
            data['title'] = r.html.find('#episode_title', first=True).find('h2', first=True).text
            data['requester'] = author

            for i in r.html.find('p'):
                if 'Podcast by ' in i.text:
                    for y in i.text.split(' '):
                        if "@" in y:
                            data['uploader'] = y.strip('@')
                            break
                    break

            return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data)
        except Exception as e:
            bot.logger.error(f"Error While Phasing {url}")
            bot.logger.exception(e)
            return None

    @classmethod
    async def search(cls, url, message, bot, author=None):
        loop = bot.loop or asyncio.get_event_loop()

        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except Exception as e:
            bot.logger.error(f"Error While Searching for {url}")
            bot.logger.exception(e)
            return None

        if 'entries' in data:
            data = data['entries'][0]
        if message:
            data['requester'] = message.author
            await message.add_reaction("👌")
            data['is_a_request'] = True
        elif author:
            data['requester'] = author
        else:
            bot.logger.warning(f"Can't Find the user who requested {data['webpage_url']}")
            return None

        await bot.MusicPlayer.request(cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data))
        return None

    def update_metadata(self, data):
        if 'title' in data.keys() and 'uploader' in data.keys():
            self.video_name = data['title']
            self.song_name, self.song_uploader = extract_song_artist_title(data['title'], data['uploader'])

        if 'thumbnail' in data.keys():
            self.song_thumbnail = data['thumbnail']

        if 'url' in data.keys():
            self.song_url = data['url']

        if 'webpage_url' in data.keys():
            self.song_webpage_url = data['webpage_url']

        if 'duration' in data.keys():
            self.song_duration = data['duration']

        if 'is_live' in data.keys():
            self.song_is_live = data['is_live']

        if 'extractor' in data.keys():
            self.song_extractor = data['extractor']

        if 'playlist' in data.keys():
            self.song_playlist = data['playlist']

        if 'playlist_index' in data.keys():
            self.song_playlist_index = data['playlist_index']

        if 'playlist_size' in data.keys():
            self.song_playlist_size = data['playlist_size']

        if 'requester' in data.keys():
            self.requester = data['requester']

        if 'is_a_request' in data.keys():
            self.user_request = data['is_a_request']


def extract_song_artist_title(name, artist):
    name = re.sub(r"[(\[].*?[)\]]", "", name).lower().replace('official', '').replace('lyric', '').replace('video',
                                                                                                           '').strip()
    artist = re.sub(r"(\w)([A-Z])", r"\1 \2", artist.replace('VEVO', '')).lower().replace('vevo', '').replace(
        'official', '').strip()

    artist_from_title = ''

    for i in name.translate(str.maketrans('', '', string.punctuation)).split(' '):
        for y in artist.split(' '):
            if i == y:
                artist_from_title += y + ' '

    if len(artist_from_title.strip()) > 2:
        if SequenceMatcher(None, artist, artist_from_title.strip()).ratio() > 0.6:
            artist = min(artist, artist_from_title.strip())

    names = name.split(' - ')

    if len(names) <= 1:
        names = name.split('-')

    if len(names) <= 1:
        names = name.split(' ')

    name = ''

    for n in names:
        if artist not in n:
            name += n + ' '

    if name.find('ft') > 2:
        name = name[:name.find('ft')]
    return name.strip().title().replace('  ', ' '), artist.strip().title().replace('  ', ' ')
