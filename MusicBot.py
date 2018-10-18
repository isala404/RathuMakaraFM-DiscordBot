from Player import Song, MusicPlayer
from utils import *
from bot_constants import *


# noinspection PyMethodMayBeStatic
class MusicBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voice_client = None
        self.volume = 100
        self.MusicPlayer = None
        self.now_playing_msg = None

    async def get_voice_client(self, channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.Object):
            channel = self.get_channel(channel.id)

        if not isinstance(channel, discord.VoiceChannel):
            raise AttributeError('Channel passed must be a voice channel')

        # if channel.guild.voice_client:
        #     return channel.guild.voice_client
        # else:
        return await channel.connect(timeout=60, reconnect=True)

    async def on_ready(self):
        print('Logged in as')
        print(bot.user.name)
        print(bot.user.id)
        print('------')
        await self.auto_join()
        async for message in self.get_channel(now_playing_channel).history(limit=None):
            await message.delete()
        async for message in self.get_channel(queue_channel).history(limit=None):
            await message.delete()
        self.loop.create_task(embed_for_queue(self))
        self.loop.create_task(embed_for_nowplaying(self))
        self.loop.create_task(chat_cleaner(self))

    async def join(self, channel_id):
        self.voice_client = self.get_voice_client(channel_id)
        self.MusicPlayer = MusicPlayer(self)
        self.MusicPlayer.bot_cmd_channel = self.get_channel(bot_cmd_channel)
        self.MusicPlayer.now_playing_channel = self.get_channel(now_playing_channel)
        self.MusicPlayer.queue_channel = self.get_channel(queue_channel)

    async def auto_join(self):
        await self.wait_until_ready()
        self.voice_client = await self.get_voice_client(self.get_channel(music_channel))
        self.MusicPlayer = MusicPlayer(self)
        self.MusicPlayer.bot_cmd_channel = self.get_channel(bot_cmd_channel)
        self.MusicPlayer.queue_channel = self.get_channel(queue_channel)
        self.MusicPlayer.now_playing_channel = self.get_channel(now_playing_channel)

    async def on_message(self, message):
        await self.wait_until_ready()

        if message.author == self.user:
            # TODO: Log this
            return

        message_content = message.content.strip()

        if not message_content.startswith(prefix):
            return

        if message.channel != self.MusicPlayer.bot_cmd_channel:
            return

        if isinstance(message.channel, discord.abc.PrivateChannel):
            return

        cmd = message_content.strip(prefix).split(' ')[0].lower()
        args = ' '.join((message_content.strip(prefix).split(' ')[1:]))

        if cmd == 'hello':
            await self.cmd_hello(message)

        elif cmd == 'play' or cmd == 'p':
            await self.cmd_play(args, message)

        elif cmd == 'join':
            await self.join(message.author.voice.channel)

        elif cmd == 'volume' or cmd == 'v':
            await self.cmd_volume(args)

        elif cmd == 'skip' or cmd == 's':
            await self.cmd_skip()

        elif cmd == 'pause' or cmd == 'ps':
            await self.cmd_pause()

        elif cmd == 'resume' or cmd == 'r':
            await self.cmd_resume()

        elif cmd == 'clearQueue':
            await self.cmd_clear_queue()

        elif cmd == '!play':
            await self.cmd_play(args, message, download=True)

        elif cmd == 'remove' or cmd == 'rm':
            await self.cmd_remove_from_queue(args)

        elif cmd == 'move' or cmd == 'm':
            await self.cmd_move_song(args)

    async def cmd_hello(self, message):
        await message.channel.send('Hello {0.author.mention}'.format(message))

    async def cmd_play(self, url, message, download=False):
        if self.voice_client is None:
            await self.auto_join()

        if url.strip() == '' or not url:
            if not self.MusicPlayer.is_playing():
                await self.cmd_resume()
            return

        if download:
            song = await Song.download(url, loop=self.loop)
        else:
            song = await Song.stream(url, loop=self.loop)

        if song:
            song.requester = message.author
            await self.MusicPlayer.add(song, message.channel)
        else:
            await message.channel.send(
                "{0.author.mention} I couldn't find that song :disappointed_relieved:".format(message))

    async def cmd_volume(self, volume):
        if not volume.isdigit():
            await self.get_channel(bot_cmd_channel).send(":no_entry: Sound level is not given")
            return
        volume = int(volume)
        if bot.MusicPlayer.volume * 100 > volume:
            for i in range(round(bot.MusicPlayer.volume * 100), volume - 1, -1):
                self.MusicPlayer.set_volume(i)
                await asyncio.sleep(.01)
            await self.get_channel(bot_cmd_channel).send(f":sound: Volume is set to {volume}")
        else:
            for i in range(round(bot.MusicPlayer.volume * 100), volume + 1):
                self.MusicPlayer.set_volume(i)
                await asyncio.sleep(.01)
            await self.get_channel(bot_cmd_channel).send(f":loud_sound: Volume is set to {volume}")

    async def cmd_skip(self):
        if self.MusicPlayer.is_playing() and self.MusicPlayer.current:
            self.MusicPlayer.skip()
            await self.get_channel(bot_cmd_channel).send(":track_next: Skipping")

    async def cmd_pause(self):
        self.MusicPlayer.pause()
        await self.get_channel(bot_cmd_channel).send(":pause_button: Paused")

    async def cmd_resume(self):
        await self.get_channel(bot_cmd_channel).send(":arrow_forward: Resuming")
        self.MusicPlayer.resume()

    async def cmd_clear_queue(self):
        self.MusicPlayer.clear()
        await self.get_channel(bot_cmd_channel).send(":boom: Queue was Cleared :boom:")

    async def cmd_remove_from_queue(self, index):
        if index.isdigit() and len(self.MusicPlayer.queue) >= int(index):
            index = int(index)
            await self.get_channel(bot_cmd_channel).send(
                f":boom: {self.MusicPlayer.queue[index-1].song_name} was Removed")
            del self.MusicPlayer.queue[index + 1]

    async def cmd_move_song(self, arg):
        if len(arg.split(" ")) == 2:
            current, new = arg.split(" ")
        else:
            current = arg
            new = None

        if current == new:
            return
        if current.isdigit() and len(self.MusicPlayer.queue) >= int(current):
            current = int(current)
            if new and new.isdigit() and len(self.MusicPlayer.queue) >= int(new):
                new = int(new)
                song = self.MusicPlayer.queue.pop(current-1)
                self.MusicPlayer.queue.insert(new-1, song)
                if current > new:
                    await self.get_channel(bot_cmd_channel).send(
                        f":arrow_up_small:  {song.song_name} was Moved #{new}")
                else:
                    await self.get_channel(bot_cmd_channel).send(
                        f":arrow_down_small: {song.song_name} was Moved #{new}")

            else:
                song = self.MusicPlayer.queue.pop(current-1)
                self.MusicPlayer.queue.insert(0, song)
                await self.get_channel(bot_cmd_channel).send(
                    f":arrow_double_up: {song.song_name} was Moved to the Top of the Queue")


bot = MusicBot()
bot.run(auth_key)
