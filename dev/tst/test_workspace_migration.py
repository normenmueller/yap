"""Legacy workspace migration is explicit, source-preserving and resumable."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yap import workspace_links as links, workspace_migration as migration


class WorkspaceMigrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap migration ')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / 'portfolio'
        self.folder = self.root / 'pfo/act/task'
        self.folder.mkdir(parents=True)
        self.source = self.folder / 'task.md'
        self.original = b'---\n# Keep header comment\nkind: activity\nkey: task\ntitle: Task # inline\nlast-update: 2026-01-01\n---\n\n## Notes\nKeep authored body.\n'
        self.source.write_bytes(self.original)
        self.target = self.base / 'work'
        self.target.mkdir()
        (self.target / 'private.md').write_text('Preserve workspace contents')
        self.config = self.root / '.yap/cfg/machine.json'
        self.configure({'task': {'repo': '../work'}})

    def configure(self, bindings, **other):
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps(dict(other, links=bindings), ensure_ascii=False))

    def test_preview_is_read_only_and_apply_migrates_both_navigation_layouts(self):
        self.configure({'task': {'repo': '../work', 'shlf': str(self.target)}}, keep={'mode': 'local'})
        (self.folder / 'repo').symlink_to(self.target)
        workspace = self.folder / 'wsp'
        workspace.mkdir()
        (workspace / 'repo').symlink_to(self.target)
        (workspace / 'shlf').symlink_to(self.target)
        before_config = self.config.read_bytes()
        proposal = migration.plan(self.root)
        self.assertIn('YAML: pfo/act/task/task.md', proposal.preview())
        self.assertIn('Remove verified legacy shortcut', proposal.preview())
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.config.read_bytes(), before_config)
        self.assertTrue((self.folder / 'repo').is_symlink())
        migration.apply(proposal)
        self.assertEqual(links.bindings(self.source.read_bytes(), self.source), {'repo': '../work', 'shlf': str(self.target)})
        self.assertEqual(json.loads(self.config.read_text()), {'keep': {'mode': 'local'}})
        self.assertFalse((self.folder / 'repo').is_symlink())
        self.assertEqual((workspace / 'repo').resolve(), self.target)
        self.assertEqual((workspace / 'shlf').resolve(), self.target)
        self.assertEqual((self.target / 'private.md').read_text(), 'Preserve workspace contents')
        self.assertIn('# Keep header comment\n', self.source.read_text())
        self.assertIn('title: Task # inline\nlast-update: 2026-01-01\n', self.source.read_text())
        self.assertTrue(self.source.read_bytes().endswith(b'---\n\n## Notes\nKeep authored body.\n'))
        second = migration.plan(self.root)
        self.assertIn('No changes.', second.preview())
        previous = self.source.read_bytes(), self.config.read_bytes()
        migration.apply(second)
        self.assertEqual((self.source.read_bytes(), self.config.read_bytes()), previous)

    def test_existing_equal_yaml_is_kept_byte_for_byte(self):
        authored = self.original.replace(b'last-update:', b'wsp: {repo: "../work"} # keep map style\nlast-update:')
        self.source.write_bytes(authored)
        migration.apply(migration.plan(self.root))
        self.assertEqual(self.source.read_bytes(), authored)
        self.assertNotIn('links', json.loads(self.config.read_text()))

    def test_unknown_shortcuts_and_real_legacy_named_files_are_preserved(self):
        (self.folder / 'repo').write_text('Ordinary source material')
        workspace = self.folder / 'wsp'
        workspace.mkdir()
        (workspace / 'manual').symlink_to(self.base / 'missing')
        (workspace / 'notes.txt').write_text('Keep local notes')
        proposal = migration.plan(self.root)
        self.assertEqual(len(proposal.messages), 1)
        migration.apply(proposal)
        self.assertEqual((self.folder / 'repo').read_text(), 'Ordinary source material')
        self.assertTrue((workspace / 'manual').is_symlink())
        self.assertEqual((workspace / 'notes.txt').read_text(), 'Keep local notes')

    def test_conflicts_stop_before_any_source_or_configuration_changes(self):
        alternatives = [
            ('root', lambda: (self.folder / 'repo').symlink_to(self.base / 'elsewhere')),
            ('workspace', lambda: self.make_workspace_link('repo', self.base / 'elsewhere')),
            ('real-content', lambda: self.make_workspace_file('repo')),
            ('yaml', lambda: self.source.write_bytes(self.original.replace(b'last-update:', b'wsp: {repo: ../elsewhere}\nlast-update:'))),
            ('case', lambda: self.source.write_bytes(self.original.replace(b'last-update:', b'wsp: {Repo: ../work}\nlast-update:'))),
        ]
        for label, mutate in alternatives:
            with self.subTest(label=label):
                mutate()
                before_source, before_config = self.source.read_bytes(), self.config.read_bytes()
                with self.assertRaises(ValueError):
                    migration.plan(self.root)
                self.assertEqual(self.source.read_bytes(), before_source)
                self.assertEqual(self.config.read_bytes(), before_config)
                self.source.write_bytes(self.original)
                root_link = self.folder / 'repo'
                if root_link.is_symlink():
                    root_link.unlink()
                workspace = self.folder / 'wsp'
                if workspace.exists():
                    for path in workspace.iterdir():
                        path.unlink()
                    workspace.rmdir()

    def make_workspace_link(self, label, target):
        workspace = self.folder / 'wsp'
        workspace.mkdir(exist_ok=True)
        (workspace / label).symlink_to(target)

    def make_workspace_file(self, label):
        workspace = self.folder / 'wsp'
        workspace.mkdir(exist_ok=True)
        (workspace / label).write_text('Keep real content')

    def test_unknown_entries_invalid_roles_and_invalid_values_are_rejected(self):
        for bindings in ({'unknown': {'repo': '../work'}}, {'task': {'custom': '../work'}},
                         {'task': []}, {'task': {'repo': None}}, {'task': {'repo': 5}}):
            with self.subTest(bindings=bindings):
                self.configure(bindings)
                before = self.config.read_bytes()
                with self.assertRaises(ValueError):
                    migration.plan(self.root)
                self.assertEqual(self.config.read_bytes(), before)
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_missing_target_is_a_warning_and_is_not_created(self):
        self.configure({'task': {'repo': '../missing-mount'}})
        proposal = migration.plan(self.root)
        self.assertEqual(len(proposal.messages), 1)
        migration.apply(proposal)
        self.assertTrue((self.folder / 'wsp/repo').is_symlink())
        self.assertFalse((self.folder / 'wsp/repo').exists())
        self.assertFalse((self.base / 'missing-mount').exists())

    def test_two_entries_targeting_each_others_future_links_fail_before_source_writes(self):
        other = self.root / 'pfo/act/other/other.md'
        other.parent.mkdir()
        other.write_text('---\nkind: activity\nkey: other\ntitle: Other\n---\n')
        self.configure({'task': {'repo': str(other.parent / 'wsp/repo')},
                        'other': {'repo': str(self.folder / 'wsp/repo')}})
        before = self.source.read_bytes(), other.read_bytes(), self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, 'cycle'):
            migration.plan(self.root)
        self.assertEqual((self.source.read_bytes(), other.read_bytes(), self.config.read_bytes()), before)
        self.assertFalse((self.folder / 'wsp').exists())
        self.assertFalse((other.parent / 'wsp').exists())

    def test_stale_config_source_and_link_prevent_all_writes(self):
        mutations = [
            ('config', lambda: self.configure({'task': {'repo': '../work'}}, concurrent=True)),
            ('source', lambda: self.source.write_bytes(self.original + b'Concurrent body\n')),
            ('link', lambda: self.make_workspace_link('repo', self.base / 'elsewhere')),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                proposal = migration.plan(self.root)
                mutate()
                before_source, before_config = self.source.read_bytes(), self.config.read_bytes()
                with self.assertRaises(ValueError):
                    migration.apply(proposal)
                self.assertEqual(self.source.read_bytes(), before_source)
                self.assertEqual(self.config.read_bytes(), before_config)
                self.source.write_bytes(self.original)
                self.configure({'task': {'repo': '../work'}})
                workspace = self.folder / 'wsp'
                if workspace.exists():
                    for path in workspace.iterdir():
                        path.unlink()
                    workspace.rmdir()

    def test_changed_second_source_stops_before_first_source_is_written(self):
        other = self.root / 'pfo/act/other/other.md'
        other.parent.mkdir()
        other.write_text('---\nkind: activity\nkey: other\ntitle: Other\n---\n')
        self.configure({'task': {'repo': '../work'}, 'other': {'shlf': '../work'}})
        proposal = migration.plan(self.root)
        other.write_text(other.read_text() + '\nConcurrent work\n')
        with self.assertRaisesRegex(ValueError, 'changed since planning'):
            migration.apply(proposal)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertIn('links', json.loads(self.config.read_text()))

    def test_partial_navigation_failure_can_be_replanned_without_rewriting_sources(self):
        (self.folder / 'repo').symlink_to(self.target)
        proposal = migration.plan(self.root)
        with patch.object(links, 'sync', side_effect=OSError('simulated navigation failure')):
            with self.assertRaisesRegex(OSError, 'simulated'):
                migration.apply(proposal)
        migrated_source = self.source.read_bytes()
        self.assertEqual(links.bindings(migrated_source, self.source), {'repo': '../work'})
        self.assertIn('links', json.loads(self.config.read_text()))
        self.assertTrue((self.folder / 'repo').is_symlink())
        migration.apply(migration.plan(self.root))
        self.assertEqual(self.source.read_bytes(), migrated_source)
        self.assertNotIn('links', json.loads(self.config.read_text()))
        self.assertEqual((self.folder / 'wsp/repo').resolve(), self.target)
        self.assertFalse((self.folder / 'repo').is_symlink())

    def test_partial_source_failure_is_resumable_without_overwriting_equal_yaml(self):
        other = self.root / 'pfo/act/other/other.md'
        other.parent.mkdir()
        other.write_text('---\nkind: activity\nkey: other\ntitle: Other\n---\n')
        self.configure({'task': {'repo': '../work'}, 'other': {'shlf': '../work'}})
        proposal = migration.plan(self.root)
        second = proposal.sources[1].path
        original_write = links.write
        def write(path, before, after):
            if path == second:
                raise OSError('simulated second source failure')
            return original_write(path, before, after)
        with patch.object(links, 'write', side_effect=write):
            with self.assertRaisesRegex(OSError, 'second source failure'):
                migration.apply(proposal)
        first = proposal.sources[0].path
        first_after = first.read_bytes()
        self.assertNotEqual(first_after, proposal.sources[0].before)
        self.assertEqual(second.read_bytes(), proposal.sources[1].before)
        self.assertIn('links', json.loads(self.config.read_text()))
        migration.apply(migration.plan(self.root))
        self.assertEqual(first.read_bytes(), first_after)
        self.assertEqual((self.folder / 'wsp/repo').resolve(), self.target)
        self.assertEqual((other.parent / 'wsp/shlf').resolve(), self.target)
        self.assertNotIn('links', json.loads(self.config.read_text()))

    def test_config_write_failure_keeps_completed_navigation_resumable(self):
        (self.folder / 'repo').symlink_to(self.target)
        proposal = migration.plan(self.root)
        original_write = links.write
        def write(path, before, after):
            if path == self.config:
                raise OSError('simulated config failure')
            return original_write(path, before, after)
        with patch.object(links, 'write', side_effect=write):
            with self.assertRaisesRegex(OSError, 'config failure'):
                migration.apply(proposal)
        self.assertFalse((self.folder / 'repo').is_symlink())
        self.assertEqual((self.folder / 'wsp/repo').resolve(), self.target)
        self.assertIn('links', json.loads(self.config.read_text()))
        migration.apply(migration.plan(self.root))
        self.assertNotIn('links', json.loads(self.config.read_text()))


class WorkspaceSourceEditTests(unittest.TestCase):
    def test_insertions_preserve_original_bytes_with_comments_crlf_bom_and_unicode(self):
        originals = [
            b'---\nkind: activity\nkey: task\ntitle: Task # keep\n---\n\nBody\n',
            b'---\nkind: activity\nkey: task\ntitle: Task\nwsp: {} # keep flow\nlast-update: 2026-01-01\n---\nBody\n',
            b'---\nkind: activity\nkey: task\ntitle: Task\nwsp:\n  code: ../work # keep path\n# Keep next comment\nlast-update: 2026-01-01\n---\nBody\n',
            '\ufeff---\r\nkind: activity\r\nkey: task\r\ntitle: Beispiel # bleibt\r\n---\r\n\r\nÜberblick\r\n'.encode(),
        ]
        for original in originals:
            with self.subTest(original=original):
                after = links.add_bindings(original, 'example.md', {'proposal': '../work ä_*literal*_[draft]'})
                before_map = links.bindings(original, 'example.md')
                self.assertEqual(links.bindings(after, 'example.md'), dict(before_map, proposal='../work ä_*literal*_[draft]'))
                self.assertEqual(after.split(b'---', 2)[-1], original.split(b'---', 2)[-1])
                if original.startswith(b'\xef\xbb\xbf'):
                    self.assertTrue(after.startswith(b'\xef\xbb\xbf'))
                    self.assertNotIn(b'\n', after.replace(b'\r\n', b''))
                for comment in (b'# keep', b'# keep flow', b'# keep path', b'# Keep next comment'):
                    if comment in original:
                        self.assertIn(comment, after)

    def test_source_edits_refuse_alias_rewrites_and_existing_bindings(self):
        aliased = b'---\nkind: activity\nkey: task\ntitle: Task\nshared: &shared {code: ../work}\nwsp: *shared\n---\nBody\n'
        with self.assertRaisesRegex(ValueError, 'aliased'):
            links.add_bindings(aliased, 'example.md', {'proposal': '../proposal'})
        with self.assertRaisesRegex(ValueError, 'already exists'):
            links.add_bindings(aliased, 'example.md', {'code': '../proposal'})

    def test_source_edits_reject_anchored_workspace_maps_referenced_by_later_fields(self):
        for workspace in (b'&shared {code: ../work}', b'&shared\n  code: ../work'):
            original = (b'---\nkind: activity\nkey: task\ntitle: Task\nwsp: ' + workspace
                        + b'\nother: *shared\n---\nBody\n')
            with self.subTest(workspace=workspace), self.assertRaisesRegex(ValueError, 'anchored'):
                links.add_bindings(original, 'example.md', {'proposal': '../proposal'})
