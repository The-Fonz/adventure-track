import json
import unittest
from unittest.mock import patch

from flask import Flask

from webapp import history


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(history.bp)
        self.app.config.update(
            DEBUG=True,
            TESTING=True,
            CA_LOCATION_SERVICE='mock-location-link',
        )
        self.app = self.app.test_client()
        self.mock_get_patcher = patch('webapp.history.requests.get')
        # Start patching
        self.mock_get = self.mock_get_patcher.start()

    def tearDown(self):
        self.mock_get_patcher.stop()

    def test_track_statuscode_not_200(self):
        "Should return status message and code from track server if not 200"
        self.mock_get.return_value.status_code = 999
        self.mock_get.return_value.text = 'too bad!'
        rv = self.app.get('/tracks/nonexisting-id')
        self.assertEqual(rv.status_code, 999)
        # Ignore quotes by using *in*
        self.assertIn('too bad!', rv.data.decode('utf-8'))

    def test_track_success(self):
        "Should return output of track service if success"
        # Set behavior of mocked get
        self.mock_get.return_value.json.return_value = {'hi': 'there'}
        self.mock_get.return_value.status_code = 200
        rv = self.app.get('/tracks/nonexisting-id')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'application/json')
        self.assertEqual(json.loads(rv.data.decode('utf-8')), {'hi': 'there'})

    # def test_post_success(self):
    #     pass


if __name__=="__main__":
    unittest.main()
