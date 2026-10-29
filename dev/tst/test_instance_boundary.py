"""A selected portfolio owns content and branding, never application resources."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from yap import documents, home, instance, navigation
from yap.resources import APPLICATION


@contextmanager
def selected(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class InstanceBoundaryTests(unittest.TestCase):
    def test_manifest_schema_requires_the_integer_version_without_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'yap.json'
            for schema in (True, False, 1.0, '1', None, [], {}, 2):
                with self.subTest(schema=schema):
                    path.write_text(json.dumps({'schema': schema, 'slug': 'portfolio'}))
                    before = path.read_bytes()
                    with self.assertRaisesRegex(ValueError, 'schema 1'):
                        instance.manifest(root)
                    self.assertEqual(path.read_bytes(), before)
            value = {'schema': 1, 'slug': 'portfolio'}
            path.write_text(json.dumps(value))
            before = path.read_bytes()
            self.assertEqual(instance.manifest(root), value)
            self.assertEqual(path.read_bytes(), before)

    def test_external_empty_instance_checks_without_embedded_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name, text in {
                'pfo/act/act.md': '---\ntitle: Activities\n---\n',
                'pfo/asp/goals.md': '---\ntitle: Goals\n---\n',
            }.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            environment = dict(os.environ, PYTHONPATH=str(APPLICATION / 'dev/src'))
            result = subprocess.run([sys.executable, '-B', '-m', 'yap', '--instance', str(root), 'check'],
                                    cwd=APPLICATION, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Checked: 0', result.stdout)
            self.assertFalse((root / '.yap/app').exists())
            self.assertFalse((root / '.yap/utl').exists())

    def test_homepage_branding_and_historical_destinations_are_instance_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'assets').mkdir()
            (root / 'assets/logo.svg').write_text('<svg/>')
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'my-portfolio',
                'publication_prefix': 'historic-', 'branding': {'title': 'My portfolio.',
                'logo': 'assets/logo.svg', 'footer': 'Maintained locally'}}))
            with selected(root):
                home.render(root / 'output')
                self.assertTrue((root / 'output/my-portfolio.html').is_file())
                self.assertFalse((root / 'output/yap.html').exists())
                self.assertEqual((root / 'output/assets/logo.svg').read_text(), '<svg/>')
                self.assertIn('My portfolio.', navigation.head('board'))
                self.assertIn('../../my-portfolio.html', navigation.render('board'))
                self.assertTrue(documents.pdf_target('act-example/qualified').startswith('historic-'))

    def test_branding_rejects_paths_outside_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                'branding': {'logo': '../logo.svg'}}))
            with selected(root), self.assertRaisesRegex(ValueError, 'relative instance paths'):
                instance.manifest()

    def test_open_builds_selected_instance_then_opens_its_homepage(self):
        from unittest.mock import patch
        from yap import cli
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'portfolio'}))
            previous = Path.cwd()
            try:
                with patch('sys.argv', ['yap', '--instance', str(root), 'open']), \
                     patch.object(cli, 'main') as build, \
                     patch.object(cli.webbrowser, 'open', return_value=True) as browser:
                    self.assertEqual(cli.cli(), 0)
                    build.assert_called_once_with('all', instance=root)
                    browser.assert_called_once_with((root / 'portfolio.html').as_uri())
            finally:
                os.chdir(previous)

    def test_pin_rejects_different_or_dirty_application_before_opening(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from yap import cli
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'portfolio',
                'application': {'revision': 'a' * 40}}))
            for actual, dirty, message in [('b' * 40, '', 'differs'), ('a' * 40, ' M src/code.py', 'changes')]:
                responses = [SimpleNamespace(returncode=0, stdout=str(APPLICATION)),
                             SimpleNamespace(returncode=0, stdout=actual),
                             SimpleNamespace(returncode=0, stdout=dirty)]
                with patch('subprocess.run', side_effect=responses), self.assertRaisesRegex(ValueError, message):
                    instance.verify_application({'application': {'revision': 'a' * 40}})
