"""Build preflight preserves redirected output and checks only needed dependencies."""

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from yap import build, content


class BuildBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(os.chdir, Path.cwd())
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'portfolio'
        for name, text in [('pfo/act/act.md', '---\ntitle: Activities\n---\n'),
                           ('pfo/asp/goals.md', '---\ntitle: Goals\n---\n')]:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def test_redirected_owned_output_is_rejected_before_writes(self):
        for index, relative in enumerate(('.yap', '.yap/local', '.yap/local/build',
                                         '.yap/local/build/stage', '.yap/local/site',
                                         '.yap/local/site/assets')):
            with self.subTest(relative=relative):
                root = self.base / f'instance-{index}'
                root.mkdir()
                external = self.base / f'external-{index}'
                external.mkdir()
                sentinel = external / 'unrelated.txt'
                sentinel.write_text('Preserve external data')
                link = root / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(external, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'symlinks'):
                    build.main('resources', instance=root)
                self.assertEqual(sentinel.read_text(), 'Preserve external data')
                self.assertEqual(list(external.iterdir()), [sentinel])
                self.assertTrue(link.is_symlink())

    def test_check_needs_no_pdf_toolchain_and_preserves_unrelated_local_navigation(self):
        unrelated = self.root / '.yap/local/development-link'
        unrelated.parent.mkdir(parents=True)
        unrelated.symlink_to(self.base, target_is_directory=True)
        pandoc = shutil.which('pandoc')
        self.assertIsNotNone(pandoc)
        with patch.object(build.shutil, 'which', side_effect=lambda tool: pandoc if tool == 'pandoc' else None), \
             redirect_stdout(StringIO()) as output:
            build.main('check', instance=self.root)
            self.assertIn('Checked:', output.getvalue())
            with self.assertRaisesRegex(ValueError, 'latexmk'):
                build.main('report', instance=self.root)
        self.assertTrue(unrelated.is_symlink())

    def test_cold_and_warm_builds_share_catalog_without_losing_binding_changes(self):
        source = self.root / 'pfo/act/task/task.md'
        source.parent.mkdir()
        source.write_text('---\nkind: activity\nkey: task\ntitle: Task\n'
                          'wsp: {code: "../../private-workspace-one"}\n---\n')
        with patch.object(content, 'read', wraps=content.read) as read, redirect_stdout(StringIO()):
            build.main('check', instance=self.root)
            self.assertEqual(sum(Path(call.args[0]).resolve() == source for call in read.call_args_list), 1)
            read.reset_mock()
            build.main('resources', instance=self.root)
            self.assertEqual(sum(Path(call.args[0]).resolve() == source for call in read.call_args_list), 1)
            read.reset_mock()
            build.main('resources', instance=self.root)
            read.assert_not_called()
            cache = self.root / build.BUILD / 'model.json'
            self.assertNotIn('private-workspace-one', cache.read_text())
            self.assertNotIn('wsp', json.dumps(json.loads(cache.read_text())))
            read.reset_mock()
            source.write_text(source.read_text().replace('private-workspace-one', 'private-workspace-two'))
            build.main('resources', instance=self.root)
            self.assertEqual(sum(Path(call.args[0]).resolve() == source for call in read.call_args_list), 1)
            self.assertEqual((source.parent / 'wsp/code').readlink(), self.root.parent.parent / 'private-workspace-two')
            self.assertNotIn('private-workspace-two', cache.read_text())

    def test_warm_cache_rejects_redirected_note_collection_before_source_reads(self):
        notes = self.root / 'pfo/nts'
        notes.mkdir()
        (notes / 'note.md').write_text('---\nkind: note\nkey: note\ntitle: Note\n---\n')
        with redirect_stdout(StringIO()):
            build.main('resources', instance=self.root)
        external = self.base / 'external-notes'
        notes.rename(external)
        notes.symlink_to(external, target_is_directory=True)
        before = {p.name: p.read_bytes() for p in external.iterdir()}
        with patch.object(build, 'hashes', side_effect=AssertionError('redirected source read')), \
             self.assertRaisesRegex(ValueError, 'source collection cannot be a symlink'):
            build.main('resources', instance=self.root)
        self.assertEqual({p.name: p.read_bytes() for p in external.iterdir()}, before)

    def test_build_state_hardlink_does_not_modify_external_file(self):
        external = self.base / 'external-state.json'
        external.write_text('{}')
        state = self.root / build.BUILD / 'state.json'
        state.parent.mkdir(parents=True)
        state.hardlink_to(external)
        with self.assertRaisesRegex(ValueError, 'hardlinks'):
            build.main('resources', instance=self.root)
        self.assertEqual(external.read_text(), '{}')
        self.assertEqual(state.read_text(), '{}')

    def test_report_refuses_hardlinked_renderer_output_before_any_tool_runs(self):
        external = self.base / 'external-image.png'
        external.write_bytes(b'Preserve this image')
        image = self.root / build.BUILD / 'work/overview/board.png'
        image.parent.mkdir(parents=True)
        image.hardlink_to(external)
        with patch.object(build, 'run', side_effect=AssertionError('renderer reached')), \
             self.assertRaisesRegex(ValueError, 'hardlinks'):
            build.main('report', instance=self.root)
        self.assertEqual(external.read_bytes(), b'Preserve this image')
        self.assertEqual(image.read_bytes(), b'Preserve this image')


if __name__ == '__main__':
    unittest.main()
