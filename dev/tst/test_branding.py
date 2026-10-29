"""Instance choices preserve application identity, copy and offline navigation."""
import base64
from contextlib import contextmanager
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit

from yap import footer, home, navigation, perspective_html, board, activity_map, dgraph, views, content


@contextmanager
def selected(root):
    previous = Path.cwd()
    os.chdir(root)
    try:
        yield
    finally:
        os.chdir(previous)


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.images = []
        self.text = []
        self.in_footer = False
        self.footer_text = []
        self.footer_links = []
        self.footer_anchors = []
        self.current_footer_anchor = None
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == 'footer':
            self.in_footer = True
        if tag == 'a':
            self.links.append(fields.get('href', ''))
            if self.in_footer:
                self.footer_links.append(fields.get('href', ''))
                self.current_footer_anchor = {'href': fields.get('href', ''), 'text': []}
                self.footer_anchors.append(self.current_footer_anchor)
        if tag == 'img':
            self.images.append(fields)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.current_footer_anchor = None
        if tag == 'footer':
            self.in_footer = False

    def handle_data(self, data):
        self.text.append(data)
        if self.in_footer:
            self.footer_text.append(data)
            if self.current_footer_anchor is not None:
                self.current_footer_anchor['text'].append(data)


class BrandingTests(unittest.TestCase):
    def test_instance_choices_do_not_override_product_copy_or_logo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            custom_logo = '<svg xmlns="http://www.w3.org/2000/svg" aria-label="Example portfolio"/>'
            (root / 'assets/yap-logo.svg').write_text(custom_logo)
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example', 'branding': {
                'title': 'Example <portfolio>.', 'tagline': 'Example activities',
                'logo': 'assets/yap-logo.svg', 'favicon': 'assets/yap-logo.svg',
                'author': 'Example <author>', 'footer': 'Maintained by Example <team>'}}))
            with selected(root):
                home.render(root / 'site')
                for view in ('home', 'board', 'map', 'graph', 'performance'):
                    self.assertIn('Example &lt;portfolio&gt;.', navigation.head(view))
                self.assertIn('Example activities', navigation.head('home'))
                self.assertIn('Über yap.', navigation.head('about'))
                self.assertNotIn('Über Example', navigation.render('about'))
            site = root / 'site'
            homepage = (site / 'example.html').read_text()
            self.assertIn('Vorhaben bewegen. Wirkung sichtbar machen.', homepage)
            self.assertIn('yap dein yapic mit mir!', homepage)
            self.assertIn('Example activities', homepage)
            self.assertIn('Example &lt;portfolio&gt;<span>.</span>', homepage)
            self.assertIn('Dein Wirkungsfeld umfasst deine Vorhaben, Ziele und Beiträge.', homepage)
            self.assertNotIn('class="tiles"', homepage)
            collection = (site / 'views/yapics/index.html').read_text()
            self.assertIn('Arbeiten. Wirken. Nachlesen.', collection)
            self.assertIn('Dein Beitrag. An jedem Heute.', collection)
            self.assertIn('Seeds of Insight. Tailored to your needs.', collection)
            about = (site / 'about.html').read_text()
            self.assertIn('Kleine Spuren, die etwas erzählen.', about)
            self.assertIn('yap dein yapic mit mir!', about)
            self.assertIn('<textarea', homepage)
            self.assertIn('type="button" disabled', homepage)
            self.assertNotIn('<form', homepage)
            self.assertNotIn('class="preview-badge"', homepage)
            self.assertNotIn('class="yap-navigation"', homepage)
            self.assertIn('class="yap-navigation"', collection)
            self.assertIn('Teil des Produktzielbilds', about)
            product_logo = next(image for image in Page(about).images if image['alt'] == 'yap.')
            self.assertEqual(base64.b64decode(product_logo['src'].split(',', 1)[1]),
                             (home.RESOURCE_ASSETS / 'yap-logo.svg').read_bytes())
            self.assertEqual(product_logo['width'], '64')
            self.assertEqual((site / 'assets/yap-logo.svg').read_text(), custom_logo)
            for page in (homepage, collection, about):
                self.assertEqual(''.join(Page(page).footer_text), 'Maintained by Example <team> · Focused with yap')
                self.assertIn('Maintained by Example &lt;team&gt;', page)
                self.assertNotIn('Example &lt;author&gt;', page)
                self.assertNotIn('<author>', page)
                self.assertNotIn('<team>', page)
            for route in ('example.html', 'views/yapics/index.html', 'about.html'):
                # Resolve links using each page's directory, including nested collections.
                page_path = site / route
                for link in Page(page_path.read_text()).links:
                    if not urlsplit(link).scheme:
                        target = (page_path.parent / urlsplit(link).path).resolve()
                        self.assertTrue(target.is_relative_to(site.resolve()))
                about_link = next(link for link in Page(page_path.read_text()).links if link.endswith('about.html'))
                self.assertEqual((page_path.parent / about_link).resolve(), (site / 'about.html').resolve())

    def test_assistant_display_is_explicit_escaped_and_survives_root_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            branding = {'assistant': 'Example <helper>', 'assistant_credit': 'by Example <team>',
                        'footer_link': {'text': 'Example <team>', 'url': 'https://example.org/assist'}}
            manifest = {'schema': 1, 'slug': 'example', 'branding': branding}
            (root / 'yap.json').write_text(json.dumps(manifest))
            site = root / 'site'
            with selected(root):
                home.render(site)
                home.root_entry(site, root / 'example.html')
            homepage = (site / 'example.html').read_text()
            entry = (root / 'example.html').read_text()
            self.assertIn('Hi, ich bin Example &lt;helper&gt;.', homepage)
            self.assertIn('by <a href="https://example.org/assist">Example &lt;team&gt;</a>', homepage)
            self.assertIn('src="site/acc/img/gertrud-ai4x.png"', entry)
            self.assertIn('href="site/views/yapics/index.html"', entry)
            self.assertIn('href="https://example.org/assist"', entry)
            self.assertNotIn('<helper>', homepage)
            self.assertNotIn('<team>', homepage)
            self.assertNotIn('<script', homepage)
            self.assertNotIn('<form', homepage)
            self.assertIn('type="button" disabled', homepage)
            branding.pop('assistant_credit')
            (root / 'yap.json').write_text(json.dumps(manifest))
            with selected(root):
                home.render(site)
            self.assertNotIn('example.org/assist', (site / 'example.html').read_text())

    def test_default_footer_is_only_the_product_link_in_both_languages(self):
        with tempfile.TemporaryDirectory() as directory, selected(directory):
            for language in ('de', 'en'):
                rendered = footer.render(language, about_href='../../about.html')
                parsed = Page(rendered)
                self.assertEqual(''.join(parsed.footer_text), 'Focused with yap')
                self.assertEqual(parsed.footer_links, ['../../about.html'])
                self.assertEqual([''.join(anchor['text']) for anchor in parsed.footer_anchors], ['yap'])
                self.assertNotIn('ai4X', rendered)
                self.assertNotIn('Curated', rendered)
                self.assertNotIn('That’s right!', rendered)
                self.assertNotIn('Portfolio von ', rendered)
                self.assertNotIn('Portfolio by ', rendered)

    def test_additional_credit_is_plain_text_and_author_is_not_a_footer_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credit = '<a href="https://example.org">Example credit</a>'
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                'branding': {'title': 'Example portfolio', 'author': '<Example author>', 'footer': credit}}))
            with selected(root):
                for language in ('de', 'en'):
                    rendered = footer.render(language)
                    parsed = Page(rendered)
                    self.assertEqual(''.join(parsed.footer_text), credit + ' · Focused with yap')
                    self.assertEqual(parsed.footer_links, ['../../about.html'])
                    self.assertEqual([''.join(anchor['text']) for anchor in parsed.footer_anchors], ['yap'])
                    self.assertIn('&lt;a href=&quot;https://example.org&quot;&gt;', rendered)
                    self.assertNotIn('Example author', rendered)
                    self.assertNotIn('Example portfolio', rendered)

    def test_blank_additional_credit_has_no_separator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for credit in ('', '   '):
                (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                    'branding': {'footer': credit}}))
                with selected(root):
                    self.assertEqual(''.join(Page(footer.render()).footer_text), 'Focused with yap')

    def test_saved_perspectives_keep_instance_title_and_product_footer_in_both_languages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                'branding': {'title': 'Example <portfolio>.', 'author': 'Example author'}}))
            source = root / 'pfo/act/act.md'
            source.parent.mkdir(parents=True)
            source.write_text('---\ntitle: Activities\n---\n')
            output = root / 'site/views/perspectives'
            with selected(root):
                perspective_html.render(root, destination=output, model={'nodes': []})
            for filename in ('index.html', 'index.en.html'):
                rendered = (output / filename).read_text()
                self.assertIn('<title>Example &lt;portfolio&gt;.', rendered)
                self.assertEqual(''.join(Page(rendered).footer_text), 'Focused with yap')
                self.assertNotIn('Example author', rendered)
                self.assertIn('../../example.html', rendered)

    def test_all_actual_view_renderers_share_the_minimal_footer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = {
                'pfo/act/act.md': '---\ntitle: Activities\ntracking:\n  example: {status: wip}\n---\n',
                'pfo/act/example/example.md': '---\nkind: activity\nkey: example\ntitle: Example activity\n---\n',
                'pfo/asp/goals.md': '---\ntitle: Goals\n---\n',
            }
            for name, text in sources.items():
                source = root / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(text)
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                'branding': {'title': 'Example portfolio', 'author': 'Example author',
                             'footer': 'Curated by Example',
                             'footer_link': {'text': 'Example', 'url': 'https://example.org/'}}}))
            site = root / 'site'
            with selected(root):
                model = content.load(root)
                home.render(site)
                board.render_html(board.lanes(model), site / 'views/activity-board')
                map_file = site / 'views/activity-map/index.html'
                map_file.parent.mkdir(parents=True, exist_ok=True)
                map_file.write_text(activity_map.render(model))
                dgraph.render_html(model['dgraph'], site / 'views/dependency-graph')
                views.render_mpm(model, site / 'views/mPM-ish')
                perspective_html.render(root, destination=site / 'views/perspectives', model=model)
            pages = list(site.rglob('*.html'))
            self.assertGreaterEqual(len(pages), 9)
            for page in pages:
                parsed = Page(page.read_text())
                self.assertEqual(''.join(parsed.footer_text), 'Curated by Example · Focused with yap', str(page.relative_to(site)))
                self.assertEqual(parsed.footer_links[0], 'https://example.org/')
                self.assertEqual([''.join(anchor['text']) for anchor in parsed.footer_anchors], ['Example', 'yap'])
                self.assertEqual((page.parent / parsed.footer_links[1]).resolve(), (site / 'about.html').resolve())
            for name, original in sources.items():
                self.assertEqual((root / name).read_text(), original)

    def test_optional_link_names_only_one_unique_credit_fragment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for url in ('https://example.org/docs?q=x&name=y#section', 'http://example.org/'):
                (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example', 'branding': {
                    'footer': 'Curated by Example', 'footer_link': {'text': 'Example', 'url': url}}}))
                with selected(root):
                    for language in ('de', 'en'):
                        parsed = Page(footer.render(language))
                        self.assertEqual(''.join(parsed.footer_text), 'Curated by Example · Focused with yap')
                        self.assertEqual(parsed.footer_links, [url, '../../about.html'])
                        self.assertEqual([''.join(anchor['text']) for anchor in parsed.footer_anchors], ['Example', 'yap'])

    def test_invalid_or_ambiguous_credit_links_fall_back_to_escaped_plain_text(self):
        invalid = [None, [], 'https://example.org/', {}, {'text': 'Example'},
                   {'text': 1, 'url': 'https://example.org/'},
                   {'text': 'Example', 'url': True},
                   {'text': 'Example', 'url': 'https://example.org/', 'extra': 'ignored'},
                   {'text': '', 'url': 'https://example.org/'},
                   {'text': ' Example', 'url': 'https://example.org/'},
                   {'text': 'Absent', 'url': 'https://example.org/'}]
        for url in ('javascript:alert(1)', 'data:text/html,example', '//example.org/',
                    'https:///missing', 'https://[broken', 'https://example.org:bad/',
                    'https://user:secret@example.org/', 'https://example.org/ with space',
                    'https://example.org/\npath', 'https://example.org/\x00path'):
            invalid.append({'text': 'Example', 'url': url})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = [('Curated by <Example>', link) for link in invalid]
            cases.append(('Curated by Example Example', {'text': 'Example', 'url': 'https://example.org/'}))
            cases.append(('aaa', {'text': 'aa', 'url': 'https://example.org/'}))
            for credit, link in cases:
                with self.subTest(link=link):
                    (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                        'branding': {'footer': credit, 'footer_link': link}}))
                    with selected(root):
                        rendered = footer.render()
                        parsed = Page(rendered)
                        self.assertEqual(''.join(parsed.footer_text), credit + ' · Focused with yap')
                        self.assertEqual(parsed.footer_links, ['../../about.html'])
                        self.assertEqual([''.join(anchor['text']) for anchor in parsed.footer_anchors], ['yap'])
                        self.assertNotIn('<Example>', rendered)
