"""Live hierarchy navigation and portable publication boundaries."""

from fixtures import source_text

import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
from html.parser import HTMLParser

from yap import content, files, home, perspectives as p, perspective_html


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.targets = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.targets.extend(value for key, value in attrs if key in {'href', 'src'})


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap live workspace ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for name, text in {
            'pfo/act/act.md': '---\ntitle: Activities\n---\n',
            'pfo/act/area/area.md': '---\ntitle: Area\n---\n',
            'pfo/act/area/task/task.md': '---\ntitle: Task\n---\n\n[Attachment](res/note.txt)\n',
            'pfo/act/area/task/res/note.txt': 'A resource.\n',
            'pfo/asp/goals.md': '---\ntitle: Goals\n---\n',
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source_text(name, text))
        (self.root / 'pfo/asp/obj').mkdir()
        self.view = self.root / 'pov/focus'
        self.view.mkdir(parents=True)
        self.link('Task', 'pfo/act/area/task')
        self.link('Attachment', 'pfo/act/area/task/res/note.txt')
        p.apply(p.plan(self.root, 'focus', 'save'))

    def link(self, name, target):
        (self.view / name).symlink_to(os.path.relpath(self.root / target, self.view))

    def test_nested_source_identity_and_restore_preserve_originals(self):
        entries = p.catalog(self.root)
        self.assertEqual(set(entries), {'area', 'area--task'})
        saved = json.loads((self.view / p.DEFINITION).read_text())
        self.assertEqual({item['target']['entry'] for item in saved['entries']}, {'area--task'})
        before = {path: path.read_bytes() for path in files.source_files(self.root / 'pfo')}
        (self.view / 'Task').unlink()
        p.apply(p.plan(self.root, 'focus', 'restore', choose=True))
        self.assertEqual((self.view / 'Task').resolve(), entries['area--task']['folder'])
        self.assertEqual(before, {path: path.read_bytes() for path in files.source_files(self.root / 'pfo')})

    def test_published_perspectives_link_only_inside_portable_site(self):
        model = content.load(self.root)
        site = self.root / '.yap/local/site'
        output = site / 'views/perspectives'
        perspective_html.render(self.root, destination=output, model=model)
        html = (output / 'index.html').read_text()
        self.assertIn('Activity - Details.pdf#nameddest=act-area--task', html)
        self.assertIn('../../res/area--task/note.txt', html)
        for target in Links(html).targets:
            address = urlsplit(target)
            if address.scheme or address.netloc:
                self.assertEqual(target, 'https://github.com/normenmueller/ai4X')
                continue  # The shared footer intentionally links to its curator.
            path = unquote(address.path)
            self.assertTrue((output / path).resolve().is_relative_to(site))
        self.assertNotIn(str(self.root), html)
        self.assertNotIn('pfo/act', html)

    def test_root_entry_keeps_portable_site_and_external_links_intact(self):
        site = self.root / '.yap/local/site'
        site.mkdir(parents=True)
        original = '<a href="views/perspectives/index.html">Views</a><img src="acc/img/logo.svg"><a href="https://example.org">Web</a><a href="#help">Help</a>'
        (site / 'yap.html').write_text(original)
        home.root_entry(site, self.root / 'yap.html')
        self.assertEqual(Links((self.root / 'yap.html').read_text()).targets,
                         ['.yap/local/site/views/perspectives/index.html', '.yap/local/site/acc/img/logo.svg',
                          'https://example.org', '#help'])
        self.assertEqual((site / 'yap.html').read_text(), original)

    def test_durable_repo_binding_is_checkout_relative_and_not_authored(self):
        config = self.root / '.yap/cfg/machine.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'links': {'area--task': {'repo': '.'}}}))
        model = content.load(self.root)
        plan, warnings = files.link_plan(self.root)
        self.assertFalse(warnings)
        files.sync_links(plan)
        self.assertEqual((self.root / 'pfo/act/area/task/repo').resolve(), self.root)
        self.assertFalse(any('work' in node['meta'] for node in model['nodes']))
        config.write_text(json.dumps({'links': {'unknown': {'repo': '.'}}}))
        with self.assertRaisesRegex(ValueError, 'unknown activities'):
            files.link_plan(self.root)
        source = self.root / 'pfo/act/area/task/task.md'
        source.write_text(source_text('pfo/act/area/task/task.md', '---\ntitle: Task\nwork: /tmp\n---\n'))
        with self.assertRaisesRegex(ValueError, 'machine.json'):
            content.load(self.root)
