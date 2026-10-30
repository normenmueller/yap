"""Illustrative display values stay explicit, escaped and separate from navigation."""
from contextlib import contextmanager
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile
import unittest

from yap import card_inputs, home, instance


@contextmanager
def selected(root):
    previous = Path.cwd()
    os.chdir(root)
    try:
        yield
    finally:
        os.chdir(previous)


class Controls(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.in_link = False
        self.nested_controls = []
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == 'a':
            self.in_link = True
            if fields.get('class', '').startswith('tile'):
                self.links.append(fields['href'])
        elif tag in {'details', 'summary', 'blockquote'} and self.in_link:
            self.nested_controls.append(tag)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.in_link = False


class CardInputTests(unittest.TestCase):
    def test_decoder_owns_paragraphs_without_changing_authored_text(self):
        paragraphs = ['  Hello!  ', 'First line\nSecond line', 'Ein weiterer Absatz.']
        source = {'activity': {'need': {'paragraphs': paragraphs, 'sender': 'Example owner'},
                               'growth_label': 'v0.42.7'}}
        cards = card_inputs.decode(source)
        paragraphs[0] = 'Changed later'
        paragraphs.append('Another mutable value')
        self.assertEqual(cards.activity.need, card_inputs.Need(
            ('  Hello!  ', 'First line\nSecond line', 'Ein weiterer Absatz.'), 'Example owner'))
        self.assertEqual(cards.activity.growth_label, 'v0.42.7')
        self.assertEqual(cards.performance, card_inputs.Card())

    def test_invalid_values_fail_at_the_manifest_boundary_without_rewriting(self):
        invalid = [None, [], '', {'unknown': {}}, {'activity': None},
                   {'activity': []}, {'activity': {'growth': 'v1'}},
                   *({'activity': {'growth_label': value}} for value in (None, True, 1, [], '', '  ')),
                   {'performance': {'need': None}}, {'activity': {'need': {}}},
                   {'activity': {'need': {'text': 'A question'}}},
                   *({'activity': {'need': {'paragraphs': value}}}
                     for value in (None, 'Text', [], [False], [1], [''], ['  '], [{}])),
                   {'activity': {'need': {'paragraphs': ['A question'], 'sender': ''}}},
                   {'activity': {'need': {'paragraphs': ['A question'], 'recipient': 1}}},
                   {'activity': {'need': {'paragraphs': ['A question'], 'html': '<p>Text</p>'}}}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'yap.json'
            for value in invalid:
                with self.subTest(value=value):
                    path.write_text(json.dumps({'schema': 1, 'slug': 'example', 'illustrative_cards': value}))
                    before = path.read_bytes()
                    with self.assertRaisesRegex(ValueError, 'yap.json: illustrative_cards'):
                        instance.manifest(root)
                    self.assertEqual(path.read_bytes(), before)

    def test_cards_escape_distinct_values_keep_paragraphs_and_separate_controls(self):
        manifest = {'schema': 1, 'slug': 'example', 'illustrative_cards': {
            'activity': {'need': {'paragraphs': ['Hello <helper>!', 'A & B\nC', '</p><script>alert(1)</script>'],
                                  'sender': 'Owner <one>', 'recipient': 'Helper "two"'},
                         'growth_label': 'v0.42.7 <authored>'},
            'performance': {'need': {'paragraphs': ['Was habe ich vorangebracht?']},
                            'growth_label': 'v0.3.2'}}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'yap.json').write_text(json.dumps(manifest))
            with selected(root):
                html = home._cards('../../')
                local = home._cards()
            controls = Controls(html)
            self.assertEqual(controls.nested_controls, [])
            self.assertEqual(controls.links, ['../../views/activity-board/index.html', '../../views/mPM-ish/index.html'])
            self.assertEqual(Controls(local).links, ['views/activity-board/index.html', 'views/mPM-ish/index.html'])
            self.assertEqual(html.count('<details class="yapic-prompt">'), 2)
            self.assertNotIn('<details class="yapic-prompt" open', html)
            self.assertIn('<h2>Aktivitäten</h2>', html)
            self.assertIn('<h2>Performance</h2>', html)
            self.assertIn('<span>01</span>', html)
            self.assertIn('<span>02</span>', html)
            self.assertEqual(html.count('class="arrow"'), 2)
            self.assertIn('<p>Hello &lt;helper&gt;!</p><p>A &amp; B\nC</p>', html)
            self.assertIn('&lt;/p&gt;&lt;script&gt;alert(1)&lt;/script&gt;', html)
            self.assertNotIn('<script>', html)
            self.assertIn('Owner &lt;one&gt;', html)
            self.assertIn('Helper &quot;two&quot;', html)
            activity, performance = html.split('<div class="yapic performance">')
            self.assertIn('v0.42.7 &lt;authored&gt;', activity)
            self.assertNotIn('v0.3.2', activity)
            self.assertIn('v0.3.2', performance)
            self.assertNotIn('prompt-byline', performance)

    def test_optional_values_do_not_borrow_branding_or_private_settings(self):
        for fields in ({}, {'activity': {}}, {'activity': {'growth_label': 'v0.1.2'}},
                       {'performance': {'need': {'paragraphs': ['A question']}}}):
            with self.subTest(fields=fields), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                    'branding': {'author': 'PRIVATE-AUTHOR', 'assistant': 'PRIVATE-HELPER'},
                    'illustrative_cards': fields}))
                private = root / '.yap/cfg/session.md'
                private.parent.mkdir(parents=True)
                private.write_text('PRIVATE-NAVIGATION')
                with selected(root):
                    html = home._cards()
                self.assertNotIn('PRIVATE-', html)
                self.assertNotIn('prompt-byline', html)
                self.assertEqual(html.count('<details'), int('need' in fields.get('performance', {})))
                self.assertEqual(html.count('class="tile-growth"'), int('growth_label' in fields.get('activity', {})))

    def test_invalid_input_preserves_existing_pages_and_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / 'yap.json'
            manifest.write_text(json.dumps({'schema': 1, 'slug': 'example'}))
            site = root / 'site'
            with selected(root):
                home.render(site)
                before = {path.relative_to(site): path.read_bytes() for path in site.rglob('*') if path.is_file()}
                manifest.write_text(json.dumps({'schema': 1, 'slug': 'example', 'illustrative_cards': {
                    'performance': {'need': {'paragraphs': [42]}}}}))
                with self.assertRaisesRegex(ValueError, 'illustrative_cards.performance.need.paragraphs'):
                    home.render(site)
                self.assertEqual(before, {path.relative_to(site): path.read_bytes()
                                         for path in site.rglob('*') if path.is_file()})
