from flask import Blueprint
from flask_socketio import SocketIO

bp = Blueprint('live', __name__)
# socketio = SocketIO(bp)

# Listen to pubsub module, broadcast named msg on new location point

# Listen to pubsub module, broadcast named msg on new msg

# Listen to pubsub module, broadcast named msg on new chatmsg

# Listen to websocket for chatmsg, filter, post to messages service
