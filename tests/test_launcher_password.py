import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'nt', 'Windows batch launcher tests')
class LauncherPasswordTests(unittest.TestCase):
    def run_password_setup(self, answers, expected_password, existing_password=None):
        source = (Path(__file__).resolve().parents[1] / 'start_dual_overlay.bat').read_text(encoding='utf-8')
        setup = '\n:configure_control_password\n' + source.split('\n:configure_control_password\n', 1)[1]
        wrapper = (
            '@echo off\n'
            'setlocal EnableExtensions DisableDelayedExpansion\n'
            'call :configure_control_password\n'
            'if errorlevel 1 exit /b 1\n'
            'python -c "import hashlib, os; actual = os.getenv(\'CONTROL_PASSWORD\', \'\'); '
            'raise SystemExit(0 if hashlib.sha256(actual.encode()).hexdigest() == os.environ[\'EXPECTED_PASSWORD_SHA256\'] else 2)"\n'
            'exit /b %errorlevel%\n'
        )
        environment = os.environ.copy()
        environment.pop('CONTROL_PASSWORD', None)
        environment['EXPECTED_PASSWORD_SHA256'] = hashlib.sha256(expected_password.encode()).hexdigest()
        environment['PORT'] = '5000'
        if existing_password is not None:
            environment['CONTROL_PASSWORD'] = existing_password
        with tempfile.TemporaryDirectory(prefix='widget-password-test-') as directory:
            batch_path = Path(directory) / 'password_test.bat'
            input_path = Path(directory) / 'answers.txt'
            batch_path.write_text(wrapper + setup, encoding='utf-8')
            input_path.write_bytes(('\r\n'.join(answers) + '\r\n').encode('ascii'))
            with input_path.open('rb') as input_file:
                result = subprocess.run(
                    [os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/v:off', '/c', str(batch_path)],
                    stdin=input_file, capture_output=True, text=True, env=environment,
                    timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
                )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('http://127.0.0.1:5000/control', result.stdout)
        self.assertNotIn(expected_password, result.stdout + result.stderr)
        return result.stdout

    def test_prompt_creates_password(self):
        output = self.run_password_setup(['chosen-test-password'], 'chosen-test-password')
        self.assertIn('No password is configured yet', output)

    def test_enter_keeps_configured_password(self):
        output = self.run_password_setup([''], 'existing-test-password', existing_password='existing-test-password')
        self.assertIn('A password is already configured', output)

    def test_unknown_existing_password_can_be_replaced(self):
        self.run_password_setup(['replacement-test-password'], 'replacement-test-password', existing_password='unknown-old-password')

    def test_empty_and_placeholder_passwords_are_rejected(self):
        output = self.run_password_setup(
            ['', '   ', 'your_password', 'your_secure_pass', 'YourSecurePassword', 'chosen-test-password'],
            'chosen-test-password',
        )
        self.assertEqual(output.count('[ERROR]'), 5)

    def test_shell_metacharacters_are_preserved_as_data(self):
        password = 'test-%PATH%-^&|!<>"-password'
        self.run_password_setup([password], password)

    def test_setup_runs_before_stopping_existing_server(self):
        source = (Path(__file__).resolve().parents[1] / 'start_dual_overlay.bat').read_text(encoding='utf-8')
        self.assertLess(source.index('call :configure_control_password'), source.index('echo [CLEANUP]'))
        self.assertIn('setlocal EnableExtensions DisableDelayedExpansion', source)


if __name__ == '__main__':
    unittest.main()
