"""Named source-owned workspaces remain local, literal and safely reconciled."""

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yap import build, catalog, content, files, perspectives, portfolio, workspace_links as links


class LocationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap locations ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.folder = self.root / 'pfo/act/area/task'
        self.folder.mkdir(parents=True)
        self.source = self.folder / 'task.md'
        self.external = self.root / 'external'
        self.external.mkdir()
        (self.external / 'secret.md').write_text('Private external material')
        self.configure({})

    def configure(self, values):
        self.source.write_text('---\nkind: activity\nkey: task\ntitle: Task\nwsp: '
                               + json.dumps(values, ensure_ascii=False) + '\n---\n')

    def sync(self):
        plan, messages = files.link_plan(self.root)
        files.sync_links(plan)
        return messages

    def test_free_names_and_shared_targets_are_literal_and_not_public_metadata(self):
        target = self.root / 'external_*literal*_folder [draft]'
        target.mkdir()
        self.configure({'code': target.name, 'proposal-2': str(target), 'shared_material': target.name})
        self.assertEqual(self.sync(), [])
        for label in ('code', 'proposal-2', 'shared_material'):
            self.assertEqual((self.folder / 'wsp' / label).resolve(), target)
        entry = catalog.discover(self.root)['task']
        self.assertEqual(entry['workspace']['code'], target.name)
        self.assertNotIn('wsp', entry['document']['meta'])
        self.assertNotIn(target.name, json.dumps(entry['document']))
        self.assertNotIn('wsp', content.read(self.source)['meta'])
        self.assertEqual(set(catalog.discover(self.root)), {'task'})

    def test_relative_paths_use_instance_root_and_home_paths_expand_explicitly(self):
        self.configure({'code': 'external'})
        self.sync()
        self.assertEqual((self.folder / 'wsp/code').resolve(), self.external)
        self.assertEqual(links.target(self.root, '~/example-workspace'), Path.home() / 'example-workspace')
        self.assertEqual(links.target(self.root, '../neighbor'), self.root.parent / 'neighbor')

    def test_activities_and_areas_do_not_inherit_and_modules_do_not_relocate_links(self):
        area = self.folder.parent
        (area / 'area.md').write_text('---\nkind: area\nkey: area\ntitle: Area\nwsp: {shared: external}\n---\n')
        self.sync()
        self.assertEqual((area / 'wsp/shared').resolve(), self.external)
        self.assertFalse((self.folder / 'wsp').exists())
        self.configure({'code': 'external'})
        self.sync()
        child = self.folder / 'mod/group/child'
        child.mkdir(parents=True)
        (child / 'child.md').write_text('---\nkind: activity\nkey: child\ntitle: Child\n---\n')
        self.sync()
        self.assertEqual((self.folder / 'wsp/code').resolve(), self.external)
        self.assertFalse((self.folder / 'code').exists())
        self.assertFalse((child / 'wsp').exists())

    def test_source_move_retains_binding_without_inferring_relationships(self):
        self.configure({'code': 'external'})
        self.sync()
        moved = self.root / 'pfo/act/moved'
        self.folder.rename(moved)
        (moved / 'task.md').rename(moved / 'moved.md')
        self.assertEqual(self.sync(), [])
        self.assertEqual((moved / 'wsp/code').resolve(), self.external)
        self.assertEqual(set(catalog.discover(self.root)), {'task'})

    def test_missing_targets_warn_but_existing_regular_files_fail_before_links_change(self):
        self.configure({'offline': 'missing-mount'})
        self.assertEqual(len(self.sync()), 1)
        offline = self.folder / 'wsp/offline'
        self.assertTrue(offline.is_symlink())
        self.assertFalse(offline.exists())
        (self.root / 'a-file').write_text('Preserve')
        self.configure({'new': 'external', 'file': 'a-file'})
        with self.assertRaisesRegex(ValueError, 'not a directory'):
            self.sync()
        self.assertFalse((self.folder / 'wsp/new').exists())
        self.assertTrue(offline.is_symlink())

    def test_unknown_shortcuts_and_real_content_are_preserved_when_map_changes(self):
        self.configure({'code': 'external'})
        self.sync()
        workspace = self.folder / 'wsp'
        (workspace / 'manual').symlink_to(self.root / 'missing')
        (workspace / 'notes.txt').write_text('Keep real notes')
        self.configure({})
        messages = self.sync()
        self.assertEqual(len(messages), 2)
        self.assertTrue((workspace / 'code').is_symlink())
        self.assertTrue((workspace / 'manual').is_symlink())
        self.assertEqual((workspace / 'notes.txt').read_text(), 'Keep real notes')
        self.assertEqual((self.external / 'secret.md').read_text(), 'Private external material')

    def test_all_collisions_are_checked_before_any_navigation_mutation(self):
        workspace = self.folder / 'wsp'
        workspace.mkdir()
        (workspace / 'zbox').write_text('Keep real content')
        self.configure({'code': 'external', 'zbox': 'external'})
        with self.assertRaisesRegex(ValueError, 'not a symlink'):
            self.sync()
        self.assertFalse((workspace / 'code').is_symlink())
        self.assertEqual((workspace / 'zbox').read_text(), 'Keep real content')

    def test_redirected_workspace_and_configuration_paths_are_rejected(self):
        self.configure({'code': 'external'})
        workspace = self.folder / 'wsp'
        workspace.symlink_to(self.external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks are not allowed'):
            self.sync()
        self.assertFalse((self.external / 'code').exists())
        workspace.unlink()
        workspace.write_text('Keep workspace file')
        with self.assertRaisesRegex(ValueError, 'workspace directory'):
            self.sync()
        self.assertEqual(workspace.read_text(), 'Keep workspace file')
        workspace.unlink()
        (self.root / '.yap').mkdir()
        (self.root / '.yap/cfg').symlink_to(self.external)
        with self.assertRaisesRegex(ValueError, 'symlinks are not allowed'):
            self.sync()

    def test_lexical_and_resolved_navigation_cycles_are_rejected(self):
        alias = self.root / 'external-alias'
        alias.symlink_to(self.folder, target_is_directory=True)
        for value in (str(self.root), str(self.folder), str(self.folder / 'wsp'), str(alias)):
            with self.subTest(value=value):
                self.configure({'cycle': value})
                with self.assertRaisesRegex(ValueError, 'cycle'):
                    self.sync()
        self.assertFalse((self.folder / 'wsp').exists())

    def test_absent_self_and_descendant_targets_are_rejected_before_link_creation(self):
        path = self.folder / 'wsp/self'
        for destination in (path, path / 'nested'):
            with self.subTest(destination=destination):
                self.configure({'self': str(destination)})
                with self.assertRaisesRegex(ValueError, 'cycle'):
                    self.sync()
                self.assertFalse((self.folder / 'wsp').exists())

    def test_shared_link_planner_rejects_filesystem_spelling_collisions(self):
        workspace = self.folder / 'wsp'
        workspace.mkdir()
        (workspace / 'Code').symlink_to(self.external)
        with self.assertRaisesRegex(ValueError, 'case-insensitive navigation collision'):
            links.link_change(workspace / 'code', self.external)
        self.assertEqual(os.readlink(workspace / 'Code'), str(self.external))

    def test_stale_second_link_prevents_first_link_mutation(self):
        self.configure({'first': 'external', 'second': 'external'})
        proposal, _ = files.link_plan(self.root)
        workspace = self.folder / 'wsp'
        workspace.mkdir()
        (workspace / 'second').symlink_to(self.root / 'elsewhere')
        with self.assertRaisesRegex(ValueError, 'changed since planning'):
            files.sync_links(proposal)
        self.assertFalse((workspace / 'first').is_symlink())
        self.assertEqual(os.readlink(workspace / 'second'), str(self.root / 'elsewhere'))

    def test_legacy_json_and_root_navigation_require_explicit_migration(self):
        config = self.root / '.yap/cfg/machine.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'links': {'task': {'repo': 'external'}}}))
        with self.assertRaisesRegex(ValueError, 'workspace migrate'):
            self.sync()
        self.assertFalse((self.folder / 'wsp').exists())
        config.write_text('{}')
        (self.folder / 'repo').symlink_to(self.external)
        with self.assertRaisesRegex(ValueError, 'workspace migrate'):
            self.sync()
        self.assertTrue((self.folder / 'repo').is_symlink())

    def test_workspace_contents_never_enter_source_scanning_or_resource_publication(self):
        self.configure({'code': 'external'})
        self.sync()
        before_files = list(files.source_files(self.root / 'pfo'))
        before_shape = files.source_shape(self.root / 'pfo')
        (self.external / 'secret.md').write_text('Changed private work')
        (self.external / 'new.md').write_text('Not a source')
        self.assertEqual(list(files.source_files(self.root / 'pfo')), before_files)
        self.assertEqual(files.source_shape(self.root / 'pfo'), before_shape)
        resource = self.folder / 'res/public.txt'
        resource.parent.mkdir()
        resource.write_text('Public material')
        hidden = resource.parent / 'wsp'
        hidden.mkdir()
        (hidden / 'secret.txt').write_text('Private material')
        model = {'nodes': [{'path': str(self.source.relative_to(self.root)), 'resource_root': 'task'}]}
        self.assertEqual(set(files.resource_plan(self.root, model)), {'res/task/public.txt'})
        with self.assertRaisesRegex(ValueError, 'local navigation only'):
            content.local_target('wsp/code/secret.md', self.source, self.root)

    def test_reserved_legacy_names_remain_excluded_from_capture_and_publication(self):
        entry = catalog.discover(self.root)['task']
        for label in files.LOCAL_NAMES:
            with self.subTest(label=label):
                self.assertEqual(perspectives.capture(self.root, label).stem, label + '-entry')
                with self.assertRaises(ValueError):
                    portfolio.publication({'publication': {'t': 'MetaMap', 'c': {'task': {
                        't': 'MetaMap', 'c': {'resource-root': {'t': 'MetaString', 'c': label + '/private'}}}}}},
                        {'task': entry})

    def test_links_command_ignores_unrelated_broken_report_controls(self):
        (self.root / 'pfo/act/act.md').write_text('---\ntitle: Activity\nmembers:\n  missing: [task]\n---\n')
        with self.assertRaisesRegex(ValueError, 'unknown entry'):
            portfolio.load(self.root)
        self.configure({'code': 'external'})
        previous = Path.cwd()
        try:
            with patch.object(build, 'ROOT', self.root), patch.object(content, 'load') as loader:
                with redirect_stdout(StringIO()):
                    build.main('links')
                loader.assert_not_called()
        finally:
            os.chdir(previous)
        self.assertEqual((self.folder / 'wsp/code').resolve(), self.external)


class WorkspaceYamlTests(unittest.TestCase):
    def document(self, yaml):
        return ('---\nkind: activity\nkey: example\ntitle: Example\n' + yaml + '\n---\nBody\n').encode()

    def test_invalid_map_shapes_and_nontext_values_are_rejected(self):
        for value in ('null', '[]', 'a-path', '{code: 3}', '{code: true}', '{code: null}',
                      '{code: []}', '{code: {nested: path}}', '{3: path}'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                links.bindings(self.document('wsp: ' + value), 'example.md')
        self.assertEqual(links.bindings(self.document('wsp: {code: "3"}'), 'example.md'), {'code': '3'})

    def test_duplicate_case_colliding_and_unsafe_names_are_rejected(self):
        for yaml in ('wsp: {code: one, code: two}', 'wsp: {Code: one, code: two}',
                     'wsp: {}\nwsp: {}', 'wsp: {../escape: path}', 'wsp: {"a/b": path}',
                     'wsp: {".hidden": path}', 'wsp: {"a b": path}', 'wsp: {"a:b": path}'):
            with self.subTest(yaml=yaml), self.assertRaises(ValueError):
                links.bindings(self.document(yaml), 'example.md')

    def test_invalid_paths_do_not_become_schemes_environment_or_user_expansion(self):
        for value in ('', ' ', ' padded ', '~someone/path', 'https://example.org', 'file:///tmp/path',
                      '$WORK/path', 'a\nb', 'a\x00b', 'a\\b'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                links.bindings(self.document('wsp: ' + json.dumps({'code': value})), 'example.md')

    def test_workspace_metadata_on_unsupported_document_kinds_is_rejected(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap invalid workspace ')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative, kind in [('pfo/act/act.md', 'activity'), ('pfo/asp/goals.md', ''),
                               ('pfo/asp/obj/goal/goal.md', 'activity'),
                               ('pfo/nts/note.md', 'note'), ('pfo/nts/other/other.md', 'area')]:
            source = root / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('---\ntitle: Example\n' + (f'kind: {kind}\n' if kind else '')
                              + 'wsp: {private: /private-workspace}\n---\n')
            with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, 'only in an activity or area'):
                content.read(source)

    def test_workspace_in_later_pandoc_yaml_block_requires_initial_header_placement(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap misplaced workspace ')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        source = root / 'pfo/act/task/task.md'
        source.parent.mkdir(parents=True)
        source.write_text('---\nkind: activity\nkey: task\ntitle: Task\n---\n\nBody.\n\n'
                          '---\nwsp: {code: /private-workspace-marker}\n---\n')
        with self.assertRaisesRegex(ValueError, 'initial YAML'):
            content.read(source)
