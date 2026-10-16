"""Both public entry routes share argument handling and application results."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]


class EntryPointTests(unittest.TestCase):
    def run_routes(self, *arguments):
        environment = dict(os.environ)
        environment.pop('PYTHONPATH', None)
        direct = subprocess.run(
            [sys.executable, '-B', str(ROOT / 'dev/src/main.py'), *arguments],
            cwd=ROOT, env=environment, capture_output=True, text=True)
        environment['PYTHONPATH'] = str(ROOT / 'dev/src')
        package = subprocess.run(
            [sys.executable, '-B', '-m', 'yap', *arguments],
            cwd=ROOT, env=environment, capture_output=True, text=True)
        return direct, package

    def test_help_and_invalid_arguments_have_equivalent_behavior(self):
        for arguments, status in [(('--help',), 0), (('unknown-command',), 2)]:
            with self.subTest(arguments=arguments):
                direct, package = self.run_routes(*arguments)
                self.assertEqual((direct.returncode, package.returncode), (status, status))
                for result in (direct, package):
                    output = result.stdout + result.stderr
                    self.assertIn('demo-date', output)
                    self.assertIn('usage:', output)
                if status:
                    self.assertIn('invalid choice', direct.stderr)
                    self.assertIn('invalid choice', package.stderr)
