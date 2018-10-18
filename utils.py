import discord
import datetime
import asyncio
from bot_constants import *

queue_msg_holder = []


async def embed_for_queue(bot):
    await asyncio.sleep(2)
    while True:
        embeds = list(chunks(bot.MusicPlayer.queue, 23))
        if not embeds:
            embed = discord.Embed(title="Song Queue is empty :sob:",
                                  description="type !play `[song name|url]` or !request `[song name|url]` to add song to the queue",
                                  colour=discord.Colour(0x3f8517))
            if len(queue_msg_holder) == 0:
                msg = await bot.MusicPlayer.queue_channel.send(embed=embed)
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
                    songs, song.song_name, song.song_uploader, song.song_webpage_url.replace("www.youtube.com/watch?v=", "youtu.be/"),
                    format_time(song.song_duration), song.requester.name
                )
                embed.add_field(name="\u200b", value=text)
                songs += 1

            if len(queue_msg_holder) == i:
                msg = await bot.MusicPlayer.queue_channel.send(embed=embed)
                queue_msg_holder.append(msg)
            elif len(queue_msg_holder) > i:
                await queue_msg_holder[i].edit(embed=embed)

        for msg in queue_msg_holder[len(embeds):]:
            await msg.delete()
            queue_msg_holder.remove(msg)

        await asyncio.sleep(5)


async def embed_for_nowplaying(bot):
    await asyncio.sleep(1)
    while True:
        player = bot.MusicPlayer
        if player.current:
            embed = discord.Embed(title=f"Now Playing",
                                  description=f"[{player.current.song_name}]({player.current.song_webpage_url})",
                                  colour=discord.Colour(0x3f8517))

            embed.set_image(url=f"{player.current.song_thumbnail}")

            if hasattr(player.current, 'progress'):
                embed.add_field(name=f"`{progress_bar(player.current.progress, player.current.song_duration)}`",
                                value=f"`{format_time(player.current.progress)}/{format_time(player.current.song_duration)}`",
                                inline=False)
            else:
                embed.add_field(name=f"`{progress_bar(player.current.song_duration, player.current.song_duration)}`",
                                value=f"`{format_time(player.current.song_duration)}/{format_time(player.current.song_duration)}`",
                                inline=False)

            embed.add_field(name="By", value=f"`{player.current.song_uploader}`".title(), inline=True)
            embed.add_field(name="Source", value=f"`{player.current.song_extractor}`".title(), inline=True)
            embed.add_field(name="Requested by", value=f"`{player.current.requester}`".title(), inline=True)
            embed.add_field(name="Volume", value=f"`{round(player.volume*100)}`", inline=True)

        else:
            embed = discord.Embed(title="Nothing to Play :disappointed_relieved:",
                                  description="type !play `[song name|url]` or !request `[song name|url]` to play a song",
                                  colour=discord.Colour(0x3f8517))

        if bot.now_playing_msg is None:
            bot.now_playing_msg = await bot.MusicPlayer.now_playing_channel.send(embed=embed)

        else:
            await bot.now_playing_msg.edit(embed=embed)
        if player.current:
            await asyncio.sleep(player.current.song_duration/35)
        else:
            while not bot.MusicPlayer.current:
                await asyncio.sleep(0.5)


async def chat_cleaner(bot):
    while True:
        # async for message in bot.get_channel(now_playing_channel).history(limit=None):
        #     if message.author != bot.user:
        #         await message.delete()
        async for message in bot.get_channel(player_channel).history(limit=None):
            if message.author != bot.user:
                await message.delete()


def chunks(l, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i + n]


def sample():
    embed = discord.Embed(title="title ~~(did you know you can have markdown here too?)~~",
                          colour=discord.Colour(0x3f8517), url="https://discordapp.com",
                          description="this supports [named links](https://discordapp.com) on top of the previously shown subset of markdown. ```\nyes, even code blocks```",
                          timestamp=datetime.datetime.utcfromtimestamp(1539693869))

    embed.set_image(url="https://cdn.discordapp.com/embed/avatars/0.png")
    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
    embed.set_author(name="author name", url="https://discordapp.com",
                     icon_url="https://cdn.discordapp.com/embed/avatars/0.png")
    embed.set_footer(text="footer text", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")

    embed.add_field(name="🤔", value="some of these properties have certain limits...")
    embed.add_field(name="😱", value="try exceeding some of them!")
    embed.add_field(name="🙄",
                    value="an informative error should show up, and this view will remain as-is until all issues are fixed")
    embed.add_field(name="<:thonkang:219069250692841473>", value="these last two", inline=True)
    embed.add_field(name="<:thonkang:219069250692841473>", value="are inline fields", inline=True)
    return embed


def format_time(seconds):
    m, s = divmod(seconds, 60)
    return "%02d:%02d" % (m, s)


def progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=35, fill='▰'):
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
    return '%s |%s| %s%% %s' % (prefix, bar, percent, suffix)
