from flask import Blueprint

bp = Blueprint('serve', __name__)

@bp.route('/')
def serve_spa():
    # Get config for specific site
    # Return template using proper config
    return 'Hello world!'
