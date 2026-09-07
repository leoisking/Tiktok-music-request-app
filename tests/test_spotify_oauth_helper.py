import http.client
import unittest

from spotify_oauth_helper import CallbackServer


class OAuthCallbackTests(unittest.TestCase):
    def setUp(self):
        self.server = CallbackServer('127.0.0.1', 0, 'expected-state', '/custom-callback')
        self.server.start()
        self.addCleanup(self.server.stop)

    def request(self, query, path='/custom-callback'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.httpd.server_port, timeout=3)
        try:
            connection.request('GET', path + '?' + query)
            response = connection.getresponse()
            response.read()
            return response.status
        finally:
            connection.close()

    def test_invalid_state_cannot_abort_authorization(self):
        self.assertEqual(self.request('state=wrong&error=access_denied'), 400)
        self.assertFalse(self.server.done.is_set())
        self.assertIsNone(self.server.error)
        self.assertEqual(self.request('state=expected-state&code=valid-code'), 200)
        self.assertTrue(self.server.done.wait(1))
        self.assertEqual(self.server.code, 'valid-code')

    def test_callback_cannot_be_replayed(self):
        self.assertEqual(self.request('state=expected-state&code=first'), 200)
        self.assertTrue(self.server.done.wait(1))
        self.assertEqual(self.request('state=expected-state&code=second'), 409)
        self.assertEqual(self.server.code, 'first')

    def test_custom_path_and_invalid_query(self):
        self.assertEqual(self.request('state=expected-state&code=first', '/callback'), 404)
        self.assertEqual(self.request('&'.join('field=value' for field in range(11))), 400)
        self.assertFalse(self.server.done.is_set())

    def test_trusted_error_is_reported(self):
        self.assertEqual(self.request('state=expected-state&error=access_denied'), 200)
        self.assertTrue(self.server.done.wait(1))
        self.assertIn('access_denied', self.server.error)


if __name__ == '__main__':
    unittest.main()
