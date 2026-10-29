"""Publication refuses redirected trees before touching external or existing files."""

from pathlib import Path
import tempfile
import unittest

from yap.outputs import publish, validate_tree, write_text


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        (self.stage / 'index.html').write_text('New page')
        self.site = self.root / 'site'
        self.external = self.root / 'external'
        self.external.mkdir()
        (self.external / 'unrelated.txt').write_text('Keep this')

    def assert_preserved(self):
        self.assertEqual(list(self.external.iterdir()), [self.external / 'unrelated.txt'])
        self.assertEqual((self.external / 'unrelated.txt').read_text(), 'Keep this')

    def test_regular_publication_reconciles_and_preserves_unchanged_files(self):
        self.site.mkdir()
        (self.site / 'obsolete.txt').write_text('Old generated output')
        publish(self.stage, self.site, root=self.root)
        self.assertEqual((self.site / 'index.html').read_text(), 'New page')
        self.assertFalse((self.site / 'obsolete.txt').exists())
        before = (self.site / 'index.html').stat().st_mtime_ns
        publish(self.stage, self.site, root=self.root)
        self.assertEqual((self.site / 'index.html').stat().st_mtime_ns, before)
        self.assert_preserved()

    def test_generated_text_replacement_preserves_external_hardlink_content_and_mode(self):
        self.site.mkdir()
        external = self.external / 'unrelated.txt'
        external.chmod(0o640)
        generated = self.site / 'state.json'
        generated.hardlink_to(external)
        write_text(generated, 'New generated state', root=self.root)
        self.assertEqual(generated.read_text(), 'New generated state')
        self.assertEqual(generated.stat().st_mode & 0o777, 0o640)
        self.assertNotEqual(generated.stat().st_ino, external.stat().st_ino)
        self.assert_preserved()

    def test_site_root_redirection_is_rejected_before_cleanup(self):
        self.site.symlink_to(self.external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            publish(self.stage, self.site, root=self.root)
        self.assertTrue(self.site.is_symlink())
        self.assert_preserved()

    def test_nested_directory_redirection_is_rejected_before_any_page_write(self):
        self.site.mkdir()
        (self.site / 'index.html').write_text('Previous page')
        (self.site / 'assets').symlink_to(self.external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            publish(self.stage, self.site, root=self.root)
        self.assertEqual((self.site / 'index.html').read_text(), 'Previous page')
        self.assert_preserved()

    def test_old_predictable_temporary_symlink_cannot_overwrite_external_file(self):
        self.site.mkdir()
        (self.site / '.index.html.tmp').symlink_to(self.external / 'unrelated.txt')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            publish(self.stage, self.site, root=self.root)
        self.assertFalse((self.site / 'index.html').exists())
        self.assertTrue((self.site / '.index.html.tmp').is_symlink())
        self.assert_preserved()

    def test_stage_symlink_is_never_copied_to_publication(self):
        (self.stage / 'private.txt').symlink_to(self.external / 'unrelated.txt')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            publish(self.stage, self.site, root=self.root)
        self.assertFalse(self.site.exists())
        self.assert_preserved()

    def test_output_ancestry_and_overlapping_trees_are_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            validate_tree(self.root, alias / 'new-site')
        with self.assertRaisesRegex(ValueError, 'separate trees'):
            publish(self.stage, self.stage / 'site', root=self.root)
        with self.assertRaisesRegex(ValueError, 'beneath'):
            validate_tree(self.root, self.root / '..' / 'elsewhere')
        self.assert_preserved()


if __name__ == '__main__':
    unittest.main()
