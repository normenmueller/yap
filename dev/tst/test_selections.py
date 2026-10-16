"""Yapic selection must preserve facts while excluding unselected content."""

from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote

from yap import board, content, dgraph, goaltree, navigation, selections, views


class SelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.write('pfo/act/act.md', '''---
title: Activities
members:
  bundle: [x, "y"]
tracking:
  x: {status: on hold, priority: p2, next: 3}
  "y": {status: wip, priority: p1}
dgraph:
  spec: |
    bundle -> z
---
''')
        for key in ('bundle', 'x', 'y', 'z'):
            self.write(f'pfo/act/{key}/{key}.md', f'---\nkind: activity\nkey: "{key}"\ntitle: "{key.upper()}"\n---\n')
        self.write('pfo/okr/goals.md', '''---
title: Goals
sequence: [a, b, c]
tracking:
  a: {status: active}
  b: {status: on hold}
  c: {status: closed}
---
''')
        for key in ('a', 'b', 'c'):
            self.write(f'pfo/okr/obj/{key}.md', f'---\nkey: "{key}"\ntitle: Goal {key.upper()}\n---\n')
        self.definition = {'schema': 1, 'title': 'Selected', 'entries': [
            {'id': 'p000001', 'name': 'X', 'target': {'entry': 'x'}},
            {'id': 'p000002', 'name': 'Z', 'target': {'entry': 'z'}},
            {'id': 'p000003', 'name': 'Empty', 'entries': []},
        ]}
        self.write('pov/focus/.perspective.yaml', json.dumps(self.definition))
        self.model = content.load(self.root)

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def test_saved_subset_preserves_tracking_and_never_appends_unassigned(self):
        original = deepcopy(self.model)
        selections.prepare(self.root, self.model)
        full, focus = list(selections.activities(self.model))
        self.assertEqual(full['report'], original['report'])
        self.assertEqual([p['entry'] for p in focus['report']['nodes']], ['x', 'z', None])
        rows = list(board.display_rows(board.lanes(focus)))
        cards = [card for row in rows for cell in row['cells'].values() for card in cell]
        self.assertEqual({card['key'] for card in cards}, {'x', 'z'})
        x = next(card for card in cards if card['key'] == 'x')
        self.assertEqual((x['status'], x['priority'], x['next']), ('on hold', 'p2', 3))
        self.assertEqual(focus['nodes'], original['nodes'])
        self.assertEqual(focus['members'], original['members'])
        self.assertEqual(json.loads((self.root / 'pov/focus/.perspective.yaml').read_text()), self.definition)

    def test_dependency_subset_cannot_reintroduce_excluded_group_members(self):
        selections.prepare(self.root, self.model)
        focus = list(selections.activities(self.model))[1]
        graph = focus['dgraph']
        self.assertEqual({tuple(edge) for edge in graph['edges']}, {('x', 'z')})
        self.assertEqual({node['key'] for node in graph['nodes']}, {'x', 'z'})
        self.assertEqual(graph['expansions'], {'x': ['x'], 'z': ['z']})
        self.assertIn('data-key="x"', dgraph.svg(graph))
        self.assertNotIn('data-key="y"', dgraph.svg(graph))
        disconnected = selections.dependency_selection(self.model['dgraph'], {'x', 'y'})
        self.assertEqual({n['key'] for n in disconnected['nodes']}, {'x', 'y'})
        self.assertEqual(disconnected['edges'], [])
        dgraph.render_html(disconnected, self.root / 'empty', selection=focus['selection'])
        page = (self.root / 'empty/p-focus.html').read_text()
        self.assertIn('Zwischen diesen Aktivitäten sind keine Abhängigkeiten hinterlegt.', page)
        self.assertIn('data-key="x"', page)
        self.assertIn('data-key="y"', page)
        self.assertNotIn(dgraph.MODULE_EXPLANATION, page)
        self.assertNotIn('Grundlage →', page)
        self.assertIn('Graph · PDF', page)
        dgraph.render_html(selections.dependency_selection(self.model['dgraph'], set()),
                           self.root / 'empty', selection=focus['selection'])
        page = (self.root / 'empty/p-focus.html').read_text()
        self.assertIn('Keine Aktivitäten in dieser Auswahl.', page)
        self.assertNotIn('Graph · PDF', page)

    def test_board_overview_grouping_keeps_ancestors_without_extra_cards(self):
        overview = {'schema': 1, 'title': 'Overview', 'entries': [
            {'id': 'p000001', 'name': 'Support', 'entries': [
                {'id': 'p000002', 'name': 'Bundle', 'entries': [
                    {'id': 'p000003', 'name': 'Bundle description', 'target': {'entry': 'bundle'}},
                    {'id': 'p000004', 'name': 'X', 'target': {'entry': 'x'}},
                    {'id': 'p000005', 'name': 'Y', 'target': {'entry': 'y'}}]}]},
            {'id': 'p000006', 'name': 'Impact', 'entries': [
                {'id': 'p000007', 'name': 'Z', 'target': {'entry': 'z'}}]}],
            'presentation': {'placements': {
                'p000001': {'role': 'category', 'category': 'sup', 'tone': 'support'},
                'p000002': {'heading-source': 'p000003'},
                'p000003': {'board-card': 'always'},
                'p000006': {'role': 'category', 'category': 'ipc', 'tone': 'impact'}},
                'board': {'category-order': ['sup', 'ipc']}}}
        self.write('pov/overview/.perspective.yaml', json.dumps(overview))
        control = self.root / 'pfo/act/act.md'
        control.write_text(control.read_text().replace('title: Activities',
                           'title: Activities\nreport-perspective: overview'))
        self.definition['presentation'] = {'board': {'grouping': 'overview'}}
        self.write('pov/focus/.perspective.yaml', json.dumps(self.definition))
        model = content.load(self.root)
        before = deepcopy(model)
        selections.prepare(self.root, model)
        focus = list(selections.activities(model))[1]
        lanes = board.lanes(focus)
        self.assertEqual([lane['key'] for lane in lanes], ['sup', 'ipc'])
        self.assertEqual(lanes[0]['sublanes'][0]['title'], 'BUNDLE')
        cards = [c['key'] for row in board.display_rows(lanes) for cell in row['cells'].values() for c in cell]
        self.assertEqual(cards, ['x', 'z'])
        self.assertEqual([p['entry'] for p in focus['report']['nodes']], ['x', 'z', None])
        self.assertEqual(model['report'], before['report'])
        self.assertEqual(model['nodes'], before['nodes'])
        only_x = selections.board_selection(model['report'], {'x'})
        self.assertEqual([lane['key'] for lane in board.lanes(dict(model, board_report=only_x))], ['sup'])
        with self.assertRaisesRegex(ValueError, 'missing activities'):
            selections.board_selection(model['report'], {'unknown'})

    def test_selected_activity_without_any_dependency_is_visible(self):
        self.write('pfo/act/solo/solo.md', '---\nkind: activity\nkey: solo\ntitle: Standalone\n---\n')
        self.definition['entries'] = [{'id': 'p000001', 'name': 'Solo', 'target': {'entry': 'solo'}}]
        self.write('pov/focus/.perspective.yaml', json.dumps(self.definition))
        model = content.load(self.root)
        selections.prepare(self.root, model)
        graph = list(selections.activities(model))[1]['dgraph']
        self.assertEqual([n['key'] for n in graph['nodes']], ['solo'])
        self.assertEqual(graph['edges'], [])

    def test_goal_filters_preserve_source_order_numbers_and_kr_facts(self):
        self.model['key_results'] = {'b': [{'key': 'k', 'title': 'Measured', 'measure': 'Evidence',
                                          'target': 9, 'activities': []}]}
        original = deepcopy(self.model)
        selected = list(selections.performance(self.model))
        self.assertEqual([[g['key'] for g in s['goals']] for s in selected], [['a', 'b', 'c'], ['a'], ['b'], ['c']])
        paused = selected[2]
        graph = goaltree.graph_data(paused)
        self.assertEqual(graph['nodes'][0]['label'], 'O 2')
        self.assertEqual(paused['key_results'], self.model['key_results'])
        self.assertEqual(self.model, original)

    def test_portable_routes_and_goal_pages(self):
        special = {'key': 'R&D #?', 'label': 'Special', 'options': [('', 'All'), ('R&D #?', 'Special')]}
        page = navigation.render('board', selection=special)
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.targets = []
            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    self.targets.append(dict(attrs)['href'])
        links = Links()
        links.feed(page)
        target = next(href for href in links.targets if 'activity-map/' in href)
        self.assertEqual(Path(unquote(target)).name, selections.filename(special))
        views.render_mpm(self.model, self.root / 'performance')
        paused = (self.root / 'performance/p-paused.html').read_text()
        self.assertIn('Goal B', paused)
        self.assertNotIn('Goal A', paused)
        self.assertNotIn('Goal C', paused)
        self.assertIn('class="goal-section goals-on-hold" open', paused)
        self.assertIn('Berichte &amp; Export', paused)
        self.assertIn('Gesamtes Portfolio', paused)


if __name__ == '__main__':
    unittest.main()
