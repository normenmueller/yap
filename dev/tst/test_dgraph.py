"""Authored graph validation, reference resolution and shared rendering layout."""

from fixtures import report_model

from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from yap import content, dgraph


def node(key, acronym='', title=None):
    return dict(key=key, id='act-' + key.replace('/', '--'), kind='activity', acronym=acronym or (key.rsplit('/', 1)[-1] if '/' in key else ''),
                title=title or key.rsplit('/', 1)[-1])


class DependencyGraphTests(unittest.TestCase):
    def parse(self, spec, nodes=None, prop='horizontal-alignment'):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'act.md'
            path.write_text('---\ntitle: Test\ndgraph:\n  prop: ' + prop + '\n  spec: |\n' +
                            ''.join('    ' + line + '\n' for line in spec.splitlines()) + '---\n')
            meta = content.read(path)['meta']
        fixture = report_model({'nodes': nodes or [node('a'), node('b'), node('c')]})
        return dgraph.parse(meta, fixture['nodes'], fixture['members'], fixture['report'])

    def test_yaml_literal_block_resolves_names_acronyms_and_paths(self):
        nodes = [node('rnd/sup/ace/ai4X'), node('rnd/gov/noEA/o2i'),
                 node('dbf/sup/cpp'), node('dbf/sup/cpp/sfe', 'SFE')]
        graph = self.parse('ai4X -> o2i\nai4X -> cpp\n\no2i -> SFE\no2i -> dbf/sup/cpp/sfe', nodes)
        self.assertEqual(graph['edges'], [('rnd/sup/ace/ai4X', 'rnd/gov/noEA/o2i'),
            ('rnd/sup/ace/ai4X', 'dbf/sup/cpp'), ('rnd/gov/noEA/o2i', 'dbf/sup/cpp/sfe')])
        self.assertNotIn(('dbf/sup/cpp', 'dbf/sup/cpp/sfe'), graph['edges'])
        self.assertEqual(graph['nodes'][-1]['label'], 'SFE')
        self.assertEqual(dgraph.parse({}, nodes)['nodes'], [])
        self.assertEqual({n['key'] for n in self.parse('')['nodes']}, {'a', 'b', 'c'})

    def test_invalid_specs_and_cycles_fail_with_actionable_errors(self):
        for spec, message in [('a -> missing', 'unknown activity'), ('a => b', 'A -> B'),
                              ('a -> b -> c', 'A -> B'), ('a -> a', 'self-reference'),
                              ('a -> b\nb -> a', 'cycle')]:
            with self.subTest(spec=spec), self.assertRaisesRegex(ValueError, message):
                self.parse(spec)
        with self.assertRaisesRegex(ValueError, 'horizontal-alignment'):
            self.parse('a -> b', prop='diagonal')
        for value, message in [({'t': 'MetaList', 'c': []}, 'mapping'),
                               ({'t': 'MetaMap', 'c': {}}, 'spec is missing'),
                               ({'t': 'MetaMap', 'c': {'unknown': {}}}, 'unknown field')]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, message):
                dgraph.parse({'dgraph': value}, [])

    def test_centered_vertical_and_horizontal_routes_remain_distinct(self):
        graph = self.parse('a -> b\na -> c\na -> e\nb -> e\na -> d\nd -> e',
                           [node(key) for key in 'abcdef'])
        graph.update(columns=[['b', 'a'], ['f', 'c'], ['e', 'd']],
                     align_centers=[['a', 'c']], edge_ports=[
                         dict(source='a', target='b', exit='top', entry='bottom'),
                         dict(source='b', target='e', exit='top', entry='top'),
                         dict(source='a', target='d', exit='right', entry='bottom'),
                         dict(source='d', target='e', exit='top', entry='bottom')])
        drawing = dgraph.layout(graph)
        curves = {tuple(chain): dgraph._curves(chain, drawing) for chain in drawing['chains']}
        for pair, axis in [(('a', 'b'), 0), (('d', 'e'), 0), (('a', 'c'), 1)]:
            route = curves[pair]
            self.assertEqual(len(route), 1)
            self.assertEqual(len({point[axis] for point in route[0]}), 1)
        for pair in [('a', 'b'), ('d', 'e')]:
            source, target = (drawing['boxes'][key] for key in pair)
            self.assertEqual(curves[pair][0][0], (source[0]+source[2]/2, source[1]-1))
            self.assertEqual(curves[pair][-1][-1], (target[0]+target[2]/2, target[1]+target[3]+2))
        lines = {pair: [(a, b) for a, c, d, b in curves[pair] if a == c and d == b]
                 for pair in [('a', 'e'), ('b', 'e')]}
        horizontal = lambda pair: [a[1] for a, b in lines[pair] if a[1] == b[1] and abs(a[0]-b[0]) > 50]
        self.assertGreaterEqual(min(horizontal(('a', 'e')))-min(horizontal(('b', 'e'))), 14)
        for pair, side in [(('b', 'e'), 'top'), (('a', 'd'), 'bottom')]:
            target = drawing['boxes'][pair[1]]
            self.assertEqual(curves[pair][-1][-1],
                             (target[0]+target[2]/2, target[1]-2 if side == 'top' else target[1]+target[3]+2))
        self.assertGreater(curves[('a', 'd')][0][0][1], drawing['positions']['a'][1])
        for p, q in lines[('a', 'e')]:
            for r, s in lines[('b', 'e')]:
                axis = 1 if p[0] == q[0] else 0
                other = 1-axis
                if p[other] == q[other] == r[other] == s[other]:
                    self.assertLessEqual(min(max(p[axis], q[axis]), max(r[axis], s[axis]))-
                                         max(min(p[axis], q[axis]), min(r[axis], s[axis])), 0)

    def test_module_alignment_moves_container_and_preserves_siblings(self):
        graph = self.parse('a -> q/x\nq/x -> r/z',
                           [node(key) for key in ('a', 'b', 'q', 'q/x', 'q/y', 'r', 'r/z', 'c')])
        graph.update(columns=[['b', 'a'], ['q'], ['c', 'r']],
                     node_order=['q/y', 'q/x'])
        before = dgraph.layout(graph)
        self.assertLess(before['positions']['q/y'][1], before['positions']['q/x'][1])
        graph['align_centers'] = [['a', 'q/x'], ['r/z', 'q/x']]
        drawing = dgraph.layout(graph)
        self.assertEqual(len({drawing['positions'][key][1] for key in ('a', 'q/x', 'r/z')}), 1)
        self.assertEqual(drawing['positions']['r/z'][1]-drawing['positions']['r'][1],
                         before['positions']['r/z'][1]-before['positions']['r'][1])
        for chain in drawing['chains']:
            curves = dgraph._curves(chain, drawing)
            self.assertEqual(len(curves), 1)
            self.assertEqual(len({point[1] for point in curves[0]}), 1)
        graph['align_centers'] = [['q/x', 'q/y']]
        with self.assertRaisesRegex(ValueError, 'distinct outer containers'):
            dgraph.layout(graph)
        graph['align_centers'] = [['r/z', 'q/y']]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            dgraph.layout(graph)

    def test_vertical_offsets_preserve_title_clearance_and_reject_collisions(self):
        graph = self.parse('a -> b', [node(key) for key in 'abc'])
        graph.update(columns=[['a', 'c'], ['b']],
                     lanes=[dict(key='support', label='Support', tone='support', columns=[1, 2])],
                     edge_ports=[dict(source='a', target='b', exit='top', entry='top')],
                     offset_y={'a': -16, 'b': -16})
        drawing = dgraph.layout(graph)
        self.assertEqual(drawing['boxes']['a'][1], 64)
        curves = dgraph._curves(['a', 'b'], drawing)
        self.assertGreaterEqual(min(point[1] for curve in curves for point in curve), 50)
        for offsets, message in [({'a': 40}, 'overlap'), ({'a': -40}, 'leave the drawing')]:
            graph['offset_y'] = offsets
            with self.assertRaisesRegex(ValueError, message):
                dgraph.layout(graph)

    def test_positioned_side_ports_keep_straight_upper_and_center_arrivals_distinct(self):
        graph = self.parse('b -> c\na -> c', [node(key) for key in 'abc'])
        graph.update(columns=[['b', 'a'], ['c']], edge_ports=[
            dict(source='b', target='c', exit='right', entry='left', exit_position=.25, entry_position=.25),
            dict(source='a', target='c', exit='right', entry='left', entry_position=.5)])
        drawing = dgraph.layout(graph)
        upper = dgraph._curves(['b', 'c'], drawing)
        lower = dgraph._curves(['a', 'c'], drawing)
        self.assertEqual(len(upper), 1)
        self.assertEqual(len({p[1] for p in upper[0]}), 1)
        self.assertLess(upper[-1][-1][1], lower[-1][-1][1])
        self.assertEqual(lower[-1][-1][1], drawing['positions']['c'][1])
        graph.update(edge_ports=[], sections=[dict(label=str(i), tone='support') for i in range(2)])
        drawing = dgraph.layout(graph)
        self.assertEqual(len(dgraph._curves(['b', 'c'], drawing)), 1)
        self.assertEqual(dgraph._curves(['b', 'c'], drawing)[0][0][1], drawing['positions']['b'][1])

    def test_bottom_entry_uses_clear_space_below_target_container(self):
        graph = self.parse('a -> p/m', [node(key) for key in ('a', 'p', 'p/m', 'q', 'r', 's')])
        graph.update(columns=[['a'], ['p'], ['q', 'r', 's']], offset_y={'a': 140},
                     edge_ports=[dict(source='a', target='p/m', exit='right', entry='bottom')])
        drawing = dgraph.layout(graph)
        curves = dgraph._curves(['a', 'p/m'], drawing)
        target = drawing['boxes']['p/m']
        self.assertEqual(curves[-1][-1], (target[0]+target[2]/2, target[1]+target[3]+2))
        self.assertEqual(len(curves), 3)

    def test_realm_routes_use_separate_tracks_and_right_container_arrival(self):
        graph = self.parse('a -> b\na -> p\na -> c\na -> t\nb -> t\nc -> p/m\ng -> d\np/m -> d',
                           [node(key) for key in ('a', 'b', 'c', 'p', 'p/m', 't', 'd', 'd/x', 'g')])
        graph.update(columns=[['a', 'b', 'c'], ['p', 't'], ['d'], ['g']],
                     sections=[dict(label=str(i), tone='support') for i in range(4)],
                     lanes=[dict(key='one', label='One', tone='support', columns=[1]),
                            dict(key='two', label='Two', tone='support', columns=[2, 3, 4])],
                     edge_ports=[dict(source='a', target='b', exit='bottom', entry='top'),
                                 dict(source='g', target='d', exit='left', entry='right')])
        drawing = dgraph.layout(graph)
        target = drawing['boxes']['d']
        spans = drawing['column_bounds']
        self.assertEqual([right[0]-left[1] for left, right in zip(spans, spans[1:])],
                         [112, 64, 64])
        self.assertEqual(dgraph._curves(['g', 'd'], drawing)[-1][-1][0], target[0]+target[2]+2)
        vertical = []
        for pair in [('a', 't'), ('b', 't'), ('c', 'p/m')]:
            curves = dgraph._curves(list(pair), drawing)
            self.assertLessEqual(len(curves), 5)
            vertical.extend((p, q) for p, c, d, q in curves if p == c and d == q and p[0] == q[0])
        for i, (p, q) in enumerate(vertical):
            for r, s in vertical[i+1:]:
                if min(max(p[1], q[1]), max(r[1], s[1])) > max(min(p[1], q[1]), min(r[1], s[1])):
                    self.assertGreaterEqual(abs(p[0]-r[0]), 14)

    def test_cross_lane_vertical_routes_stay_between_panels(self):
        graph = self.parse('b -> c\ne -> d\ne -> f', [node(key) for key in 'abcdef'])
        graph.update(columns=[['a', 'b'], ['c', 'd'], ['e', 'f']], lanes=[
            dict(key='one', label='One', tone='support', columns=[1]),
            dict(key='two', label='Two', tone='impact', columns=[2]),
            dict(key='three', label='Three', tone='governance', columns=[3]),
        ], edge_ports=[dict(source='e', target='f', exit='bottom', entry='top')])
        drawing = dgraph.layout(graph)
        panels = drawing['lane_panels']
        for source, target in [('b', 'c'), ('e', 'd')]:
            curves = dgraph._curves([source, target], drawing)
            verticals = [(a, b) for a, c, d, b in curves
                         if a == c and d == b and a[0] == b[0] and a[1] != b[1]]
            self.assertTrue(verticals)
            for a, b in verticals:
                self.assertTrue(any(left['x']+left['width'] < a[0] < right['x']
                                    for left, right in zip(panels, panels[1:])), (source, target, a, b))
                self.assertIn(a[0], [(left['x']+left['width']+right['x'])/2
                                    for left, right in zip(panels, panels[1:])])
        downward = dgraph._curves(['e', 'f'], drawing)
        self.assertEqual(len(downward), 1)
        self.assertEqual(len({point[0] for point in downward[0]}), 1)
        self.assertLess(downward[0][0][1], downward[0][-1][1])

    def test_ambiguous_names_require_paths(self):
        nodes = [node('rnd/gov/item'), node('dbf/gov/item'), node('target')]
        with self.assertRaisesRegex(ValueError, 'ambiguous.*dbf/gov/item.*rnd/gov/item'):
            self.parse('item -> target', nodes)
        graph = self.parse('rnd/gov/item -> target', nodes)
        self.assertEqual(graph['edges'], [('rnd/gov/item', 'target')])

    def test_project_shorthand_expands_modules_and_preserves_targeted_edges(self):
        nodes = [node('rnd/sup/ace', 'ACE'), node('rnd/sup/ace/ai4X'),
                 node('dbf/sup/cpp', 'cpp'), node('dbf/sup/cpp/sfe', 'SFE'),
                 node('dbf/sup/cpp/fnd', 'FND'), node('o2i')]
        graph = self.parse('ai4X -> cpp\nai4X -> SFE\no2i -> SFE', nodes)
        self.assertEqual(graph['effective_edges'], [
            ('rnd/sup/ace/ai4X', 'dbf/sup/cpp/fnd'),
            ('rnd/sup/ace/ai4X', 'dbf/sup/cpp/sfe'), ('o2i', 'dbf/sup/cpp/sfe')])
        drawing = dgraph.layout(graph)
        self.assertEqual(len(drawing['chains']), 2)  # Redundant module arrow is covered by cpp.
        for item in graph['nodes']:
            if item['parent']:
                x, y, w, h = drawing['boxes'][item['key']]
                px, py, pw, ph = drawing['boxes'][item['parent']]
                self.assertGreater(x, px)
                self.assertGreaterEqual(y, py + drawing['headers'][item['parent']])
                self.assertLess(x+w, px+pw)
                self.assertLess(y+h, py+ph)
        self.assertIn('E6D58A', dgraph.svg(graph))
        self.assertIn('B5A5FF', dgraph.tex(graph))

    def test_group_expansion_validates_cycles_and_both_endpoints(self):
        nodes = [node('rnd/sup/a'), node('rnd/sup/a/x'), node('rnd/sup/a/y'),
                 node('dbf/sup/b'), node('dbf/sup/b/z')]
        graph = self.parse('a -> b', nodes)
        self.assertEqual(graph['effective_edges'], [('rnd/sup/a/x', 'dbf/sup/b/z'),
                                                   ('rnd/sup/a/y', 'dbf/sup/b/z')])
        with self.assertRaisesRegex(ValueError, 'cycle'):
            self.parse('a -> z\nz -> x', nodes)
        with self.assertRaisesRegex(ValueError, 'self-reference'):
            self.parse('a -> x', nodes)
        graph = self.parse('x -> z\nz -> y', nodes)
        self.assertEqual(len(dgraph.layout(graph)['chains']), 2)
        ET.fromstring(dgraph.svg(graph))  # Opposing container directions are not a module cycle.

    def test_report_selection_keeps_unconnected_activities_without_inventing_edges(self):
        nodes = [node(key) for key in ('context', 'foundation', 'works', 'unused',
                                      'project', 'module', 'sibling', 'external')]
        placements = []
        for key, parent, role in (
                ('context', '', 'lane'), ('foundation', 'context', 'leaf'),
                ('works', 'context', 'leaf'), ('unused', 'context', 'leaf'),
                ('project', '', 'lane'), ('module', 'project', 'leaf'),
                ('sibling', 'project', 'leaf'), ('external', '', 'leaf')):
            placements.append(dict(placement=key, entry=key, parent=parent,
                                   role=role, tone='neutral', category='', document=True))
        members = {'project': ['module', 'sibling']}

        def parse(spec):
            return dgraph.parse({'dgraph': {'t': 'MetaMap', 'c': {
                'spec': {'t': 'MetaString', 'c': spec}}}}, nodes, members, {'nodes': placements})

        graph = parse('foundation -> works\nmodule -> external')
        self.assertEqual({n['key'] for n in graph['nodes']},
                         {n['key'] for n in nodes})
        self.assertEqual(graph['effective_edges'], [('foundation', 'works'), ('module', 'external')])
        ET.fromstring(dgraph.svg(graph))
        # A source explicitly used as an endpoint must still be rendered.
        self.assertIn('context', {n['key'] for n in parse('context -> foundation')['nodes']})

    def test_internal_dependencies_use_reserved_right_gutter_and_distinct_ports(self):
        parent, first, second = 'rnd/sup/ace', 'rnd/sup/ace/ai4X', 'rnd/sup/ace/yap'
        nodes = [node(key) for key in (parent, first, second, 'external')]
        for source, target in ((first, second), (second, first)):
            with self.subTest(source=source):
                graph = self.parse(f'{source} -> {target}\n{source} -> external', nodes)
                drawing = dgraph.layout(graph)
                internal = next(chain for chain in drawing['chains'] if chain[-1] == target)
                curves = dgraph._curves(internal, drawing)
                a, b = curves[0][0], curves[-1][-1]
                sx, sy, sw, sh = drawing['boxes'][source]
                tx, _, tw, _ = drawing['boxes'][target]
                px, py, pw, ph = drawing['boxes'][parent]
                self.assertGreater(a[0], sx+sw)
                self.assertGreater(b[0], tx+tw)
                self.assertTrue(all(px < x < px+pw and py < y < py+ph
                                    for curve in curves for x, y in curve))
                external = next(chain for chain in drawing['chains'] if chain[-1] == 'external')
                departure = dgraph._curves(external, drawing)[0][0]
                self.assertGreater(departure[0], sx+sw)
                self.assertNotEqual(departure[1], a[1])

    def test_nested_internal_fanout_clears_cards_and_wide_neighbor_heading(self):
        project = 'area/imp/project'
        fnd, near, group, far = [project+'/'+name for name in ('foundation', 'near', 'group', 'far')]
        keys = ['input', 'output', project, fnd, near, group, group+'/a', group+'/b', far]
        graph = self.parse(f'input -> {fnd}\ninput -> output\n{fnd} -> {near}\n'
                           f'{fnd} -> {group}\n{fnd} -> {far}', [node(k) for k in keys])
        drawing = dgraph.layout(graph)
        parents = {n['key']: n['parent'] for n in graph['nodes']}
        fx, _, fw, _ = drawing['boxes'][fnd]
        for target in (near, group, far):
            self.assertGreater(drawing['boxes'][target][0], fx+fw)
        def ancestor(key, end):
            while end:
                if key == end:
                    return True
                end = parents[end]
            return False
        branches = []
        for chain in drawing['chains']:
            curves = dgraph._curves(chain, drawing)
            samples = []
            for a, c, d, b in curves:
                for step in range(101):
                    t = step/100
                    x, y = [(1-t)**3*a[j]+3*(1-t)**2*t*c[j]+3*(1-t)*t*t*d[j]+t**3*b[j]
                            for j in (0, 1)]
                    samples.append((x, y))
                    for key, (bx, by, w, h) in drawing['boxes'].items():
                        if ancestor(key, chain[0]) or ancestor(key, chain[-1]):
                            continue
                        self.assertFalse(bx < x < bx+w and by < y < by+h, (chain, key))
            if chain[0] == fnd:
                self.assertGreater(curves[0][0][0], fx+fw)
                self.assertLess(curves[-1][-1][0], drawing['boxes'][chain[-1]][0])
                branches.append(samples)
                px, py, pw, ph = drawing['boxes'][project]
                self.assertTrue(all(px < x < px+pw and py < y < py+ph for x, y in samples))
        self.assertEqual(len(branches), 3)
        # Separate internal arrows never share a path or cross one another.
        for i, path in enumerate(branches):
            for other in branches[i+1:]:
                closest = min((x-u)**2+(y-v)**2 for x, y in path for u, v in other)
                self.assertGreater(closest, 8**2)
        self.assertEqual(drawing, dgraph.layout(graph))

    def test_layout_routes_skipped_ranks_and_keeps_disconnected_components(self):
        graph = self.parse('a -> b\nb -> c\na -> c\nd -> e',
                           [node(name) for name in ('a', 'b', 'c', 'd', 'e')])
        drawing = dgraph.layout(graph)
        self.assertEqual(len(drawing['chains'][2]), 3)  # Reserved slot beside b.
        self.assertEqual(drawing, dgraph.layout(graph))
        for source, target in graph['edges']:
            self.assertLess(drawing['positions'][source][0], drawing['positions'][target][0])
        points = [drawing['positions'][n['key']] for n in graph['nodes']]
        self.assertEqual(len(points), len(set(points)))

    def test_internal_skipped_ranks_stay_inside_their_own_container(self):
        groups = ['area/imp/first', 'area/imp/second']
        keys, specs = [], []
        for group in groups:
            keys.extend([group, *(group+'/'+n for n in ('a', 'b', 'c'))])
            specs.extend([f'{group}/a -> {group}/b', f'{group}/b -> {group}/c',
                          f'{group}/a -> {group}/c'])
        specs.append(f'{groups[0]}/c -> {groups[1]}/a')
        graph = self.parse('\n'.join(specs), [node(k) for k in keys])
        drawing = dgraph.layout(graph)
        waypoints = []
        for group in groups:
            chain = next(c for c in drawing['chains'] if c[0] == group+'/a' and c[-1] == group+'/c')
            self.assertEqual(len(chain), 3)
            waypoints.append(chain[1])
            px, py, pw, ph = drawing['boxes'][group]
            bx, by, bw, bh = drawing['boxes'][group+'/b']
            for a, c, d, b in dgraph._curves(chain, drawing):
                for step in range(101):
                    t = step/100
                    x, y = [(1-t)**3*a[j]+3*(1-t)**2*t*c[j]+3*(1-t)*t*t*d[j]+t**3*b[j]
                            for j in (0, 1)]
                    self.assertTrue(px < x < px+pw and py < y < py+ph)
                    self.assertFalse(bx < x < bx+bw and by < y < by+bh)
        self.assertNotEqual(*waypoints)

    def test_svg_tex_escape_labels_and_html_links_are_portable(self):
        graph = self.parse('a -> b', [node('a', title='<script>&_#'), node('b')])
        svg = dgraph.svg(graph)
        root = ET.fromstring(svg)
        links = root.findall('{http://www.w3.org/2000/svg}a')
        self.assertEqual([link.attrib['href'] for link in links],
                         ['../../acc/pdf/Activity - Details.pdf#nameddest=act-a', '../../acc/pdf/Activity - Details.pdf#nameddest=act-b'])
        self.assertNotIn('<script>', svg)
        self.assertIn(r'\&\_\#', dgraph.tex(graph))
        with tempfile.TemporaryDirectory() as temp:
            dgraph.render_html(graph, temp)
            html = (Path(temp) / 'index.html').read_text()
            self.assertIn('Grundlage → darauf aufbauendes Vorhaben', html)
            self.assertIn('../activity-board/index.html', html)
            self.assertTrue((Path(temp) / 'graph.svg').is_file())

    def test_semantic_groups_keep_routes_clear_and_targets_centered(self):
        keys = ['rnd/sup/ace', 'rnd/sup/ace/ai4X', 'rnd/sup/ace/yap',
                'rnd/gov/noEA', 'rnd/gov/noEA/o2i', 'dbf/sup/cpp',
                'dbf/sup/cpp/sfe', 'dbf/sup/cpp/fnd', 'dbf/imp/cio-fv',
                'dbf/imp/cio-fv/itd-tv', 'dbf/imp/cio-fv/itd-tv/itd-fv',
                'dbf/imp/cio-fv/itd-tv/dbia', 'dbf/imp/ops-fv',
                'dbf/imp/ops-fv/tm-tv', 'dbf/imp/ops-fv/tm-tv/pps',
                'dbf/imp/ops-fv/tm-tv/lift']
        graph = self.parse('ai4X -> o2i\nai4X -> cpp\no2i -> sfe\no2i -> dbia\no2i -> itd-fv\n'
                           'ai4X -> tm-tv\nai4X -> lift\nai4X -> yap', [node(key) for key in keys])
        drawing = dgraph.layout(graph)
        boxes = drawing['boxes']
        self.assertEqual(boxes['rnd/sup/ace'][1], boxes['dbf/sup/cpp'][1])
        self.assertEqual(boxes['dbf/imp/cio-fv'][0], boxes['dbf/imp/ops-fv'][0])
        self.assertLess(boxes['rnd/gov/noEA'][1], boxes['rnd/sup/ace'][1])
        # Separate edges into one project must remain individually traceable,
        # even when authored in the opposite order to their target cards.
        branches = [chain for chain in drawing['chains']
                    if chain[-1] in ('dbf/imp/cio-fv/itd-tv/dbia',
                                     'dbf/imp/cio-fv/itd-tv/itd-fv')]
        branches.sort(key=lambda chain: drawing['positions'][chain[-1]][1])
        upper, lower = (dgraph._curves(chain, drawing) for chain in branches)
        self.assertEqual(len(upper), len(lower))
        for top, bottom in zip(upper, lower):
            for step in range(101):
                t = step/100
                heights = [(1-t)**3*a[1]+3*(1-t)**2*t*c[1]+3*(1-t)*t*t*d[1]+t**3*b[1]
                           for a, c, d, b in (top, bottom)]
                self.assertGreaterEqual(heights[1]-heights[0], 12-1e-9)
        self.assertEqual(drawing, dgraph.layout(graph))
        for chain in drawing['chains']:
            if chain[-1] in ('dbf/sup/cpp', 'dbf/imp/ops-fv/tm-tv'):
                x, y, w, h = boxes[chain[-1]]
                self.assertEqual(dgraph._curves(chain, drawing)[-1][-1], (x-2, y+h/2))
            for a, c, d, b in dgraph._curves(chain, drawing):
                for step in range(1, 100):
                    t = step/100
                    x, y = [(1-t)**3*a[j]+3*(1-t)**2*t*c[j]+3*(1-t)*t*t*d[j]+t**3*b[j]
                            for j in (0, 1)]
                    for key, (bx, by, w, h) in boxes.items():
                        if any(key == end or end.startswith(key+'/') or key.startswith(end+'/')
                               for end in (chain[0], chain[-1])):
                            continue
                        self.assertFalse(bx < x < bx+w and by < y < by+h, (chain, key, x, y))

    def test_fanout_has_separate_ports_and_routes_avoid_unrelated_groups(self):
        keys = ['rnd/sup/ace', 'rnd/sup/ace/ai4X', 'rnd/gov/noEA', 'rnd/gov/noEA/o2i',
                'dbf/sup/cpp', 'dbf/sup/cpp/sfe', 'dbf/sup/cpp/fnd', 'dbf/imp/dbia',
                'dbf/ops/tmtv', 'dbf/ops/tmtv/pps', 'dbf/ops/tmtv/lift']
        graph = self.parse('ai4X -> o2i\nai4X -> cpp\no2i -> sfe\no2i -> dbia\nai4X -> tmtv\nai4X -> lift',
                           [node(key) for key in keys])
        drawing = dgraph.layout(graph)
        departures = [dgraph._curves(chain, drawing)[0][0] for chain in drawing['chains']
                      if chain[0] == 'rnd/sup/ace/ai4X']
        self.assertEqual(len(set(departures)), 3)
        # Fan-out must not cross in the first gap, including the long cpp edge
        # whose corridor lies above tmtv although cpp itself sits below it.
        fanout = []
        for chain in drawing['chains']:
            if chain[0] == 'rnd/sup/ace/ai4X':
                fanout.append(next(curve for curve in dgraph._curves(chain, drawing)
                                   if curve[0][1] != curve[-1][1]))
        fanout.sort(key=lambda curve: curve[-1][1])
        for step in range(101):
            t = step/100
            heights = [(1-t)**3*a[1]+3*(1-t)**2*t*c[1]+3*(1-t)*t*t*d[1]+t**3*b[1]
                       for a, c, d, b in fanout]
            self.assertTrue(all(a < b for a, b in zip(heights, heights[1:])), heights)
        route = next(chain for chain in drawing['chains'] if chain[-1] == 'dbf/sup/cpp')
        project_arrival = dgraph._curves(route, drawing)[-1][-1]
        project_box = drawing['boxes']['dbf/sup/cpp']
        self.assertLess(project_arrival[0], project_box[0])
        self.assertEqual(project_arrival[1], project_box[1]+project_box[3]/2)
        module_route = next(chain for chain in drawing['chains'] if chain[-1] == 'dbf/sup/cpp/sfe')
        module_arrival = dgraph._curves(module_route, drawing)[-1][-1]
        self.assertGreater(project_arrival[1]-module_arrival[1], 12)
        # The covered ai4X -> lift edge is not a separate visible module arrow:
        # tmtv receives its project arrow centrally, from the left.
        tmtv_route = next(chain for chain in drawing['chains'] if chain[-1] == 'dbf/ops/tmtv')
        tmtv_arrival = dgraph._curves(tmtv_route, drawing)[-1][-1]
        tx, ty, tw, th = drawing['boxes']['dbf/ops/tmtv']
        self.assertLess(tmtv_arrival[0], tx)
        self.assertEqual(tmtv_arrival[1], ty+th/2)
        y = drawing['positions'][route[1]][1]
        top, bottom = drawing['boxes']['rnd/gov/noEA'], drawing['boxes']['dbf/ops/tmtv']
        self.assertGreater(y, top[1]+top[3])
        self.assertLess(y, bottom[1])
        for chain in drawing['chains']:
            for a, c, d, b in dgraph._curves(chain, drawing):
                for step in range(1, 100):
                    t = step/100
                    x, y = [(1-t)**3*a[j]+3*(1-t)**2*t*c[j]+3*(1-t)*t*t*d[j]+t**3*b[j]
                            for j in (0, 1)]
                    for key, (bx, by, w, h) in drawing['boxes'].items():
                        if any(key == end or end.startswith(key+'/') or key.startswith(end+'/')
                               for end in (chain[0], chain[-1])):
                            continue
                        self.assertFalse(bx < x < bx+w and by < y < by+h, (chain, key))


if __name__ == '__main__':
    unittest.main()
