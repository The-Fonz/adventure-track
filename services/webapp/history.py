import requests
from flask import Blueprint, current_app
from flask_restful import Resource, Api, reqparse, inputs

bp = Blueprint('history', __name__)
api = Api(bp)

parser = reqparse.RequestParser()
parser.add_argument('--since', type=inputs.datetime_from_iso8601,
    help="Retrieve items with timestamp after this datetime, must be in ISO 8601 format")

class Tracks(Resource):
    def get(self, adventure_id, since=None):
        args = parser.parse_args()
        # Get location points (simplified if needed)
        loc_url = current_app.config['CA_LOCATION_SERVICE']
        # Must be specified with trailing slash
        if not loc_url[-1] == '/':
            raise Warning("Specify service URL with trailing slash")
        resp = requests.get(loc_url + adventure_id,
                timeout=3.05,
                params={'since': args.get('since', None)})
        if resp.status_code != 200:
            return resp.text, resp.status_code
        return resp.json()

class Posts(Resource):
    def get(self, adventure_id, since=None):
        args = parser.parse_args()
        args.get('since', None)
        return "all posts since"

class ChatMsgs(Resource):
    def get(self, adventure_id, since=None):
        args = parser.parse_args()
        args.get('since', None)
        return "all chat msgs since"

api.add_resource(Tracks, '/tracks/<adventure_id>')
api.add_resource(Posts, '/posts/<adventure_id>')
api.add_resource(ChatMsgs, '/chatmsgs/<adventure_id>')
