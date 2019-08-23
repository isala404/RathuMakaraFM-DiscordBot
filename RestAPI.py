from flask import Flask, request, jsonify
from utils import *
import asyncio

app = Flask(__name__)


@app.route('/API/bot/get/user/', methods=["POST"])
def user_info():
    try:
        response = validate_request(app, request)
        if isinstance(response, str):
            return response
        else:
            user, guild, member, _ = response

        d = {
            'name': user.name,
            'roles': [y.id for y in member.roles],
            'is_bot': user.bot,
            'dm_channel': user.dm_channel,
            'created_at': user.created_at,
            'default_avatar_url': user.default_avatar_url,
            'is_blocked': user.is_blocked()
        }
        return jsonify(d)

    except Exception as e:
        app.config['bot'].logger.error("Error While Processing a API Request")
        app.config['bot'].logger.exception(e)
        return json.dumps({'error': 'Internal Server Error'}), 400, {'ContentType': 'application/json'}


@app.route('/API/bot/request/', methods=["POST"])
def bot_command():
    try:
        response = validate_request(app, request)
        if isinstance(response, str):
            return response
        else:
            user, guild, member, data = response

        if data['cmd'] != "request" and not [y.id for y in member.roles if
                                             y.id in app.config['bot'].BotConfig.bot_commanders]:
            return json.dumps({'error': 'User Don\'t have permission for this action'}), 401, {
                'ContentType': 'application/json'}

        result = asyncio.run_coroutine_threadsafe(
            parse_cmd(app.config['bot'], data['cmd'], data['args'], user), app.config['bot'].loop)

        if result.result():
            return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

    except Exception as e:
        app.config['bot'].logger.error("Error While Processing a API Request")
        app.config['bot'].logger.exception(e)
        return json.dumps({'error': 'Internal Server Error'}), 400, {'ContentType': 'application/json'}


@app.route('/player_status/', methods=["GET"])
def get_player_status():
    try:
        while True:
            if os.stat("status.json").st_size != 0:
                break

        with open('status.json', "r") as f:
            return jsonify(json.load(f))

    except Exception as e:
        app.logger.error("Reading status.json")
        app.logger.exception(e)
        return jsonify(
            {
                "now_playing": {"song": None, "uploader": None, "thumbnail": None, "url": None,
                                "duration": None, "progress": None, "extractor": None, "requester": None,
                                "is_pause": False},
                'queue': [],
                "is_pause": False,
                "auto_play": False,
                "volume": 100
            }
        )
