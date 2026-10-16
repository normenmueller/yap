"""Preview measurement semantics and source-backed nested activity lanes."""

from fixtures import report_model

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yap import content, performance, performance_lanes


class PerformancePreviewTests(unittest.TestCase):
    def setUp(self):
        self.nodes = []
        for key in ('rnd', 'rnd/sup', 'rnd/sup/ace', 'rnd/sup/ace/a', 'rnd/sup/ace/b'):
            self.nodes.append(dict(key=key, parent=key.rpartition('/')[0], id='act-'+key.replace('/', '--'),
                                   title=key.rsplit('/', 1)[-1], status='wip' if key.endswith('/a') else '',
                                   priority='p2' if key.endswith('/a') else '', depth=key.count('/')+1))
        self.goals = [dict(key=key, id='goal-'+key, title=key, status=status, activities=[])
                      for key, status in [('delivery', 'active'), ('training', 'on hold'), ('value', 'closed')]]
        self.spec = """key: result
title: "Outcome <proof>"
measure: "Confirmed outcomes, not commits."
unit: "%"
metric: "Anteil bestätigter Ergebnisse"
deadline: "2026-12-31"
target: 80
current: 40
previous: 20
activities: [rnd/sup/ace/a]
"""

    def parse(self, spec):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'result.md'
            path.write_text('---\n'+spec+'---\n')
            return {'delivery': [performance.parse(content.read(path)['meta'], self.nodes, str(path))]}

    def test_invalid_metrics_and_stale_references_fail(self):
        for before, after in [('target: 80', 'target: 0'), ('2026-12-31', '2026-02-30'), ('current: 40', 'current: NaN'),
                              ('current: 40', 'current: -2'), ('rnd/sup/ace/a]', 'missing]'),
                              ('key: result', 'key: invalid/key'),
                              ('current: 40\n', '')]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                self.parse(self.spec.replace(before, after))
        with self.assertRaises(ValueError):
            self.parse('')

    def test_preview_does_not_create_actual_assignments_or_achieve_closed_goals(self):
        preview = self.parse(self.spec)
        preview['delivery'][0]['title'] = 'Outcome <proof>'
        for key in ('training', 'value'):
            preview[key] = deepcopy(preview['delivery'])
            preview[key][0]['current'] = 80
        self.goals[0]['activities'] = [{'key':'rnd/sup/ace/b', 'anchor':''}]
        model = dict(nodes=self.nodes, goals=self.goals, key_results=preview, board_sequence=['sup'])
        model = report_model(model)
        before = deepcopy(model)
        html = performance.render(model)
        self.assertEqual(model, before)
        for marker in ('Konzeptvorschau', 'Vorschlag', 'Vorschläge', 'Demo', 'Szenario'):
            self.assertNotIn(marker, html)
        self.assertIn('31.12.2026', html)
        self.assertIn('Anteil bestätigter Ergebnisse', html)
        self.assertIn('Outcome &lt;proof&gt;', html)
        self.assertIn('class="okr-section okr-active" open', html)
        self.assertNotRegex(html, r'<details class="okr-(?:objective|kr)"[^>]*\bopen\b')
        self.assertIn('data-kr="delivery/result"', html)
        self.assertIn('okr-orb', html)
        self.assertIn('Mit diesem Objective verbunden:', html)
        for key in ('training', 'value'):
            section = html.split('data-objective="'+key+'"', 1)[1].split('</details></div></details>', 1)[0]
            self.assertNotIn('Ergebnisse erreicht', section)
            self.assertIn('Messung ausgesetzt', section)
            self.assertNotIn('okr-delta', section)

    def test_filtered_lanes_preserve_explicit_identity_and_own_tracking(self):
        self.nodes[2].update(status='on hold', priority='p4', next=2)
        model = dict(nodes=self.nodes, goals=self.goals, board_sequence=['sup'])
        model = report_model(model)
        html = performance_lanes.render(model, ['rnd/sup/ace/a'])
        self.assertIn('data-group="sup"', html)
        self.assertIn('data-group="rnd"', html)
        self.assertIn('data-lane="rnd/sup/ace"', html)
        self.assertIn('data-activity="rnd/sup/ace/a"', html)
        self.assertNotIn('data-activity="rnd/sup/ace/b"', html)
        self.assertIn('p2', html)
        self.assertIn('aria-label="WIP"', html)
        before = deepcopy(model)
        changed = performance_lanes.render(model, ['rnd/sup/ace'])
        self.assertIn('data-activity="rnd/sup/ace"', changed)
        self.assertNotIn('data-activity="rnd/sup/ace/a"', changed)
        self.assertNotIn('data-activity="rnd/sup/ace/b"', changed)
        self.assertIn('p4', changed)
        self.assertIn('next-marker', changed)
        self.assertIn('aria-label="On hold"><ul class="kr-activity-list"><li', changed)
        combined = performance_lanes.render(model, ['rnd/sup/ace', 'rnd/sup/ace/a'])
        self.assertEqual(combined.count('data-activity="rnd/sup/ace"'), 1)
        self.assertEqual(combined.count('data-activity="rnd/sup/ace/a"'), 1)
        self.assertNotIn('data-activity="rnd/sup/ace/b"', combined)
        self.assertEqual(model, before)
        self.assertNotIn('data-activity=', performance_lanes.render(model, []))

    def test_hidden_parent_does_not_substitute_its_modules(self):
        model = report_model(dict(nodes=self.nodes, goals=self.goals, board_sequence=['sup']))
        html = performance_lanes.render(model, ['rnd/sup/ace'])
        self.assertNotIn('data-activity=', html)

    def test_missing_measurements_are_not_reported_as_zero_achievement(self):
        results = self.parse(self.spec)
        kr = results['delivery'][0]
        kr.pop('current')
        kr.pop('previous')
        model = dict(nodes=self.nodes, goals=self.goals, key_results=results, board_sequence=['sup'])
        model = report_model(model)
        html = performance.render(model)
        self.assertIn('Noch kein Messstand', html)
        self.assertNotIn('Ergebnisse erreicht', html)
        self.assertNotIn('class="okr-progress"', html)
        other = deepcopy(kr)
        other.update(key='other-result', current=80)
        results['delivery'].append(other)
        html = performance.render(model)
        self.assertIn('Messstand unvollständig', html)
        self.assertIn('Messstand für 1 von 2 Key Results', html)
        self.assertNotIn('Ergebnisse erreicht', html)
        kr['current'] = 0
        html = performance.render(model)
        self.assertNotIn('Messstand unvollständig', html)
        self.assertIn('1 von 2<small>Ergebnissen erreicht', html)


if __name__ == '__main__':
    unittest.main()
