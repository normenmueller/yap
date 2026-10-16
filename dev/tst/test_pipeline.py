"""Behavior checks for authoring, portable outputs and incremental publication."""

from fixtures import source_text

from contextlib import redirect_stdout
from io import StringIO
from html.parser import HTMLParser
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote, unquote, urlsplit

from yap import board, content, dgraph, documents, files, views
from yap import build as yap


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='yap-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.application = self.root / 'application-fixture'
        (self.application / 'dev/src').mkdir(parents=True)
        (self.application / 'dev/src/tool.py').write_text('# renderer dependency')
        application_patch = patch.object(yap, 'APPLICATION', self.application)
        application_patch.start()
        self.addCleanup(application_patch.stop)
        asset_root = self.application / 'dev/acc/assets'
        shutil.copytree(yap.home.RESOURCE_ASSETS, asset_root)
        asset_patch = patch.object(yap.home, 'RESOURCE_ASSETS', asset_root)
        asset_patch.start()
        self.addCleanup(asset_patch.stop)
        self.write('pfo/act/act.md', '---\ntitle: Activity\ndate: fixed\n---\n')
        self.write('pfo/act/x/x.md', '---\ntitle: X\nsubtitle: First\n---\n\n## Detail\n\nA body.\n')
        self.write('pfo/okr/goals.md', """---
title: mPM
subtitle: Ziele und Beiträge
author: Example author
lang: de-DE
sequence: [a, b]
tracking:
  a: {status: active}
  b: {status: active}
---
## Annex

Historical notes excluded.
""")
        self.write('pfo/okr/obj/a.md', """---
title: Goal A
key: a
---
**Contributions**

[Detail](../../act/x/x.md#detail)
""")
        self.write('pfo/okr/obj/b.md', """---
title: Goal B
key: b
---
A second goal.
""")
        self.write('pfo/okr/obj/a/contribution.md', '---\nkey: contribution\ntitle: Contribution\n'
                   'measure: Evidence\nunit: result\ntarget: 1\nactivities: [x]\n---\n')

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source_text(name, value))
        return path

    def load(self):
        return content.load(self.root)

    def test_activity_notes_require_existing_assignment_and_section(self):
        for key, section, error in [('x', 'history', None),
                                    ('missing', 'history', 'not linked'),
                                    ('x', 'missing', 'existing level-two section')]:
            self.write('pfo/okr/obj/a.md', '---\ntitle: Goal A\nkey: a\nactivity-notes:\n'
                       f'  {key}:\n    text: "Earlier runs see"\n    section: {section}\n'
                       '---\n\n## Contributions {#history}\n\nHistorical work.\n')
            with self.subTest(key=key, section=section):
                if error:
                    with self.assertRaisesRegex(ValueError, error):
                        self.load()
                else:
                    model = self.load()
                    self.assertEqual(len(model['goals'][0]['activities']), 1)
                    cards = views._goal_cards(model)
                    self.assertIn('class="activity-note"', cards)
                    self.assertIn('href="#goal-a--history"', cards)
                    self.assertIn('id="goal-a--history"', cards)

    def test_objective_activities_follow_kr_edits_without_inferred_relations(self):
        self.write('pfo/act/y/y.md', '---\ntitle: "Y"\n---\n')
        self.write('pfo/act/z/z.md', '---\ntitle: Z\n---\n')
        self.write('pfo/act/act.md', '---\ntitle: Activity\nmembers:\n  x: ["y"]\n'
                   'dgraph:\n  spec: |\n    z -> x\n---\n')
        template = ('---\nkey: {key}\ntitle: Result\nmeasure: Evidence\nunit: result\n'
                    'target: 1\nactivities:\n{entries}\n---\n')
        first = self.root / 'pfo/okr/obj/a/contribution.md'
        first.write_text(template.format(key='contribution', entries='  - x\n  - x\n'
            '  - "[Linked work](https://example.org/work)"\n  - {title: Named contribution}'))
        second = self.write('pfo/okr/obj/a/second.md', template.format(key='second', entries='  - x\n  - z'))
        self.write('pfo/okr/obj/b/shared.md', template.format(key='shared', entries='  - x'))

        def assigned():
            model = self.load()
            return {g['key']: [a['key'] for a in g['activities']] for g in model['goals']}

        self.assertEqual(assigned(), {'a': ['x', 'z'], 'b': ['x']})
        goal = self.root / 'pfo/okr/obj/a.md'
        goal.write_text(goal.read_text().replace('key: a', 'key: a\nkr-sequence: [second, contribution]'))
        second.write_text(template.format(key='second', entries='  - z\n  - x'))
        self.assertEqual(assigned(), {'a': ['z', 'x'], 'b': ['x']})
        # Removing one shared contribution does not remove another KR's link.
        first.unlink()
        goal.write_text(goal.read_text().replace('kr-sequence: [second, contribution]', 'kr-sequence: [second]'))
        self.assertEqual(assigned(), {'a': ['z', 'x'], 'b': ['x']})
        second.write_text(template.format(key='second', entries='  - z'))
        self.assertEqual(assigned(), {'a': ['z'], 'b': ['x']})
        second.unlink()
        goal.write_text(goal.read_text().replace('\nkr-sequence: [second]', ''))
        # A prose link and dependency/membership edges never retain a removed KR link.
        self.assertEqual(assigned(), {'a': [], 'b': ['x']})
        first.write_text(template.format(key='contribution', entries='  - missing'))
        with self.assertRaisesRegex(ValueError, 'unknown activity'):
            self.load()

    def test_released_activity_tracking_and_sections_disallow_priority(self):
        for priority in ('p1', '""', ''):
            self.write('pfo/act/act.md', '---\ntitle: Activity\ntracking:\n  x:\n'
                       '    status: released\n    priority: ' + priority + '\n---\n')
            with self.subTest(priority=priority), self.assertRaisesRegex(ValueError, 'released does not allow priority'):
                self.load()
        self.write('pfo/act/act.md', '---\ntitle: Activity\ntracking:\n  x: {status: released}\n---\n')
        self.assertEqual(self.load()['nodes'][0]['status'], 'released')
        source = self.root / 'pfo/act/x/x.md'
        source.write_text(source.read_text() + '\n## Release {status=released priority=p2}\n')
        with self.assertRaisesRegex(ValueError, 'released does not allow priority'):
            self.load()

    def test_composed_pdf_targets_reject_parent_child_and_goal_collisions(self):
        node = self.root / 'pfo/act/x/x.md'
        original = node.read_text()
        node.write_text(original + '\n## Additional heading {#y}\n')
        self.write('pfo/act/x/y/y.md', '---\ntitle: "Y"\n---\n')
        with self.assertRaisesRegex(ValueError, r'Duplicate PDF destination act-x--y:.*x.md#y.*y.md'):
            self.load()
        node.write_text(original)
        self.load()

        goal = self.root / 'pfo/okr/obj/a.md'
        goal.write_text(goal.read_text() + '\n## Additional heading {#b}\n')
        control = self.root / 'pfo/okr/goals.md'
        control.write_text(control.read_text().replace('tracking:', 'tracking:\n  a--b: {status: active}'))
        self.write('pfo/okr/obj/ab.md', '---\ntitle: Other\nkey: a--b\n---\n')
        with self.assertRaisesRegex(ValueError, r'Duplicate PDF destination goal-a--b:.*a.md#b.*ab.md'):
            self.load()

    def test_source_move_preserves_identity_tracking_and_goal_reference(self):
        self.write('pfo/act/z/z.md', '---\ntitle: Z\n---\n')
        self.write('pfo/act/act.md', '---\ntitle: Activity\ntracking:\n  x: {status: wip}\n---\n')
        before = self.load()
        (self.root / 'pfo/act/x').rename(self.root / 'pfo/act/z/x')
        with self.assertRaisesRegex(ValueError, 'Link target is missing'):
            self.load()
        goal = self.root / 'pfo/okr/obj/a.md'
        goal.write_text(goal.read_text().replace('../act/x/', '../act/z/x/'))
        model = self.load()
        x = next(n for n in model['nodes'] if n['key'] == 'x')
        self.assertEqual((x['id'], x['status']), ('act-x', 'wip'))
        self.assertNotIn('parent', x)
        self.assertEqual(model['goals'][0]['activities'], before['goals'][0]['activities'])
        goal.write_text(goal.read_text().replace('[Detail](../../act/z/x/x.md#detail)', 'No link.'))
        control = self.root / 'pfo/okr/goals.md'
        (self.root / 'pfo/okr/obj/a/contribution.md').unlink()
        shutil.rmtree(self.root / 'pfo/act/z/x')
        with self.assertRaisesRegex(ValueError, 'unknown activity key'):
            self.load()
        self.write('pfo/act/act.md', '---\ntitle: Activity\n---\n')
        self.assertEqual([n['key'] for n in self.load()['nodes']], ['z'])

    def test_qualified_module_keys_across_tracking_graphs_links_and_publication(self):
        self.write('pfo/act/x/x.md', '---\nkind: activity\nkey: cpp/sfe\ntitle: SFE\n---\n'
                   '## v1 {#detail .version}\n\n[Resource](res/example.txt)\n')
        self.write('pfo/act/elsewhere/elsewhere.md',
                   '---\nkind: activity\nkey: noEA/o2i\ntitle: O2I\n---\n')
        self.write('pfo/act/act.md', '---\ntitle: Activity\nreport-perspective: report\n'
                   'tracking:\n  "cpp/sfe#detail": {status: on hold, priority: p1, next: 1}\n'
                   '  noEA/o2i: {status: wip, priority: p2}\n'
                   'dgraph:\n  spec: |\n    noEA/o2i -> cpp/sfe\n---\n')
        self.write('pfo/okr/obj/a/contribution.md', '---\nkey: contribution\ntitle: Contribution\n'
                   'measure: Agreed result\nunit: result\ntarget: 1\nactivities: [cpp/sfe]\n---\n')
        self.write('pov/report/.perspective.yaml', json.dumps({'schema': 1, 'title': 'Report', 'entries': [
            {'id': 'p000001', 'name': 'Module', 'target': {'entry': 'cpp/sfe'}}]}))
        self.write('pfo/act/x/res/example.txt', 'Public resource')
        external = self.root / 'external'
        external.mkdir()
        self.write('.yap/cfg/machine.json', json.dumps({'links': {'cpp/sfe': {'repo': 'external'}}}))
        plan, warnings = files.link_plan(self.root)
        self.assertEqual(warnings, [])
        files.sync_links(plan)
        self.assertEqual((self.root / 'pfo/act/x/repo').resolve(), external.resolve())

        model = self.load()
        self.assertEqual(model['members'], {})  # Prefixes never create membership.
        self.assertEqual(model['dgraph']['effective_edges'], [('noEA/o2i', 'cpp/sfe')])
        self.assertEqual(model['goals'][0]['activities'], [dict(key='cpp/sfe', anchor='', label='SFE')])
        self.assertEqual(model['key_results']['a'][0]['activities'], ['cpp/sfe'])
        self.assertEqual(model['report']['nodes'][0]['entry'], 'cpp/sfe')
        node = next(n for n in model['nodes'] if n['key'] == 'cpp/sfe')
        self.assertEqual((node['id'], node['resource_root']), ('act-cpp/sfe', 'cpp/sfe'))
        self.assertEqual(node['versions'][0]['next'], 1)
        self.assertEqual(set(files.resource_plan(self.root, model)), {'res/cpp/sfe/example.txt'})
        document = documents.activity(model, self.root / 'stage')
        target = documents.pdf_target('act-cpp/sfe--detail')
        self.assertTrue(any(i['t'] == 'Header' and i['c'][1][0] == target for i in content.walk(document)))
        board.render_html(board.lanes(model), self.root / 'board')
        self.assertIn('#nameddest=' + target, (self.root / 'board/index.html').read_text())

        # Explicit legacy publication destinations survive the naming change.
        control = self.root / 'pfo/act/act.md'
        control.write_text(control.read_text().replace('dgraph:',
            'publication:\n  cpp/sfe: {id: act-legacy-sfe, resource-root: legacy/sfe}\ndgraph:'))
        node = next(n for n in self.load()['nodes'] if n['key'] == 'cpp/sfe')
        self.assertEqual((node['id'], node['resource_root']), ('act-legacy-sfe', 'legacy/sfe'))

    def test_saved_report_orders_sources_without_changing_canonical_identity(self):
        self.write('pfo/act/z/z.md', '---\ntitle: Z\n---\n')
        self.write('pfo/act/act.md', '---\ntitle: Activity\nreport-perspective: report\n---\n')
        definition = {'schema': 1, 'title': 'Report', 'entries': [
            {'id': 'p000001', 'name': key, 'target': {'entry': key}} for key in ['z']]}
        path = self.write('pov/report/.perspective.yaml', json.dumps(definition))
        model = self.load()
        self.assertEqual([n['key'] for n in model['nodes']], ['x', 'z'])
        self.assertEqual([p['entry'] for p in model['report']['nodes'] if p['document']], ['z', 'x'])
        self.assertEqual(json.loads(path.read_text()), definition)
        self.assertIn('Nicht eingeordnet', content.plain(documents.activity(model, Path('stage'))['blocks']))

    def test_obsolete_path_ordering_is_rejected_in_favor_of_saved_perspective(self):
        for fields in ('sequence: {}', 'board-sequence: [sup]'):
            self.write('pfo/act/act.md', '---\ntitle: Activity\n'+fields+'\n---\n')
            with self.assertRaisesRegex(ValueError, 'saved report perspective'):
                self.load()

    def test_explicit_membership_validates_unknown_keys_and_cycles(self):
        for value, error in (('x: [missing]', 'unknown member'), ('x: [x]', 'cycle')):
            self.write('pfo/act/act.md', '---\ntitle: Activity\nmembers:\n  '+value+'\n---\n')
            with self.assertRaisesRegex(ValueError, error):
                self.load()

    def test_tracking_is_independent_of_sequence_and_not_inherited(self):
        self.write('pfo/act/z/z.md', '---\ntitle: Z\n---\n')
        self.write('pfo/act/x/child/child.md', '---\ntitle: Child\n---\n\n## Version {status=released}\n')
        prefix = '---\ntitle: Activity\n'
        report = self.write('pfo/act/act.md', prefix +
            'tracking:\n  x: {status: on hold, priority: p2}\n  z: {priority: p1}\n---\n')
        model = self.load()
        expected = [('x', 'on hold', 'p2'), ('x--child', '', ''), ('z', '', 'p1')]
        self.assertEqual([(n['key'], n['status'], n['priority']) for n in model['nodes']], expected)
        ast = documents.activity(model, Path('stage'))
        headings = {item['c'][1][0]: dict(item['c'][1][2])
                    for item in content.walk(ast) if item['t'] == 'Header'}
        self.assertEqual((headings['act-x']['status'], headings['act-x']['priority']), ('on hold', 'p2'))
        self.assertEqual(headings['act-x--child--version']['status'], 'released')
        report.write_text(prefix +
            'tracking:\n  z: {priority: p1}\n  x: {status: on hold, priority: p2}\n---\n')
        self.assertEqual([(n['key'], n['status'], n['priority']) for n in self.load()['nodes']], expected)
        report.write_text(prefix + 'tracking:\n  x: {status: wip}\n---\n')
        self.assertEqual([(n['key'], n['status'], n['priority']) for n in self.load()['nodes']],
                         [('x', 'wip', ''), ('x--child', '', ''), ('z', '', '')])
        report.write_text(prefix + '---\n')
        self.assertTrue(all(not n['status'] and not n['priority'] for n in self.load()['nodes']))

    def test_invalid_tracking_and_local_assignments_are_explicit(self):
        cases = (
            ('tracking: [x]', 'mapping'),
            ('tracking:\n  x: wip', 'mapping'),
            ('tracking:\n  x: {prio: p1}', 'unknown field'),
            ('tracking:\n  x: {status: done}', 'unknown status'),
            ('tracking:\n  x: {status: planned}', 'unknown status'),
            ('tracking:\n  x: {priority: p5}', 'unknown priority'),
            ('tracking:\n  x: {status: [wip]}', 'single text value'),
            ('tracking:\n  x: {priority: true}', 'single text value'),
            ('tracking:\n  missing: {status: wip}', 'unknown activity key'),
            ('tracking:\n  ./x: {status: wip}', 'unknown activity key'),
            ('tracking:\n  .: {status: wip}', 'unknown activity key'),
        )
        for value, message in cases:
            with self.subTest(value=value):
                self.write('pfo/act/act.md', f'---\ntitle: Activity\n{value}\n---\n')
                with self.assertRaisesRegex(ValueError, message):
                    self.load()
        self.write('pfo/act/act.md', '---\ntitle: Activity\ntracking: {}\n---\n')
        node = self.root / 'pfo/act/x/x.md'
        original = node.read_text()
        for value in ('status: wip', 'priority: p2', 'tracking: {}'):
            with self.subTest(value=value):
                node.write_text(original.replace('title: X', f'title: X\n{value}'))
                with self.assertRaisesRegex(ValueError, '(maintained|belongs).*pfo/act/act.md'):
                    self.load()
        node.write_text(original)
        self.write('pfo/act/z/z.md', '---\ntitle: Z\n---\n')
        report = self.write('pfo/act/act.md', '---\ntitle: Activity\ntracking:\n  z: {status: wip}\n---\n')
        (self.root / 'pfo/act/z').rename(self.root / 'pfo/act/x/z')
        self.assertEqual(self.load()['nodes'][-1]['status'], 'wip')
        shutil.rmtree(self.root / 'pfo/act/x/z')
        with self.assertRaisesRegex(ValueError, 'unknown activity key'):
            self.load()

    def test_invalid_source_and_broken_anchor_are_explicit(self):
        self.write('pfo/act/x/extra.md', 'Extra')
        self.assertEqual([n['key'] for n in self.load()['nodes']], ['x'])
        (self.root / 'pfo/act/x/extra.md').unlink()
        goals = self.root / 'pfo/okr/obj/a.md'
        goals.write_text(goals.read_text().replace('#detail)', '#missing)'))
        with self.assertRaisesRegex(ValueError, 'Anchor is missing'):
            self.load()

    def test_acronym_labels_board_without_changing_report_title_or_links(self):
        path = self.root / 'pfo/act/x/x.md'
        original = path.read_text().replace('title: X', 'title: Full Activity Title')
        path.write_text(original.replace('title: Full Activity Title',
            'title: Full Activity Title\n# PRIVATE YAML COMMENT\nacronym: "A&B_#" # PRIVATE INLINE COMMENT'))
        model = self.load()
        self.assertEqual(model['nodes'][0]['acronym'], 'A&B_#')
        rows = board.lanes(model)
        card = next(card for row in board.display_rows(rows) for card in row['cells'][''])
        self.assertEqual(card['title'], 'A&B_#')
        self.assertEqual(model['nodes'][0]['title'], 'Full Activity Title')
        board.render_html(rows, self.root / 'board')
        html = (self.root / 'board/index.html').read_text()
        self.assertIn('>A&amp;B_#</a>', html)
        self.assertIn('../../acc/pdf/Activity - Details.pdf#nameddest=act-x', html)
        self.assertIn(r'A\&B\_\#', board.tex(rows))
        report = documents.activity(model, Path('stage'))
        heading = next(item for item in content.walk(report)
                       if item['t'] == 'Header' and item['c'][1][0] == 'act-x')
        self.assertEqual(content.plain(heading['c'][2]), 'Full Activity Title')
        self.assertNotIn('PRIVATE', json.dumps(model))
        for field in ('', 'acronym: ""\n'):
            path.write_text(original.replace('subtitle:', field + 'subtitle:'))
            self.assertEqual(next(card['title'] for row in board.display_rows(board.lanes(self.load())) for card in row['cells']['']),
                             'Full Activity Title')
        for value in ('[A, B]', '{name: A}', 'true'):
            path.write_text(original.replace('subtitle:', f'acronym: {value}\nsubtitle:'))
            with self.assertRaisesRegex(ValueError, 'acronym must be a single text value'):
                self.load()

    def test_slogan_preserves_emphasis_line_breaks_and_portable_links(self):
        node = self.root / 'pfo/act/x/x.md'
        node.write_text(node.read_text().replace('title: X',
            'title: X\nslogan: "Treat *it* as **people**!\\n[Detail](#detail)"'))
        model = self.load()
        ast = documents.activity(model, Path('stage'))
        quote = next(block for block in ast['blocks'] if block['t'] == 'BlockQuote')
        kinds = [item['t'] for item in content.walk(quote)]
        self.assertIn('Emph', kinds)
        self.assertIn('Strong', kinds)
        self.assertIn('LineBreak', kinds)
        self.assertNotIn('SoftBreak', kinds)
        link = next(item for item in content.walk(quote) if item['t'] == 'Link')
        self.assertEqual(link['c'][2][0], '#act-x--detail')
        self.assertIn('SoftBreak', [item['t'] for item in content.walk(model['nodes'][0]['meta']['slogan'])])
        node.write_text(node.read_text().replace('[Detail](#detail)', '[Missing](#missing)'))
        with self.assertRaisesRegex(ValueError, 'Anchor is missing'):
            self.load()

    def test_all_anchors_and_cross_document_links_match_destinations(self):
        path = self.root / 'pfo/act/x/x.md'
        path.write_text(path.read_text() + '\n::: {#box}\nBox\n:::\n\n[Box](#box) [Goal](../../okr/goals.md#goal-b)\n')
        goals = self.root / 'pfo/okr/obj/b.md'
        goals.write_text(goals.read_text().replace('A second goal.', '[First](a.md)'))
        model = self.load()
        activity = documents.activity(model, Path('stage'))
        ids = {item['c'][0][0] for item in content.walk(activity['blocks']) if item['t'] == 'Div'}
        links = [item['c'][2][0] for item in content.walk(activity) if item['t'] == 'Link']
        self.assertIn('act-x--box', ids)
        self.assertIn('#act-x--box', links)
        self.assertIn('Performance - mPM.pdf#nameddest=goal-b', links)
        mpm = documents.mpm(model, Path('stage'))
        links = [item['c'][2][0] for item in content.walk(mpm) if item['t'] == 'Link']
        self.assertIn('#goal-a', links)
        self.assertIn('Activity - Details.pdf#nameddest=act-x--detail', links)

    def test_goal_anchors_are_unique_across_the_document(self):
        first = self.root / 'pfo/okr/obj/a.md'
        second = self.root / 'pfo/okr/obj/b.md'
        original = second.read_text()
        second.write_text(original.replace('key: b', 'key: a'))
        with self.assertRaisesRegex(ValueError, 'duplicate objective ID'):
            self.load()
        second.write_text(original + '\n## Detail {#detail}\n')
        first.write_text(first.read_text() + '\n## Detail {#detail}\n')
        with self.assertRaisesRegex(ValueError, 'duplicate anchors'):
            self.load()

    def test_objective_keys_survive_renaming_and_central_tracking_controls_views(self):
        source = self.root / 'pfo/okr/obj/a.md'
        source.rename(source.with_name('renamed.md'))
        control = self.root / 'pfo/okr/goals.md'
        control.write_text(control.read_text().replace('a: {status: active}', 'a: {status: on hold, priority: p2}')
                           .replace('title: mPM', 'title: My Performance'))
        model = self.load()
        first = model['goals'][0]
        self.assertEqual((first['key'], first['id'], first['status'], first['priority']),
                         ('a', 'goal-a', 'on hold', 'p2'))
        report = documents.mpm(model, Path('stage'))
        self.assertEqual(content.plain(report['meta']['title']), 'My Performance')
        self.assertIn(('priority', 'p2'), report['blocks'][0]['c'][1][2])
        views.render_mpm(model, self.root / 'view')
        html = (self.root / 'view/index.html').read_text()
        self.assertIn('priority-dot priority-p2', html)
        self.assertIn('My Performance', html)
        self.assertEqual(first['activities'][0]['key'], 'x')
        (self.root / 'pfo/okr/obj/b').mkdir()
        (self.root / 'pfo/okr/obj/a/contribution.md').rename(
            self.root / 'pfo/okr/obj/b/contribution.md')
        model = self.load()
        self.assertEqual(model['goals'][0]['activities'], [])  # Prose links do not assign impact.
        self.assertEqual(len(model['goals'][1]['activities']), 1)
        control.write_text(control.read_text().replace('b: {status: active}', 'b: {status: closed}'))
        self.assertEqual(self.load()['goals'][1]['status'], 'closed')

    def test_objective_source_and_timeframe_survive_metadata_move(self):
        source = self.root / 'pfo/okr/obj/a.md'
        url = 'https://example.org/goal?a=1&b=2'
        source.write_text(source.read_text().replace('key: a',
            'key: a\nurl: "' + url + '"\ntimeline: "01.01.2026 - 31.12.2026 < >"') +
            '\n## Description {#a-description}\n\nDetails.\n')
        model = self.load()
        before = json.dumps(model, sort_keys=True)
        report = documents.mpm(model, Path('stage'))
        self.assertIn(url, [n['c'][2][0] for n in content.walk(report) if n['t'] == 'Link'])
        self.assertIn('Zeitraum: 01.01.2026 - 31.12.2026 < >', content.plain(report['blocks']))
        views.render_mpm(model, self.root / 'view')
        html = (self.root / 'view/index.html').read_text()
        self.assertEqual(html.count('https://example.org/goal?a=1&amp;b=2'), 2)
        self.assertEqual(html.count('01.01.2026 - 31.12.2026 &lt; &gt;'), 2)
        self.assertNotIn('< >', html)
        self.assertIn('<h4 id="goal-a--a-description">', html)
        self.assertEqual(json.dumps(model, sort_keys=True), before)
        self.assertEqual(documents.goal_metadata(model['goals'][1]), [])

    def test_objective_metadata_rejects_invalid_source_and_structured_timeframe(self):
        source = self.root / 'pfo/okr/obj/a.md'
        original = source.read_text()
        for fields, message in [('url: javascript:alert(1)', 'HTTP'),
                                ('url: /local/path', 'HTTP'),
                                ('url: [https://example.org]', 'single text value'),
                                ('timeline: [2026, 2027]', 'single text value')]:
            with self.subTest(fields=fields):
                source.write_text(original.replace('key: a', 'key: a\n' + fields))
                with self.assertRaisesRegex(ValueError, message):
                    self.load()

    def test_objective_control_and_impact_errors_are_actionable(self):
        control = self.root / 'pfo/okr/goals.md'
        original = control.read_text()
        cases = [('title: mPM', 'title: mPM\nigraph: {}', 'derived from KR activities'),
                 ('title: mPM', 'title: mPM\nimpact-graph: {}', 'derived from KR activities'),
                 ('sequence: [a, b]', 'sequence: [a, missing]', 'unknown objective'),
                 ('sequence: [a, b]', 'sequence: [a, a]', 'duplicate'),
                 ('status: active', 'status: invalid', 'status requires'),
                 ('a: {status: active}', 'a: {status: active, priority: p5}', 'priority requires')]
        for before, after, message in cases:
            with self.subTest(after=after):
                control.write_text(original.replace(before, after))
                with self.assertRaisesRegex(ValueError, message):
                    self.load()
        control.write_text(original)
        objective = self.root / 'pfo/okr/obj/a.md'
        original_objective = objective.read_text()
        for field in ('status: active', 'priority: p1', 'tracking: {}', 'sequence: []', 'igraph: {}', 'impact-graph: {}'):
            objective.write_text(original_objective.replace('key: a', 'key: a\n'+field))
            with self.assertRaisesRegex(ValueError, 'derived from KR activities' if 'graph' in field
                                        else 'centrally in pfo/okr/goals.md'):
                self.load()
        objective.write_text(original_objective)
        self.write('pfo/okr/obj/c.md', '---\ntitle: C\nkey: c\n---\n')
        with self.assertRaisesRegex(ValueError, 'status is missing'):
            self.load()
        control.write_text(original.replace('tracking:', 'tracking:\n  c: {status: active}'))
        self.assertEqual([goal['key'] for goal in self.load()['goals']], ['a', 'b', 'c'])
        (self.root / 'pfo/okr/obj/c.md').unlink()
        with self.assertRaisesRegex(ValueError, 'unknown objective'):
            self.load()


    def test_repo_is_local_ignored_and_never_published(self):
        local = self.root / 'external'
        local.mkdir()
        node = self.root / 'pfo/act/x/x.md'
        self.write('.yap/cfg/machine.json', json.dumps({'links': {'x': {'repo': 'external'}}}))
        model = self.load()
        plan, messages = files.link_plan(self.root)
        self.assertEqual(messages, [])
        files.sync_links(plan)
        self.assertTrue((node.parent / 'repo').is_symlink())
        self.write('external/new.md', 'Must not be read')
        self.assertEqual([n['key'] for n in self.load()['nodes']], ['x'])
        self.assertFalse(any('repo' in path.parts for path in files.source_files(self.root / 'pfo/act')))
        self.assertFalse(any('repo' in Path(path).parts for path, _ in files.source_shape(self.root / 'pfo/act')))
        node.write_text(node.read_text() + '\n[Local](repo/new.md)\n')
        with self.assertRaisesRegex(ValueError, 'repo is for local navigation only'):
            self.load()
        node.write_text(node.read_text().replace('\n[Local](repo/new.md)\n', ''))
        self.write('pfo/act/x/res/repo/private.txt', 'Must not be published')
        self.write('pfo/act/x/res/shared file.pdf', 'Public bytes')
        resources = files.resource_plan(self.root, model)
        self.assertEqual(set(resources), {'res/x/shared file.pdf'})
        files.copy_resources(resources, self.root / 'stage')
        self.assertEqual((self.root / 'stage/res/x/shared file.pdf').read_text(), 'Public bytes')
        self.write('.yap/cfg/machine.json', json.dumps({'links': {}}))
        files.sync_links(files.link_plan(self.root)[0])
        self.assertFalse((node.parent / 'repo').is_symlink())
        (node.parent / 'repo').mkdir()
        self.write('.yap/cfg/machine.json', json.dumps({'links': {'x': {'repo': 'external'}}}))
        with self.assertRaisesRegex(ValueError, 'not a symlink'):
            files.link_plan(self.root)
        self.assertTrue((node.parent / 'repo').is_dir())
        (node.parent / 'repo').rmdir()
        (node.parent / 'repo').write_text('Keep this file')
        with self.assertRaisesRegex(ValueError, 'not a symlink'):
            files.link_plan(self.root)
        self.assertEqual((node.parent / 'repo').read_text(), 'Keep this file')
        (node.parent / 'repo').unlink()
        shutil.rmtree(local)
        plan, messages = files.link_plan(self.root)
        self.assertEqual(len(messages), 1)
        files.sync_links(plan)
        self.assertTrue((node.parent / 'repo').is_symlink())
        self.assertFalse((node.parent / 'repo').exists())

    def test_areas_keep_descriptions_without_becoming_work_or_goal_contributions(self):
        self.write('pfo/act/area/area.md', '---\nkind: area\nkey: area\ntitle: Area\n---\nAreaNarrative\n')
        self.write('pfo/act/act.md', '---\ntitle: Activity\nmembers:\n  area: [x]\n---\n')
        model = self.load()
        area = next(n for n in model['nodes'] if n['key'] == 'area')
        self.assertEqual((area['kind'], area['id'], area['resource_root']), ('area', 'act-area', 'area'))
        placement = next(p for p in model['report']['nodes'] if p['entry'] == 'area')
        self.assertTrue(placement['render_body'])
        self.assertEqual(placement['board_card'], 'never')
        cards = [card['key'] for row in board.display_rows(board.lanes(model))
                 for group in row['cells'].values() for card in group]
        self.assertEqual(cards, ['x'])
        self.assertIn('AreaNarrative', str(documents.activity(model, Path('stage'))['blocks']))
        self.write('pfo/act/act.md', '---\ndgraph:\n  spec: area -> x\n---\n')
        with self.assertRaisesRegex(ValueError, 'endpoints must be activities'):
            self.load()
        self.write('pfo/act/act.md', '---\ntitle: Activity\n---\n')
        self.write('pfo/okr/obj/a/result.md', '---\nkey: result\ntitle: Result\nmeasure: Evidence\nunit: count\ntarget: 1\nactivities: [area]\n---\n')
        with self.assertRaisesRegex(ValueError, 'unknown activity'):
            self.load()

    def test_context_notes_keep_details_without_becoming_activity_cards(self):
        self.write('pfo/nts/context/context.md', '---\nkind: note\nkey: context\ntitle: Context\n---\n## Tool Stack\nKeep my tools.\n')
        model = self.load()
        cards = [card['key'] for row in board.display_rows(board.lanes(model))
                 for group in row['cells'].values() for card in group]
        self.assertEqual(cards, ['x'])
        report = documents.activity(model, Path('stage'))
        self.assertIn('Keep my tools.', content.plain(report['blocks']))
        self.assertNotIn('Context', views.map_tex(model))
        self.assertIn('X', views.map_tex(model))

    def test_synonyms_are_validated_and_rendered_as_alternative_names(self):
        source = self.root / 'pfo/act/x/x.md'
        original = source.read_text()
        source.write_text(original.replace('title: X', 'title: X\nsynonyms: ["Other & name", "50% alias"]'))
        model = self.load()
        node = next(node for node in model['nodes'] if node['key'] == 'x')
        self.assertEqual(node['synonyms'], ['Other & name', '50% alias'])
        report = documents.activity(model, Path('stage'))
        self.assertIn('Auch bekannt als: Other & name · 50% alias', content.plain(report['blocks']))
        for value in ('Name', '[""]', '[Same, Same]', '[{nested: value}]'):
            source.write_text(original.replace('title: X', 'title: X\nsynonyms: '+value))
            with self.assertRaises(ValueError):
                self.load()

        source.write_text(original.replace('title: X', 'title: X\nboard-caption: "Board only"'))
        model = self.load()
        self.assertEqual(model['nodes'][0]['board-caption'], 'Board only')
        self.assertNotIn('Board only', content.plain(documents.activity(model, Path('stage'))['blocks']))
        source.write_text(original.replace('title: X', 'title: X\nboard-caption: [Wrong, format]'))
        with self.assertRaisesRegex(ValueError, 'board-caption must be a single text value'):
            self.load()

    def test_mpm_view_is_goal_first_and_keeps_resource_links(self):
        self.write('pfo/act/x/res/paper.pdf', 'PDF')
        self.write('pfo/act/x/res/picture.png', 'PNG')
        goals = self.root / 'pfo/okr/obj/b.md'
        goals.write_text(goals.read_text().replace('A second goal.',
            '[Paper](../../act/x/res/paper.pdf)\n\n![Picture](../../act/x/res/picture.png)\n\n[First](a.md)'))
        model = self.load()
        views.render_mpm(model, self.root / 'view')
        html = (self.root / 'view/index.html').read_text()
        self.assertIn('../../res/x/paper.pdf', html)
        self.assertIn('../../res/x/picture.png', html)
        pdf = documents.mpm(model, Path('stage'))
        links = [item['c'][2][0] for item in content.walk(pdf) if item['t'] == 'Link']
        self.assertIn('../../res/x/paper.pdf', links)
        self.assertIn('../../acc/pdf/Performance - mPM.pdf#nameddest=goal-a', html)
        self.assertNotIn('Historical notes excluded', html)
        self.assertNotIn('pfo/act', html)
        self.assertLess(html.index('<span>Ziele</span>'), html.index('<span>Fortschritt</span>'))
        self.assertLess(html.index('<span>Fortschritt</span>'), html.index('<span>Zusammenhänge</span>'))
        self.assertIn('id="cards" aria-controls="cards-panel" checked', html)
        navigation = html.split('</nav>', 1)[0]
        self.assertIn('aria-label="Darstellung"', navigation)
        self.assertIn('id="graph"', navigation)
        self.assertNotIn('class="tabs"', html)
        self.assertNotIn('class="eyebrow"', html)
        tree = html.split('id="tracking-panel"', 1)[1]
        self.assertLess(tree.index('Goal A'), tree.index('X'))

    def test_internal_blocks_are_removed_before_validation_and_publication(self):
        node = self.root / 'pfo/act/x/x.md'
        internal = '\n::: {.internal}\n\n## Internal note {#private-note}\n\nPRIVATE-NOTE\n\n[Local](work/missing.md)\n\n![Draft](missing.png)\n\n:::\n'
        node.write_text(node.read_text() + internal + '\nPublic ending.\n')
        goals = self.root / 'pfo/okr/obj/a.md'
        goals.write_text(goals.read_text().replace('**Contributions**',
            '**Contributions**\n\n::: {.internal}\n\nPRIVATE-GOAL\n\n[Wrong](../act/x/missing.md)\n\n:::\n'))
        model = self.load()
        for ast in (model, documents.activity(model, Path('stage')), documents.mpm(model, Path('stage'))):
            text = json.dumps(ast)
            self.assertNotIn('PRIVATE-', text)
            self.assertNotIn('private-note', text)
        views.render_mpm(model, self.root / 'views')
        self.assertNotIn('PRIVATE-', (self.root / 'views/index.html').read_text())
        board.render_html(board.lanes(model), self.root / 'board')
        self.assertNotIn('PRIVATE-', (self.root / 'board/index.html').read_text())
        self.assertIn('Public ending.', content.plain(model['nodes'][0]['blocks']))
        node.write_text(node.read_text() + '\n[Private note](#private-note)\n')
        with self.assertRaisesRegex(ValueError, 'Anchor is missing'):
            self.load()

    def test_resource_urls_preserve_reserved_filename_characters(self):
        names = ['space name', 'überblick', 'hash#name', 'percent%20name', 'query?name']
        markdown = []
        for name in names:
            self.write(f'pfo/act/x/res/{name}.pdf', 'PDF ' + name)
            self.write(f'pfo/act/x/res/{name}.svg', '<svg xmlns="http://www.w3.org/2000/svg"/>')
            path = '../../act/x/res/' + quote(name, safe='')
            markdown.append(f'[Resource]({path}.pdf#page=2)\n\n![Image]({path}.svg)')
        objective = self.root / 'pfo/okr/obj/b.md'
        objective.write_text(objective.read_text() + '\n\n' + '\n\n'.join(markdown))
        model = self.load()
        stage = self.root / '.yap/local/site'
        files.copy_resources(files.resource_plan(self.root, model), stage)
        view = stage / 'views/mPM-ish'
        views.render_mpm(model, view)

        class ResourceURLs(HTMLParser):
            def __init__(self):
                super().__init__()
                self.urls = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                url = attrs.get('href') if tag == 'a' else attrs.get('src') if tag == 'img' else None
                if url and url.startswith('../../res/'):
                    self.urls.append((tag, url))

        html = ResourceURLs()
        html.feed((view / 'index.html').read_text())
        self.assertEqual(len(html.urls), len(names) * 2)
        for tag, url in html.urls:
            parsed = urlsplit(url)
            self.assertEqual(parsed.query, '')
            self.assertEqual(parsed.fragment, 'page=2' if tag == 'a' else '')
            target = (view / unquote(parsed.path)).resolve()
            self.assertTrue(target.is_file(), url)
            self.assertIn(target.stem, names)

        pdf = documents.mpm(model, stage)
        resource_nodes = [item for item in content.walk(pdf['blocks'])
                          if item['t'] in {'Link', 'Image'} and '/res/' in item['c'][2][0]]
        self.assertEqual(len(resource_nodes), len(names) * 2)
        for item in resource_nodes:
            parsed = urlsplit(item['c'][2][0])
            base = stage / 'acc/pdf' if item['t'] == 'Link' else Path()
            target = (base / unquote(parsed.path)).resolve()
            self.assertTrue(target.is_file(), item['c'][2][0])
            self.assertEqual(parsed.fragment, 'page=2' if item['t'] == 'Link' else '')
        # The TeX writer consumes image URLs as filesystem names, decoding once.
        latex = subprocess.run(['pandoc', '-f', 'json', '-t', 'latex'], input=json.dumps(pdf),
                               text=True, capture_output=True, check=True).stdout
        self.assertIn('hash\\#name.svg', latex)
        self.assertIn('percent\\%20name.svg', latex)
        self.assertIn('query?name.svg', latex)

    def test_empty_resources_are_current_and_missing_resources_are_restored(self):
        self.addCleanup(os.chdir, Path.cwd())

        def run():
            output = StringIO()
            with redirect_stdout(output):
                yap.main('resources')
            return output.getvalue()

        with patch.object(yap, 'ROOT', self.root):
            run()
            with patch.object(yap, 'publish') as publish, patch.object(yap, 'copy_resources') as copy:
                self.assertIn('Up to date', run())
                publish.assert_not_called()
                copy.assert_not_called()
            resource = self.write('pfo/act/x/res/attachment.pdf', 'Public bytes')
            run()
            published = self.root / '.yap/local/site/res/x/attachment.pdf'
            self.assertEqual(published.read_text(), 'Public bytes')
            published.unlink()
            run()
            self.assertEqual(published.read_text(), 'Public bytes')
            resource.unlink()
            run()
            self.assertFalse(published.exists())
            with patch.object(yap, 'publish') as publish, patch.object(yap, 'copy_resources') as copy:
                self.assertIn('Up to date', run())
                publish.assert_not_called()
                copy.assert_not_called()

    def test_incremental_publication_handles_subtitle_move_delete_and_failure(self):
        (self.root / 'pfo/okr/obj/a/contribution.md').unlink()
        original_cwd = Path.cwd()
        self.addCleanup(os.chdir, original_cwd)
        calls = []

        def maps(model):
            calls.append('maps')
            path = yap.STAGE / 'views/activity-map/map.png'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps([(n['key'], n['subtitle']) for n in yap.overview.activity_nodes(model)]))

        def pdf(model, name):
            calls.append(name)
            # Real PDFs contain Objective documents, not the KR measurement rows.
            (yap.STAGE / yap.PDF_NAMES[name]).write_text(json.dumps(
                {key: value for key, value in model.items() if key != 'key_results'}))

        def html(model, destination):
            calls.append('views')
            destination.mkdir(parents=True, exist_ok=True)
            (destination / 'index.html').write_text(json.dumps(model))

        def status_board(model):
            calls.append('board')
            destination = yap.STAGE / 'views/activity-board'
            for selected in yap.selections.activities(model):
                board.render_html(board.lanes(selected), destination,
                                  selection=selected['selection'])
            (destination / 'board.png').write_text(json.dumps(board.lanes(model)))

        def overview(model):
            logo = Path(yap.navigation.LOGO)
            self.assertEqual((yap.STAGE / logo).read_bytes(), yap.home.asset_source(logo).read_bytes())
            (yap.STAGE / 'acc/pdf/Activity - Overview.pdf').write_text(json.dumps(board.lanes(model)))

        def dependency_graph(model):
            calls.append('dgraph')
            destination = yap.STAGE / 'views/dependency-graph'
            dgraph.render_html(model['dgraph'], destination)
            if model['dgraph']['nodes']:
                for name in ('graph.pdf', 'graph.png'):
                    (destination / name).write_text(json.dumps(model['dgraph']))

        def run():
            with redirect_stdout(StringIO()):
                yap.main('all')

        with patch.object(yap, 'ROOT', self.root), patch.object(yap, 'render_maps', maps), \
             patch.object(yap, 'render_pdf', pdf), patch.object(yap.views, 'render_mpm', html), \
             patch.object(yap, 'render_board', status_board), \
             patch.object(yap, 'render_dgraph', dependency_graph), \
             patch.object(yap.browser, 'fit_cards'), \
             patch.object(yap, 'render_overview', overview):
            run()
            calls.clear()
            saved = self.write('pov/focus/.perspective.yaml', json.dumps({
                'schema': 1, 'title': 'Focus', 'entries': [
                    {'id': 'p000001', 'name': 'Selected', 'target': {'entry': 'x'}}]}))
            run()
            self.assertTrue({'maps', 'board', 'dgraph'} <= set(calls))
            focused_page = self.root / '.yap/local/site/views/activity-board/p-focus.html'
            self.assertTrue(focused_page.is_file())
            self.assertIn('Focus', focused_page.read_text())
            saved.parent.rename(saved.parent.with_name('renamed'))
            run()
            renamed_page = focused_page.with_name('p-renamed.html')
            self.assertFalse(focused_page.exists())
            self.assertTrue(renamed_page.is_file())
            (saved.parent.with_name('renamed') / '.perspective.yaml').unlink()
            run()
            self.assertFalse(renamed_page.exists())
            self.assertNotIn('p-renamed.html', renamed_page.with_name('index.html').read_text())
            calls.clear()
            script = self.application / 'dev/src/tool.py'
            script.write_text('// Initial browser component\n')
            run()
            self.assertIn('views', calls)
            calls.clear()
            script.write_text('// Changed browser component\n')
            run()
            self.assertIn('views', calls)
            calls.clear()
            self.write('tests/fixtures.py', '# Test-only fixture change\n')
            before = yap.hashes(files.source_files(Path('.yap/local/site')))
            run()
            self.assertEqual(calls, [])
            kr = self.write('pfo/okr/obj/a/result.md',
                '---\nkey: result\ntitle: Result\nmeasure: Confirmed\nunit: outcomes\ntarget: 2\ncurrent: 0\n---\n')
            run()
            self.assertEqual(calls, ['views'])
            self.assertEqual(json.loads((self.root / '.yap/local/site/views/mPM-ish/index.html').read_text())
                             ['key_results']['a'][0]['current'], 0)
            calls.clear()
            kr.write_text(kr.read_text().replace('current: 0', 'current: 1'))
            run()
            self.assertEqual(calls, ['views'])
            self.assertEqual(json.loads((self.root / '.yap/local/site/views/mPM-ish/index.html').read_text())
                             ['key_results']['a'][0]['current'], 1)
            calls.clear()
            kr.write_text(kr.read_text().replace('current: 1', 'current: 1\nactivities: [x]'))
            run()
            self.assertEqual(set(calls), {'Activity', 'mPM', 'views'})
            self.assertEqual(json.loads((self.root / '.yap/local/site/views/mPM-ish/index.html').read_text())
                             ['goals'][0]['activities'], [dict(key='x', anchor='', label='X')])
            calls.clear()
            kr.write_text(kr.read_text().replace('\nactivities: [x]', ''))
            run()
            self.assertEqual(set(calls), {'Activity', 'mPM', 'views'})
            self.assertEqual(json.loads((self.root / '.yap/local/site/views/mPM-ish/index.html').read_text())
                             ['goals'][0]['activities'], [])
            calls.clear()
            preview = self.write('.yap/cfg/progress-preview.json', json.dumps(dict(
                provenance='illustrative-not-collected', as_of='2026-10-13', quips=[dict(
                    id='example', activity='x', date='2026-10-13', kind='Draft', title='First draft')])) )
            run()
            self.assertEqual(calls, ['views'])
            calls.clear()
            preview.write_text(preview.read_text().replace('First draft', 'Refined draft'))
            run()
            self.assertEqual(calls, ['views'])
            self.assertEqual(json.loads((self.root / '.yap/local/site/views/mPM-ish/index.html').read_text())
                             ['work_preview']['quips'][0]['title'], 'Refined draft')
            calls.clear()
            preview.unlink()
            run()
            self.assertEqual(calls, ['views'])
            calls.clear()
            renamed_kr = kr.with_name('renamed.md')
            kr.rename(renamed_kr)
            run()
            self.assertEqual(calls, [])
            renamed_kr.unlink()
            run()
            self.assertEqual(calls, ['views'])
            self.assertEqual(json.loads((self.root / '.yap/local/site/views/mPM-ish/index.html').read_text())['key_results'], {})
            calls.clear()
            run()
            self.assertEqual(calls, [])
            self.assertEqual(before, yap.hashes(files.source_files(Path('.yap/local/site'))))
            collection = self.root / '.yap/local/site/views/yapics/index.html'
            self.assertIn('Seeds of Insight. Tailored to your needs.', collection.read_text())
            self.assertIn(collection.resolve(), [path.resolve() for path in yap.group_files(Path('.yap/local/site'), 'home')])
            collection.unlink()
            run()
            self.assertTrue(collection.is_file())
            self.assertEqual(before, yap.hashes(files.source_files(Path('.yap/local/site'))))
            for asset in yap.home.ASSETS:
                source = self.root / yap.home.asset_source(asset)
                published = self.root / '.yap/local/site' / asset
                original = source.read_bytes()
                self.assertEqual(published.read_bytes(), original)
                source.write_bytes(b'Updated asset')
                run()
                self.assertEqual(published.read_bytes(), b'Updated asset')
                self.assertEqual(calls, [])
                published.unlink()
                run()
                self.assertEqual(published.read_bytes(), b'Updated asset')
                source.write_bytes(original)
                run()
            control = self.root / 'pfo/okr/goals.md'
            original_control = control.read_text()
            control.write_text(original_control.replace('title: mPM', 'title: Updated Performance'))
            run()
            self.assertEqual(set(calls), {'mPM', 'views'})
            control.write_text(original_control)
            run()
            calls.clear()
            node = self.root / 'pfo/act/x/x.md'
            original_node = node.read_text()
            node.write_text(original_node + '\n::: {.internal}\n\nPRIVATE-NOTE [Local](work/notes.md)\n\n:::\n')
            run()
            self.assertEqual(calls, [])
            self.assertEqual(before, yap.hashes(files.source_files(Path('.yap/local/site'))))
            self.assertNotIn('PRIVATE-NOTE', (self.root / '.yap/local/build/model.json').read_text())
            node.write_text(original_node)
            local = self.root / 'external'
            local.mkdir()
            self.write('.yap/cfg/machine.json', json.dumps({'links': {'x': {'repo': 'external'}}}))
            run()
            self.assertEqual(calls, [])
            self.assertEqual(before, yap.hashes(files.source_files(Path('.yap/local/site'))))
            self.assertEqual((node.parent / 'repo').resolve(), local.resolve())
            self.write('.yap/cfg/machine.json', json.dumps({'links': {}}))
            run()
            self.assertEqual(calls, [])
            self.assertFalse((node.parent / 'repo').is_symlink())
            self.write('pfo/act/x/res/attachment.txt', 'Original attachment')
            run()
            calls.clear()
            control_path = self.root / 'pfo/act/act.md'
            control_text = control_path.read_text()
            control_path.write_text(control_text.replace('title: Activity',
                'title: Activity\npublication:\n  x: {resource-root: durable/x}'))
            run()
            self.assertIn('mPM', calls)
            self.assertTrue((self.root / '.yap/local/site/res/durable/x/attachment.txt').is_file())
            self.assertFalse((self.root / '.yap/local/site/res/x/attachment.txt').exists())
            control_path.write_text(control_text)
            (self.root / 'pfo/act/x/res/attachment.txt').unlink()
            run()
            calls.clear()
            goals = self.root / 'pfo/okr/obj/a.md'
            goals.write_text(goals.read_text().replace('**Contributions**', '#### Detail {#detail}\n\n**Contributions**'))
            run()
            calls.clear()
            goals.write_text(goals.read_text().replace('#### Detail {#detail}\n\n', ''))
            other = self.root / 'pfo/okr/obj/b.md'
            other.write_text(other.read_text().replace('A second goal.', '#### Detail {#detail}'))
            run()
            self.assertIn('Activity', calls)
            calls.clear()
            node = self.root / 'pfo/act/x/x.md'
            node.write_text(node.read_text().replace('subtitle: First', 'subtitle: Changed'))
            run()
            self.assertIn('maps', calls)
            calls.clear()
            self.write('pfo/act/y/y.md', '---\ntitle: "Y"\n---\n')
            run()
            self.assertIn('Y', (self.root / '.yap/local/site/acc/pdf/Activity - Details.pdf').read_text())
            report = self.root / 'pfo/act/act.md'
            saved = report.read_text()
            report.write_text(saved.replace('title: Activity',
                'title: Activity\ndgraph:\n  spec: |\n    x -> y'))
            calls.clear()
            run()
            self.assertEqual(set(calls), {'dgraph', 'board', 'Activity'})
            self.assertNotIn('graph-preview', (self.root / '.yap/local/site/views/activity-board/index.html').read_text())
            self.assertTrue((self.root / '.yap/local/site/views/dependency-graph/graph.svg').exists())
            ast = documents.activity(self.load(), Path('stage'))
            self.assertEqual(ast['meta']['dependency-graph']['c'], 'stage/views/dependency-graph/graph.pdf')
            before_graph = yap.hashes(files.source_files(Path('.yap/local/site')))
            report.write_text(report.read_text().replace('x -> y', 'y -> x'))
            with patch.object(yap, 'render_dgraph', side_effect=RuntimeError('graph failed')):
                with self.assertRaises(RuntimeError):
                    run()
            self.assertEqual(before_graph, yap.hashes(files.source_files(Path('.yap/local/site'))))
            run()
            graph = json.loads((self.root / '.yap/local/site/views/dependency-graph/graph.pdf').read_text())
            self.assertEqual(graph['edges'], [['y', 'x']])
            report.write_text(saved)
            run()
            self.assertTrue((self.root / '.yap/local/site/views/dependency-graph/graph.svg').exists())
            graph = json.loads((self.root / '.yap/local/site/views/dependency-graph/graph.pdf').read_text())
            self.assertEqual(graph['edges'], [])
            self.assertTrue(graph['nodes'])
            self.assertNotIn('<a class="graph-preview"', (self.root / '.yap/local/site/views/activity-board/index.html').read_text())
            calls.clear()
            report = self.root / 'pfo/act/act.md'
            original_report = report.read_text()
            report.write_text(original_report.replace('title: Activity', 'title: Activity\nreport-perspective: report'))
            saved_view = self.write('pov/report/.perspective.yaml', json.dumps({
                'schema': 1, 'title': 'Report', 'entries': [
                    {'id': 'p000001', 'name': 'Y', 'target': {'entry': 'y'}},
                    {'id': 'p000002', 'name': 'X', 'target': {'entry': 'x'}}]}))
            run()
            self.assertIn('Activity', calls)
            self.assertIn('maps', calls)
            for output in ('acc/pdf/Activity - Details.pdf', 'views/mPM-ish/index.html'):
                published = json.loads((self.root / '.yap/local/site' / output).read_text())
                self.assertEqual([n['key'] for n in published['nodes']], ['x', 'y'])
                self.assertEqual([n['entry'] for n in published['report']['nodes']], ['y', 'x'])
            calls.clear()
            report.write_text(report.read_text().replace('title: Activity',
                'title: Activity\ntracking:\n  x: {status: on hold, priority: p2}'))
            run()
            self.assertEqual(set(calls), {'maps', 'board', 'Activity', 'mPM', 'views'})
            for output in ('acc/pdf/Activity - Details.pdf', 'acc/pdf/Performance - mPM.pdf', 'views/mPM-ish/index.html'):
                published = json.loads((self.root / '.yap/local/site' / output).read_text())
                self.assertEqual([n['key'] for n in published['nodes']], ['x', 'y'])
                self.assertEqual((published['nodes'][0]['status'], published['nodes'][0]['priority']),
                                 ('on hold', 'p2'))
            report.write_text(original_report)
            saved_view.unlink()
            calls.clear()
            (self.root / 'pfo/act/y').rename(self.root / 'pfo/act/x/y')
            run()
            self.assertIn('x/y', (self.root / '.yap/local/site/acc/pdf/Activity - Details.pdf').read_text())
            shutil.rmtree(self.root / 'pfo/act/x/y')
            run()
            self.assertNotIn('x/y', (self.root / '.yap/local/site/acc/pdf/Activity - Details.pdf').read_text())
            before = yap.hashes(files.source_files(Path('.yap/local/site')))
            node.write_text(node.read_text() + '\n[Broken](missing.pdf)\n')
            with self.assertRaises(ValueError):
                run()
            self.assertEqual(before, yap.hashes(files.source_files(Path('.yap/local/site'))))
            node.write_text(node.read_text().replace('[Broken](missing.pdf)', 'Changed body'))
            report.write_text(report.read_text().replace('title: Activity',
                'title: Activity\ntracking:\n  x: {status: ibx}'))
            with patch.object(yap, 'render_board', side_effect=RuntimeError('board failed')):
                with self.assertRaises(RuntimeError):
                    run()
            self.assertEqual(before, yap.hashes(files.source_files(Path('.yap/local/site'))))
            with patch.object(yap, 'render_pdf', side_effect=RuntimeError('renderer failed')):
                with self.assertRaises(RuntimeError):
                    run()
            self.assertEqual(before, yap.hashes(files.source_files(Path('.yap/local/site'))))
            with patch.object(yap, 'render_overview', side_effect=RuntimeError('browser failed')):
                with self.assertRaises(RuntimeError):
                    run()
            self.assertEqual(before, yap.hashes(files.source_files(Path('.yap/local/site'))))


if __name__ == '__main__':
    unittest.main()
