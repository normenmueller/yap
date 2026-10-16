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

from yap import footer, home, navigation, perspective_html


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
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == 'a':
            self.links.append(fields.get('href', ''))
        if tag == 'img':
            self.images.append(fields)

    def handle_data(self, data):
        self.text.append(data)


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
            self.assertIn('Example activities', homepage)
            self.assertIn('Dein Wirkungsfeld umfasst deine Vorhaben, Ziele und Beiträge.', homepage)
            self.assertIn('Arbeiten. Wirken. Nachlesen.', homepage)
            self.assertIn('Dein Beitrag. An jedem Heute.', homepage)
            collection = (site / 'views/yapics/index.html').read_text()
            self.assertIn('Seeds of Insight. Tailored to your needs.', collection)
            about = (site / 'about.html').read_text()
            self.assertIn('Kleine Spuren, die etwas erzählen.', about)
            self.assertIn('yap dein yapic mit mir!', about)
            self.assertNotIn('<textarea', homepage)
            self.assertNotIn('disabled', homepage)
            self.assertIn('Teil des Produktzielbilds', about)
            product_logo = next(image for image in Page(about).images if image['alt'] == 'yap.')
            self.assertEqual(base64.b64decode(product_logo['src'].split(',', 1)[1]),
                             (home.RESOURCE_ASSETS / 'yap-logo.svg').read_bytes())
            self.assertEqual(product_logo['width'], '64')
            self.assertEqual((site / 'assets/yap-logo.svg').read_text(), custom_logo)
            for page in (homepage, collection, about):
                self.assertIn('yap. That’s right!', page)
                self.assertIn('Maintained by Example &lt;team&gt;', page)
                self.assertIn('Portfolio von Example &lt;author&gt; · Maintained by Example &lt;team&gt;', page)
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

    def test_shared_footer_keeps_exact_signature_and_localized_description(self):
        with tempfile.TemporaryDirectory() as directory, selected(directory):
            for language, description in [('de', 'Klarheit über Vorhaben und Wirkung.'),
                                          ('en', 'Clarity about initiatives and impact.')]:
                rendered = footer.render(language, about_href='../../about.html')
                self.assertIn('<em>yap. That’s right!</em>', rendered)
                self.assertIn(description, rendered)
                self.assertIn('href="../../about.html"', rendered)
                self.assertIn('Powered by yap', rendered)
                self.assertNotIn('Portfolio von ', rendered)
                self.assertNotIn('Portfolio by ', rendered)

    def test_author_byline_is_localized_and_never_replaces_product_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'yap.json').write_text(json.dumps({'schema': 1, 'slug': 'example',
                'branding': {'title': 'Example portfolio', 'author': '<Example author>', 'footer': ''}}))
            with selected(root):
                for language, label in [('de', 'Portfolio von '), ('en', 'Portfolio by ')]:
                    rendered = footer.render(language)
                    self.assertIn(label + '&lt;Example author&gt;', rendered)
                    self.assertNotIn('<Example author>', rendered)
                    self.assertNotIn(' · </p>', rendered)
                    self.assertIn('yap. That’s right!', rendered)
                    self.assertNotIn('<em>Example portfolio</em>', rendered)

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
            for filename, byline in [('index.html', 'Portfolio von '), ('index.en.html', 'Portfolio by ')]:
                rendered = (output / filename).read_text()
                self.assertIn('<title>Example &lt;portfolio&gt;.', rendered)
                self.assertIn('yap. That’s right!', rendered)
                self.assertIn(byline + 'Example author', rendered)
                self.assertIn('../../example.html', rendered)
