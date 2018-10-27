from random import choice
import discord
import asyncio
from bot_constants import *
import subprocess
import select

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
                        title=f"Song Queue {i+1}/{len(embeds)+1}",
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
                    embed.add_field(name="\u200b", value=text)
                    songs += 1

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
            if player.is_pause and player.current:
                activity = discord.Game(f"{player.current.song_name} by {player.current.song_uploader}")
                await player.bot.change_presence(status=discord.Status.idle, activity=activity)
                while player.is_pause:
                    await asyncio.sleep(1)
                await player.bot.change_presence(status=discord.Status.online, activity=activity)
                continue

            if player.current and player.is_playing():
                embed = discord.Embed(title=f"Now Playing",
                                      description=f"[{player.current.song_name}]({player.current.song_webpage_url})",
                                      colour=discord.Colour(0x3f8517))

                if player.current.song_thumbnail:
                    embed.set_image(url=f"{player.current.song_thumbnail}")

                if player.current.song_is_live:
                    embed.add_field(name=f"`{progress_bar(1, 1)}`",
                                    value=f":red_circle: Live Stream - {format_time(player.current.song_progress)}",
                                    inline=False)

                elif not player.current.song_duration:
                    embed.add_field(name=f"`{progress_bar(player.current.song_progress, player.current.song_progress)}`",
                                    value=f"`{format_time(player.current.song_progress)}/{format_time(player.current.song_progress)}`",
                                    inline=False)
                else:
                    embed.add_field(
                        name=f"`{progress_bar(player.current.song_progress, player.current.song_duration)}`",
                        value=f"`{format_time(player.current.song_progress)}/{format_time(player.current.song_duration)}`",
                        inline=False)

                embed.add_field(name="By", value=f"`{player.current.song_uploader}`".title(), inline=True)
                embed.add_field(name="Source", value=f"`{player.current.song_extractor}`".title(), inline=True)
                embed.add_field(name="Requested by", value=f"`{player.current.requester}`".title(), inline=True)
                embed.add_field(name="Volume", value=f"`{round(player.volume*100)}`", inline=True)

            else:
                await bot.change_presence(status=discord.Status.idle, activity=None)
                embed = discord.Embed(title="Nothing to Play :disappointed_relieved:",
                                      description="type !play `[song name|url]` or !request `[song name|url]` to play a song",
                                      colour=discord.Colour(0x3f8517))

                if player.autoplay:
                    if not player.queue:
                        player.clear()
                        song = choice(player.auto_playlist)
                        bot.logger.info(f"Queue is empty, Auto Playing: {song}")
                        await player.bot.cmd_play(song, None, download=False, author=player.bot.user)
                    else:
                        bot.logger.warning(
                            f"Bot Hit a Idle status\nqueue = {player.queue}, is_pause = {player.is_pause}, play_next_song = {player.play_next_song}, current = {player.current}")
                        bot.logger.warning("Restarting Bot")
                        queue = bot.MusicPlayer.queue
                        await bot.cmd_reset()
                        bot.MusicPlayer.queue = queue
                        bot.MusicPlayer.autoplay = True
                        await asyncio.sleep(5)
                        continue

            try:
                if bot.now_playing_msg is None:
                    bot.now_playing_msg = await bot.MusicPlayer.player_channel.send(embed=embed)
                else:
                    await bot.now_playing_msg.edit(embed=embed)
            except Exception as e:
                bot.logger.error("Error While Updating Now Playing")
                bot.logger.exception(e)
                bot.now_playing_msg = await bot.MusicPlayer.player_channel.send(embed=embed)

            if player.is_playing() and player.current.song_duration:
                await asyncio.sleep(player.current.song_duration / 35)
            elif player.is_playing() and not player.current.song_duration:
                await asyncio.sleep(10)
            else:
                await asyncio.sleep(5)

        except Exception as e:
            bot.logger.error("Error While Displaying Now Playing")
            bot.logger.exception(e)
            await asyncio.sleep(2)


async def update_song_progress(bot):
    await bot.wait_until_ready()
    await asyncio.sleep(3)
    while True:
        if bot.current and bot.MusicPlayer.is_playing() and not bot.MusicPlayer.is_pause:
            bot.current.song_progress += 1
            await asyncio.sleep(1)


async def chat_cleaner(bot):
    await bot.wait_until_ready()
    async for message in bot.get_channel(player_channel).history(limit=None):
        await message.delete()
    async for message in bot.get_channel(song_request_queue_channel).history(limit=None):
        await message.delete()

    while True:
        async for message in bot.get_channel(player_channel).history(limit=None):
            if message.author != bot.user:
                await message.delete()

        async for message in bot.get_channel(song_request_queue_channel).history(limit=None):
            if message.author != bot.user:
                await message.delete()

        async for message in bot.get_channel(bot_log_channel).history(limit=None):
            if message.author != bot.user:
                await message.delete()

        async for message in bot.get_channel(cmd_help_channel).history(limit=None):
            if message.author != bot.get_user(supiri):
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
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '▱' * (length - filled_length)
    return '%s |%s| %s%% %s' % (prefix_, bar, percent, suffix)


async def stream_logs(filename, bot):
    f = subprocess.Popen(['tail', '-F', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p = select.poll()
    p.register(f.stdout)
    await bot.get_channel(bot_log_channel).send("```\n```")
    while True:
        if p.poll(1):
            await bot.get_channel(bot_log_channel).send(f"```py\n{f.stdout.readline().decode().strip()}```")
        await asyncio.sleep(1)
