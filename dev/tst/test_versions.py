"""Versions are explicit board views; activity identity and relationships stay intact."""

from fixtures import source_text

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yap import board, content, documents, overview, performance_lanes, publication_links


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='yap-versions-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.track({'#v0.2': '{status: released}', '#v0.3': '{status: wip, priority: p2}'})
        for key in ('area', 'area/sup', 'area/sup/project', 'area/sup/project/other'):
            self.write(f'pfo/act/{key}/{key.rsplit("/", 1)[-1]}.md',
                       f'---\ntitle: {key.rsplit("/", 1)[-1]}\n---\n')
        self.write('pov/report/.perspective.yaml', '''{"schema": 1, "title": "Report", "entries": [{"id": "p000001", "name": "Project", "entries": [{"id": "p000002", "name": "Module", "target": {"entry": "area--sup--project--module"}}, {"id": "p000003", "name": "Other", "target": {"entry": "area--sup--project--other"}}]}]}''')
        self.path = 'pfo/act/area/sup/project/module/module.md'
        self.prefix = '---\nacronym: MOD\ntitle: Module\nboard-caption: Shared caption\n---\n'
        self.body = '''## v0.2 {#v0.2 .version}

Released content.

## v0.3 {#v0.3 .version}

Current work.
'''
        self.write(self.path, self.prefix + self.body)
        self.write('pfo/asp/goals.md', '''---
title: Goals
tracking:
  result: {status: active}
---
''')
        self.write('pfo/asp/obj/result/delivered.md', '---\nkey: delivered\ntitle: Delivered\n'
                   'measure: Evidence\nunit: result\ntarget: 1\nactivities: [area--sup--project--module]\n---\n')
        self.write('pfo/asp/obj/result.md', '---\nkey: result\ntitle: Result\n---\n')

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source_text(name, value))

    def track(self, entries):
        tracking = '\n'.join('  "area--sup--project--module' + suffix + '": ' + value
                             for suffix, value in entries.items())
        self.write('pfo/act/act.md', '---\ntitle: Activities\ntracking: ' + ('\n' + tracking if tracking else '{}') +
                   '\nmembers:\n  area--sup--project: [area--sup--project--module, area--sup--project--other]\nreport-perspective: report\ndgraph:\n  spec: |\n    area--sup--project--other -> area--sup--project--module\n---\n')

    def load(self):
        return content.load(self.root)

    def cards(self, model):
        return [card for row in board.display_rows(board.lanes(model))
                for cards in row['cells'].values() for card in cards
                if card['key'] == 'area--sup--project--module']

    def test_versions_preserve_one_activity_and_all_relationships(self):
        model = self.load()
        self.write(self.path, self.prefix + self.body.replace(' .version', ''))
        self.track({'': '{status: on hold, priority: p1}'})
        ordinary = self.load()
        self.assertEqual([n['key'] for n in model['nodes']], [n['key'] for n in ordinary['nodes']])
        self.assertEqual([n['key'] for n in overview.activity_nodes(model)],
                         [n['key'] for n in overview.activity_nodes(ordinary)])
        self.assertEqual(model['dgraph'], ordinary['dgraph'])
        self.assertEqual(model['goals'], ordinary['goals'])
        activity = next(n for n in model['nodes'] if n['key'].endswith('--module'))
        self.assertEqual((activity['status'], activity['priority']), ('', ''))
        self.assertEqual(len(activity['versions']), 2)
        self.assertEqual(len(self.cards(ordinary)), 1)
        self.assertEqual(self.cards(ordinary)[0]['status'], 'on hold')

    def test_cards_replace_summary_share_lane_and_link_to_sections_in_all_boards(self):
        model = self.load()
        before = deepcopy(model)
        rows = board.lanes(model)
        cards = self.cards(model)
        self.assertEqual({(c['version'], c['status'], c['priority']) for c in cards},
                         {('v0.2', 'released', ''), ('v0.3', 'wip', 'p2')})
        self.assertTrue(all(c['title'] == 'MOD' and c['caption'] == 'Shared caption' for c in cards))
        module_rows = [row for row in board.display_rows(rows)
                       if any(c['key'].endswith('--module') for cell in row['cells'].values() for c in cell)]
        self.assertEqual(len(module_rows), 1)
        self.assertEqual(module_rows[0]['key'], 'p000001')
        self.assertFalse(module_rows[0]['cells']['on hold'])
        out = self.root / 'output'
        board.render_html(rows, out)
        html = (out / 'index.html').read_text()
        embedded = performance_lanes.render(model, ['area--sup--project--module'])
        self.assertEqual(embedded.count('data-activity="area--sup--project--module"'), 2)
        for card in cards:
            self.assertIn(publication_links.activity_pdf(card), embedded)
            self.assertIn(publication_links.activity_pdf(card), html)
            self.assertIn('<span class="card-version">' + card['version'] + '</span>', embedded)
        parent = performance_lanes.render(model, ['area--sup--project'])
        self.assertNotIn('data-activity="area--sup--project--module"', parent)
        tex = board.tex(rows)
        for card in cards:
            self.assertIn(r'\scriptsize\color{namMuted}' + card['version'], tex)
        self.assertEqual(model, before)

    def test_only_public_marked_sections_create_cards_and_removal_is_authoritative(self):
        extra = '''
## Ordinary {status=ibx}

::: internal

## Secret {.version status=invalid}

:::
'''
        self.write(self.path, self.prefix + self.body + extra)
        self.assertEqual(len(self.cards(self.load())), 2)
        self.write(self.path, self.prefix + self.body.split('## v0.3')[0] + extra)
        with self.assertRaisesRegex(ValueError, 'unknown public version anchor'):
            self.load()
        self.track({'#v0.2': '{status: released}'})
        self.assertEqual([c['version'] for c in self.cards(self.load())], ['v0.2'])
        self.write(self.path, self.prefix + extra)
        self.track({})
        self.assertEqual([c['version'] for c in self.cards(self.load())], [''])

    def test_invalid_version_sections_fail_before_rendering(self):
        for body, error in (
            ('## v0.2 {.version status=released}', 'belong in'),
            ('## v0.2 {.version priority=p1}', 'belong in'),
            ('## v0.2 {.version priority=""}', 'belong in'),
            ('### v0.2 {.version}', '## heading'),
            ('## {.version}', 'version name'),
            ('## v0.2 {#one .version}\n\n## v0.2 {#two .version}', 'duplicate version'),
        ):
            with self.subTest(body=body):
                self.write(self.path, self.prefix + body + '\n')
                with self.assertRaisesRegex(ValueError, error):
                    self.load()

    def test_central_version_tracking_rejects_ambiguous_or_incomplete_assignments(self):
        defaults = {'#v0.2': '{status: released}', '#v0.3': '{status: wip}'}
        cases = [
            ({**defaults, '': '{}'}, 'versioned activities must be tracked only'),
            ({**defaults, '': '{status: on hold}'}, 'versioned activities must be tracked only'),
            ({'#v0.2': '{status: released}'}, 'each public version requires a status'),
            ({**defaults, '#v0.3': '{priority: p1}'}, 'each public version requires a status'),
            ({**defaults, '#v0.3': '{status: ""}'}, 'each public version requires a status'),
            ({**defaults, '#v0.3': '{status: done}'}, 'unknown status'),
            ({**defaults, '#v0.3': '{status: wip, priority: p9}'}, 'unknown priority'),
            ({**defaults, '#v0.2': '{status: released, priority: p1}'}, 'released does not allow priority'),
            ({**defaults, '#v0.2': '{status: released, priority: ""}'}, 'released does not allow priority'),
            ({**defaults, '#missing': '{status: wip}'}, 'unknown public version anchor'),
            ({**defaults, '#': '{status: wip}'}, 'unknown public version anchor'),
            ({**defaults, '#ordinary': '{status: wip}'}, 'unknown public version anchor'),
            ({**defaults, '#secret': '{status: wip}'}, 'unknown public version anchor'),
            ({**defaults, '/missing#v1': '{status: wip}'}, 'unknown activity key'),
        ]
        self.write(self.path, self.prefix + self.body +
                   '\n## Ordinary {#ordinary}\n\n::: internal\n\n## Secret {#secret .version}\n\n:::\n')
        for entries, error in cases:
            with self.subTest(entries=entries):
                self.track(entries)
                with self.assertRaisesRegex(ValueError, error):
                    self.load()

    def test_anchor_survives_label_changes_and_pdf_uses_central_tracking(self):
        self.write(self.path, self.prefix + self.body.replace('## v0.3', '## Next release'))
        self.track({'#v0.2': '{status: released}', '#v0.3': '{status: on hold, priority: p1}'})
        model = self.load()
        before = deepcopy(model)
        current = next(c for c in self.cards(model) if c['version'] == 'Next release')
        self.assertTrue(current['id'].endswith('--v0.3'))
        self.assertEqual((current['status'], current['priority']), ('on hold', 'p1'))
        report = documents.activity(model, Path('.yap/local/site'))
        versions = {content.plain(h['c'][2]): dict(h['c'][1][2])
                    for h in content.walk(report['blocks'])
                    if h['t'] == 'Header' and 'version' in h['c'][1][1]}
        self.assertEqual(versions['Next release'], {'status': 'on hold', 'priority': 'p1'})
        self.assertEqual(versions['v0.2'], {'status': 'released'})
        self.assertEqual(model, before)

    def test_same_status_uses_explicit_priority_then_section_order(self):
        self.write(self.path, self.prefix + '''## v1 {#v1 .version}

## v2 {#v2 .version}

## v3 {#v3 .version}
''')
        self.track({'#v1': '{status: wip}', '#v2': '{status: wip, priority: p2}',
                    '#v3': '{status: wip, priority: p2}'})
        self.assertEqual([c['version'] for c in self.cards(self.load())], ['v2', 'v3', 'v1'])
