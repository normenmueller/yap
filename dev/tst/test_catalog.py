"""Identity survives filing changes; discovery never turns ordinary files into work."""

from pathlib import Path
import errno
import os
import tempfile
import unittest
from unittest.mock import patch

from yap import catalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap catalog ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def entry(self, folder, key, kind='activity'):
        return self.write(f'{folder}/{Path(folder).name}.md',
                          f'---\nkind: {kind}\nkey: {key}\ntitle: {key}\n---\n\nAuthored body.\n')

    def test_nested_independent_activity_and_ordinary_intermediate_folders(self):
        self.entry('pfo/act/cpp', 'cpp')
        sfe = self.entry('pfo/act/cpp/modules/sfe', 'sfe')
        self.write('pfo/act/cpp/modules/modules.md', '---\ntitle: Ordinary documentation\n---\n')
        self.write('pfo/act/cpp/extra.md', 'Ordinary additional file.')
        entries = catalog.discover(self.root)
        self.assertEqual(set(entries), {'cpp', 'sfe'})
        self.assertEqual(entries['sfe']['source'], sfe)
        self.assertNotIn('parent', entries['sfe'])

    def test_move_and_folder_rename_preserve_identity_and_body(self):
        old = self.entry('pfo/act/group/original', 'permanent-key')
        before = old.read_bytes()
        new_folder = self.root / 'pfo/act/renamed'
        old.parent.rename(new_folder)
        new_source = new_folder / 'renamed.md'
        (new_folder / old.name).rename(new_source)
        entries = catalog.discover(self.root)
        self.assertEqual(set(entries), {'permanent-key'})
        self.assertEqual(entries['permanent-key']['source'], new_source)
        self.assertEqual(new_source.read_bytes(), before)

    def test_notes_are_explicit_and_do_not_enroll_ordinary_preparation(self):
        self.entry('pfo/nts/dbf', 'dbf', 'note')
        self.write('pfo/nts/pfm/pfm.md', '---\ntitle: Private preparation\n---\n')
        self.write('pfo/act/unmarked/unmarked.md', '---\nkey: unmarked\ntitle: Ordinary\n---\n')
        entries = catalog.discover(self.root)
        self.assertEqual(set(entries), {'dbf'})
        self.assertEqual(entries['dbf']['kind'], 'note')

    def test_areas_are_explicit_and_share_activity_identity_namespace(self):
        self.entry('pfo/act/area', 'area', 'area')
        self.entry('pfo/act/area/task', 'task')
        self.write('pfo/act/ordinary/ordinary.md', '---\ntitle: Ordinary field\n---\n')
        entries = catalog.discover(self.root)
        self.assertEqual({key: e['kind'] for key, e in entries.items()},
                         {'area': 'area', 'task': 'activity'})
        self.assertNotIn('parent', entries['task'])
        duplicate = self.entry('pfo/act/duplicate', 'area')
        with self.assertRaisesRegex(ValueError, 'duplicate entry key'):
            catalog.discover(self.root)

        duplicate.unlink()
        self.entry('pfo/nts/wrong', 'wrong', 'area')
        with self.assertRaisesRegex(ValueError, 'kind must be note'):
            catalog.discover(self.root)

    def test_free_file_notes_keep_distinct_identity_in_shared_topic_and_root(self):
        for name, key in [('rnd.md', 'rnd'), ('nts.md', 'collection-note'),
                          ('topic/one.md', 'one'), ('topic/two.md', 'two')]:
            self.write('pfo/nts/' + name, f'---\nkind: note\nkey: {key}\ntitle: {key}\n---\n')
        self.write('pfo/nts/topic/private.md', 'Ordinary private note.')
        self.write('pfo/nts/topic/res/hidden.md', '---\nkind: note\nkey: hidden\ntitle: Hidden\n---\n')
        entries = catalog.discover(self.root)
        self.assertEqual(set(entries), {'rnd', 'collection-note', 'one', 'two'})
        self.assertTrue(all(catalog.entry_root(e) == e['source'] for e in entries.values()))

    def test_skips_shortcuts_hidden_resources_and_work_without_traversal(self):
        self.entry('pfo/act/real', 'real')
        for folder in ('pfo/act/work/fake', 'pfo/act/real/res/fake', 'pfo/act/.hidden/fake',
                       'pfo/act/real/repo/fake', 'pfo/act/real/shlf/fake', 'pfo/act/real/zbox/fake'):
            self.entry(folder, 'fake')
        base = self.root / 'pfo/act'
        (base / 'alias').symlink_to(base / 'real', target_is_directory=True)
        (base / 'cycle').symlink_to(base, target_is_directory=True)
        (base / 'broken').symlink_to(base / 'missing')
        self.assertEqual(set(catalog.discover(self.root)), {'real'})

    def test_rejects_duplicate_keys_even_across_collections_and_case(self):
        self.entry('pfo/act/one', 'same')
        self.entry('pfo/nts/two', 'SAME', 'note')
        with self.assertRaisesRegex(ValueError, 'duplicate entry key'):
            catalog.discover(self.root)

    def test_marked_entries_require_kind_key_and_title_in_correct_collection(self):
        path = self.entry('pfo/act/test', 'test')
        for text, error in (
            ('kind: activity\ntitle: Task', 'key requires'),
            ('kind: activity\nkey: some//path\ntitle: Task', 'key requires'),
            ('kind: activity\nkey: test', 'title is required'),
            ('kind: note\nkey: test\ntitle: Task', 'kind must be'),
        ):
            with self.subTest(text=text):
                path.write_text('---\n' + text + '\n---\n')
                with self.assertRaisesRegex(ValueError, error):
                    catalog.discover(self.root)

    def test_qualified_keys_are_exact_identities_not_source_paths(self):
        self.entry('pfo/act/unrelated', 'cpp/sfe')
        self.entry('pfo/act/nested', 'dbia/tv-tm/pps')
        self.entry('pfo/act/flat', 'cpp-sfe')
        self.assertEqual(set(catalog.discover(self.root)), {'cpp/sfe', 'dbia/tv-tm/pps', 'cpp-sfe'})
        self.entry('pfo/act/duplicate', 'CPP/SFE')
        with self.assertRaisesRegex(ValueError, 'duplicate entry key'):
            catalog.discover(self.root)

    def test_qualified_keys_reject_empty_unsafe_and_anchor_segments(self):
        path = self.entry('pfo/act/test', 'valid')
        for key in ('/cpp', 'cpp/', 'cpp//sfe', 'cpp/../sfe', 'cpp/./sfe',
                    'cpp/#sfe', 'cpp/sfe#v1', 'cpp/sfe?x', 'cpp/%2f',
                    'cpp/ space', 'cpp/_sfe', 'cpp/\\sfe'):
            with self.subTest(key=key):
                path.write_text(f"---\nkind: activity\nkey: '{key}'\ntitle: Task\n---\n")
                with self.assertRaisesRegex(ValueError, 'key (requires|must be)'):
                    catalog.discover(self.root)

    def test_collection_symlink_is_rejected(self):
        folder = self.root / 'pfo'
        folder.mkdir()
        (folder / 'act').symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'collection cannot be a symlink'):
            catalog.discover(self.root)

    def test_identity_fields_never_silently_lose_markdown_formatting(self):
        path = self.entry('pfo/act/test', 'test')
        for value in ('a-_b_', 'a-__b__'):
            path.write_text(f'---\nkind: activity\nkey: {value}\ntitle: Task\n---\n')
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'literal text token'):
                catalog.discover(self.root)
        # Intraword underscores remain plain and retain exact identity.
        self.entry('pfo/act/test', 'a_b')
        self.assertEqual(set(catalog.discover(self.root)), {'a_b'})
        path.write_text('---\nkind: "**activity**"\nkey: test\ntitle: Task\n---\n')
        with self.assertRaisesRegex(ValueError, 'kind must be a literal'):
            catalog.discover(self.root)

    def test_unreadable_folder_fails_instead_of_returning_partial_catalog(self):
        self.entry('pfo/act/readable', 'readable')
        self.entry('pfo/act/unreadable', 'unreadable')
        original = os.scandir

        def scandir(path):
            if Path(path).name == 'unreadable':
                raise PermissionError(errno.EACCES, 'Permission denied', str(path))
            return original(path)

        with patch('os.scandir', side_effect=scandir):
            with self.assertRaisesRegex(ValueError, 'Cannot scan source directory .*unreadable'):
                catalog.discover(self.root)
