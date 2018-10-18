import asyncio
import string
import youtube_dl
import discord
import re
from difflib import SequenceMatcher


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
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())
        self.volume = 1
        self.request_queue = []

    def is_playing(self):
        return self.voice.is_playing()

    def skip(self):
        self.voice.stop()
        self.play_next_song = True

    def pause(self):
        if self.is_playing():
            self.voice.pause()

    def resume(self):
        if not self.is_playing():
            self.voice.resume()

    def clear(self):
        self.voice.stop()
        self.queue = []

    def set_volume(self, volume):
        self.volume = volume / 100
        if self.is_playing and self.current:
            self.current.volume = volume / 100

    def toggle_play_next_song(self):
        self.play_next_song = True

    async def add(self, song, channel=None):
        self.queue.append(song)
        if channel:
            await channel.send(
                f':white_check_mark: {song.song_name} by {song.song_uploader} was added to the queue\n{song.song_webpage_url}')
        else:
            if song.user_request_msg:
                await song.user_request_msg.channel.send(
                    f"{song.user_request_msg.author.mention} Your song request was accepted :blush:"
                )

    async def request(self, song):
        song.user_request = await self.song_request_queue_channel.send(
            f"{song.user_request_msg.author.mention} Requested {song.song_webpage_url}")
        self.request_queue.append(song)

    async def audio_player_task(self):
        while True:
            if self.queue and self.play_next_song:
                self.current = self.queue.pop(0)
                self.current.volume = self.volume

                try:
                    activity = discord.Game(f"{self.current.song_name} by {self.current.song_uploader}")
                    await self.bot.change_presence(status=discord.Status.online, activity=activity)
                except:
                    pass

                # Some kind of a weird bug in after argument require to pass toggle like this
                self.voice.play(self.current,
                                after=lambda e: self.toggle_play_next_song() if e else self.toggle_play_next_song())
                self.play_next_song = False
            else:
                await asyncio.sleep(0.01)


class Song(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.4):
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
        self.user_request_msg = None
        self.user_request = None
        self.update_metadata(data)

    @classmethod
    async def stream(cls, url, message, bot, playlist=False):
        loop = bot.loop or asyncio.get_event_loop()

        # noinspection PyBroadException
        try:
            if playlist:
                await message.channel.send(':robot: I am Processing the Playlist this may take few minutes')
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except Exception:
            return None

        if playlist and 'entries' in data and data['entries'][0]['playlist'] != '':
            for entry in data['entries']:
                entry['requester'] = message.author
                await bot.MusicPlayer.add(cls(discord.FFmpegPCMAudio(entry['url'], **ffmpeg_options), data=entry),
                                          message.channel)
            return True

        if 'entries' in data:
            data = data['entries'][0]
        data['requester'] = message.author

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data)

    @classmethod
    async def download(cls, url, message, bot):
        loop = bot.loop or asyncio.get_event_loop()

        # noinspection PyBroadException
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
        except Exception:
            return None

        if 'entries' in data:
            data = data['entries'][0]
        data['requester'] = message.author

        return cls(discord.FFmpegPCMAudio(ytdl.prepare_filename(data), **ffmpeg_options), data=data)

    @classmethod
    async def search(cls, url, message, bot):
        loop = bot.loop or asyncio.get_event_loop()

        # noinspection PyBroadException
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except Exception:
            return None

        if 'entries' in data:
            data = data['entries'][0]
        data['request'] = message
        data['requester'] = message.author

        await message.add_reaction("👌")

        await bot.MusicPlayer.request(cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data))
        return None

    def update_metadata(self, data):
        if 'title' in data.keys() and data['uploader']:
            self.song_name, self.song_uploader = extract_song_artist_title(data['title'], data['uploader'])

        if 'name' in data.keys() and 'title' not in data.keys():
            self.song_name = data['name']

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

        if 'request' in data.keys():
            self.user_request_msg = data['request']


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
