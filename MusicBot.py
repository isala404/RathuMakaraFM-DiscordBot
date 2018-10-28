import os
from Player import Song, MusicPlayer
from utils import *
from bot_constants import *
from random import shuffle
import logging
from logging.handlers import RotatingFileHandler


# noinspection PyMethodMayBeStatic
class MusicBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voice_client = None
        self.volume = 100
        self.MusicPlayer = None
        self.now_playing_msg = None
        self.logger = start_logger()

    async def get_voice_client(self, channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.Object):
            channel = self.get_channel(channel.id)

        if not isinstance(channel, discord.VoiceChannel):
            self.logger.error(f"{channel.mention} is not voice channel")
            return

        return await channel.connect(timeout=60, reconnect=True)

    async def on_ready(self):
        self.logger.debug(f"Starting Bot as {self.user.name} ")
        self.loop.create_task(embed_for_nowplaying(self))
        self.loop.create_task(embed_for_queue(self))
        self.loop.create_task(update_song_progress(self))

    async def on_connect(self):
        await self.auto_join()
        self.MusicPlayer = MusicPlayer(self)
        self.MusicPlayer.bot_cmd_channel = self.get_channel(bot_cmd_channels[0])
        self.MusicPlayer.player_channel = self.get_channel(player_channel)
        self.MusicPlayer.song_request_channel = self.get_channel(song_request_channel)
        self.MusicPlayer.song_request_queue_channel = self.get_channel(song_request_queue_channel)
        self.MusicPlayer.playlist_queue_channel = self.get_channel(playlist_queue_channel)
        self.loop.create_task(chat_cleaner(self))
        self.loop.create_task(stream_logs('logs/RathuMakara.log', self))
        await asyncio.sleep(2)

    async def join(self, channel):
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
        self.voice_client = await self.get_voice_client(channel)
        self.MusicPlayer.voice = self.voice_client

    async def auto_join(self):
        await self.wait_until_ready()
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
        self.voice_client = await self.get_voice_client(self.get_channel(bot_voice_channel))
        self.logger.debug(f"Auto Joining {self.get_channel(bot_voice_channel).mention}")

    async def on_reaction_add(self, reaction, user):
        if reaction.message.channel != self.MusicPlayer.song_request_queue_channel:
            return

        if not [y.id for y in user.roles if int(y.id) in bot_commanders]:
            self.logger.info(f"{user.name} is not authorized to accept song requests")
            return

        for request in self.MusicPlayer.request_queue:
            if reaction.message.id == request.user_request.id:
                if reaction.emoji == '✅':
                    await self.MusicPlayer.song_request_channel.send(
                        f"{request.requester.mention} Your song request was accepted :blush:"
                    )
                    self.logger.info(
                        f"{user.name} accepted {request.requester.name}'s Request to play {request.song_webpage_url}")
                    await self.cmd_play(request.song_webpage_url, None, author=request.requester)
                    self.MusicPlayer.request_queue.remove(request)
                    await reaction.message.delete()
                elif reaction.emoji == '❌':
                    await self.MusicPlayer.song_request_channel.send(
                        f"{request.requester.mention} Your song request was declined :sweat:"
                    )
                    self.logger.info(
                        f"{user.name} declined {request.requester.name}'s Request to play {request.song_webpage_url}")
                    self.MusicPlayer.request_queue.remove(request)
                    await reaction.message.delete()

    async def on_message(self, message):
        await self.wait_until_ready()

        if message.author == self.user:
            return

        message_content = message.content.strip()

        if not message_content.startswith(prefix):
            return

        if not [channel for channel in bot_cmd_channels if message.channel == self.get_channel(channel)] and (
                message.channel != self.MusicPlayer.song_request_channel or not message_content.startswith('!req')):
            return

        if isinstance(message.channel, discord.abc.PrivateChannel):
            return

        cmd = message_content.strip(prefix).split(' ')[0].lower()
        args = ' '.join((message_content.strip(prefix).split(' ')[1:])).strip(" ")

        self.logger.info(f"{message.author.name} => !{cmd} {args}")
        if cmd == 'hello':
            await self.cmd_hello(message)

        elif cmd == 'play' or cmd == 'p':
            await self.cmd_play(args, message, download=True)

        elif cmd == 'playnow':
            await self.cmd_play(args, message, download=False, play_now=True)

        elif cmd == 'playlist':
            await self.cmd_play(args, message, playlist=True)

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

        elif cmd == 'clearqueue':
            await self.cmd_clear_queue()

        elif cmd == 'stream':
            await self.cmd_play(args, message)

        elif cmd == 'shuffle':
            shuffle(self.MusicPlayer.queue)
            await message.channel.send(':twisted_rightwards_arrows: Shuffling the queue pseudo randomly')

        elif cmd == 'remove' or cmd == 'rm':
            await self.cmd_remove_from_queue(args)

        elif cmd == 'move' or cmd == 'm':
            await self.cmd_move_song(args)

        elif cmd == 'request' or cmd == 'req':
            await self.cmd_request(args, message)

        elif cmd == 'autoplay' or cmd == 'ap':
            await self.cmd_autoplay(args, message)

        elif cmd == 'reset':
            await self.cmd_reset()

        elif cmd == 'leave' or cmd == 'fuckoff':
            self.logger.info("Bot is disconnecting")
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.disconnect()
            await message.channel.send(':hand_splayed: :hand_splayed:')

        else:
            await message.channel.send(
                '{0.author.mention} !{1} is invalid command refer #bot-command-list for more info'.format(message, cmd))

    async def cmd_hello(self, message):
        await message.channel.send('Hello {0.author.mention}'.format(message))

    async def cmd_reset(self):
        await self.MusicPlayer.bot_cmd_channel.send(":arrows_counterclockwise: Restarting Bot")
        await self.auto_join()
        self.MusicPlayer = MusicPlayer(self)
        self.MusicPlayer.bot_cmd_channel = self.get_channel(bot_cmd_channels[0])
        self.MusicPlayer.player_channel = self.get_channel(player_channel)
        self.MusicPlayer.song_request_channel = self.get_channel(song_request_channel)
        self.MusicPlayer.song_request_queue_channel = self.get_channel(song_request_queue_channel)
        self.MusicPlayer.playlist_queue_channel = self.get_channel(playlist_queue_channel)

    async def cmd_play(self, url, message, download=False, playlist=False, author=None, play_now=False):
        if self.voice_client is None:
            await self.auto_join()

        if url.strip() == '' or not url:
            if not self.MusicPlayer.is_playing():
                await self.cmd_resume()
            return False

        if 'www.podcasts.com' in url:
            song = await Song.podcast(url, message, self)
        elif play_now:
            song = await Song.stream(url, message, self)
        elif not message:
            song = await Song.download(url, None, self, author=author)
            await self.MusicPlayer.add(song, None)
            return True
        elif download and not playlist:
            song = await Song.download(url, message, self)
        elif playlist:
            song = await Song.download(url, message, self, playlist=playlist)
        elif not download:
            song = await Song.stream(url, message, self)
        else:
            song = await Song.download(url, message, self)

        if playlist:
            return True

        if song and not play_now:
            await self.MusicPlayer.add(song, message.channel)
            return True
        elif song and play_now:
            await self.MusicPlayer.add(song, message.channel, play_now=True)
            await self.cmd_skip()
            return True
        else:
            self.logger.warning(f"Can't play or find {url}")
            await message.channel.send(
                "{0.author.mention} I couldn't find that song :disappointed_relieved:".format(message))
            return False

    async def cmd_volume(self, volume):
        if not volume.isdigit():
            await self.MusicPlayer.bot_cmd_channel.send(":no_entry: Sound level is not given")
            return
        volume = int(volume)
        if self.MusicPlayer.volume * 100 > volume:
            for i in range(round(self.MusicPlayer.volume * 100), volume - 1, -1):
                self.MusicPlayer.set_volume(i)
                await asyncio.sleep(.01)
            await self.MusicPlayer.bot_cmd_channel.send(f":sound: Volume is set to {volume}")
        else:
            for i in range(round(self.MusicPlayer.volume * 100), volume + 1):
                self.MusicPlayer.set_volume(i)
                await asyncio.sleep(.01)
            await self.MusicPlayer.bot_cmd_channel.send(f":loud_sound: Volume is set to {volume}")

    async def cmd_skip(self):
        if self.MusicPlayer.is_playing() and self.MusicPlayer.current:
            self.MusicPlayer.skip()
            await self.MusicPlayer.bot_cmd_channel.send(f":track_next: Skipping {self.MusicPlayer.current.song_name}")
            return True

    async def cmd_pause(self):
        self.MusicPlayer.pause()
        await self.MusicPlayer.bot_cmd_channel.send(":pause_button: Paused")
        return True

    async def cmd_resume(self):
        await self.MusicPlayer.bot_cmd_channel.send(":arrow_forward: Resuming")
        self.MusicPlayer.resume()
        return True

    async def cmd_clear_queue(self):
        self.logger.warning("Playlist was Cleared")
        self.MusicPlayer.clear()
        await self.MusicPlayer.bot_cmd_channel.send(":boom: Queue was Cleared :boom:")
        return True

    async def cmd_remove_from_queue(self, index):
        if index.isdigit() and len(self.MusicPlayer.queue) >= int(index):
            index = int(index) - 1
            await self.MusicPlayer.bot_cmd_channel.send(
                f":boom: {self.MusicPlayer.queue[index].song_name} was Removed")
            del self.MusicPlayer.queue[index]
            return True
        return False

    async def cmd_move_song(self, arg):
        if len(arg.split(" ")) == 2:
            current, new = arg.split(" ")
        else:
            current = arg
            new = None

        if current == new:
            return False
        if current.isdigit() and len(self.MusicPlayer.queue) >= int(current):
            current = int(current)
            if new and new.isdigit() and len(self.MusicPlayer.queue) >= int(new):
                new = int(new)
                song = self.MusicPlayer.queue.pop(current - 1)
                self.MusicPlayer.queue.insert(new - 1, song)
                if current > new:
                    await self.MusicPlayer.bot_cmd_channel.send(
                        f":arrow_up_small:  {song.song_name} was Moved #{new}")
                else:
                    await self.MusicPlayer.bot_cmd_channel.send(
                        f":arrow_down_small: {song.song_name} was Moved #{new}")

            else:
                song = self.MusicPlayer.queue.pop(current - 1)
                self.MusicPlayer.queue.insert(0, song)
                await self.MusicPlayer.bot_cmd_channel.send(
                    f":arrow_double_up: {song.song_name} was Moved to the Top of the Queue")
            return True

    async def cmd_request(self, arg, message, author=None):
        if arg == '':
            return False
        if message:
            await Song.search(arg, message, self)
        elif author:
            await Song.search(arg, None, self, author=author)

    async def cmd_autoplay(self, arg, message):
        if arg == 'on':
            self.MusicPlayer.autoplay = True
            self.logger.info(f"AutoPlay was Enabled by {message.author.name}")
            await message.channel.send("AutoPlay is Now Enabled")

        elif arg == 'off':
            self.MusicPlayer.autoplay = False
            self.logger.info(f"AutoPlay was Disabled by {message.author.name}")
            await message.channel.send("AutoPlay is Now Disabled")
        else:
            return False


def start_logger():
    logger = logging.getLogger('RathuMakara FM')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    should_roll_over = os.path.isfile('logs/RathuMakara.log')
    fh = RotatingFileHandler('logs/RathuMakara.log', mode='w', backupCount=5)
    if should_roll_over:  # log already exists, roll over!
        fh.doRollover()
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        fmt='%(asctime)-10s - %(levelname)-5s: %(module)s:%(lineno)-d -  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


if __name__ == "__main__":
    bot = None
    try:
        bot = MusicBot()
        bot.run(bot_auth_key)
    except InterruptedError:
        if bot:
            bot.logger.info("Shutting Down")
        exit()
    except Exception as e:
        log = start_logger()
        log.critical("Something Really Went Wrong")
        log.exception(e)
        os.system("/root/Musicbot.sh")
