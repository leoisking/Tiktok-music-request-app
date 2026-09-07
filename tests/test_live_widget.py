import asyncio
import base64
import hashlib
import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from TikTokLive.proto import User

os.environ['ALLOWED_ORIGINS'] = ''

import live_widget as widget


class WidgetTests(unittest.TestCase):
    def setUp(self):
        self.settings = patch.multiple(
            widget, CONTROL_PASSWORD='test-only-password', MOD_SET={'trusted', 'twitch:trusted'},
            AUTO_NEXT_ON_THRESHOLD=False, AUTO_RESET_SKIP_ENABLED=False,
            SPOTIFY_QUEUE_ON_REQUEST=False, ADAPTIVE_SKIP_THRESHOLD_ENABLED=False,
        )
        self.settings.start()
        self.addCleanup(self.settings.stop)
        widget.socket_rate_buckets.clear()
        widget.song_queue.clear()
        widget.request_last_by_user.clear()
        widget.request_last_song_by_user.clear()
        widget.active_chat_users.clear()
        widget.manual_skip_threshold_override = None
        widget.reset_skip_state()
        widget.visibility_state.update(requests=False, chat=True, voting=True)
        self.client = widget.socketio.test_client(widget.app)
        self.addCleanup(self.client.disconnect)

    def emit(self, event, **payload):
        return self.client.emit(event, payload, callback=True)

    def test_public_state_is_read_only_and_targeted(self):
        observer = widget.socketio.test_client(widget.app)
        self.addCleanup(observer.disconnect)
        self.assertTrue(self.emit('request_state')['success'])
        names = {event['name'] for event in self.client.get_received()}
        self.assertIn('update_queue', names)
        self.assertIn('update_now_playing', names)
        self.assertEqual(observer.get_received(), [])

    def test_moderator_names_cannot_authorize_socket_actions(self):
        for event in ('mod_auth', 'mod_clear', 'mod_reset', 'mod_set_threshold', 'set_visibility', 'simulate_comment'):
            with self.subTest(event=event):
                self.assertEqual(self.emit(event, moderator='trusted', user='trusted'), {'error': 'unauthorized'})

    def test_loopback_and_forwarding_headers_cannot_bypass_password(self):
        for address in ('127.0.0.1', '::1', '::ffff:127.0.0.1', '198.51.100.2'):
            with self.subTest(address=address), widget.app.test_request_context(
                '/', environ_base={'REMOTE_ADDR': address}, headers={'X-Forwarded-For': '127.0.0.1'}
            ):
                self.assertFalse(widget._is_authorized_action({}))

    def test_empty_password_disables_controls(self):
        with patch.object(widget, 'CONTROL_PASSWORD', ''):
            self.assertEqual(self.emit('mod_auth', password=''), {'error': 'unauthorized'})

    def test_unicode_password_and_invalid_password_types(self):
        with patch.object(widget, 'CONTROL_PASSWORD', 'private-🔒-password'):
            self.assertTrue(self.emit('mod_auth', password='private-🔒-password')['success'])
        self.assertEqual(self.emit('mod_auth', password=['test-only-password']), {'error': 'unauthorized'})
        self.assertEqual(self.emit('mod_auth', password='invalid-\ud800'), {'error': 'unauthorized'})

    def test_authorized_queue_clear(self):
        widget.song_queue.append({'song': 'Keep me', 'user': 'Viewer'})
        self.assertEqual(self.emit('mod_clear'), {'error': 'unauthorized'})
        self.assertEqual(len(widget.song_queue), 1)
        self.assertTrue(self.emit('mod_clear', password='test-only-password')['success'])
        self.assertEqual(widget.song_queue, [])

    def test_socket_payload_types(self):
        for payload in ([], 'not an object', 42):
            self.assertEqual(self.client.emit('set_visibility', payload, callback=True), {'error': 'invalid_payload'})

    def test_visibility_is_strict_and_atomic(self):
        original = dict(widget.visibility_state)
        response = self.emit('set_visibility', password='test-only-password', requests=True, voting='false')
        self.assertEqual(response, {'error': 'invalid_payload'})
        self.assertEqual(widget.visibility_state, original)
        self.assertTrue(self.emit('set_visibility', password='test-only-password', requests=True)['success'])
        self.assertTrue(widget.visibility_state['requests'])
        self.assertTrue(widget.visibility_state['voting'])

    def test_extra_socket_arguments_are_rejected(self):
        response = self.client.emit('mod_clear', {}, 'extra', callback=True)
        self.assertEqual(response, {'error': 'invalid_payload'})

    def test_simulation_validates_fields(self):
        for payload in ({'nickname': []}, {'message': 'x' * 281}, {'is_moderator': 'false'}, {'message': ''}):
            data = {'password': 'test-only-password', 'message': '!skip'}
            data.update(payload)
            self.assertEqual(self.emit('simulate_comment', **data), {'error': 'invalid_payload'})

    def test_state_rate_limit(self):
        for attempt in range(4):
            self.assertTrue(self.emit('request_state')['success'])
        self.assertEqual(self.emit('request_state'), {'error': 'rate_limited'})

    def test_rate_limit_expires_and_memory_is_bounded(self):
        with patch.object(widget.time, 'monotonic', return_value=100):
            self.assertTrue(widget._consume_socket_budget('test', 'viewer', 1))
            self.assertFalse(widget._consume_socket_budget('test', 'viewer', 1))
        with patch.object(widget.time, 'monotonic', return_value=111):
            self.assertTrue(widget._consume_socket_budget('test', 'viewer', 1))
        for viewer in range(4200):
            widget._consume_socket_budget('test', str(viewer), 1)
        self.assertLessEqual(len(widget.socket_rate_buckets), 4096)

    def test_moderator_display_name_impersonation(self):
        self.assertFalse(widget.is_mod('trusted', 'attacker'))
        self.assertFalse(widget.is_mod('trusted', ''))
        self.assertTrue(widget.is_mod('New display name', 'TRUSTED'))
        self.assertTrue(widget.is_mod('', 'trusted', source='twitch'))

    def test_twitch_uses_account_name_not_display_name(self):
        fake = '@display-name=trusted;user-id=99;mod=0 :attacker!user@host PRIVMSG #channel :!clear'
        real = '@display-name=SomeoneElse;user-id=42;mod=0 :trusted!user@host PRIVMSG #channel :!clear'
        self.assertFalse(widget._parse_twitch_privmsg(fake)[3])
        self.assertTrue(widget._parse_twitch_privmsg(real)[3])

    def test_vote_deduplication_and_unidentified_guests(self):
        self.assertEqual(widget.process_comment('Viewer', '42', '!skip')['action'], 'skip')
        self.assertEqual(widget.process_comment('Renamed', '42', '!skip')['action'], 'duplicate_skip')
        self.assertEqual(widget.process_comment('Guest', '', '!skip')['action'], 'ignored')
        self.assertEqual(widget.skip_votes['skips'], 1)

    def test_native_tiktok_username_is_used(self):
        for account_id in (0, 123):
            with self.subTest(account_id=account_id):
                event = widget.CommentEvent(user_info=User(nick_name='Viewer', username='Viewer123', id=account_id), content='!skip')
                self.assertEqual(widget.extract_user(event), ('Viewer', 'viewer123'))

    def test_tiktok_dictionary_and_object_user_shapes(self):
        for user_key in ('user_info', 'userInfo', 'user'):
            for identity_key, value in (('uniqueId', 'viewer123'), ('unique_id', 'viewer123'), ('username', 'viewer123'),
                                        ('secUid', 'secure123'), ('sec_uid', 'secure123'), ('id', 123), ('id_str', '123')):
                for dictionary in (False, True):
                    with self.subTest(user_key=user_key, identity_key=identity_key, dictionary=dictionary):
                        fields = {'nickname': 'Viewer', identity_key: value}
                        user = fields if dictionary else SimpleNamespace(**fields)
                        event = SimpleNamespace(**{user_key: user})
                        self.assertEqual(widget.extract_user(event), ('Viewer', str(value)))

    def test_tiktok_serialized_user_and_event_fallbacks(self):
        fields = {'nickName': 'Viewer', 'uniqueId': 'viewer123'}
        for method in ('to_pydict', 'to_dict'):
            user = SimpleNamespace(**{method: lambda: fields})
            self.assertEqual(widget.extract_user(SimpleNamespace(user_info=user)), ('Viewer', 'viewer123'))
        for key in ('raw_data', 'as_dict', 'to_pydict', 'to_dict'):
            for callable_payload in (False, True):
                with self.subTest(key=key, callable_payload=callable_payload):
                    payload = {'user': fields}
                    event = SimpleNamespace(**{key: (lambda: payload) if callable_payload else payload})
                    self.assertEqual(widget.extract_user(event), ('Viewer', 'viewer123'))

    def test_broken_optional_serialization_does_not_erase_identity(self):
        event = SimpleNamespace(
            user_info=SimpleNamespace(nickname='Viewer', unique_id='viewer123'),
            as_dict=Mock(side_effect=RuntimeError('optional serialization failed')),
        )
        self.assertEqual(widget.extract_user(event), ('Viewer', 'viewer123'))
        event.user_info = SimpleNamespace(to_pydict=Mock(side_effect=RuntimeError('bad user serializer')))
        event.raw_data = {'user': {'nickname': 'Viewer', 'uniqueId': 'viewer123'}}
        self.assertEqual(widget.extract_user(event), ('Viewer', 'viewer123'))

    def test_empty_fallback_does_not_overwrite_primary_identity(self):
        event = SimpleNamespace(
            user_info={'nickname': 'Viewer', 'uniqueId': 'viewer123'},
            raw_data={'user': {'nickname': '', 'uniqueId': ''}},
        )
        self.assertEqual(widget.extract_user(event), ('Viewer', 'viewer123'))

    def test_invalid_numeric_identity_uses_valid_fallback(self):
        for invalid_id in (0, '0', -1, '-1', True, {}, [], 'unknown'):
            with self.subTest(invalid_id=invalid_id):
                event = SimpleNamespace(user_info={'nickname': 'Viewer', 'id': invalid_id, 'id_str': '123'})
                self.assertEqual(widget.extract_user(event), ('Viewer', '123'))
                event.user_info.pop('id_str')
                self.assertEqual(widget.extract_user(event), ('Viewer', ''))

    def test_same_display_name_viewers_do_not_share_votes_or_cooldowns(self):
        with patch.object(widget, 'REQUEST_COOLDOWN_SEC', 8):
            for account in ('first_viewer', 'second_viewer'):
                event = widget.CommentEvent(user_info=User(nick_name='Same Name', username=account), content='!skip')
                nickname, identity = widget.extract_user(event)
                self.assertEqual(widget.process_chat_message('tiktok', nickname, identity, '!skip')['action'], 'skip')
                self.assertEqual(widget.process_chat_message('tiktok', nickname, identity, '!req Test Song')['action'], 'request')
                self.assertEqual(widget.process_chat_message('tiktok', nickname, identity, '!skip')['action'], 'duplicate_skip')
                self.assertEqual(widget.process_chat_message('tiktok', nickname, identity, '!req Other Song')['action'], 'request_rate_limited')
        self.assertEqual(widget.skip_votes['skips'], 2)
        self.assertEqual(len(widget.song_queue), 2)

    def test_extracted_display_name_cannot_grant_moderator_access(self):
        event = widget.CommentEvent(user_info=User(nick_name='trusted', username='attacker'), content='!clear')
        self.assertFalse(widget.is_mod(*widget.extract_user(event)))
        event.user_info.username = 'trusted'
        self.assertTrue(widget.is_mod(*widget.extract_user(event)))

    def test_tiktok_handler_uses_stable_identity_and_preserves_mod_aliases(self):
        handlers = {}

        def register(event_type):
            def save_handler(handler):
                handlers[event_type] = handler
                return handler
            return save_handler

        client = SimpleNamespace(on=register)
        with patch.object(widget, 'TikTokLiveClient', return_value=client):
            self.assertIs(widget.create_client_and_connect(), client)
        for usernames, moderators in ((('viewer', ''), set()), (('trusted', ''), {'trusted'}), (('viewer', ''), {'123'})):
            for username in usernames:
                with self.subTest(username=username, moderators=moderators), patch.object(widget, 'MOD_SET', moderators):
                    event = widget.CommentEvent(user_info=User(nick_name='trusted', username=username, id=123), content='!skip')
                    with patch.object(widget, 'process_chat_message') as process:
                        asyncio.run(handlers[widget.CommentEvent](event))
                    expected_mod = '123' in moderators or bool(username and username in moderators)
                    process.assert_called_once_with('tiktok', 'trusted', '123', '!skip', is_moderator=expected_mod)

    def test_stable_tiktok_identity_survives_renamed_or_missing_username(self):
        for username in ('viewer', 'renamed', ''):
            event = widget.CommentEvent(user_info=User(nick_name='Viewer', username=username, id=123), content='!skip')
            self.assertEqual(widget.extract_user(event, prefer_stable_id=True), ('Viewer', '123'))
        event = SimpleNamespace(user_info={'nickname': 'Viewer', 'username': 'viewer', 'id': '0', 'secUid': 'secure123'})
        self.assertEqual(widget.extract_user(event, prefer_stable_id=True), ('Viewer', 'secure123'))

    def test_rejected_chat_commands_have_diagnostic_logs(self):
        widget.process_chat_message('tiktok', 'Viewer', '123', '!skip')
        for nickname, identity, message, explanation in (
            ('Viewer', '123', '!skip', 'already voted'),
            ('Guest', '', '!skip', 'usable viewer identity'),
            ('Viewer', '123', '!req', 'No supported command matched'),
            ('Viewer', '123', 'hello !unknown', 'No supported command matched'),
        ):
            with self.subTest(message=message, identity=identity), patch('builtins.print') as output:
                widget.process_chat_message('tiktok', nickname, identity, message)
                self.assertIn(explanation, ' '.join(str(call.args) for call in output.call_args_list))

    def test_platform_identities_do_not_share_votes(self):
        widget.process_chat_message('tiktok', 'Viewer', '42', '!skip')
        widget.process_chat_message('twitch', 'Viewer', '42', '!skip')
        self.assertEqual(widget.skip_votes['skips'], 2)

    def test_request_cooldown_and_unicode_commands(self):
        first = widget.process_comment('Viewer', '42', '！req Song by Artist')
        self.assertEqual(first['action'], 'request')
        second = widget.process_comment('Viewer', '42', '!req Another Song')
        self.assertEqual(second['action'], 'request_rate_limited')
        self.assertEqual(len(widget.song_queue), 1)

    def test_invalid_and_valid_thresholds(self):
        for value in ('', 'nan', 0, 201, True, [], 2.5):
            self.assertFalse(widget._set_skip_threshold(value)['ok'])
        self.assertEqual(widget._set_skip_threshold(7)['threshold'], 7)
        self.assertEqual(widget._set_skip_threshold('auto')['mode'], 'fixed')

    def test_nonfinite_environment_values_use_defaults(self):
        for value in ('nan', 'inf', '-inf'):
            with patch.dict(os.environ, {'TEST_FLOAT': value}):
                self.assertEqual(widget._env_float('TEST_FLOAT', 8.0), 8.0)

    def test_security_headers_and_inline_script_hashes(self):
        with widget.app.test_client() as client:
            for path in ('/', '/control', '/queue_widget'):
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    if path == '/control':
                        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
                    else:
                        self.assertNotIn('X-Frame-Options', response.headers)
                    policy = response.headers['Content-Security-Policy']
                    script_policy = policy.split('script-src ', 1)[1].split(';', 1)[0]
                    self.assertNotIn("'unsafe-inline'", script_policy)
                    html = response.get_data(as_text=True).replace('\r\n', '\n')
                    for script in re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL):
                        if script.strip():
                            digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                            self.assertIn('sha256-' + digest, policy)
                    response.close()

    def test_cross_origin_socket_handshake_is_rejected(self):
        with widget.app.test_client() as client:
            response = client.get('/socket.io/?EIO=4&transport=polling', headers={'Origin': 'https://untrusted.example'})
            self.assertEqual(response.status_code, 400)

    def test_tunnel_origin_can_connect_without_wildcard(self):
        with widget.app.test_client() as client:
            response = client.get('/socket.io/?EIO=4&transport=polling', headers={
                'Host': 'overlay.example', 'Origin': 'https://overlay.example', 'X-Forwarded-Proto': 'https',
            })
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
