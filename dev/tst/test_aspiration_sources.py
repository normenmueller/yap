"""Selected aspiration sources, portable references and warm-cache boundaries."""

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote

from yap import aspirations, build, content, documents, home, instance, perspectives, views


class AspirationSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap-aspirations-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.application = Path.cwd()
        self.addCleanup(os.chdir, Path.cwd())
        self.write('pfo/act/act.md', '---\ntitle: Activities\ntracking:\n  task: {status: wip}\n---\n')
        self.write('pfo/act/task/task.md', '---\nkind: activity\nkey: task\ntitle: Task\n---\n')
        self.write('pfo/asp/goals.md', '---\ntitle: Goals\nsequence: [alpha]\n'
                   'tracking:\n  alpha: {status: active, priority: p2}\n---\n')
        self.write('pfo/asp/obj/alpha.md', '---\nkey: alpha\ntitle: An objective\n---\n'
                   '## Detail {#detail}\n\nOriginal objective prose.\n\n'
                   '[Control](../goals.md#detail) [Self](#detail)\n')
        self.write('pfo/asp/obj/alpha/result.md', '---\nkey: result\ntitle: A result\n'
                   'measure: Recorded evidence\nunit: outcomes\ntarget: 2\ncurrent: 0\nactivities: [task]\n---\n')
        self.write('pov/focus/.perspective.yaml', json.dumps({'schema': 1, 'title': 'Focus',
                   'entries': [{'id': 'p000001', 'name': 'Task', 'target': {'entry': 'task'}}]}))
        shortcut = self.root / 'pov/focus/Task'
        shortcut.symlink_to('../../pfo/act/task', target_is_directory=True)
        self.write('.yap/cfg/machine.json', '{"links": {}}\n')
        self.source = 'pfo/asp'
        self.repair_links()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def configure(self, source):
        self.write('yap.json', json.dumps({'schema': 1, 'slug': 'example',
                                         'sources': {'aspirations': source}}))

    def repair_links(self):
        activity = self.root / 'pfo/act/task/task.md'
        objective = self.root / self.source / 'obj/alpha.md'
        control = self.root / self.source / 'goals.md'
        link = quote(os.path.relpath(control, activity.parent))
        activity.write_text(activity.read_text().split('\n[Goal]')[0] + f'\n[Goal]({link}#goal-alpha)\n')
        link = quote(os.path.relpath(activity, objective.parent))
        objective.write_text(objective.read_text().split('\n[Task]')[0] + f'\n[Task]({link})\n')

    def move(self, source):
        destination = self.root / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        (self.root / self.source).rename(destination)
        self.source = source
        self.configure(source)
        self.repair_links()

    def run_build(self):
        with redirect_stdout(StringIO()):
            build.main('resources', instance=self.root)
        return json.loads((self.root / '.yap/local/build/model.json').read_text())

    def preserved(self):
        """Include source/config bytes, saved perspectives and unsaved shortcuts."""
        return {str(path.relative_to(self.root)): ('link', os.readlink(path)) if path.is_symlink()
                else ('file', path.read_bytes()) if path.is_file() else ('dir', None)
                for path in self.root.rglob('*')
                if not path.is_relative_to(self.root / '.yap/local') and path.name != 'example.html'}

    def test_default_and_explicit_roots_preserve_facts_and_publication_links(self):
        baseline = content.load(self.root)
        for source in ('pfo/asp', 'plans/long term/aspirations', 'plans/work/aspirations', 'pfo/okr'):
            with self.subTest(source=source):
                if source != self.source:
                    self.move(source)
                before = self.preserved()
                # Direct loading must resolve against the selected root, not cwd.
                os.chdir(self.application)
                model = content.load(self.root)
                self.assertEqual(model['goal_source'], source + '/goals.md')
                self.assertEqual(model['key_results'], baseline['key_results'])
                self.assertEqual(model['goals'][0]['activities'], baseline['goals'][0]['activities'])
                self.assertEqual(model['goals'][0]['id'], 'goal-alpha')
                self.assertEqual(model['goals'][0]['priority'], 'p2')
                # Rendering keeps the parsed selection even if configuration later changes.
                manifest = self.root / 'yap.json'
                original = manifest.read_bytes() if manifest.exists() else None
                self.configure('unused/location')
                activity = documents.activity(model, Path('stage'))
                performance = documents.mpm(model, Path('stage'))
                html = views._goal_cards(model)
                targets = [item['c'][2][0] for item in content.walk(activity['blocks']) if item['t'] == 'Link']
                self.assertIn('Performance - mPM.pdf#nameddest=goal-alpha', targets)
                targets = [item['c'][2][0] for item in content.walk(performance['blocks']) if item['t'] == 'Link']
                self.assertEqual(targets.count('#' + documents.pdf_target('goal-alpha--detail')), 2)
                self.assertIn('Activity - Details.pdf#nameddest=act-task', targets)
                self.assertIn('../../acc/pdf/Performance%20-%20mPM.pdf#nameddest=', html.replace(' ', '%20'))
                if original is None:
                    manifest.unlink()
                else:
                    manifest.write_bytes(original)
                self.run_build()
                self.assertEqual(self.preserved(), before)

    def test_selected_public_documents_allow_work_names_but_reject_private_aliases(self):
        self.move('plans/work/aspirations')
        control = self.root / self.source / 'goals.md'
        control.write_text(control.read_text().replace('alpha', 'work'))
        objective = self.root / self.source / 'obj/alpha.md'
        moved = objective.with_name('work.md')
        objective.rename(moved)
        moved.write_text(moved.read_text().replace('key: alpha', 'key: work'))
        activity = self.root / 'pfo/act/task/task.md'
        link = quote(os.path.relpath(moved, activity.parent))
        activity.write_text(activity.read_text().replace('#goal-alpha', '#goal-work') + f'\n[Work]({link}#detail)\n')
        (moved.parent / 'alpha').rename(moved.parent / 'work')
        self.assertEqual(content.load(self.root)['goals'][0]['key'], 'work')
        alias = activity.parent / 'repo'
        alias.symlink_to(control.parent, target_is_directory=True)
        activity.write_text(activity.read_text() + '\n[Private alias](repo/goals.md#goal-work)\n')
        with self.assertRaisesRegex(ValueError, 'repo is for local navigation only'):
            content.load(self.root)

    def test_old_named_tree_requires_explicit_selection_without_fallback_or_creation(self):
        self.move('pfo/okr')
        (self.root / 'yap.json').unlink()
        before = self.preserved()
        for operation in (lambda: content.load(self.root), self.run_build):
            with self.assertRaisesRegex(ValueError, 'pfo/asp: expected an existing'):
                operation()
        self.assertEqual(self.preserved(), before)
        self.assertFalse((self.root / 'pfo/asp').exists())
        self.configure('pfo/okr')
        self.assertEqual(content.load(self.root)['goal_source'], 'pfo/okr/goals.md')

    def test_empty_portfolio_does_not_require_objective_directory(self):
        shutil.rmtree(self.root / 'pfo/asp/obj')
        self.write('pfo/asp/goals.md', '---\ntitle: Goals\n---\n')
        self.write('pfo/act/task/task.md', '---\nkind: activity\nkey: task\ntitle: Task\n---\n')
        model = content.load(self.root)
        self.assertEqual(model['goals'], [])
        self.assertEqual(model['key_results'], {})
        self.assertFalse((self.root / 'pfo/asp/obj').exists())

    def test_manifest_validates_structure_without_requiring_source_files(self):
        self.configure('not/provisioned')
        self.assertEqual(instance.manifest(self.root)['sources']['aspirations'], 'not/provisioned')
        # These operations have their existing independent prerequisites.
        self.assertTrue(perspectives.capture(self.root, 'Another activity').is_file())
        self.assertTrue(perspectives.plan(self.root, 'focus', 'save').preview())
        os.chdir(self.root)
        home.render(self.root / '.yap/local/branding-preview')
        self.assertFalse((self.root / 'not').exists())
        for sources in (None, [], 'path', {'aspirations': None}, {'aspirations': 1},
                        {'aspirations': ''}, {'aspirations': ' '}, {'aspirations': '/absolute'},
                        {'aspirations': '../escape'}, {'aspirations': 'a/../b'}, {'aspirations': 'a\0b'}):
            with self.subTest(sources=sources):
                self.write('yap.json', json.dumps({'schema': 1, 'slug': 'example', 'sources': sources}))
                with self.assertRaisesRegex(ValueError, 'yap.json: sources'):
                    instance.manifest(self.root)

    def test_selected_path_errors_precede_discovery_and_hashing(self):
        for source in ('missing/tree', '.yap', '.yap/cfg/source', '.YAP/local/asp', '.git/asp',
                       '.GIT/asp', 'pov', 'POV/focus/asp', 'pov/focus/asp', 'pfo', '.', 'PFO',
                       'pfo/act', 'pfo/ACT/task/asp', 'pfo/nts/sub'):
            with self.subTest(source=source):
                self.configure(source)
                with patch.object(content, 'read', side_effect=AssertionError('read before validation')), \
                     patch.object(build, 'hashes', side_effect=AssertionError('hash before validation')):
                    for operation in (lambda: content.load(self.root), self.run_build):
                        with self.assertRaises(ValueError) as error:
                            operation()
                        self.assertIn(str(Path(source)), str(error.exception))

    def test_protected_case_variants_are_rejected_with_warm_cache(self):
        self.run_build()
        for source in ('.YAP/local/asp', 'POV/asp', 'PFO/ACT/asp', 'pfo/NTS/asp'):
            with self.subTest(source=source):
                self.configure(source)
                with patch.object(build, 'hashes', side_effect=AssertionError('hash before validation')):
                    with self.assertRaisesRegex(ValueError, 'overlaps'):
                        self.run_build()

    def test_objective_keys_matching_local_navigation_names_are_hashed(self):
        for key in ('repo', 'shlf', 'zbox', 'wsp', 'work'):
            with self.subTest(key=key):
                self.write('pfo/asp/goals.md', '---\ntitle: Goals\ntracking:\n'
                           f'  alpha: {{status: active}}\n  {key}: {{status: active}}\n---\n')
                self.write(f'pfo/asp/obj/{key}.md', f'---\nkey: {key}\ntitle: Goal\n---\n')
                kr = self.write(f'pfo/asp/obj/{key}/result.md', '---\nkey: result\ntitle: Result\n'
                                'measure: Evidence\nunit: count\ntarget: 2\ncurrent: 0\n---\n')
                self.run_build()
                kr.write_text(kr.read_text().replace('current: 0', 'current: 1'))
                self.assertEqual(self.run_build()['key_results'][key][0]['current'], 1)
                kr.unlink()
                self.assertNotIn(key, self.run_build()['key_results'])
                unexpected = kr.parent / 'nested'
                unexpected.mkdir()
                with self.assertRaisesRegex(ValueError, 'expected a KR file'):
                    self.run_build()
                unexpected.rmdir()
                kr.parent.rmdir()
                (self.root / f'pfo/asp/obj/{key}.md').unlink()

    def test_cache_refreshes_edits_additions_deletions_and_selection(self):
        self.move('plans/deeper/aspirations')
        self.run_build()
        with patch.object(content, 'load', wraps=content.load) as load:
            self.run_build()
            load.assert_not_called()
        kr = self.root / self.source / 'obj/alpha/result.md'
        kr.write_text(kr.read_text().replace('current: 0', 'current: 1'))
        self.assertEqual(self.run_build()['key_results']['alpha'][0]['current'], 1)
        kr.write_text(kr.read_text().replace('activities: [task]', 'activities: []'))
        self.assertEqual(self.run_build()['goals'][0]['activities'], [])
        second = self.write(self.source + '/obj/alpha/second.md', kr.read_text().replace('key: result', 'key: second'))
        self.assertEqual(len(self.run_build()['key_results']['alpha']), 2)
        kr.unlink()
        self.assertEqual(self.run_build()['key_results']['alpha'][0]['key'], 'second')
        second.unlink()
        self.assertEqual(self.run_build()['key_results'], {})
        objective = self.root / self.source / 'obj/alpha.md'
        objective.write_text(objective.read_text().replace('Original objective prose.', 'Edited objective prose.'))
        self.assertIn('Edited', content.plain(self.run_build()['goals'][0]['blocks']))
        self.move('pfo/okr')
        self.assertEqual(self.run_build()['goal_source'], 'pfo/okr/goals.md')

    def test_invalid_root_control_or_objective_structure_cannot_reuse_warm_cache(self):
        self.move('plans/aspirations')
        self.run_build()
        # Keep identical bytes behind links to ensure content hashes alone cannot pass.
        root = self.root / self.source
        for relative in ('goals.md', 'obj', 'obj/alpha.md', 'obj/alpha', ''):
            with self.subTest(relative=relative):
                path = root / relative
                backup = path.with_name(path.name + '-moved')
                path.rename(backup)
                path.symlink_to(backup, target_is_directory=backup.is_dir())
                for operation in (lambda: content.load(self.root), self.run_build):
                    with self.assertRaisesRegex(ValueError, re.escape(self.source)):
                        operation()
                path.unlink()
                backup.rename(path)
        parent = root.parent
        backup = parent.with_name('plans-moved')
        parent.rename(backup)
        parent.symlink_to(backup, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.run_build()
        parent.unlink()
        backup.rename(parent)
        for relative in ('goals.md', 'obj', ''):
            with self.subTest(non_directory=relative):
                path = root / relative
                backup = path.with_name(path.name + '-moved')
                path.rename(backup)
                path.write_text('not a directory or a control document') if relative != 'goals.md' else path.mkdir()
                with self.assertRaisesRegex(ValueError, re.escape(self.source)):
                    self.run_build()
                path.rmdir() if path.is_dir() else path.unlink()
                backup.rename(path)
        unexpected = root / 'obj/alpha/nested'
        unexpected.mkdir()
        with self.assertRaisesRegex(ValueError, 'expected a KR file'):
            self.run_build()
        unexpected.rmdir()
        # A named pipe must be rejected as source structure, never opened for hashing.
        pipe = root / 'obj/alpha/result.md'
        pipe.unlink()
        os.mkfifo(pipe)
        with self.assertRaisesRegex(ValueError, 'expected a KR file'):
            self.run_build()


if __name__ == '__main__':
    unittest.main()
