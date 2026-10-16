"""Map semantics must survive switching from the whole portfolio to an area."""

from fixtures import report_model
from copy import deepcopy
from html.parser import HTMLParser

import unittest

from yap import activity_map, overview, views


class MapParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.areas = []
        self.branches = []
        self.names = []
        self.in_name = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'map-area' in attrs.get('class', '').split():
            self.areas.append((tag, 'open' in attrs))
        if 'map-branch' in attrs.get('class', '').split():
            self.branches.append((tag, 'open' in attrs))
        if attrs.get('class') == 'map-name':
            self.in_name = True

    def handle_data(self, data):
        if self.in_name:
            self.names.append(data)

    def handle_endtag(self, tag):
        if tag in ('div', 'h2'):
            self.in_name = False


class MapTests(unittest.TestCase):
    def test_activity_labels_match_board_without_subtitle_fallback(self):
        model = report_model({'nodes': [
            dict(key='area', title='Area heading', kind='area', subtitle='Area context'),
            dict(key='area/sfe', title='Full source title', acronym='SFE',
                 subtitle='Report-only subtitle', **{'board-caption': 'agentic <assisted>\nSFE'}),
            dict(key='area/plain', title='Fallback title', subtitle='Not a caption'),
        ]})
        before = deepcopy(model)
        page = activity_map.render(model)
        self.assertEqual(MapParser(page).names, ['Area heading', 'SFE', 'Fallback title'])
        self.assertIn('agentic &lt;assisted&gt; SFE', page)
        tex = views.map_tex(model)
        self.assertIn('agentic <assisted> SFE', tex)
        for output in (page, tex):
            self.assertIn('Area context', output)
            for hidden in ('Full source title', 'Report-only subtitle', 'Not a caption'):
                self.assertNotIn(hidden, output)
        self.assertEqual(model, before)

    def test_notes_and_empty_note_groups_are_omitted_without_losing_activities(self):
        model = report_model({'nodes': [
            dict(key='area', title='Area', kind='area'),
            dict(key='area/work', title='Work'),
            dict(key='area/note', title='Mixed note', kind='note'),
            dict(key='notes', title='Notes'),
            dict(key='notes/note', title='Only note', kind='note'),
            dict(key='note-parent', title='Note parent', kind='note'),
            dict(key='note-parent/work', title='Retained work'),
        ]})
        model['report']['nodes'][3]['entry'] = ''
        before = deepcopy(model)
        nodes = overview.map_nodes(model)
        self.assertEqual([n['title'] for n in nodes], ['Area', 'Work', 'Retained work'])
        self.assertEqual((nodes[-1]['parent'], nodes[-1]['depth']), ('', 1))
        self.assertEqual(MapParser(activity_map.render(model)).names, ['Area', 'Work', 'Retained work'])
        tex = views.map_tex(model)
        for title in ('Mixed note', 'Notes', 'Only note', 'Note parent'):
            self.assertNotIn(title, tex)
        self.assertEqual(model, before)

    def test_version_tracking_is_visible_within_one_activity_in_both_maps(self):
        model = report_model({'nodes': [dict(key='sfe', title='SFE', depth=1,
            versions=[dict(label='v0.2', status='released', priority=''),
                      dict(label='v0.3 <next>', status='on hold', priority='p1', next=1)])]})
        before = deepcopy(model)
        page = activity_map.render(model)
        self.assertEqual(MapParser(page).names, ['SFE'])
        self.assertEqual(page.count('class="map-version"'), 2)
        self.assertIn('<details class="map-entry map-disclosure map-versioned">', page)
        self.assertLess(page.index('</summary>', page.index('map-versioned"')), page.index('<div class="map-versions"'))
        released, paused = page.split('class="map-version"')[1:]
        self.assertIn('v0.2', released)
        self.assertIn('released', released)
        self.assertNotIn('Priorität', released)
        self.assertIn('v0.3 &lt;next&gt;', paused)
        self.assertIn('on hold', paused)
        self.assertIn('Priorität p1', paused)
        self.assertIn('aria-label="Als Nächstes: 1">1</span>', paused)
        self.assertNotIn('nxt 1', paused)
        self.assertNotIn('map-next', released)
        self.assertNotIn('map-meta', page.split('class="map-versions"')[0].split('<main>')[1])
        tex = views.map_tex(model)
        self.assertEqual(tex.count(r'\node[box,'), 1)
        self.assertIn(r'v0.2\quad \textcolor{namReleased}{released}', tex)
        self.assertIn(r'\textcolor{namHold}{on hold}', tex)
        self.assertIn(r'\textcolor{namAccent}{\textbullet}\ p1', tex)
        self.assertIn(r'\mapnext{1}', tex)
        self.assertEqual(model, before)

    def test_browser_preserves_placement_order_and_only_folds_parents(self):
        model = report_model({'nodes': [
            dict(key='one', title='First'),
            dict(key='one/child', title='Child', status='wip', priority='p1'),
            dict(key='one/child/grandchild', title='Grandchild'),
            dict(key='two', title='Leaf <&>'),
            dict(key='three', title='Third'),
            dict(key='three/child', title='Last'),
        ]})
        # A placement alias owns its displayed title; roots may be pure groups.
        model['report']['nodes'][0].update(entry='', title='Group alias')
        page = activity_map.render(model)
        parsed = MapParser(page)
        self.assertEqual(parsed.names, ['Group alias', 'Child', 'Grandchild', 'Leaf <&>', 'Third', 'Last'])
        self.assertEqual(parsed.areas, [('details', True), ('section', False), ('details', True)])
        self.assertEqual(parsed.branches, [('details', False)])
        self.assertIn('Leaf &lt;&amp;&gt;', page)
        self.assertNotIn('<img', page.split('<main>', 1)[1])
        self.assertIn('Priorität p1', page)
        self.assertEqual(page.count('class="map-entry map-wip"'), 1)

    def test_export_wraps_root_pairs_below_both_previous_subtrees(self):
        model = report_model({'nodes': [dict(key=key, title=key, depth=key.count('/') + 1)
                            for key in ('a', 'a/child', 'b', 'c', 'd', 'd/child', 'e')]})
        tex = views.map_tex(model)
        self.assertIn(r'\p1=(node1.south), \p2=(node2.south)', tex)
        self.assertIn(r'\p1=(node3.south), \p2=(node5.south)', tex)
        self.assertIn(r'min(\y1,\y2)', tex)
        self.assertNotIn('+(24.0,', tex)
        self.assertNotIn('coordinate (band', views.map_tex(model, 'a'))

    def test_category_colors_stay_stable_in_area_submaps(self):
        entries = [
            ('rnd', 'Research'), ('rnd/gov', 'Governance RND'),
            ('rnd/gov/noEA', 'noEA'), ('dbf', 'DB Fernverkehr'),
            ('dbf/sup', 'Support'), ('dbf/sup/cpp', 'cpp'),
            ('dbf/sup/cpp/sfe', 'Strategic Fit Evaluation'),
            ('dbf/imp', 'Impact'), ('dbf/imp/project', 'Impact project'),
            ('dbf/gov', 'Governance DBF'), ('dbf/gov/project', 'Governance project'),
        ]
        nodes = [dict(key=key, title=title, parent=key.rpartition('/')[0],
                      depth=key.count('/') + 1) for key, title in entries]
        nodes[6].update(status='wip', priority='p1')
        model = {'nodes': nodes}
        model = report_model(model)
        colors = {'rnd': 'namMuted', 'dbf': 'namMuted',
                  'rnd/gov': 'namGovernance', 'dbf/gov': 'namGovernance',
                  'dbf/sup': 'namSupport', 'dbf/imp': 'namImpact',
                  'dbf/sup/cpp/sfe': 'namStrategy'}
        for area in ('', 'rnd', 'dbf'):
            with self.subTest(area=area or 'portfolio'):
                diagram = views.map_tex(model, area)
                for node in nodes:
                    key = node['key']
                    if key not in colors or (area and key != area and not key.startswith(area + '/')):
                        continue
                    self.assertIn(r'{\bfseries\color{' + colors[key] + '}' + node['title'] + '}', diagram)
                if area != 'rnd':
                    self.assertIn(r'\textcolor{namWip}{wip}', diagram)
                    self.assertIn(r'\textcolor{namAccent}{\textbullet}\ p1', diagram)
