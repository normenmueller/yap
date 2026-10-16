"""Review alternatives preserve relationships and avoid unrelated containers."""

from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from yap import dgraph
import test_dgraph as fixtures


class DependencyGraphVariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        keys = ['rnd/sup/ace', 'rnd/sup/ace/ai4X', 'rnd/sup/ace/yap',
                'rnd/gov/noEA', 'rnd/gov/noEA/o2i', 'dbf/sup/cpp',
                'dbf/sup/cpp/sfe', 'dbf/sup/cpp/fnd', 'dbf/imp/cio-fv',
                'dbf/imp/cio-fv/itd-tv', 'dbf/imp/cio-fv/itd-tv/dbia',
                'dbf/imp/cio-fv/itd-tv/itd-fv', 'dbf/imp/ops-fv',
                'dbf/imp/ops-fv/tm-tv', 'dbf/imp/ops-fv/tm-tv/pps',
                'dbf/imp/ops-fv/tm-tv/lift']
        cls.graph = fixtures.DependencyGraphTests().parse(
            'ai4X -> o2i\nai4X -> cpp\no2i -> sfe\no2i -> dbia\n'
            'ai4X -> tm-tv\nai4X -> lift\nai4X -> yap', [fixtures.node(key) for key in keys])

    def test_two_distinct_arrangements_preserve_authored_directions_and_clearance(self):
        expected = {(chain[0], chain[-1]) for chain in dgraph.layout(self.graph)['chains']}
        for variant in dgraph.VARIANTS:
            with self.subTest(variant=variant):
                drawing = dgraph.layout(self.graph, variant)
                boxes = drawing['boxes']
                ace, cpp, gov, imp = (boxes[key] for key in
                    ('rnd/sup/ace', 'dbf/sup/cpp', 'rnd/gov/noEA', 'dbf/imp/cio-fv'))
                # Containers may differ in width; their column centers align.
                self.assertEqual(ace[0]+ace[2]/2, cpp[0]+cpp[2]/2)
                self.assertLess(cpp[1]+cpp[3], ace[1])
                if variant == 'semantic':
                    self.assertLess(ace[0], imp[0])
                    self.assertLess(imp[0], gov[0])
                else:
                    self.assertLess(ace[0], gov[0])
                    self.assertLess(gov[0], imp[0])
                    self.assertLess(cpp[1]+cpp[3]/2, gov[1]+gov[3]/2)
                    self.assertLess(gov[1]+gov[3]/2, ace[1]+ace[3]/2)
                self.assertEqual(expected, {(chain[0], chain[-1]) for chain in drawing['chains']})
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
                                self.assertFalse(bx < x < bx+w and by < y < by+h,
                                                 (variant, chain, key, x, y))

    def test_inline_svg_ids_are_unique_and_export_remains_default(self):
        seen = set()
        for variant in (None, *dgraph.VARIANTS):
            root = ET.fromstring(dgraph.svg(self.graph, variant))
            identifiers = {item.attrib['id'] for item in root.iter() if 'id' in item.attrib}
            self.assertFalse(seen & identifiers)
            seen.update(identifiers)
        with tempfile.TemporaryDirectory() as temp:
            dgraph.render_html(self.graph, temp)
            self.assertEqual((Path(temp) / 'graph.svg').read_text(), dgraph.svg(self.graph))
            page = (Path(temp) / 'index.html').read_text()
            self.assertIn('A · Wirkungsfeld', page)
            self.assertIn('B · Versetzte Gruppen', page)
            self.assertIn('Dieselben Vorhaben und Abhängigkeiten', page)

    def test_identifier_namespacing_does_not_change_authored_names_or_links(self):
        graph = fixtures.DependencyGraphTests().parse('arrow -> graph-title',
            [fixtures.node('arrow'), fixtures.node('graph-title')])
        result = dgraph.svg(graph, 'semantic')
        self.assertIn('#nameddest=act-arrow"', result)
        self.assertIn('#nameddest=act-graph-title"', result)
        self.assertIn('>arrow</text>', result)
        self.assertIn('>graph-title</text>', result)


if __name__ == '__main__':
    unittest.main()
