[![codebeat badge](https://codebeat.co/badges/2feda3cc-114f-40a1-a9e2-b6dc26ce3fd2)](https://codebeat.co/projects/github-com-mrsupiri-rathumakarafm-discordbot-master)
![GitHub issues](https://img.shields.io/github/issues/mrsupiri/RathuMakaraFM-DiscordBot)
[![Requirements Status](https://requires.io/github/mrsupiri/RathuMakaraFM-DiscordBot/requirements.svg?branch=master)](https://requires.io/github/mrsupiri/RathuMakaraFM-DiscordBot/requirements/?branch=master)
![GitHub license](https://img.shields.io/github/license/mrsupiri/RathuMakaraFM-DiscordBot)
![Platform](https://img.shields.io/badge/platform-Kubernetes/Docker/Linux-blue)
[![Say Thanks!](https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg)](https://saythanks.io/to/mrsupiri)
[![Discord Shield](https://discordapp.com/api/guilds/589829086583455757/widget.png?style=shield)](https://discord.gg/8dQCZzk)
[![Twitter Follow](https://img.shields.io/twitter/follow/mrsupiri?style=social)](https://twitter.com/mrsupiri)


# RathuMakaraFM-DiscordBot
This Discord Bot Used to Manage The first Sri Lanken Open-Mic Online Radio, [RathumakaraFM](http://rathumakara.com/)


## Technologies Used
- Async.io 
- Docker
- WebSocket
- OAuth2
- ffmpeg
- Discord.py

#### Commands for @admin/@DJ
```diff
!play [song url | song name]                                          (alias - !p)
-  Play Song from url or search youtube if only a name is given
!playnext [song url | song name]                                      (alias - !pn)
- Add this song to top of the queue
!playnow [song url | song name] 
- Skip song currently playing song and instantly start playing this the song
!playlist [playlist url]
-  Plays a entire playlist from youtube **only works for youtube
!join
-  Join callers current channel
!volume [level]                                                       (alias - !v)
-  Change the Volume level
!skip                                                                 (alias - !s)
-  Skip the current song
!pause                                                                (alias - !ps)
-  Pause the current song
!resume                                                               (alias - !r)
-  Resume the current song
!clearQueue
-  Clear the whole playlist
!stream [stream url]
-  Playback a live stream **only works on twitch.tv
!remove [song number]                                                 (alias - !rm)
-  Remove the song from the queue
!autoplay [on/off]                                                    (alias - !ap)
-  Enable/Disable Auto Playing Music if Queue is empty
!shuffle
-  Pseudo randomly shuffle the queue
!reset
-  Restart the bot
!move [song to be moved] [position to be moved]                       (alias - !m)
-  Change the position of the song in the queue, if second 
-  option is not give song will be moved to top of the queue
```

#### Commands for @everyone
```diff
!request [song url | song name]                                       (alias - !req)
-  You can request a song by a url or song name and 
-  admins review it and add it to queue
-  This command only work in #song-request
!hello
-  Bot will say hello to you
```

| WARNING: This was tailor made to run on Rathumakara Discord |
| --- |

## Setup Development Environment 

You need to have docker installed on your system and build the custom docker image with the Dockerfile on .github/development

```bash
cd .github/development
docker-compose up --build
```

## Usage
- Update the environment variables in .github/development/docker-compose.yaml
- Build the Docker container with `docker-compose up --build`

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

