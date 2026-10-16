"""Repository starters preserve source meaning, language boundaries and license bytes."""

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from yap import repo_templates as templates


class RepositoryTemplates(unittest.TestCase):
    def inputs(self, languages=('en',), primary='en', **values):
        return dict({'title': 'A project', 'languages': list(languages), 'primary_language': primary}, **values)

    def db_inputs(self, **values):
        return self.inputs(db_metadata=dict(templates.defaults()['db_metadata'], contacts=['maintainer@example.org']), db_confirmed=True, **values)

    def test_general_has_recovery_chain_and_no_inferred_license_or_git(self):
        result = templates.render_template('general', self.inputs())
        self.assertEqual(set(result), {'README.md', 'doc/README.md', 'AGENTS.md', '.gitattributes',
                                      '.gitignore', '.ai4x/BEHAVIOR.md', '.ai4x/CONTEXT.md', '.ai4x/STATE.md'})
        self.assertIn(b'Not selected yet.', result['README.md'])
        self.assertNotIn(b'[LICENSE]', result['README.md'])
        self.assertIn(b'.ai4x/BEHAVIOR.md', result['AGENTS.md'])
        self.assertNotIn(b'CONTEXT.md', result['AGENTS.md'])
        self.assertIn(b'Read CONTEXT.md and STATE.md', result['.ai4x/BEHAVIOR.md'])
        self.assertIn(b'No project-specific build or test results', result['.ai4x/STATE.md'])
        self.assertIn(b'!.env.example', result['.gitignore'])
        self.assertNotIn(b'Gertrud', b''.join(result.values()))

    def test_language_choices_have_reciprocal_matching_language_links(self):
        for languages, primary in [(('de',), 'de'), (('en',), 'en'), (('de', 'en'), 'de'), (('de', 'en'), 'en')]:
            with self.subTest(languages=languages, primary=primary):
                result = templates.render_template('general', self.inputs(languages, primary))
                for language in languages:
                    name = 'README.md' if language == primary else f'README.{language}.md'
                    readme, doc = result[name], result['doc/' + name]
                    self.assertIn(('## Zweck' if language == 'de' else '## Purpose').encode(), readme)
                    self.assertNotIn(('## Purpose' if language == 'de' else '## Zweck').encode(), readme)
                    self.assertIn(f'](doc/{name})'.encode(), readme)
                    self.assertIn(f'](../{name})'.encode(), doc)
                    if len(languages) == 2:
                        other = 'README.md' if language != primary else f'README.{"en" if primary == "de" else "de"}.md'
                        self.assertIn(f']({other})'.encode(), readme)
                        self.assertIn(f']({other})'.encode(), doc)
                    else:
                        self.assertFalse(any(key in result for key in ('README.de.md', 'README.en.md')))
                self.assertIn(f'Primary documentation language: {primary}'.encode(), result['.ai4x/CONTEXT.md'])

    def test_language_and_named_inputs_are_explicit(self):
        for invalid in ({'languages': []}, {'languages': ['fr']}, {'languages': ['en', 'en']},
                        {'primary_language': None}, {'primary_language': 'de'}, {'tilte': 'Typo'},
                        {'purpose': {'de': 'Nicht ausgewählt'}}, {'maintainer': 'Name'},
                        {'title': 'Title\n# Injected heading'}, {'copyright_year': True},
                        {'ai4x_footer': 'yes'}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                templates.render_template('general', self.inputs(**invalid))
        with self.assertRaises(ValueError):
            templates.render_template('general', {'title': 'Missing languages'})

    def test_project_prose_is_escaped_without_becoming_agent_context(self):
        result = templates.render_template('general', self.inputs(
            title='A [title](javascript:evil) <b>& {{title}}',
            purpose={'en': '<script>alert(1)</script>\n# Heading\n![image](https://example.org)'},
            maintainer={'en': 'A *person*'}))
        readme = result['README.md'].decode()
        self.assertNotIn('<script>', readme)
        self.assertIn('&lt;script&gt;', readme)
        self.assertIn('\\# Heading', readme)
        self.assertIn('\\!\\[image\\]', readme)
        self.assertNotIn('{{title}}', readme)
        self.assertNotIn(b'alert', result['.ai4x/CONTEXT.md'])

    def test_generic_defaults_are_independent_and_can_be_changed(self):
        result = templates.render_template('general', self.inputs())
        self.assertIn('© 2026 Project contributors'.encode(), result['README.md'])
        self.assertIn(b'Curated by', result['README.md'])
        customized = templates.render_template('general', self.inputs(
            copyright_holder='Another owner', copyright_year=2027, ai4x_footer=False))
        self.assertIn('© 2027 Another owner'.encode(), customized['README.md'])
        self.assertNotIn(b'git.tech.rz.db.de', customized['README.md'])
        self.assertNotIn(b'Curated by', customized['README.md'])
        first = templates.defaults()
        first['db_metadata']['contacts'].append('Changed')
        self.assertEqual(len(templates.defaults()['db_metadata']['contacts']), 0)

    def test_copyright_profile_cannot_inject_markdown_or_unsafe_scheme(self):
        for url in ('javascript:alert(1)', 'https://example.org>\nInjected', 'https://user:secret@example.org',
                    'https://:secret@example.org', 'https://example.org/"x', 'https://example.org/has space'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                templates.render_template('general', self.inputs(copyright_url=url))
        result = templates.render_template('general', self.inputs(copyright_url='https://example.org/a(b)'))
        self.assertIn(b'](<https://example.org/a(b)>)', result['README.md'])

    def test_db_requires_complete_confirmed_supported_metadata(self):
        for confirmation in (None, False, 'yes', 1):
            with self.subTest(confirmation=confirmation), self.assertRaises(ValueError):
                templates.render_template('db-gitlab', self.inputs(
                    db_metadata=templates.defaults()['db_metadata'], db_confirmed=confirmation))
        for field, value in [('version', 'v4'), ('license', 'MIT'), ('contacts', []), ('custom', {}),
                             ('confidentiality', ''), ('protected-branches', 'trunk')]:
            inputs = self.db_inputs()
            inputs['db_metadata'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                templates.render_template('db-gitlab', inputs)
        inputs = self.db_inputs()
        del inputs['db_metadata']['reference-ids']
        with self.assertRaises(ValueError):
            templates.render_template('db-gitlab', inputs)
        with self.assertRaises(ValueError):
            templates.render_template('general', self.db_inputs())

    def test_db_preserves_license_and_serializes_metadata_as_data(self):
        inputs = self.db_inputs()
        contact = 'name: "quoted" # literal {{contacts}}'
        inputs['db_metadata']['contacts'] = [contact]
        inputs['db_metadata']['confidentiality'] = 'custom: level'
        inputs['db_metadata']['custom']['confidentiality'] = 'other: level'
        result = templates.render_template('db-gitlab', inputs)
        self.assertEqual(hashlib.sha256(result['LICENSE']).hexdigest(),
                         '4ce4bb9e7085ad333f4e28b17ec1f97228c37d6e65eedeecb6c7229e2c08ccc7')
        metadata = result['scm-info.yaml'].decode()
        self.assertIn('version: v3\nlicense: LicenseRef-DBISL\n', metadata)
        contacts = next(line.split(': ', 1)[1] for line in metadata.splitlines() if line.startswith('contacts:'))
        self.assertEqual(json.loads(contacts), [contact])
        self.assertIn('confidentiality: "custom: level"', metadata)
        self.assertIn('  confidentiality: "other: level"', metadata)
        self.assertIn(b'LICENSE -text\n', result['.gitattributes'])
        self.assertIn(b'See [LICENSE](./LICENSE).', result['README.md'])
        self.assertIn(b'confirmed DB repository metadata', result['.ai4x/CONTEXT.md'])
        with self.assertRaises(ValueError):
            templates.render_template('db-gitlab', dict(inputs, license_text='Changed'))

    def test_explicit_general_license_is_preserved_without_selecting_one(self):
        license_text = 'License supplied by user\n\nExact ending:  '
        result = templates.render_template('general', self.inputs(license_text=license_text))
        self.assertEqual(result['LICENSE'], license_text.encode())
        self.assertIn(b'See [LICENSE](./LICENSE).', result['README.md'])
        self.assertIn(b'LICENSE -text', result['.gitattributes'])
        self.assertNotIn('scm-info.yaml', result)

    def test_renderer_is_deterministic_and_does_not_mutate_inputs(self):
        inputs = self.db_inputs()
        before = json.dumps(inputs, sort_keys=True)
        first = templates.render_template('db-gitlab', inputs)
        self.assertEqual(first, templates.render_template('db-gitlab', inputs))
        self.assertEqual(json.dumps(inputs, sort_keys=True), before)
        self.assertEqual(list(first), sorted(first))
        self.assertTrue(all(isinstance(value, bytes) for value in first.values()))

    def test_template_paths_reject_links_git_metadata_and_executable_hooks(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary).resolve() / 'repo'
            shutil.copytree(templates.TEMPLATES, source)
            with patch.object(templates, 'TEMPLATES', source):
                for relative in ('base/.git', 'base/nested/.git', 'base/hooks/pre-commit'):
                    path = source / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('Do not copy')
                    with self.subTest(relative=relative), self.assertRaises(ValueError):
                        templates.render_template('general', self.inputs())
                    path.unlink()
                    if path.parent.name == 'hooks':
                        path.parent.rmdir()
                link = source / 'base/link'
                link.symlink_to(source / 'base/AGENTS.md')
                with self.assertRaises(ValueError):
                    templates.render_template('general', self.inputs())
                link.unlink()
                executable = source / 'base/run.sh'
                executable.write_text('#!/bin/sh\nexit 0\n')
                executable.chmod(0o755)
                with self.assertRaises(ValueError):
                    templates.render_template('general', self.inputs())

    def test_unresolved_template_fields_fail_before_any_materialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary).resolve() / 'repo'
            shutil.copytree(templates.TEMPLATES, source)
            (source / 'base/README.en.md').write_text('# {{unknown}}\n')
            with patch.object(templates, 'TEMPLATES', source), self.assertRaisesRegex(ValueError, 'unresolved placeholder'):
                templates.render_template('general', self.inputs())

    def test_footer_uses_the_same_safe_source_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary).resolve() / 'repo'
            shutil.copytree(templates.TEMPLATES, source)
            footer = source / 'ai4x-footer.html'
            original = footer.read_bytes()
            footer.unlink()
            footer.symlink_to(source / 'base/AGENTS.md')
            with patch.object(templates, 'TEMPLATES', source):
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    templates.render_template('general', self.inputs())
                footer.unlink()
                footer.write_bytes(original)
                footer.chmod(0o755)
                with self.assertRaisesRegex(ValueError, 'nonexecutable regular file'):
                    templates.render_template('general', self.inputs())
                footer.chmod(0o644)
                footer.unlink()
                footer.mkdir()
                with self.assertRaisesRegex(ValueError, 'nonexecutable regular file'):
                    templates.render_template('general', self.inputs())
            # The profile's parent is also within the template source boundary.
            gitlab = source / 'gitlab'
            gitlab.rename(source / 'other')
            gitlab.symlink_to(source / 'other', target_is_directory=True)
            with patch.object(templates, 'TEMPLATES', source), self.assertRaisesRegex(ValueError, 'symlink'):
                templates.render_template('db-gitlab', self.db_inputs(ai4x_footer=False))

    def test_symlink_above_template_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / 'real/repo'
            shutil.copytree(templates.TEMPLATES, source)
            (root / 'alias').symlink_to(root / 'real', target_is_directory=True)
            with patch.object(templates, 'TEMPLATES', root / 'alias/repo'):
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    templates.render_template('general', self.inputs())

    def test_effective_inputs_expose_exact_defaults_without_confirming_db(self):
        inputs = self.inputs(copyright_holder='Another owner')
        effective = templates.resolved_inputs(inputs)
        self.assertEqual(effective['copyright_url'], '')
        self.assertEqual(effective['copyright_year'], 2026)
        self.assertEqual(effective['purpose'], {'en': 'Open.'})
        self.assertEqual(effective['maintainer'], {'en': 'Open.'})
        self.assertNotIn('db_metadata', effective)
        self.assertNotIn('db_confirmed', effective)
        self.assertNotIn('copyright_url', inputs)


if __name__ == '__main__':
    unittest.main()
