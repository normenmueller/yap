"""One validated source catalog feeds a build without persisting private bindings."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yap import catalog, content, workspace_links


class CatalogReuseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap catalog reuse ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        sources = {
            'pfo/act/act.md': '---\ntitle: Activities\n---\n',
            'pfo/asp/goals.md': '---\ntitle: Goals\n---\n',
            'pfo/act/area/area.md':
                '---\nkind: area\nkey: field\ntitle: Field\n---\n',
            'pfo/act/area/unrelated/unrelated.md':
                '---\nkind: activity\nkey: effort/task\ntitle: Task\n'
                'wsp: {code: "private-workspace-marker"}\n---\n\nAuthored body.\n',
            'pfo/nts/topic.md': '---\nkind: note\nkey: context\ntitle: Context\n---\n',
        }
        for relative, text in sources.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def source_hashes(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob('*.md')}

    def test_reusing_discovery_preserves_the_public_model_and_authored_sources(self):
        expected = content.load(self.root)
        entries = catalog.discover(self.root)
        original_entries = deepcopy(entries)
        sources = {path: path.read_bytes() for path in self.root.rglob('*.md')}
        with patch.object(catalog, 'discover', side_effect=AssertionError('duplicate source discovery')):
            actual = content.load(self.root, entries=entries)
        self.assertEqual(actual, expected)
        self.assertEqual(entries, original_entries)
        self.assertEqual({path: path.read_bytes() for path in sources}, sources)
        self.assertNotIn('private-workspace-marker', json.dumps(actual))

    def test_cached_public_nodes_recover_the_same_private_navigation_without_pandoc(self):
        entries = catalog.discover(self.root)
        model = json.loads(json.dumps(content.load(self.root, entries=entries)))
        before = deepcopy(model)
        expected = workspace_links.plan(self.root, entries)
        with patch.object(content, 'read', side_effect=AssertionError('cached identity reparsed')):
            private_entries = catalog.workspace_entries(self.root, model['nodes'], source_hashes=self.source_hashes())
            actual = workspace_links.plan(self.root, private_entries)
        self.assertEqual(actual, expected)
        self.assertEqual(set(private_entries), {'field', 'effort/task'})
        self.assertEqual(model, before)
        self.assertNotIn('private-workspace-marker', json.dumps(model))

    def test_cached_navigation_rejects_redirected_sources_without_reading_the_target(self):
        model = content.load(self.root)
        hashes = self.source_hashes()
        task = next(node for node in model['nodes'] if node['kind'] == 'activity')
        source = self.root / task['path']
        external = self.root / 'external.md'
        external.write_text('Unrelated material stays untouched.')
        source.unlink()
        source.symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'symlinks are not allowed'):
            catalog.workspace_entries(self.root, model['nodes'], source_hashes=hashes)
        self.assertEqual(external.read_text(), 'Unrelated material stays untouched.')

    def test_cached_navigation_rejects_outside_missing_and_non_source_paths(self):
        for relative in ('../outside.md', '/outside.md', 'pfo/nts/topic.md',
                         'pfo/act/act.md', 'pfo/act/task/other.md', 'pfo/act/missing/missing.md'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                catalog.workspace_entries(self.root, [dict(kind='activity', key='task', path=relative)],
                                          source_hashes=self.source_hashes())

    def test_binding_edit_after_the_build_snapshot_stops_navigation_planning(self):
        model = content.load(self.root)
        hashes = self.source_hashes()
        task = next(node for node in model['nodes'] if node['kind'] == 'activity')
        source = self.root / task['path']
        source.write_text(source.read_text().replace('private-workspace-marker', 'new-workspace-marker'))
        with self.assertRaisesRegex(ValueError, 'source changed since the build snapshot'):
            catalog.workspace_entries(self.root, model['nodes'], source_hashes=hashes)
        self.assertFalse((source.parent / 'wsp').exists())
        self.assertNotIn('private-workspace-marker', json.dumps(model))
        self.assertNotIn('new-workspace-marker', json.dumps(model))

    def test_identical_notes_redirect_is_rejected_before_cold_or_cached_source_reads(self):
        model = content.load(self.root)
        hashes = self.source_hashes()
        notes = self.root / 'pfo/nts'
        outside = self.root / 'private-notes'
        notes.rename(outside)
        notes.symlink_to(outside, target_is_directory=True)
        before = (outside / 'topic.md').read_bytes()
        with patch.object(content, 'read', side_effect=AssertionError('redirected collection parsed')):
            with self.assertRaisesRegex(ValueError, 'source collection cannot be a symlink'):
                catalog.discover(self.root)
            with self.assertRaisesRegex(ValueError, 'source collection cannot be a symlink'):
                catalog.workspace_entries(self.root, model['nodes'], source_hashes=hashes)
        self.assertTrue(notes.is_symlink())
        self.assertEqual((outside / 'topic.md').read_bytes(), before)

    def test_empty_cached_catalog_still_refuses_collection_redirection(self):
        outside = self.root / 'outside'
        outside.mkdir()
        for index, relative in enumerate(('pfo', 'pfo/act', 'pfo/nts')):
            with self.subTest(relative=relative):
                root = self.root / f'empty-cache-{index}'
                link = root / relative
                link.parent.mkdir(parents=True)
                link.symlink_to(outside, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'source collection cannot be a symlink'):
                    catalog.workspace_entries(root, [], source_hashes={})
                self.assertTrue(link.is_symlink())
        self.assertEqual(list(outside.iterdir()), [])

    def test_collection_preflight_accepts_absence_and_rejects_files_without_writes(self):
        empty = self.root / 'empty'
        empty.mkdir()
        catalog.validate_collections(empty)
        self.assertEqual(list(empty.iterdir()), [])
        for index, relative in enumerate(('pfo', 'pfo/act', 'pfo/nts')):
            with self.subTest(relative=relative):
                root = self.root / f'file-root-{index}'
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_text('Keep source-root collision')
                with self.assertRaisesRegex(ValueError, 'expected a source collection directory'):
                    catalog.validate_collections(root)
                self.assertEqual(path.read_text(), 'Keep source-root collision')


if __name__ == '__main__':
    unittest.main()
