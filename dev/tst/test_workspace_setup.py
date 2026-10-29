"""Local provisioning preserves user files, Git boundaries and private bindings."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yap import workspace_setup as setup


class WorkspaceSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap setup ')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / 'portfolio'
        self.root.mkdir()
        self.target = self.base / 'new project'
        self.files = {'README.md': b'# New\n', '.ai4x/STATE.md': b'Initial state.\n', 'doc/README.md': b'Documents.\n'}
        self.config = self.root / '.yap/cfg/machine.json'
        self.folder = self.root / 'pfo/act/task'
        self.folder.mkdir(parents=True)
        (self.folder / 'task.md').write_text('---\nkind: activity\nkey: task\ntitle: Task\n---\n')

    def plan(self, **kwargs):
        return setup.plan(self.root, 'create', self.target, **kwargs)

    def configure(self, settings):
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps(settings))

    def source_bindings(self, values):
        (self.folder / 'task.md').write_text('---\nkind: activity\nkey: task\ntitle: Task\n# Keep this comment.\nwsp: ' + json.dumps(values) + '\n---\n\nAuthored body.\n')

    def test_preview_and_template_only_creation_are_independent_of_git_and_capture(self):
        proposal = self.plan(files=self.files)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.config.exists())
        self.assertIn('Datei schreiben', proposal.preview('de'))
        result = setup.apply(proposal)
        self.assertTrue(result.success, result.error)
        self.assertEqual((self.target / 'README.md').read_bytes(), self.files['README.md'])
        self.assertFalse((self.target / '.git').exists())
        self.assertFalse(self.config.exists())

    def test_plain_directory_and_git_only_create_no_hidden_template(self):
        self.assertTrue(setup.apply(self.plan()).success)
        self.assertEqual(list(self.target.iterdir()), [])
        result = setup.apply(self.plan(resume=True, initialize_git=True))
        self.assertTrue(result.success, result.error)
        self.assertEqual({p.name for p in self.target.iterdir()}, {'.git'})
        self.assertEqual(setup._git(self.target, 'symbolic-ref', '--short', 'HEAD').stdout.strip(), 'trunk')

    def test_existing_destination_conflicts_and_stale_plan_changes_nothing(self):
        proposal = self.plan(files=self.files)
        self.target.mkdir()
        (self.target / 'user.txt').write_text('User material')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.plan(files=self.files)
        result = setup.apply(proposal)
        self.assertFalse(result.success)
        self.assertEqual(result.completed, [])
        self.assertEqual((self.target / 'user.txt').read_text(), 'User material')
        self.assertFalse((self.target / 'README.md').exists())

    def test_partial_git_failure_preserves_files_and_requires_explicit_verified_resume(self):
        proposal = self.plan(files=self.files, initialize_git=True, remote_url='ssh://example.invalid/project.git')
        original = setup._git
        def fail_init(target, *args, **kwargs):
            if args[0] == 'init':
                raise OSError('simulated init failure')
            return original(target, *args, **kwargs)
        with patch.object(setup, '_git', side_effect=fail_init):
            result = setup.apply(proposal)
        self.assertFalse(result.success)
        self.assertIn('write README.md', result.completed)
        self.assertEqual(result.pending, ['initialize Git', 'configure remote'])
        with self.assertRaises(ValueError):
            self.plan(files=self.files, initialize_git=True)
        unchanged = (self.target / 'README.md').stat().st_mtime_ns
        retry = self.plan(files=self.files, resume=True, initialize_git=True,
                          remote_url='ssh://example.invalid/project.git')
        self.assertNotIn('write README.md', retry.steps)
        self.assertTrue(setup.apply(retry).success)
        self.assertEqual((self.target / 'README.md').stat().st_mtime_ns, unchanged)
        self.assertEqual(setup._git(self.target, 'config', 'remote.origin.fetch').stdout.strip(),
                         '+refs/heads/*:refs/remotes/origin/*')
        self.assertNotEqual(setup._git(self.target, 'rev-parse', '--verify', 'HEAD', check=False).returncode, 0)

    def test_resume_rejects_changed_unexpected_files_directories_and_symlinks(self):
        self.assertTrue(setup.apply(self.plan(files=self.files)).success)
        for name, kind in [('README.md', 'changed'), ('extra', 'file'), ('empty', 'directory'), ('link', 'symlink')]:
            with self.subTest(kind=kind):
                path = self.target / name
                if kind in {'file', 'changed'}:
                    path.write_text('Unexpected')
                elif kind == 'directory':
                    path.mkdir()
                else:
                    path.symlink_to(self.root, target_is_directory=True)
                with self.assertRaises(ValueError):
                    self.plan(files=self.files, resume=True)
                if kind == 'directory':
                    path.rmdir()
                else:
                    path.unlink()
                if kind == 'changed':
                    path.write_bytes(self.files[name])

    def test_unsafe_template_paths_fail_before_creation(self):
        for name in ['../escape', '/absolute', 'C:/escape', 'a\\b', 'a\nb', '.git/config', 'hooks/post-checkout', 'a/../b']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.plan(files={name: b'no'})
        for files in [{'a': b'1', 'a/b': b'2'}, {'A/x': b'1', 'a/y': b'2'}]:
            with self.assertRaises(ValueError):
                self.plan(files=files)
        self.assertFalse(self.target.exists())

    def test_ancestor_repository_and_worktree_are_not_reinitialized(self):
        setup._git(self.base, 'init', '--template=', '--initial-branch=trunk')
        with self.assertRaisesRegex(ValueError, 'inside an existing'):
            self.plan(initialize_git=True)
        self.assertFalse(self.target.exists())
        # A .git file is the critical worktree/submodule redirection boundary.
        other = self.base / 'linked'
        other.mkdir()
        (other / '.git').write_text('gitdir: /unrelated/metadata\n')
        with self.assertRaisesRegex(ValueError, 'worktrees'):
            setup.plan(self.root, 'create', other, initialize_git=True, resume=True)

    def test_git_environment_and_hook_templates_are_isolated(self):
        template = self.base / 'evil-template'
        (template / 'hooks').mkdir(parents=True)
        (template / 'hooks/post-checkout').write_text('#!/bin/sh\nexit 1\n')
        (template / 'hooks/post-checkout').chmod(0o755)
        foreign = self.base / 'foreign'
        foreign.mkdir()
        setup._git(foreign, 'init', '--template=', '--initial-branch=other')
        before = (foreign / '.git/config').read_bytes()
        gitconfig = self.base / 'global-config'
        gitconfig.write_text('[init]\n templateDir = ' + str(template) + '\n')
        overrides = {'GIT_DIR': str(foreign / '.git'), 'GIT_WORK_TREE': str(foreign),
                     'GIT_OBJECT_DIRECTORY': str(foreign / '.git/objects'),
                     'GIT_COMMON_DIR': str(foreign / '.git'), 'GIT_TEMPLATE_DIR': str(template),
                     'GIT_CONFIG_GLOBAL': str(gitconfig), 'GIT_CONFIG_COUNT': '1',
                     'GIT_CONFIG_KEY_0': 'core.worktree', 'GIT_CONFIG_VALUE_0': str(foreign)}
        with patch.dict(os.environ, overrides):
            result = setup.apply(self.plan(initialize_git=True))
        self.assertTrue(result.success, result.error)
        self.assertFalse((self.target / '.git/hooks').exists())
        self.assertEqual((foreign / '.git/config').read_bytes(), before)
        self.assertEqual(setup._git(foreign, 'symbolic-ref', '--short', 'HEAD').stdout.strip(), 'other')
        self.assertEqual(gitconfig.read_text(), '[init]\n templateDir = ' + str(template) + '\n')

    def test_remote_identical_is_unchanged_and_conflict_stops_before_writes(self):
        result = setup.apply(self.plan(initialize_git=True, remote_url='ssh://example.invalid/one'))
        self.assertTrue(result.success, result.error)
        before = (self.target / '.git/config').read_bytes()
        retry = self.plan(resume=True, initialize_git=True, remote_url='ssh://example.invalid/one')
        self.assertEqual(retry.steps, ())
        self.assertTrue(setup.apply(retry).success)
        self.assertEqual((self.target / '.git/config').read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'different URL'):
            self.plan(resume=True, initialize_git=True, remote_url='ssh://example.invalid/two')

    def test_resume_checks_existing_branch_and_detects_head_changes_after_planning(self):
        self.assertTrue(setup.apply(self.plan(initialize_git=True)).success)
        proposal = self.plan(resume=True, initialize_git=True, remote_url='ssh://example.invalid/project')
        setup._git(self.target, 'symbolic-ref', 'HEAD', 'refs/heads/main')
        result = setup.apply(proposal)
        self.assertFalse(result.success)
        self.assertIn('existing branch', result.error)
        self.assertEqual(setup._git(self.target, 'remote').stdout, '')
        with self.assertRaisesRegex(ValueError, 'existing branch'):
            self.plan(resume=True, initialize_git=True)
        # Remote-only setup does not select or rename an existing branch.
        result = setup.apply(self.plan(resume=True, remote_url='ssh://example.invalid/project'))
        self.assertTrue(result.success, result.error)
        self.assertEqual(setup._git(self.target, 'symbolic-ref', '--short', 'HEAD').stdout.strip(), 'main')

    def test_binding_failure_leaves_repository_for_explicit_resume(self):
        proposal = self.plan(files=self.files, binding_key='task', link_name='code')
        with patch.object(setup, '_save_binding', side_effect=OSError('simulated settings failure')):
            result = setup.apply(proposal)
        self.assertFalse(result.success)
        self.assertEqual(result.pending, ['save binding', 'update navigation'])
        self.assertEqual((self.target / 'README.md').read_bytes(), self.files['README.md'])
        self.assertTrue((self.folder / 'task.md').is_file())
        self.assertFalse(self.config.exists())
        result = setup.apply(self.plan(files=self.files, binding_key='task', link_name='code', resume=True))
        self.assertTrue(result.success, result.error)
        self.assertEqual((self.folder / 'wsp/code').resolve(), self.target)

    def test_shared_template_plan_owns_db_branch_consistency(self):
        inputs = {'db_metadata': {'protected-branches': ['trunk']}}
        with patch('yap.repo_templates.render_template', return_value=self.files):
            with self.assertRaisesRegex(ValueError, 'confirmed DB'):
                self.plan(template_profile='db-gitlab', template_inputs=inputs,
                          initialize_git=True, branch='main')
        self.assertFalse(self.target.exists())

    def test_attach_changes_only_selected_binding_and_navigation(self):
        self.target.mkdir()
        (self.target / 'real.txt').write_text('Preserve')
        unrelated = self.folder.parent / 'other'
        unrelated.mkdir()
        (unrelated / 'other.md').write_text('---\nkind: activity\nkey: other\ntitle: Other\nwsp: {code: broken}\n---\n')
        (unrelated / 'wsp').mkdir()
        (unrelated / 'wsp/code').symlink_to(self.base / 'missing')
        self.source_bindings({'materials': 'also missing'})
        self.configure({'other_setting': {'keep': True}})
        original_config = self.config.read_bytes()
        result = setup.apply(setup.plan(self.root, 'attach', self.target, binding_key='task', link_name='code'))
        self.assertTrue(result.success, result.error)
        self.assertEqual(list(p.name for p in self.target.iterdir()), ['real.txt'])
        self.assertEqual((self.target / 'real.txt').read_text(), 'Preserve')
        self.assertEqual(self.config.read_bytes(), original_config)
        self.assertEqual(os.readlink(unrelated / 'wsp/code'), str(self.base / 'missing'))
        self.assertEqual((self.folder / 'wsp/code').resolve(), self.target)
        self.assertFalse((self.folder / 'wsp/materials').exists())
        self.assertIn('also missing', (self.folder / 'task.md').read_text())
        with self.assertRaises(ValueError):
            setup.plan(self.root, 'attach', self.target, initialize_git=True)

    def test_binding_conflicts_and_concurrent_source_prevent_creation(self):
        for value in [None, '', str(self.base / 'elsewhere')]:
            self.source_bindings({'code': value})
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.plan(binding_key='task', link_name='code')
            self.assertFalse(self.target.exists())
        self.source_bindings({})
        proposal = self.plan(binding_key='task', link_name='code')
        source = self.folder / 'task.md'
        source.write_text(source.read_text() + '\nConcurrent authored change.\n')
        result = setup.apply(proposal)
        self.assertFalse(result.success)
        self.assertFalse(self.target.exists())
        self.assertIn('Concurrent authored change.', source.read_text())

    def test_identical_relative_binding_retains_authored_source_bytes(self):
        self.target.mkdir()
        self.source_bindings({'code': '../new project'})
        source = self.folder / 'task.md'
        original = source.read_bytes()
        result = setup.apply(setup.plan(self.root, 'attach', self.target, binding_key='task', link_name='code'))
        self.assertTrue(result.success, result.error)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual((self.folder / 'wsp/code').resolve(), self.target)

    def test_scoped_navigation_updates_only_selected_name_for_modules(self):
        self.target.mkdir()
        self.source_bindings({'code': str(self.target), 'materials': 'untouched'})
        (self.folder / 'wsp').mkdir()
        (self.folder / 'wsp/materials').symlink_to(self.base / 'elsewhere')
        module = self.folder / 'mod/child'
        module.mkdir(parents=True)
        (module / 'child.md').write_text('---\nkind: activity\nkey: child\ntitle: Child\n---\n')
        result = setup.apply(setup.plan(self.root, 'attach', self.target, binding_key='task', link_name='code'))
        self.assertTrue(result.success, result.error)
        self.assertEqual((self.folder / 'wsp/code').resolve(), self.target)
        self.assertEqual(os.readlink(self.folder / 'wsp/materials'), str(self.base / 'elsewhere'))
        self.assertFalse((module / 'wsp').exists())

    def test_symlink_config_parent_target_and_self_binding_are_rejected(self):
        self.target.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            setup.plan(self.root, 'attach', self.target)
        self.target.unlink()
        self.target.mkdir()
        (self.root / '.yap').mkdir()
        (self.root / '.yap/cfg').symlink_to(self.base)
        with self.assertRaises(ValueError):
            setup.plan(self.root, 'attach', self.target, binding_key='task', link_name='code')
        (self.root / '.yap/cfg').unlink()
        with self.assertRaisesRegex(ValueError, 'cycle'):
            setup.plan(self.root, 'attach', self.root, binding_key='task', link_name='code')

    def test_invalid_git_choices_fail_before_creation(self):
        for kwargs in [{'branch': '-bad', 'initialize_git': True},
                       {'branch': 'bad branch', 'initialize_git': True},
                       {'remote_url': 'ssh://example.invalid/x'},
                       {'remote_url': 'bad\nurl', 'initialize_git': True},
                       {'remote_url': 'url', 'remote_name': '../bad', 'initialize_git': True}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.plan(**kwargs)
        self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
