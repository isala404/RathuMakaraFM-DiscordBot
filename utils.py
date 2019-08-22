import os
from random import choice
import discord
import asyncio
import subprocess
import select
import json
import logging

queue_msg_holder = []


async def embed_for_queue(bot):
    await bot.wait_until_ready()
    await asyncio.sleep(5)
    while not bot.now_playing_msg:
        await asyncio.sleep(1)
    while True:
        try:
            embeds = list(chunks(bot.MusicPlayer.queue, 23))
            if not embeds:
                embed = discord.Embed(title="Song Queue is empty :sob:",
                                      description="type !play `[song name|url]` or !request `[song name|url]` to add song to the queue",
                                      colour=discord.Colour(0x3f8517))
                if len(queue_msg_holder) == 0:
                    msg = await bot.MusicPlayer.player_channel.send(embed=embed)
                    queue_msg_holder.append(msg)
                elif len(queue_msg_holder) > 0:
                    await queue_msg_holder[0].edit(embed=embed)

                await asyncio.sleep(5)
                continue

            songs = 1
            for i, embed_ in enumerate(embeds):
                if len(embeds) > 1:
                    embed = discord.Embed(
                        description=":arrow_double_down: :musical_note: :notes: :arrow_double_down:",
                        title=f"Song Queue {i + 1}/{len(embeds) + 1}",
                        colour=discord.Colour(0x3f8517))
                else:
                    embed = discord.Embed(
                        description=":arrow_double_down: :musical_note: :notes: :arrow_double_down:",
                        title=f"Song Queue",
                        colour=discord.Colour(0x3f8517))

                for song in embed_:
                    text = "`{}.`[{} by {}]({}) | `{} Requested by: {}`".format(
                        songs, song.song_name, song.song_uploader,
                        song.song_webpage_url.replace("www.youtube.com/watch?v=", "youtu.be/"),
                        format_time(song.song_duration) if song.song_duration else "", song.requester.name
                    )
                    embed.add_field(name="\u200b", value=text[:255])
                    songs += 1

                if i == len(embeds) - 1:
                    queue_length = 0
                    for song in bot.MusicPlayer.queue:
                        if song.song_duration:
                            queue_length += song.song_duration

                    bot.MusicPlayer.queue_length = queue_length

                    embed.set_footer(
                        text=f"{len(bot.MusicPlayer.queue)} songs in queue | {format_time(bot.MusicPlayer.queue_length)} total length")
                if len(queue_msg_holder) == i:
                    msg = await bot.MusicPlayer.player_channel.send(embed=embed)
                    queue_msg_holder.append(msg)
                elif len(queue_msg_holder) > i:
                    await queue_msg_holder[i].edit(embed=embed)

            for msg in queue_msg_holder[len(embeds):]:
                await msg.delete()
                queue_msg_holder.remove(msg)

            await asyncio.sleep(5)

        except Exception as e:
            bot.logger.error("Error While Displaying Queue")
            bot.logger.exception(e)
            await asyncio.sleep(2)


async def embed_for_nowplaying(bot):
    await bot.wait_until_ready()
    await asyncio.sleep(3)
    while True:
        try:
            player = bot.MusicPlayer
            if not player:
                await asyncio.sleep(1)
                continue

            if player.is_pause and player.current:
                activity = discord.Game(f"{player.current.song_name} by {player.current.song_uploader}"[:100])
                await player.bot.change_presence(status=discord.Status.idle, activity=activity)
                while player.is_pause:
                    await asyncio.sleep(1)
                await player.bot.change_presence(status=discord.Status.online, activity=activity)
                continue

            if player.current and player.is_playing():
                embed = discord.Embed(title=f"Now Playing",
                                      description=f"[{player.current.song_name}]({player.current.song_webpage_url})"[
                                                  :255],
                                      colour=discord.Colour(0x3f8517))

                if player.current.song_thumbnail:
                    embed.set_image(url=f"{player.current.song_thumbnail}")

                if player.current.song_is_live:
                    embed.add_field(name=f"`{progress_bar(1, 1)}`",
                                    value=f":red_circle: Live Stream - {format_time(player.progress())}",
                                    inline=False)

                elif not player.current.song_duration:
                    embed.add_field(name=f"`{progress_bar(player.progress(), player.progress())}`",
                                    value=f"`{format_time(player.progress())}/{format_time(player.progress())}`",
                                    inline=False)
                else:
                    embed.add_field(
                        name=f"`{progress_bar(player.progress(), player.current.song_duration)}`",
                        value=f"`{format_time(player.progress())}/{format_time(player.current.song_duration)}`",
                        inline=False)

                embed.add_field(name="By", value=f"`{player.current.song_uploader}`".title(), inline=True)
                embed.add_field(name="Source", value=f"`{player.current.song_extractor}`".title(), inline=True)
                embed.add_field(name="Requested by", value=f"`{player.current.requester}`".title(), inline=True)
                embed.add_field(name="Volume", value=f"`{round(player.volume * 100)}`", inline=True)

            else:
                await bot.change_presence(status=discord.Status.idle, activity=None)
                player.current = None
                embed = discord.Embed(title="Nothing to Play :disappointed_relieved:",
                                      description="type !play `[song name|url]` or !request `[song name|url]` to play a song",
                                      colour=discord.Colour(0x3f8517))

                if player.autoplay:
                    if not player.queue:
                        player.clear()
                        song = choice(player.auto_playlist)
                        bot.logger.info(f"Queue is empty, Auto Playing: {song}")
                        await player.bot.cmd_play(song, download=True, author=player.bot.user)
                    else:
                        await player.bot.change_presence(status=discord.Status.do_not_disturb, activity=None)
                        bot.logger.warning(
                            f"Bot Hit a Idle status\nqueue = {player.queue}, is_pause = {player.is_pause}, play_next_song = {player.play_next_song}, current = {player.current}, is_playing = {player.is_playing()}")
                        bot.logger.warning("Restarting Bot")
                        await bot.MusicPlayer.bot_cmd_channel.send(
                            "Mr Stark I don't feel so good\nI will fix my self by skipping the current song\nIf I am repeating myself type !reset and save me")
                        player.queue = player.queue[1:]
                        bot.reset_MusicPlayer()

            try:
                embed.set_footer(text="bot made by @mrsupiri",
                                 icon_url="https://cdn2.iconfinder.com/data/icons/minimalism/512/twitter.png")

                if bot.now_playing_msg is None:
                    bot.now_playing_msg = await bot.MusicPlayer.player_channel.send(embed=embed)
                else:
                    await bot.now_playing_msg.edit(embed=embed)
            except Exception as e:
                bot.logger.error("Error While Updating Now Playing")
                bot.logger.exception(e)

            await asyncio.sleep(10)

        except Exception as e:
            bot.logger.error("Error While Displaying Now Playing")
            bot.logger.exception(e)
            await asyncio.sleep(5)


async def update_song_progress(bot):
    await bot.wait_until_ready()
    await asyncio.sleep(3)
    while True:
        if not bot.MusicPlayer:
            await asyncio.sleep(1)
            continue
        if bot.MusicPlayer.current and bot.MusicPlayer.is_playing() and not bot.MusicPlayer.is_pause:
            bot.MusicPlayer.current.song_progress += 1
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(0.1)


async def chat_cleaner(bot):
    await bot.wait_until_ready()
    async for message in bot.get_channel(bot.BotConfig.player_channel).history(limit=None):
        await message.delete()
    async for message in bot.get_channel(bot.BotConfig.song_request_queue_channel).history(limit=None):
        await message.delete()

    while True:
        async for message in bot.get_channel(bot.BotConfig.player_channel).history(limit=None):
            if message.author != bot.user:
                await message.delete()

        async for message in bot.get_channel(bot.BotConfig.song_request_queue_channel).history(limit=None):
            if message.author != bot.user:
                await message.delete()

        async for message in bot.get_channel(bot.BotConfig.bot_log_channel).history(limit=None):
            if message.author != bot.user:
                await message.delete()

        if os.getenv("developer_client_id"):
            async for message in bot.get_channel(bot.BotConfig.cmd_help_channel).history(limit=None):
                if message.author != bot.get_user(int(os.getenv("developer_client_id"))):
                    await message.delete()


def chunks(l, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i + n]


def format_time(seconds):
    m, s = divmod(seconds, 60)
    return "%02d:%02d" % (m, s)


def progress_bar(iteration, total, prefix_='', suffix='', decimals=1, length=35, fill='▰'):
    """
    Credit - https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    if iteration > total:
        iteration = total
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '▱' * (length - filled_length)
    return '%s |%s| %s%% %s' % (prefix_, bar, percent, suffix)


async def stream_logs(filename, bot):
    f = subprocess.Popen(['tail', '-F', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p = select.poll()
    p.register(f.stdout)
    await bot.get_channel(bot.BotConfig.bot_log_channel).send("```\n```")
    while True:
        if p.poll(1):
            await bot.get_channel(bot.BotConfig.bot_log_channel).send(
                f"```py\n{f.stdout.readline().decode().strip()}```")
        await asyncio.sleep(1)


def song_added_embed(bot, song, play_now):
    try:
        player = bot.MusicPlayer
        embed = discord.Embed(title=f"{song.video_name}", colour=discord.Colour(0x5ddefc),
                              url=f"{song.song_webpage_url}")

        embed.set_thumbnail(url=f"{song.song_thumbnail}")

        embed.set_author(name=f"{song.requester}", url="https://isala.me",
                         icon_url=f"{song.requester.avatar_url}")

        embed.add_field(name="By", value=f"{song.song_uploader}")

        if song.song_duration:
            embed.add_field(name="Song Duration", value=f"{format_time(song.song_duration)}")

        queue_length = 0
        for song in bot.MusicPlayer.queue:
            if song.song_duration:
                queue_length += song.song_duration

        if bot.MusicPlayer.current and bot.MusicPlayer.current.song_duration:
            queue_length = queue_length + bot.MusicPlayer.current.song_duration - player.progress()

        if player.queue:
            embed.add_field(name="Estimated time until playing", value=f"{format_time(queue_length)}")
            if play_now:
                embed.add_field(name="Position in queue", value="1")
            else:
                embed.add_field(name="Position in queue", value=f"{len(player.queue)}")

        return embed
    except Exception as e:
        bot.logger.error("Error Creating Song Added Embed")
        bot.logger.exception(e)
        return None


async def save_status(bot):
    while True:
        try:
            if bot and bot.MusicPlayer:
                if bot.MusicPlayer.current:
                    d = {
                        "now_playing": {"song": bot.MusicPlayer.current.song_name,
                                        "uploader": bot.MusicPlayer.current.song_uploader,
                                        "thumbnail": bot.MusicPlayer.current.song_thumbnail,
                                        "url": bot.MusicPlayer.current.song_webpage_url,
                                        "duration": bot.MusicPlayer.current.song_duration,
                                        "progress": bot.MusicPlayer.progress(),
                                        "extractor": bot.MusicPlayer.current.song_extractor,
                                        "requester": bot.MusicPlayer.current.requester.name,
                                        },
                        "queue": [],
                        "is_pause": bot.MusicPlayer.is_pause,
                        "auto_play": bot.MusicPlayer.autoplay,
                        "volume": bot.MusicPlayer.volume
                    }
                else:
                    d = {
                        "now_playing": {"song": None, "uploader": None, "thumbnail": None, "url": None,
                                        "duration": None, "progress": None, "extractor": None, "requester": None},
                        'queue': [],
                        "is_pause": bot.MusicPlayer.is_pause,
                        "auto_play": bot.MusicPlayer.autoplay,
                        "volume": bot.MusicPlayer.volume
                    }
                for song in bot.MusicPlayer.queue:
                    d['queue'].append({"song": song.song_name,
                                       "uploader": song.song_uploader,
                                       "thumbnail": song.song_thumbnail,
                                       "url": song.song_webpage_url,
                                       "duration": song.song_duration,
                                       "extractor": song.song_extractor,
                                       "requester": song.requester.name})

            else:
                d = {
                    "now_playing": {"song": None, "uploader": None, "thumbnail": None, "url": None,
                                    "duration": None, "progress": None, "extractor": None, "requester": None},
                    'queue': [],
                    "is_pause": False,
                    "auto_play": False,
                    "volume": 100
                }

            with open('status.json', 'w') as outfile:
                json.dump(d, outfile)

        except Exception as e:
            bot.logger.error("Error Dumping status to status.json")
            bot.logger.exception(e)

        await asyncio.sleep(0.5)


async def parse_cmd(bot, cmd, args, author):
    if cmd == 'play':
        result = await bot.cmd_play(args, download=True, author=author)

    elif cmd == 'playnow':
        result = await bot.cmd_play(args, download=False, play_now=True, author=author)

    elif cmd == 'playnext':
        result = await bot.cmd_play(args, download=False, play_next=True, author=author)

    elif cmd == 'playlist':
        result = await bot.cmd_play(args, playlist=True, author=author)

    elif cmd == 'volume':
        result = await bot.cmd_volume(args, author=author)

    elif cmd == 'skip':
        result = await bot.cmd_skip(author=author)

    elif cmd == 'pause':
        result = await bot.cmd_pause(author=author)

    elif cmd == 'resume':
        result = await bot.cmd_resume(author=author)

    elif cmd == 'clearQueue':
        result = await bot.cmd_clear_queue(author=author)

    elif cmd == 'stream':
        result = await bot.cmd_play(args, None, author=author)

    elif cmd == 'remove' or cmd == 'rm':
        result = await bot.cmd_remove_from_queue(args, author=author)

    elif cmd == 'move' or cmd == 'm':
        result = await bot.cmd_move_song(args, author=author)

    elif cmd == 'request' or cmd == 'req':
        result = await bot.cmd_request(args, None, author=author)

    elif cmd == 'autoplay':
        result = await bot.cmd_autoplay(args, author=author)

    else:
        return False
    return result


def validate_request(app, request):
    app.config['bot'].logger.info(f"API Request for {request.path} from {request.remote_addr}")

    if not request.content_type == 'application/json':
        app.config['bot'].logger.info(
            f"Bad Request from {request.remote_addr}: Content-type {request.content_type} is invalid")

        return json.dumps({'error': 'Content-type must be application/json'}), 400, {
            'ContentType': 'application/json'}

    data = request.get_json(force=True)
    data_ = data.copy()
    data_.pop('authkey', None)
    app.config['bot'].logger.info(f"API Request: {request.path} => {data_}")

    if 'authkey' not in data or 'user_id' not in data:
        app.config['bot'].logger.info(f"Bad Request from {request.remote_addr}: Missing some key attributes")
        return json.dumps({'error': 'Missing key attributes'}), 400, {'ContentType': 'application/json'}

    if app.config['bot'].BotConfig.web_api_auth_key != data['authkey']:
        return json.dumps({'error': 'Invalid Auth Key'}), 401, {'ContentType': 'application/json'}

    user = app.config['bot'].get_user(int(data['user_id']))
    if not user:
        return json.dumps({'error': 'User was not found'}), 404, {'ContentType': 'application/json'}

    guild = app.config['bot'].get_guild(app.config['bot'].BotConfig.guild_id)
    if not guild:
        return json.dumps({'error': 'Server was not found'}), 404, {'ContentType': 'application/json'}
    member = guild.get_member(user.id)
    if not member:
        return json.dumps({'error': 'User was not found on the server'}), 404, {'ContentType': 'application/json'}

    return user, guild, member, data


def start_logger():
    logger = logging.getLogger('RathuMakara FM')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('MusicBot.log')
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
