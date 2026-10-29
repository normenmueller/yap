"""Public setup commands preserve capture and honor preview/apply boundaries."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yap import cli, repo_templates


class WorkspaceCliTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(os.chdir, Path.cwd())
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'portfolio'
        self.root.mkdir()

    def command(self, *arguments):
        output, errors = io.StringIO(), io.StringIO()
        with patch('sys.argv', ['yap', '--instance', str(self.root), *map(str, arguments)]):
            with redirect_stdout(output), redirect_stderr(errors):
                status = cli.cli()
        return status, output.getvalue(), errors.getvalue()

    def inputs(self, profile='general'):
        inputs = repo_templates.defaults()
        inputs.update(title='Example', languages=['de', 'en'], primary_language='en',
                      purpose={'de': 'Ein Beispiel', 'en': 'An example'}, maintainer={})
        if profile == 'general':
            inputs.pop('db_metadata', None)
        else:
            inputs['db_confirmed'] = False
            inputs['db_metadata']['contacts'] = ['maintainer@example.org']
        path = self.base / 'inputs.json'
        path.write_text(json.dumps(inputs))
        return path

    def test_preview_then_apply_bilingual_template(self):
        target = self.base / 'project'
        inputs = self.inputs()
        arguments = ('workspace', 'create', target, '--template', 'general', '--inputs', inputs, '--lang', 'en')
        status, output, errors = self.command(*arguments)
        self.assertEqual(status, 0, errors)
        self.assertIn('README.de.md', output)
        self.assertIn('--apply', output)
        self.assertFalse(target.exists())
        status, output, errors = self.command(*arguments, '--apply')
        self.assertEqual(status, 0, errors + output)
        self.assertIn('An example', (target / 'README.md').read_text())
        self.assertIn('Ein Beispiel', (target / 'README.de.md').read_text())
        self.assertFalse((target / '.git').exists())
        self.assertFalse((target / 'LICENSE').exists())
        original = (target / 'README.md').read_bytes()
        self.assertEqual(self.command(*arguments, '--apply')[0], 1)
        self.assertEqual((target / 'README.md').read_bytes(), original)
        self.assertEqual(self.command(*arguments, '--resume', '--apply')[0], 0)

    def test_defaults_are_suggestions_and_db_requires_confirmation(self):
        status, output, errors = self.command('workspace', 'defaults', '--template', 'db-gitlab')
        self.assertEqual(status, 0, errors)
        self.assertIs(json.loads(output)['db_confirmed'], False)
        target = self.base / 'db-project'
        inputs = self.inputs('db-gitlab')
        arguments = ('workspace', 'create', target, '--template', 'db-gitlab', '--inputs', inputs, '--apply')
        self.assertEqual(self.command(*arguments)[0], 1)
        self.assertFalse(target.exists())
        values = json.loads(inputs.read_text())
        values['db_confirmed'] = True
        inputs.write_text(json.dumps(values))
        status, output, errors = self.command(*arguments)
        self.assertEqual(status, 0, errors + output)
        self.assertTrue((target / 'LICENSE').is_file())
        self.assertIn('LicenseRef-DBISL', (target / 'scm-info.yaml').read_text())

    def test_capture_survives_failed_setup_without_recapture(self):
        status, output, errors = self.command('new', 'An independent activity')
        self.assertEqual(status, 0, errors)
        captured = self.root / output.strip()
        original = captured.read_bytes()
        target = self.base / 'occupied'
        target.mkdir()
        (target / 'notes.md').write_text('Preserve this.')
        status, _, _ = self.command('workspace', 'create', target, '--apply')
        self.assertEqual(status, 1)
        self.assertEqual(captured.read_bytes(), original)
        self.assertEqual((target / 'notes.md').read_text(), 'Preserve this.')
        self.assertEqual(len(list((self.root / 'pfo/act').glob('*/*.md'))), 1)

    def test_attach_only_changes_selected_source_binding(self):
        status, output, errors = self.command('new', 'A linked activity')
        self.assertEqual(status, 0, errors)
        target = self.base / 'existing'
        target.mkdir()
        (target / 'notes.md').write_text('Existing notes.')
        args = ('workspace', 'attach', target, '--bind', 'a-linked-activity', '--name', 'shared-material')
        self.assertEqual(self.command(*args)[0], 0)
        self.assertFalse((self.root / '.yap/cfg/machine.json').exists())
        status, output, errors = self.command(*args, '--apply')
        self.assertEqual(status, 0, errors + output)
        self.assertEqual(list(p.name for p in target.iterdir()), ['notes.md'])
        source = self.root / 'pfo/act/a-linked-activity'
        self.assertEqual((source / 'wsp/shared-material').resolve(), target)
        self.assertFalse((source / 'repo').exists())

    def test_migration_command_previews_then_applies_legacy_binding(self):
        status, output, errors = self.command('new', 'A migrated activity')
        self.assertEqual(status, 0, errors)
        source = self.root / output.strip()
        target = self.base / 'existing'
        target.mkdir()
        config = self.root / '.yap/cfg/machine.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'links': {'a-migrated-activity': {'repo': str(target)}}}))
        (source.parent / 'repo').symlink_to(target)
        before = source.read_bytes(), config.read_bytes()
        status, output, errors = self.command('workspace', 'migrate')
        self.assertEqual(status, 0, errors)
        self.assertIn('--apply', output)
        self.assertEqual((source.read_bytes(), config.read_bytes()), before)
        status, output, errors = self.command('workspace', 'migrate', '--apply')
        self.assertEqual(status, 0, errors + output)
        self.assertEqual((source.parent / 'wsp/repo').resolve(), target)
        self.assertFalse((source.parent / 'repo').is_symlink())
        self.assertNotIn('links', json.loads(config.read_text()))
        self.assertEqual(self.command('workspace', 'migrate', '--apply')[0], 0)

    def test_binding_requires_explicit_name_and_activity_key(self):
        status, _, errors = self.command('new', 'An activity')
        self.assertEqual(status, 0, errors)
        target = self.base / 'new-project'
        for arguments in (('--bind', 'an-activity'), ('--name', 'code')):
            with self.subTest(arguments=arguments):
                status, _, errors = self.command('workspace', 'create', target, *arguments, '--apply')
                self.assertEqual(status, 1, errors)
                self.assertFalse(target.exists())
