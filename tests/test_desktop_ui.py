import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

import desktop_launcher as launcher
from desktop_branding import icon_png, write_windows_icon
from desktop_ui import initial_window_geometry


@unittest.skipUnless(os.name == 'nt', 'Windows launcher interface')
class DesktopInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='widget-ui-test-')
        self.directory = Path(self.temporary.name)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = launcher.DesktopApp(self.root, self.directory)
        self.root.update_idletasks()

    def tearDown(self):
        if self.root.tk.call('winfo', 'exists', '.'):
            self.app.destroy()
        self.temporary.cleanup()

    def test_navigation_preserves_unsaved_fields(self):
        self.app.variables['TIKTOK_USER'].set('test-channel')
        for page in self.app.view.pages:
            self.app.view.show_page(page)
            self.assertEqual(self.app.view.page, page)
            self.assertEqual(self.app.variables['TIKTOK_USER'].get(), 'test-channel')
        self.assertIn('Unsaved changes', self.app.view.saved_text.get())

    def test_logs_folder_label_is_complete_and_fits(self):
        button = self.app.view.data_folder_button
        self.assertEqual(str(button.cget('text')), 'Logs & settings folder')
        self.assertGreaterEqual(button.winfo_width(), button.winfo_reqwidth())

    def test_chat_fields_follow_selected_source(self):
        for source, tiktok, twitch in (('preview', False, False), ('tiktok', True, False),
                                       ('twitch', False, True), ('both', True, True)):
            with self.subTest(source=source):
                self.app.variables['CHAT_SOURCE'].set(source)
                self.assertEqual(bool(self.app.view.tiktok_field.winfo_manager()), tiktok)
                self.assertEqual(bool(self.app.view.twitch_field.winfo_manager()), twitch)
                self.assertEqual(str(self.app.start_button.cget('text')), 'Start preview' if source == 'preview' else 'Start widget')

    def test_automatic_votes_disable_only_the_fixed_threshold(self):
        threshold = self.app.view.fields['SKIP_THRESHOLD']
        self.assertTrue(threshold.instate(['disabled']))
        self.app.variables['ADAPTIVE_SKIP_THRESHOLD_ENABLED'].set(False)
        self.assertFalse(threshold.instate(['disabled']))
        self.app.set_active(True)
        self.assertTrue(threshold.instate(['disabled']))
        self.app.set_active(False)
        self.assertFalse(threshold.instate(['disabled']))

    def test_running_locks_settings_but_allows_navigation(self):
        self.app.process.server = MagicMock()
        self.app.set_active(True)
        self.assertTrue(all(control.instate(['disabled']) for control, state in self.app.configuration_controls))
        self.assertTrue(self.app.start_button.instate(['disabled']))
        self.assertFalse(self.app.stop_button.instate(['disabled']))
        self.app.view.show_page('overlays')
        self.assertEqual(self.app.view.page, 'overlays')
        self.app.process.server = None

    def test_password_is_hidden_again_when_changing_pages(self):
        entry, button = self.app.view.secrets[0]
        self.app.view._toggle_secret(entry, button)
        self.assertEqual(str(entry.cget('show')), '')
        self.app.view.show_page('overlays')
        self.assertEqual(str(entry.cget('show')), '*')
        self.assertEqual(str(button.cget('text')), 'Show')

    def test_copy_feedback_never_displays_the_password(self):
        password = self.app.variables['CONTROL_PASSWORD'].get()
        with patch.object(self.root, 'clipboard_clear'), patch.object(self.root, 'clipboard_append') as append:
            self.app.copy(password, 'Control password')
        append.assert_called_once_with(password)
        self.assertIn('Keep it private', self.app.view.notice.cget('text'))
        self.assertNotIn(password, self.app.view.notice.cget('text'))

    def test_save_clears_dirty_state_and_preserves_fields(self):
        self.app.variables['TIKTOK_USER'].set('example')
        self.assertTrue(self.app.save())
        self.assertNotIn('Unsaved changes', self.app.view.saved_text.get())
        self.assertEqual(launcher.load_settings(self.directory)['TIKTOK_USER'], 'example')

    def test_save_failure_does_not_claim_success(self):
        self.app.variables['TIKTOK_USER'].set('example')
        with patch.object(launcher, 'save_settings', side_effect=OSError('disk unavailable')):
            self.assertFalse(self.app.save())
        self.assertIn('Unsaved changes', self.app.view.saved_text.get())
        self.assertIn('disk unavailable', self.app.view.notice.cget('text'))

    def test_invalid_start_uses_inline_error_and_relevant_page(self):
        self.app.variables['CHAT_SOURCE'].set('tiktok')
        self.app.view.show_page('preferences')
        self.app.start()
        self.assertEqual(self.app.view.page, 'setup')
        self.assertTrue(self.app.view.fields['TIKTOK_USER'].instate(['invalid']))
        self.assertIn('username', self.app.view.notice.cget('text'))
        self.assertIsNone(self.app.process.server)

    def test_advanced_settings_are_collapsible_without_losing_values(self):
        self.app.variables['SPOTIFY_REFRESH_TOKEN'].set('test-token')
        self.app.view.toggle_advanced()
        self.assertTrue(self.app.view.advanced_visible)
        self.app.view.toggle_advanced()
        self.assertFalse(self.app.view.advanced_visible)
        self.assertEqual(self.app.variables['SPOTIFY_REFRESH_TOKEN'].get(), 'test-token')

    def test_links_disabled_until_ready_and_control_remains_local(self):
        self.assertTrue(all(button.instate(['disabled']) for button in self.app.link_buttons))
        self.app.process.settings = {'PORT': '6123'}
        self.app.update_urls('https://example.trycloudflare.com')
        self.assertTrue(all(not button.instate(['disabled']) for button in self.app.link_buttons))
        self.assertEqual(self.app.urls['Control panel'].get(), 'http://127.0.0.1:6123/control')
        self.assertEqual(self.app.urls['Queue overlay'].get(), 'https://example.trycloudflare.com/queue_widget')
        self.app.view.links_ready(False)
        self.assertTrue(all(button.instate(['disabled']) for button in self.app.link_buttons))

    def test_sign_in_can_be_cancelled_without_changing_credentials(self):
        self.app.oauth_busy = True
        self.app.variables['SPOTIFY_REFRESH_TOKEN'].set('existing-test-token')
        self.app.cancel_spotify()
        self.assertTrue(self.app.oauth_cancelled.is_set())
        self.app.events.put(('spotify_cancelled', ''))
        self.root.after_cancel(self.app.tick_after)
        self.app.tick()
        self.assertFalse(self.app.oauth_busy)
        self.assertEqual(self.app.variables['SPOTIFY_REFRESH_TOKEN'].get(), 'existing-test-token')
        self.assertIn('cancelled', self.app.spotify_status.get())

    def test_start_is_ignored_during_sign_in(self):
        self.app.oauth_busy = True
        with patch.object(self.app.process, 'start') as start:
            self.app.start()
        start.assert_not_called()

    def test_missing_spotify_credentials_use_inline_validation(self):
        self.app.view.show_page('setup')
        self.app.connect_spotify()
        self.assertEqual(self.app.view.page, 'connections')
        self.assertTrue(self.app.view.fields['SPOTIFY_CLIENT_ID'].instate(['invalid']))
        self.assertFalse(self.app.oauth_busy)

    def test_close_cancel_keeps_unsaved_changes(self):
        self.app.variables['TIKTOK_USER'].set('not-saved')
        with patch.object(self.app.messagebox, 'askyesnocancel', return_value=None):
            self.app.close()
        self.assertFalse(self.app.closing)
        self.assertTrue(self.root.winfo_exists())

    def test_close_checks_before_stopping_a_running_stream(self):
        self.app.process.server = MagicMock()
        with patch.object(self.app.messagebox, 'askyesno', return_value=False), patch.object(self.app, 'stop') as stop:
            self.app.close()
        stop.assert_not_called()
        self.assertFalse(self.app.closing)
        self.app.process.server = None

    def test_close_does_not_silently_discard_an_active_sign_in(self):
        self.app.oauth_busy = True
        self.app.variables['SPOTIFY_CLIENT_ID'].set('unsaved-client')
        with patch.object(self.app.messagebox, 'askyesno', return_value=False):
            self.app.close()
        self.assertFalse(self.app.closing)
        self.assertFalse(self.app.oauth_cancelled.is_set())

    def test_initial_window_fits_a_small_laptop_display(self):
        screen = MagicMock()
        screen.winfo_screenwidth.return_value = 1366
        screen.winfo_screenheight.return_value = 768
        self.assertEqual(initial_window_geometry(screen), '1120x668')
        screen.winfo_screenwidth.return_value = 1920
        screen.winfo_screenheight.return_value = 1080
        self.assertEqual(initial_window_geometry(screen), '1120x820')

    def test_responsive_setup_stacks_at_small_widths(self):
        event = MagicMock(width=840)
        self.app.view._resize_content(event)
        self.assertEqual(self.app.view.setup_side.grid_info()['column'], 1)
        event.width = 620
        self.app.view._resize_content(event)
        self.assertEqual(self.app.view.setup_side.grid_info()['column'], 0)
        self.assertEqual(self.app.view.setup_side.grid_info()['row'], 1)

    def test_icon_is_loadable_and_windows_icon_is_generated(self):
        self.assertTrue(icon_png(32).startswith(b'\x89PNG'))
        path = self.directory / 'test.ico'
        write_windows_icon(path)
        source = Path(__file__).resolve().parents[1] / 'LiveWidget.ico'
        self.assertEqual(path.read_bytes(), source.read_bytes())


if __name__ == '__main__':
    unittest.main()
