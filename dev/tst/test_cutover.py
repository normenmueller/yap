"""Model identity, semantic edges and complete output survive independent placement."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest

from yap import board, content, dgraph, documents, files, performance_lanes, perspectives, selections


class CutoverTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap-cutover-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.write('pfo/act/act.md', '---\ntitle: Activities\nreport-perspective: report\n'
                   'members:\n  system: [a, b]\ndgraph:\n  spec: |\n    seed -> system\n---\n')
        self.write('pfo/okr/goals.md', '---\ntitle: Goals\n---\n')
        for key in ('seed', 'system', 'a', 'b', 'other'):
            self.write(f'pfo/act/{key}/{key}.md', f'---\nkind: activity\nkey: "{key}"\ntitle: {key}\n---\n')
        self.definition = {'schema': 1, 'title': 'Report', 'entries': [
            {'id': 'p000001', 'name': 'seed', 'target': {'entry': 'seed'}},
            {'id': 'p000002', 'name': 'System', 'entries': [
                {'id': 'p000003', 'name': 'description', 'target': {'entry': 'system'}},
                {'id': 'p000004', 'name': 'a', 'target': {'entry': 'a'}},
                {'id': 'p000005', 'name': 'b', 'target': {'entry': 'b'}}]},
            {'id': 'p000006', 'name': 'other', 'target': {'entry': 'other'}}],
            'presentation': {'placements': {'p000002': {'role': 'lane', 'heading-source': 'p000003'}}}}
        self.save()

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        return path

    def save(self):
        return self.write('pov/report/.perspective.yaml', json.dumps(self.definition))

    def meanings(self, graph):
        drawing = dgraph.layout(graph)
        children = {}
        for node in graph['nodes']:
            children.setdefault(node['parent'], []).append(node['key'])
        def leaves(key):
            return {leaf for child in children[key] for leaf in leaves(child)} if key in children else {key}
        return {(a, b) for chain in drawing['chains'] for a in leaves(chain[0]) for b in leaves(chain[-1])}

    def test_regrouping_cannot_hide_or_invent_dependencies(self):
        baseline = content.load(self.root)['dgraph']
        self.assertEqual(self.meanings(baseline), {('seed', 'a'), ('seed', 'b')})
        for moved_out, unrelated_in in ((True, False), (False, True)):
            with self.subTest(moved_out=moved_out):
                definition = deepcopy(self.definition)
                if moved_out:
                    definition['entries'].append(definition['entries'][1]['entries'].pop())
                if unrelated_in:
                    definition['entries'][1]['entries'].append(definition['entries'].pop())
                self.write('pov/report/.perspective.yaml', json.dumps(definition))
                graph = content.load(self.root)['dgraph']
                self.assertEqual(graph['effective_edges'], baseline['effective_edges'])
                self.assertEqual(self.meanings(graph), set(graph['effective_edges']))
                dgraph.tex(graph)
                dgraph.svg(graph)

    def test_realm_flow_splits_modules_without_changing_overview_or_focus(self):
        reference = content.load(self.root)['dgraph']
        reference.update(columns=[['seed'], ['system'], ['other']], lanes=[
            dict(key='support', label='Support', tone='support', columns=[1, 2]),
            dict(key='gov', label='Governance', tone='governance', columns=[3])])
        original = deepcopy(reference)
        layout = dgraph.layout(reference)
        report = dict(graph_realms=[dict(placement='realm', sections=['support', 'gov'])], nodes=[
            dict(placement='realm', parent='', entry=None, document=False, label='Realm'),
            dict(placement='support', parent='realm', entry=None, document=False, label='Support', tone='support'),
            dict(placement='gov', parent='realm', entry=None, document=False, label='Governance', tone='governance'),
            *[dict(placement=key, parent='gov' if key in ('b', 'other') else 'support',
                   entry=key, document=True, title=key) for key in ('seed', 'system', 'a', 'b', 'other')]])
        selected = selections.dependency_selection(reference, {'seed', 'system', 'a', 'b', 'other'})
        selections.arrange_flow(selected, report, reference, layout)
        self.assertEqual(selected['columns'], [['seed', 'system'], ['b', 'other']])
        self.assertEqual([l['label'] for l in selected['lanes']], ['Realm'])
        self.assertNotIn('column_widths', selected)
        self.assertEqual({n['key']: n['parent'] for n in selected['nodes']}['b'], '')
        self.assertEqual({n['key']: n['parent'] for n in selected['nodes']}['a'], 'system')
        self.assertEqual(selected['effective_edges'], reference['effective_edges'])
        self.assertEqual(self.meanings(selected), set(reference['effective_edges']))
        self.assertEqual(reference, original)
        self.assertIn('Realm', dgraph.svg(selected))
        self.assertIn('Governance', dgraph.tex(selected))
        report['graph_align_centers'] = [['other', 'system']]
        selections.arrange_flow(selected, report, reference, layout)
        aligned = dgraph.layout(selected)
        self.assertEqual(aligned['positions']['other'][1], aligned['positions']['system'][1])
        self.assertEqual(reference, original)
        focus = selections.dependency_selection(reference, {'a'})
        report['graph_edge_ports'] = [dict(source='seed', target='system', exit='right', entry='bottom')]
        report['graph_offset_y'] = {'other': 12}
        selections.realm_flow(selected, report)
        self.assertEqual(selected['offset_y'], {'other': 12})
        self.assertEqual([p for p in selected['edge_ports'] if p['source'] == 'seed'],
                         report['graph_edge_ports'])
        selections.arrange_flow(focus, dict(nodes=[]), reference, layout)
        self.assertEqual(focus['columns'], [[], ['a'], []])
        self.assertEqual(dgraph.layout(focus)['column_bounds'], layout['column_bounds'])

    def test_realm_unframe_preserves_modules_edges_and_reference(self):
        control = self.root / 'pfo/act/act.md'
        control.write_text(control.read_text().replace('seed -> system', 'seed -> a\n    seed -> b'))
        reference = content.load(self.root)['dgraph']
        original = deepcopy(reference)
        report = dict(graph_unframe=['system'], graph_node_order=['a', 'seed', 'b', 'other'],
                      graph_realms=[dict(placement='realm', sections=['support'])], nodes=[
            dict(placement='realm', parent='', entry=None, document=False, label='Realm'),
            dict(placement='support', parent='realm', entry=None, document=False, label='Support', tone='support'),
            *[dict(placement=key, parent='support', entry=key, document=True, title=key)
              for key in ('seed', 'system', 'a', 'b', 'other')]])
        selected = deepcopy(reference)
        selections.realm_flow(selected, report)
        self.assertEqual(selected['columns'], [['a', 'seed', 'b', 'other']])
        self.assertIn(dict(source='seed', target='a', exit='top', entry='bottom'), selected['edge_ports'])
        self.assertIn(dict(source='seed', target='b', exit='bottom', entry='top'), selected['edge_ports'])
        self.assertNotIn('system', {n['key'] for n in selected['nodes']})
        self.assertEqual({n['key']: n['parent'] for n in selected['nodes']}['a'], '')
        self.assertEqual(selected['effective_edges'], original['effective_edges'])
        self.assertEqual(self.meanings(selected), set(original['effective_edges']))
        self.assertEqual(reference, original)
        reference['edges'].append(('seed', 'system'))
        with self.assertRaisesRegex(ValueError, 'dependency endpoint'):
            selections.realm_flow(reference, report)

    def test_flow_columns_preserve_order_groups_and_dependency_meaning(self):
        control = self.root / 'pfo/act/act.md'
        control.write_text(control.read_text().replace('seed -> system', 'seed -> system\n    seed -> other'))
        baseline = content.load(self.root)
        self.definition['presentation']['flow'] = {'columns': [
            ['p000006', 'p000001'], ['p000002']]}
        self.save()
        model = content.load(self.root)
        graph = model['dgraph']
        self.assertEqual(graph['edges'], baseline['dgraph']['edges'])
        self.assertEqual(graph['effective_edges'], baseline['dgraph']['effective_edges'])
        self.assertEqual(model['nodes'], baseline['nodes'])
        self.assertEqual(self.meanings(graph), self.meanings(baseline['dgraph']))
        drawing = dgraph.layout(graph)
        boxes = drawing['boxes']
        self.assertEqual(drawing['columns']['other'], drawing['columns']['seed'])
        self.assertLess(boxes['other'][1]+boxes['other'][3], boxes['seed'][1])
        self.assertLess(boxes['seed'][0]+boxes['seed'][2], boxes['system'][0])
        for key in ('a', 'b'):
            self.assertGreater(boxes[key][0], boxes['system'][0])
            self.assertLess(boxes[key][1]+boxes[key][3], boxes['system'][1]+boxes['system'][3])
        for chain in drawing['chains']:
            for a, c, d, b in dgraph._curves(chain, drawing):
                for step in range(101):
                    t = step/100
                    x, y = [(1-t)**3*a[j]+3*(1-t)**2*t*c[j]+3*(1-t)*t*t*d[j]+t**3*b[j] for j in (0, 1)]
                    for key, (bx, by, width, height) in boxes.items():
                        if key in chain or key in ('a', 'b') and 'system' in chain:
                            continue
                        self.assertFalse(bx < x < bx+width and by < y < by+height, (chain, key))
        self.assertEqual(drawing, dgraph.layout(graph))
        self.assertIn('Pfeile zeigen:', dgraph.svg(graph))

    def test_semantic_leaf_cannot_visually_own_an_unrelated_activity(self):
        self.definition['entries'][1]['entries'][0]['target']['entry'] = 'a'
        self.definition['entries'][1]['entries'] = [self.definition['entries'][1]['entries'][0],
                                                     self.definition['entries'].pop()]
        self.save()
        graph = content.load(self.root)['dgraph']
        self.assertEqual(self.meanings(graph), set(graph['effective_edges']))
        self.assertNotEqual(next(n for n in graph['nodes'] if n['key']=='other')['parent'], 'a')
        # Adding an edge must preserve its separate identity and placement.
        control = self.root / 'pfo/act/act.md'
        control.write_text(control.read_text().replace('seed -> system', 'seed -> system\n    seed -> other'))
        graph = content.load(self.root)['dgraph']
        self.assertEqual(self.meanings(graph), set(graph['effective_edges']))
        self.assertNotEqual(next(n for n in graph['nodes'] if n['key']=='other')['parent'], 'a')

    def test_capture_appears_with_full_metadata_without_saving_perspective(self):
        saved = self.save(); before = saved.read_bytes()
        source = perspectives.capture(self.root, 'Fresh work')
        source.write_text(source.read_text().replace('title:',
            'subtitle: Full subtitle\nslogan: Shared slogan\nurl: https://example.org\ntitle:'))
        model = content.load(self.root)
        key = 'fresh-work'
        cards = [card for row in board.display_rows(board.lanes(model)) for cell in row['cells'].values() for card in cell]
        self.assertIn(key, [card['key'] for card in cards])
        self.assertIn('data-activity="fresh-work"', performance_lanes.render(model, [key]))
        pdf = documents.activity(model, Path('stage'))
        self.assertIn('Full subtitle', content.plain(pdf['blocks']))
        self.assertIn('Shared slogan', content.plain(pdf['blocks']))
        self.assertIn('https://example.org', json.dumps(pdf))
        self.assertEqual(saved.read_bytes(), before)

    def test_resource_route_and_pdf_target_survive_source_move(self):
        control = self.root / 'pfo/act/act.md'
        control.write_text(control.read_text().replace('title: Activities',
            'title: Activities\npublication:\n  a: {id: act-old--a, resource-root: old/a}'))
        source = self.root / 'pfo/act/a/a.md'
        source.write_text(source.read_text()+'\n[Attachment](res/file.txt)\n')
        self.write('pfo/act/a/res/file.txt', 'Original bytes')
        first = content.load(self.root)
        (self.root / 'pfo/act/a').rename(self.root / 'pfo/act/system/a')
        second = content.load(self.root)
        for model in (first, second):
            node = next(n for n in model['nodes'] if n['key']=='a')
            self.assertEqual(node['id'], 'act-old--a')
            self.assertIn('../../res/old/a/file.txt', json.dumps(documents.activity(model, Path('stage'))))
        plan = files.resource_plan(self.root, second)
        self.assertEqual(plan['res/old/a/file.txt'].read_text(), 'Original bytes')
        self.assertEqual(first['dgraph'], second['dgraph'])


if __name__ == '__main__':
    unittest.main()
