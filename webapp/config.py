from flask import Blueprint

bp = Blueprint('config', __name__)

@bp.route('/')
def config_dashboard():
    # Use flask-admin to edit users, sites
    return 'Hello world!'
