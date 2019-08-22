from BotConfig import BotConfig
from MusicBot import MusicBot
from RestAPI import app
import threading


if __name__ == "__main__":
    bot_config = BotConfig()
    bot = MusicBot(bot_config)
    app.config['bot'] = bot
    thread = threading.Thread(target=lambda: app.run(host='127.0.0.1'))
    thread.start()
    bot.run(bot_config.bot_auth_key)
