import os


class BotConfig:
    def __init__(self):
        self.prefix = self.get_env("prefix", required=True)
        self.bot_voice_channel = self.get_env("bot_voice_channel", required=True, as_int=True)
        self.player_channel = self.get_env("player_channel", required=True, as_int=True)
        self.bot_cmd_channel = self.get_env("bot_cmd_channel", required=True, as_int=True)
        self.song_request_channel = self.get_env("song_request_channel", required=True, as_int=True)
        self.song_request_queue_channel = self.get_env("song_request_queue_channel", required=True, as_int=True)
        self.playlist_queue_channel = self.get_env("playlist_queue_channel", required=True, as_int=True)
        self.cmd_help_channel = self.get_env("cmd_help_channel", required=True, as_int=True)
        self.developer_client_id = self.get_env("developer_client_id", required=True, as_int=True)
        self.bot_log_channel = self.get_env("bot_log_channel", required=True, as_int=True)
        self.bot_commanders = self.get_env("bot_commanders", required=True, as_list=True)
        self.bot_auth_key = self.get_env("bot_auth_key", required=True)
        self.guild_id = self.get_env("guild_id", required=True)
        self.web_api_auth_key = self.get_env("web_api_auth_key", required=True)

    @staticmethod
    def get_env(name, required=False, as_int=False, as_list=False):
        var = os.getenv(name).strip()
        if required and not var:
            raise RuntimeError(f"{name} environment variables is not defined")
        if as_int:
            return int(var)
        if as_list:
            return var.split(",")
        return var
