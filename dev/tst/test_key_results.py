"""Objective-owned KR discovery, ordering, and strict source validation."""

from fixtures import source_text

from pathlib import Path
import tempfile
import unittest

from yap import content


class KeyResultFilesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='yap-kr-test-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.write('pfo/act/act.md', '---\ntitle: Activities\n---\n')
        self.write('pfo/okr/goals.md', '---\ntitle: Goals\ntracking:\n  a: {status: active}\n  b: {status: closed}\n---\n')
        for key in ('a', 'b'):
            self.write(f'pfo/okr/obj/{key}.md', f'---\nkey: {key}\ntitle: Objective {key}\n---\n')
        self.kr = '---\nkey: result\ntitle: Result\nmeasure: Confirmed result\nunit: outcomes\ntarget: 2\n---\n'

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source_text(relative, text))
        return path

    def load(self):
        return content.load(self.root)

    def test_discovery_order_and_stable_identity_without_extra_objectives(self):
        self.assertEqual(self.load()['key_results'], {})
        kr = self.write('pfo/okr/obj/a/result.md', self.kr)
        self.write('pfo/okr/obj/a/alpha.md', self.kr.replace('key: result', 'key: alpha'))
        self.write('pfo/okr/obj/b/result.md', self.kr)
        self.write('pfo/okr/obj/a/.private.md', 'ignored')
        model = self.load()
        self.assertEqual([g['key'] for g in model['goals']], ['a', 'b'])
        self.assertEqual([r['key'] for r in model['key_results']['a']], ['alpha', 'result'])
        self.assertEqual([r['key'] for r in model['key_results']['b']], ['result'])
        goal = self.root / 'pfo/okr/obj/a.md'
        goal.write_text(goal.read_text().replace('key: a', 'key: a\nkr-sequence: [result]'))
        self.assertEqual([r['key'] for r in self.load()['key_results']['a']], ['result', 'alpha'])
        before = self.load()['key_results']
        goal.rename(goal.with_name('renamed-objective.md'))
        kr.rename(kr.with_name('renamed-kr.md'))
        self.assertEqual(self.load()['key_results'], before)
        self.assertEqual(self.load()['goals'][0]['activities'], [])

    def test_duplicate_key_is_scoped_to_objective_and_names_the_source(self):
        self.write('pfo/okr/obj/a/one.md', self.kr)
        self.write('pfo/okr/obj/a/two.md', self.kr)
        with self.assertRaisesRegex(ValueError, r'a/two.md: duplicate KR key'):
            self.load()

    def test_order_rejects_stale_duplicate_empty_and_structured_entries(self):
        self.write('pfo/okr/obj/a/result.md', self.kr)
        goal = self.root / 'pfo/okr/obj/a.md'
        original = goal.read_text()
        for order in ('[missing]', '[result, result]', '[""]', 'result', '[{key: result}]'):
            with self.subTest(order=order):
                goal.write_text(original.replace('key: a', 'key: a\nkr-sequence: '+order))
                with self.assertRaisesRegex(ValueError, 'kr-sequence'):
                    self.load()

    def test_orphan_nested_unexpected_and_symlink_sources_fail(self):
        orphan = self.root / 'pfo/okr/obj/missing'
        orphan.mkdir()
        with self.assertRaisesRegex(ValueError, 'matching objective key'):
            self.load()
        orphan.rmdir()
        folder = self.root / 'pfo/okr/obj/a'
        folder.mkdir()
        nested = folder / 'nested'
        nested.mkdir()
        with self.assertRaisesRegex(ValueError, 'expected a KR file'):
            self.load()
        nested.rmdir()
        invalid = self.write('pfo/okr/obj/a/result.txt', 'unexpected')
        with self.assertRaisesRegex(ValueError, 'expected a KR file'):
            self.load()
        invalid.unlink()
        link = folder / 'result.md'
        link.symlink_to(self.root / 'pfo/okr/obj/a.md')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.load()
        link.unlink()
        folder.rmdir()
        folder.symlink_to(self.root / 'pfo/act', target_is_directory=True)
        with self.assertRaises(ValueError):
            self.load()

    def test_legacy_central_and_local_definitions_are_rejected(self):
        for name in ('pfo/okr/goals.md', 'pfo/okr/obj/a.md'):
            path = self.root / name
            original = path.read_text()
            for value in ('{}', ''):
                path.write_text(original.replace('---\n', '---\nokr-preview: '+value+'\n', 1))
                with self.assertRaisesRegex(ValueError, 'obj/'):
                    self.load()
            path.write_text(original)

    def test_content_and_fields_never_disappear_silently(self):
        path = self.write('pfo/okr/obj/a/result.md', self.kr)
        for extra in ('objective: a', 'status: active', 'unknown: value'):
            path.write_text(self.kr.replace('key: result', 'key: result\n'+extra))
            with self.assertRaisesRegex(ValueError, 'unknown KR fields'):
                self.load()
        path.write_text(self.kr+'\nPublic content\n')
        with self.assertRaisesRegex(ValueError, 'YAML fields'):
            self.load()
        path.write_text(self.kr+'\n::: {.internal}\nPrivate working note\n:::\n')
        self.assertNotIn('Private working note', str(self.load()))


if __name__ == '__main__':
    unittest.main()
