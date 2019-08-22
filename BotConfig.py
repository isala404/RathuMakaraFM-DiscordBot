import os


class BotConfig:
    def __init__(self):
        self.prefix = self.get_env("prefix", required=True, as_string=True)
        self.bot_voice_channel = self.get_env("bot_voice_channel", required=True)
        self.player_channel = self.get_env("player_channel", required=True)
        self.bot_cmd_channel = self.get_env("bot_cmd_channel", required=True)
        self.song_request_channel = self.get_env("song_request_channel", required=True)
        self.song_request_queue_channel = self.get_env("song_request_queue_channel", required=True)
        self.playlist_queue_channel = self.get_env("playlist_queue_channel", required=True)
        self.cmd_help_channel = self.get_env("cmd_help_channel", required=True)
        self.developer_client_id = self.get_env("developer_client_id", required=True)
        self.bot_log_channel = self.get_env("bot_log_channel", required=True)
        self.bot_commanders = self.get_env("bot_commanders", required=True)
        self.bot_auth_key = self.get_env("bot_auth_key", required=True)
        self.discord_client_id = self.get_env("discord_client_id", required=True)
        self.discord_client_secret = self.get_env("discord_client_secret", required=True)
        self.web_api_auth_key = self.get_env("web_api_auth_key", required=True)
        self.guild_id = self.get_env("guild_id", required=True)

    @staticmethod
    def get_env(name, required, as_string=False):
        var = os.getenv(name)
        if required and not var:
            raise RuntimeError(f"{name} environment variables is not defined")
        if as_string:
            return var
        return eval(var)
