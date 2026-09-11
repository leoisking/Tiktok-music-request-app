import http.client
import ssl
import unittest
import urllib.error
from unittest.mock import patch

import spotify_oauth_helper as helper
from spotify_oauth_helper import CallbackServer


class TlsContextTests(unittest.TestCase):
    def test_module_does_not_disable_global_certificate_verification(self):
        self.assertIsNot(ssl._create_default_https_context, ssl._create_unverified_context)

    def test_verifying_context_keeps_verification_but_tolerates_inspection_cas(self):
        context = helper.verifying_ssl_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertFalse(context.verify_flags & ssl.VERIFY_X509_STRICT)

    def test_token_exchange_uses_the_verifying_context(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *arguments):
                return False

            def read(self):
                return b'{"refresh_token": "token"}'

        with patch.object(helper.urllib.request, 'urlopen', return_value=Response()) as urlopen:
            payload = helper._exchange_code_for_tokens('id', 'secret', 'code', 'http://127.0.0.1:8888/callback')
        self.assertEqual(payload['refresh_token'], 'token')
        context = urlopen.call_args.kwargs['context']
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertFalse(context.verify_flags & ssl.VERIFY_X509_STRICT)

    def test_certificate_failures_explain_network_inspection(self):
        error = urllib.error.URLError(ssl.SSLCertVerificationError('certificate verify failed: self-signed certificate'))
        with patch.object(helper.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaises(RuntimeError) as raised:
                helper._exchange_code_for_tokens('id', 'secret', 'code', 'http://127.0.0.1:8888/callback')
        message = str(raised.exception)
        self.assertIn('intercepting', message)
        self.assertIn('SSL_CERT_FILE', message)


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
