"""Optional private work locations survive moves and stay outside publication."""

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yap import build, catalog, content, files, perspectives, portfolio


class LocationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap locations ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.folder = self.root / 'pfo/act/area/task'
        self.folder.mkdir(parents=True)
        self.source = self.folder / 'task.md'
        self.source.write_text('---\nkind: activity\nkey: task\ntitle: Task\n---\n')
        self.config = self.root / '.yap/cfg/machine.json'
        self.config.parent.mkdir(parents=True)
        self.external = self.root / 'external'
        self.external.mkdir()
        (self.external / 'secret.md').write_text('Private external material')

    def configure(self, links):
        self.config.write_text(json.dumps({'links': links}))

    def sync(self):
        plan, messages = files.link_plan(self.root)
        files.sync_links(plan)
        return messages

    def test_roles_coexist_and_removal_is_independent(self):
        self.configure({'task': {role: 'external' for role in files.LINK_ROLES}})
        self.assertEqual(self.sync(), [])
        before_files = list(files.source_files(self.root / 'pfo'))
        before_shape = files.source_shape(self.root / 'pfo')
        for role in files.LINK_ROLES:
            self.assertEqual((self.folder / role).resolve(), self.external)
        self.assertEqual(set(catalog.discover(self.root)), {'task'})
        self.configure({'task': {'repo': 'external', 'zbox': 'external'}})
        self.sync()
        self.assertFalse((self.folder / 'shlf').is_symlink())
        self.assertTrue((self.folder / 'repo').is_symlink())
        self.assertTrue((self.folder / 'zbox').is_symlink())
        self.assertEqual(list(files.source_files(self.root / 'pfo')), before_files)
        self.assertEqual(files.source_shape(self.root / 'pfo'), before_shape)
        self.assertEqual((self.external / 'secret.md').read_text(), 'Private external material')

    def test_identity_binding_survives_move_and_supports_shared_target(self):
        self.configure({'task': {'repo': 'external'}})
        self.sync()
        moved = self.root / 'pfo/act/moved'
        self.folder.rename(moved)
        (moved / 'task.md').rename(moved / 'moved.md')
        other = self.root / 'pfo/act/other'
        other.mkdir()
        (other / 'other.md').write_text('---\nkind: activity\nkey: other\ntitle: Other\n---\n')
        self.configure({'task': {'repo': 'external'}, 'other': {'repo': str(self.external)}})
        self.assertEqual(self.sync(), [])
        self.assertEqual((moved / 'repo').resolve(), (other / 'repo').resolve())

    def test_area_links_are_explicit_and_do_not_inherit_to_direct_activities(self):
        area = self.folder.parent
        (area / 'area.md').write_text('---\nkind: area\nkey: area\ntitle: Area\n---\n')
        self.configure({'area': {'shlf': 'external'}})
        self.sync()
        self.assertEqual((area / 'shlf').resolve(), self.external)
        self.assertFalse((area / 'wsp').exists())
        self.assertFalse((self.folder / 'shlf').exists())
        self.configure({'area': {'shlf': 'external'}, 'task': {'repo': 'external'}})
        self.sync()
        self.assertEqual((self.folder / 'repo').resolve(), self.external)

    def test_module_lifecycle_moves_roles_without_inheritance(self):
        self.configure({'task': {role: 'external' for role in files.LINK_ROLES}})
        self.sync()
        module = self.folder / 'mod/group/child'
        module.mkdir(parents=True)
        source = module / 'child.md'
        source.write_text('---\nkind: activity\nkey: child\ntitle: Child\n---\n')
        before_files = list(files.source_files(self.root / 'pfo'))
        before_shape = files.source_shape(self.root / 'pfo')
        self.sync()
        for role in files.LINK_ROLES:
            self.assertEqual((self.folder / 'wsp' / role).resolve(), self.external)
            self.assertFalse((self.folder / role).is_symlink())
            self.assertFalse((module / role).exists())
        self.assertFalse((module / 'wsp').exists())
        self.assertEqual(list(files.source_files(self.root / 'pfo')), before_files)
        self.assertEqual(files.source_shape(self.root / 'pfo'), before_shape)
        self.configure({'task': {'repo': 'external'}, 'child': {'repo': 'external'}})
        self.sync()
        self.assertEqual((module / 'repo').resolve(), self.external)
        self.assertFalse((self.folder / 'wsp/shlf').exists())
        source.unlink()
        self.configure({'task': {'repo': 'external'}})
        self.sync()
        self.assertEqual((self.folder / 'repo').resolve(), self.external)
        self.assertFalse((self.folder / 'wsp').exists())

    def test_empty_mod_and_unbound_parent_do_not_create_workspaces(self):
        module = self.folder / 'mod'
        module.mkdir()
        self.configure({'task': {'repo': 'external'}})
        self.sync()
        self.assertTrue((self.folder / 'repo').is_symlink())
        self.assertFalse((self.folder / 'wsp').exists())
        child = module / 'child'
        child.mkdir()
        (child / 'child.md').write_text('---\nkind: activity\nkey: child\ntitle: Child\n---\n')
        self.configure({'child': {'repo': 'external'}})
        self.sync()
        self.assertFalse((self.folder / 'wsp').exists())
        self.assertFalse((self.folder / 'repo').exists())
        self.assertTrue((child / 'repo').is_symlink())

    def test_workspace_collisions_and_private_files_are_preserved(self):
        child = self.folder / 'mod/child'
        child.mkdir(parents=True)
        (child / 'child.md').write_text('---\nkind: activity\nkey: child\ntitle: Child\n---\n')
        self.configure({'task': {'repo': 'external'}})
        workspace = self.folder / 'wsp'
        workspace.symlink_to(self.external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink is not allowed'):
            self.sync()
        self.assertFalse((self.external / 'repo').exists())
        workspace.unlink()
        workspace.write_text('Keep this file')
        with self.assertRaisesRegex(ValueError, 'workspace directory'):
            self.sync()
        self.assertEqual(workspace.read_text(), 'Keep this file')
        workspace.unlink()
        workspace.mkdir()
        (workspace / 'repo').write_text('Keep real content')
        with self.assertRaisesRegex(ValueError, 'not a symlink'):
            self.sync()
        self.assertFalse((self.folder / 'repo').exists())
        self.configure({})
        self.sync()
        self.assertEqual((workspace / 'repo').read_text(), 'Keep real content')

    def test_invalid_settings_do_not_change_existing_links(self):
        self.configure({'task': {'repo': 'external'}})
        self.sync()
        stored = os.readlink(self.folder / 'repo')
        invalid = [
            {'work': {'task': 'external'}}, {'links': []}, [],
            {'links': {'missing': {'repo': 'external'}}},
            {'links': {'task': 'external'}},
            {'links': {'task': {'unknown': 'external'}}},
            *({'links': {'task': {'repo': value}}} for value in ('', ' ', None, 3, [], 'a\0b')),
        ]
        for settings in invalid:
            with self.subTest(settings=settings):
                self.config.write_text(json.dumps(settings))
                with self.assertRaises(ValueError):
                    self.sync()
                self.assertEqual(os.readlink(self.folder / 'repo'), stored)

    def test_collision_is_checked_before_any_role_changes(self):
        (self.folder / 'zbox').write_text('Keep real content')
        self.configure({'task': {'repo': 'external', 'zbox': 'external'}})
        with self.assertRaisesRegex(ValueError, 'not a symlink'):
            self.sync()
        self.assertFalse((self.folder / 'repo').is_symlink())
        self.assertEqual((self.folder / 'zbox').read_text(), 'Keep real content')
        self.configure({'task': {'repo': 'missing'}})
        self.assertEqual(len(self.sync()), 1)
        self.assertTrue((self.folder / 'repo').is_symlink())
        self.assertFalse((self.folder / 'repo').exists())
        self.assertEqual((self.folder / 'zbox').read_text(), 'Keep real content')

    def test_private_roles_are_not_authored_published_or_captured(self):
        entry = catalog.discover(self.root)['task']
        model = {'nodes': [{'path': str(self.source.relative_to(self.root)), 'resource_root': 'task'}]}
        resource = self.folder / 'res/public.txt'
        resource.parent.mkdir()
        resource.write_text('Public material')
        for role in files.LOCAL_NAMES:
            hidden = resource.parent / role
            hidden.mkdir()
            (hidden / 'secret.txt').write_text('Private material')
            with self.assertRaisesRegex(ValueError, 'local navigation only'):
                content.local_target(role + '/secret.txt', self.source, self.root)
            self.assertEqual(perspectives.capture(self.root, role).stem, role + '-entry')
            with self.assertRaises(ValueError):
                portfolio.publication({'publication': {'t': 'MetaMap', 'c': {'task': {
                    't': 'MetaMap', 'c': {'resource-root': {'t': 'MetaString', 'c': role + '/private'}}}}}},
                    {'task': entry})
        self.assertEqual(set(files.resource_plan(self.root, model)), {'res/task/public.txt'})
        for field in (*files.LOCAL_NAMES, 'file'):
            meta = dict(entry['document']['meta'], **{field: {'t': 'MetaString', 'c': '/private'}})
            with self.assertRaisesRegex(ValueError, 'machine.json'):
                content.entry_fields(meta, self.source, self.root)

    def test_links_command_ignores_unrelated_broken_report_controls(self):
        (self.root / 'pfo/act/act.md').write_text('---\ntitle: Activity\nmembers:\n  missing: [task]\n---\n')
        with self.assertRaisesRegex(ValueError, 'unknown entry'):
            portfolio.load(self.root)
        self.configure({'task': {'repo': 'external'}})
        previous = Path.cwd()
        try:
            with patch.object(build, 'ROOT', self.root), patch.object(content, 'load') as loader:
                with redirect_stdout(StringIO()):
                    build.main('links')
                loader.assert_not_called()
        finally:
            os.chdir(previous)
        self.assertEqual((self.folder / 'repo').resolve(), self.external)
