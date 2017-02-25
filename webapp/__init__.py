from flask import Flask

app = Flask(__name__)

# TODO: Set up authentication here

from .serve import bp as serve_bp
app.register_blueprint(serve_bp)

from .history import bp as history_bp
app.register_blueprint(history_bp)

from .live import bp as live_bp
app.register_blueprint(live_bp)

from .siteconfig import bp as config_bp
app.register_blueprint(config_bp)
