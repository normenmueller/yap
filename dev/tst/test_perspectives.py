"""Preservation and determinism at the filesystem/definition boundary."""

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from yap import perspectives as p, perspective_html, prototype


class PerspectiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap perspective ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'arbitrary instance'
        prototype.initialize(self.root)
        p.capture(self.root, 'Alpha')
        p.capture(self.root, 'Beta')
        self.view = self.root / 'pov/focus'
        self.view.mkdir()
        self.link('alpha', 'alpha')

    def link(self, relative, key, subpath=''):
        path = self.view / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        target = self.root / 'pfo/act' / key / subpath
        path.symlink_to(os.path.relpath(target, path.parent))
        return path

    def save(self, **kwargs):
        plan = p.plan(self.root, 'focus', 'save', **kwargs)
        p.apply(plan)
        return plan.definition

    def definition(self):
        return self.view / p.DEFINITION

    def write_definition(self, value):
        self.definition().write_text(p.encode(value))

    def test_title_only_capture_and_key_collisions(self):
        source = p.capture(self.root, 'Alpha')
        self.assertEqual(source.parent.name, 'alpha-2')
        self.assertNotIn('status:', source.read_text())
        self.assertNotIn('work:', source.read_text())
        self.assertEqual(p.capture(self.root, '你好').stem, 'entry')
        self.assertEqual(p.capture(self.root, 'work').stem, 'work-entry')
        before = source.read_bytes()
        with self.assertRaises(ValueError):
            p.capture(self.root, '\n')
        self.assertEqual(source.read_bytes(), before)

    def test_group_names_have_no_identity_and_entry_is_an_ordinary_name(self):
        (self.view / 'beta/_entry').mkdir(parents=True)
        resource = self.root / 'pfo/act/alpha/res/note.txt'
        resource.parent.mkdir()
        resource.write_text('Resource content')
        self.link('_entry', 'alpha')
        self.link('Documents/_entry', 'beta', 'beta.md')
        self.link('Resources/_entry', 'alpha', 'res/note.txt')
        saved = self.save()
        flat = p.flatten(saved['entries'])
        self.assertNotIn('target', flat['beta'])
        self.assertEqual(flat['beta/_entry']['entries'], [])
        self.assertEqual(flat['_entry']['target'], {'entry': 'alpha'})
        self.assertEqual(flat['Documents/_entry']['target'], {'entry': 'beta', 'path': 'beta.md'})
        self.assertEqual(flat['Resources/_entry']['target'], {'entry': 'alpha', 'path': 'res/note.txt'})
        self.assertNotIn('entries', flat['_entry'])
        before = {path: path.read_bytes() for path in (resource, self.root / 'pfo/act/beta/beta.md')}
        for name in ('_entry', 'Documents/_entry', 'Resources/_entry'):
            (self.view / name).unlink()
        (self.view / 'beta/_entry').rmdir()
        p.apply(p.plan(self.root, 'focus', 'restore', choose=True))
        self.assertEqual(self.save(), saved)
        self.assertTrue((self.view / 'beta/_entry').is_dir())
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        perspective_html.render(self.root)
        html = (self.root / 'yap.html').read_text()
        self.assertIn('<h3>beta</h3>', html)
        self.assertIn('<h3>_entry</h3>', html)
        self.assertIn('href="pfo/act/alpha/alpha.md">_entry</a>', html)
        self.assertIn('href="pfo/act/beta/beta.md">_entry</a>', html)
        self.assertIn('href="pfo/act/alpha/res/note.txt">_entry</a>', html)
        self.assertNotIn('class="source"', html)

    def test_shared_topic_notes_round_trip_without_capturing_siblings(self):
        topic = self.root / 'pfo/nts/topic'
        topic.mkdir(parents=True)
        for key in ('one', 'two'):
            source = topic / (key + '.md')
            source.write_text(f'---\nkind: note\nkey: {key}\ntitle: {key}\n---\n')
            (self.view / (key + '.md')).symlink_to(os.path.relpath(source, self.view))
        (topic / 'private.md').write_text('Private material')
        entries = p.catalog(self.root)
        for key in ('one', 'two'):
            self.assertEqual(p.target_path(entries, {'entry': key}), topic / (key + '.md'))
        saved = self.save()
        leaves = p.flatten(saved['entries'])
        self.assertEqual(leaves['two.md']['target'], {'entry': 'two'})
        for path in ('private.md', 'two.md', 'res/file.txt'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'own Markdown'):
                p.target_path(entries, {'entry': 'one', 'path': path})
        (self.view / 'two.md').unlink()
        p.apply(p.plan(self.root, 'focus', 'restore', choose=True))
        self.assertEqual((self.view / 'two.md').resolve(), topic / 'two.md')
        self.assertEqual(self.save(), saved)

    def test_finder_metadata_does_not_change_perspectives_or_block_restore(self):
        self.save()
        expected = self.definition().read_bytes()
        before = perspective_html.draft_state(self.root)
        for folder in (self.view, self.view.parent):
            (folder / '.DS_Store').write_bytes(b'Finder metadata')
        self.save()
        self.assertEqual(self.definition().read_bytes(), expected)
        self.assertEqual(perspective_html.draft_state(self.root), before)
        perspective_html.render(self.root)
        group = self.view / 'Temporary'
        group.mkdir()
        (group / '.DS_Store').write_bytes(b'Finder metadata')
        p.apply(p.plan(self.root, 'focus', 'restore', choose=True))
        self.assertFalse(group.exists())
        (self.view / '.DS_Store').unlink()
        (self.view / '.DS_Store').symlink_to(self.root / 'pfo/act/alpha/alpha.md')
        with self.assertRaisesRegex(ValueError, 'Unsafe or reserved name'):
            p.scan(self.root, 'focus', p.catalog(self.root))

    def test_byte_identical_save_restore_empty_groups_and_literal_metadata(self):
        (self.view / 'Empty').mkdir()
        self.link('Duplicate', 'alpha', 'alpha.md')
        saved = self.save()
        saved['presentation'] = {'format': 'list', 'literal': '**x** <script> 日本語'}
        saved['entries'].reverse()
        saved['entries'][0]['alias'] = '**Alias** <tag> & 日本語'
        self.write_definition(saved)
        self.save()
        expected = self.definition().read_bytes()
        before = self.definition().stat().st_mtime_ns
        self.save()
        self.assertEqual(self.definition().stat().st_mtime_ns, before)
        fresh = self.root.parent / 'moved checkout'
        shutil.copytree(self.root / 'pfo', fresh / 'pfo')
        destination = fresh / 'pov/focus'
        destination.mkdir(parents=True)
        (destination / p.DEFINITION).write_bytes(expected)
        p.apply(p.plan(fresh, 'focus', 'restore'))
        p.apply(p.plan(fresh, 'focus', 'save'))
        self.assertEqual((destination / p.DEFINITION).read_bytes(), expected)
        self.assertTrue((destination / 'Empty').is_dir())
        self.assertFalse(os.path.isabs(os.readlink(destination / 'alpha')))

    def test_enumeration_order_does_not_change_ids_or_bytes(self):
        self.link('Beta', 'beta')
        original = Path.iterdir
        first = p.plan(self.root, 'focus', 'save').preview()
        with patch.object(Path, 'iterdir', lambda path: iter(reversed(list(original(path))))):
            second = p.plan(self.root, 'focus', 'save').preview()
        self.assertEqual(first, second)

    def test_duplicate_targets_rename_requires_explicit_identity(self):
        self.link('second', 'alpha')
        saved = self.save()
        saved['entries'][0]['alias'] = 'First alias'
        saved['entries'][1]['alias'] = 'Second alias'
        self.write_definition(saved)
        self.save()
        (self.view / 'alpha').rename(self.view / 'renamed')
        (self.view / 'second').rename(self.view / 'other')
        with self.assertRaisesRegex(ValueError, 'match new/path=old-id'):
            self.save()
        result = self.save(matches={'renamed': saved['entries'][0]['id'], 'other': saved['entries'][1]['id']})
        self.assertEqual([(i['name'], i['alias']) for i in result['entries']],
                         [('renamed', 'First alias'), ('other', 'Second alias')])

    def test_unsaved_tree_concurrent_yaml_and_missing_state(self):
        saved = self.save()
        self.link('beta', 'beta')
        with self.assertRaisesRegex(ValueError, 'Unsaved'):
            p.plan(self.root, 'focus', 'restore')
        saved['title'] = 'Changed in another editor'
        self.write_definition(saved)
        with self.assertRaisesRegex(ValueError, 'Definition changed'):
            self.save()
        self.save(choose=True)
        self.link('third', 'alpha')
        (self.root / '.yap/local/state/focus.json').unlink()
        with self.assertRaisesRegex(ValueError, 'state is missing'):
            self.save()
        with self.assertRaisesRegex(ValueError, 'Unsaved'):
            p.plan(self.root, 'focus', 'restore')

    def test_deleted_local_tree_is_an_edit_even_when_empty(self):
        self.save()
        (self.view / 'alpha').unlink()
        with self.assertRaisesRegex(ValueError, 'Unsaved perspective deletion'):
            p.plan(self.root, 'focus', 'restore')
        p.apply(p.plan(self.root, 'focus', 'restore', choose=True))
        self.assertTrue((self.view / 'alpha').is_symlink())

    def test_missing_definition_does_not_recreate_from_stale_state(self):
        self.save()
        self.definition().unlink()
        with self.assertRaisesRegex(ValueError, 'removed'):
            self.save()

    def test_preview_detects_intervening_tree_definition_and_state_changes(self):
        self.save()
        plan = p.plan(self.root, 'focus', 'restore')
        self.link('new', 'beta')
        with self.assertRaisesRegex(ValueError, 'changed since preview'):
            p.apply(plan)
        (self.view / 'new').unlink()
        saved = json.loads(self.definition().read_text())
        saved['title'] = 'Concurrent change'
        self.write_definition(saved)
        with self.assertRaisesRegex(ValueError, 'changed since preview'):
            p.apply(plan)
        plan = p.plan(self.root, 'focus', 'save')
        (self.root / '.yap/local/state/focus.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed since preview'):
            p.apply(plan)

    def test_editor_replaced_symlink_is_preserved_even_with_choose(self):
        self.save()
        shortcut = self.view / 'alpha'
        shortcut.unlink()
        shortcut.write_text('Unsaved user content')
        for operation in ('save', 'restore'):
            with self.subTest(operation=operation), self.assertRaisesRegex(ValueError, 'unexpected real file'):
                p.plan(self.root, 'focus', operation, choose=True)
        self.assertEqual(shortcut.read_text(), 'Unsaved user content')

    def test_links_outside_entries_through_work_and_cycles_are_rejected(self):
        bad = self.view / 'bad'
        work = self.root / 'pfo/act/alpha/work'
        work.symlink_to(self.root / 'pfo/act/beta')
        for target in (self.root / 'pfo/nts', work, work / '../alpha.md', bad):
            bad.symlink_to(target)
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.save()
            self.assertTrue(bad.is_symlink())
            bad.unlink()

    def test_move_breakage_is_diagnosed_without_repair(self):
        group = self.view / 'group'
        group.mkdir()
        link = self.view / 'alpha'
        link.rename(group / 'alpha')
        stored = os.readlink(group / 'alpha')
        with self.assertRaisesRegex(ValueError, 'target .*outside canonical'):
            self.save()
        self.assertEqual(os.readlink(group / 'alpha'), stored)
        (group / 'alpha').unlink()
        self.link('group/alpha', 'alpha')
        self.save()

    def test_absolute_links_warn_and_restore_as_relative(self):
        (self.view / 'alpha').unlink()
        (self.view / 'alpha').symlink_to(self.root / 'pfo/act/alpha')
        plan = p.plan(self.root, 'focus', 'save')
        self.assertEqual(len(plan.warnings), 1)
        p.apply(plan)
        p.apply(p.plan(self.root, 'focus', 'restore'))
        self.assertFalse(os.path.isabs(os.readlink(self.view / 'alpha')))

    def test_unsafe_names_subpaths_duplicate_ids_and_seven_groups(self):
        saved = self.save()
        for name in ('../escape', '.hidden', 'work', 'repo', 'shlf', 'zbox', 'trailing.', 'a\\b'):
            invalid = json.loads(p.encode(saved))
            invalid['entries'][0]['name'] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                p.validate(invalid, p.catalog(self.root))
        for subpath in ('../beta/beta.md', 'work/data', 'repo/data', 'shlf/data', 'zbox/data', 'secret.md', 'res/../alpha.md'):
            with self.subTest(subpath=subpath), self.assertRaises(ValueError):
                p.target_path(p.catalog(self.root), {'entry': 'alpha', 'path': subpath})
        saved['entries'].append(dict(saved['entries'][0], name='duplicate'))
        with self.assertRaisesRegex(ValueError, 'duplicate placement ID'):
            p.validate(saved, p.catalog(self.root))
        for index in range(8):
            (self.view / f'group-{index}').mkdir()
        with self.assertRaisesRegex(ValueError, 'seven'):
            self.save()

    def test_case_collisions_and_duplicate_keys(self):
        saved = self.save()
        saved['entries'].append(dict(saved['entries'][0], id='p000002', name='ALPHA'))
        with self.assertRaisesRegex(ValueError, 'Case-insensitive'):
            p.validate(saved, p.catalog(self.root))
        beta = self.root / 'pfo/act/beta/beta.md'
        beta.write_text(beta.read_text().replace('"beta"', '"alpha"'))
        with self.assertRaisesRegex(ValueError, 'duplicate entry key'):
            p.catalog(self.root)

    def test_schema_requires_the_integer_version_and_targets_require_text(self):
        saved = self.save()
        entries = p.catalog(self.root)
        before = self.definition().read_bytes()
        for schema in (True, False, 1.0, '1', None, [], {}, 2):
            with self.subTest(schema=schema), self.assertRaisesRegex(ValueError, 'schema 1'):
                p.validate(dict(saved, schema=schema), entries)
        p.validate(saved, entries)
        for key in ([], {}, None, True, 1):
            invalid = json.loads(p.encode(saved))
            invalid['entries'][0]['target']['entry'] = key
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Unknown canonical target'):
                p.validate(invalid, entries)
        self.assertEqual(p.target_path(entries, {'entry': 'alpha'}),
                         self.root / 'pfo/act/alpha')
        self.assertEqual(self.definition().read_bytes(), before)

    def test_symlink_control_files_and_parent_directories_are_rejected(self):
        target = self.root / 'pfo/act/alpha/alpha.md'
        self.definition().symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.save()
        self.definition().unlink()
        state = self.root / '.yap/local/state'
        state.symlink_to(self.root / 'pfo/act/alpha')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.save()

    def test_interrupted_restore_is_recoverable_without_touching_sources(self):
        saved = self.save()
        (self.view / 'alpha').unlink()
        self.link('beta', 'beta')
        plan = p.plan(self.root, 'focus', 'restore', choose=True)
        source = self.root / 'pfo/act/alpha/alpha.md'
        before = source.read_bytes()
        with patch.object(Path, 'symlink_to', side_effect=OSError('Simulated interruption')):
            with self.assertRaisesRegex(OSError, 'interruption'):
                p.apply(plan)
        p.apply(p.plan(self.root, 'focus', 'restore', choose=True))
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(json.loads(self.definition().read_text()), saved)
        self.assertTrue((self.view / 'alpha').is_symlink())

    def test_shared_target_retargeting_does_not_modify_source(self):
        saved = self.save()
        source = self.root / 'pfo/act/alpha/alpha.md'
        before = source.read_bytes()
        (self.view / 'alpha').unlink()
        self.link('alpha', 'beta')
        result = self.save()
        self.assertEqual(result['entries'][0]['id'], saved['entries'][0]['id'])
        self.assertEqual(result['entries'][0]['target'], {'entry': 'beta'})
        self.assertEqual(source.read_bytes(), before)

    def test_saved_only_rendering_preserves_dirty_tree_and_unique_counts(self):
        self.link('again', 'alpha')
        saved = self.save()
        saved['entries'][0]['alias'] = '<script>not executable</script>'
        self.write_definition(saved)
        self.link('draft', 'beta')
        before = os.readlink(self.view / 'draft')
        perspective_html.render(self.root)
        html = (self.root / 'yap.html').read_text()
        english = (self.root / 'yap.en.html').read_text()
        self.assertIn('1 eindeutige Einträge · 2 Platzierungen', html)
        self.assertIn('Nicht zugeordnet (1)', html)
        self.assertIn('Alle Einträge (2)', html)
        self.assertIn('Ungespeicherte Änderungen', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('Unassigned (1)', english)
        self.assertIn('Alpha', english)
        self.assertEqual(os.readlink(self.view / 'draft'), before)

    def test_demo_has_shared_work_and_one_versioned_identity(self):
        demo = self.root.parent / 'demo'
        prototype.demo(demo)
        self.assertEqual(len(p.catalog(demo)), 5)
        self.assertEqual((demo / 'pfo/act/launch/repo').resolve(), (demo / 'pfo/act/evaluate/repo').resolve())
        self.assertEqual((demo / 'pfo/act/evaluate/evaluate.md').read_text().count('.version'), 2)
        for name in ('domain', 'focus'):
            p.apply(p.plan(demo, name, 'restore'))
            p.apply(p.plan(demo, name, 'save'))


if __name__ == '__main__':
    unittest.main()
