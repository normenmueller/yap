"""Central resumption order is unique, explicit, and shared by board projections."""

from fixtures import source_text

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yap import board, content, performance_lanes


class NextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='yap-next-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for key in ('area', 'area/sup', 'area/sup/a', 'area/sup/b', 'area/sup/c'):
            self.write('pfo/act/' + key + '/' + key.rsplit('/', 1)[-1] + '.md',
                       '---\ntitle: ' + key.rsplit('/', 1)[-1] + '\n---\n')
        self.write('pfo/act/area/sup/a/a.md', '---\ntitle: A\n---\n'
                   '## Current {#current .version}\n\n## Released {#released .version}\n')
        self.write('pfo/okr/goals.md', '---\ntitle: Goals\n---\n')
        self.defaults = {
            'area--sup--a#current': '{status: on hold, priority: p4, next: 1}',
            'area--sup--a#released': '{status: released}',
            'area--sup--b': '{status: on hold, priority: p1, next: 3}',
            'area--sup--c': '{status: on hold, priority: p1}',
        }
        self.track(self.defaults)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source_text(path, text))

    def track(self, entries):
        self.write('pfo/act/act.md', '---\ntitle: Activities\ntracking:\n' +
                   ''.join('  "' + key + '": ' + value + '\n' for key, value in entries.items()) + '---\n')

    def test_global_numbers_sort_before_priority_and_survive_filtering(self):
        model = content.load(self.root)
        before = deepcopy(model)
        rows = board.lanes(model)
        cards = [c for row in board.display_rows(rows) for c in row['cells']['on hold']]
        self.assertEqual([(c['key'], c['next']) for c in cards],
                         [('area--sup--a', 1), ('area--sup--b', 3), ('area--sup--c', None)])
        board.render_html(rows, self.root / 'output')
        html = (self.root / 'output/index.html').read_text()
        for rank in (1, 3):
            self.assertIn(f'title="Als Nächstes: {rank}" aria-label="Als Nächstes: {rank}"', html)
            self.assertIn(r'\boardnext{' + str(rank) + '}', board.tex(rows))
        embedded = performance_lanes.render(model, ['area--sup--b'])
        self.assertIn('aria-label="Als Nächstes: 3"', embedded)
        self.assertNotIn('aria-label="Als Nächstes: 1"', embedded)
        self.assertEqual(model, before)
        released = next(c for row in board.display_rows(rows) for c in row['cells']['released'])
        self.assertEqual(board.next_marker(released), '')

    def test_next_requires_on_hold_and_a_number_from_one_to_three(self):
        for status in ('wip', 'released', 'ibx', ''):
            fields = ('status: ' + status + ', ') if status else ''
            self.track({**self.defaults, 'area--sup--b': '{' + fields + 'next: 3}'})
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, 'only with status on hold'):
                content.load(self.root)
        for rank in ('0', '4', '-1', '1.5', 'true', '""', 'null', '[1]', '{}'):
            self.track({**self.defaults, 'area--sup--b': '{status: on hold, next: ' + rank + '}'})
            with self.subTest(rank=rank), self.assertRaisesRegex(ValueError, 'next'):
                content.load(self.root)

    def test_duplicate_numbers_across_activities_and_versions_are_rejected(self):
        self.track({**self.defaults, 'area--sup--b': '{status: on hold, next: 1}'})
        with self.assertRaisesRegex(ValueError, 'next 1 is already assigned'):
            content.load(self.root)
        self.track({**self.defaults, 'area--sup--a#released': '{status: on hold, next: 1}'})
        with self.assertRaisesRegex(ValueError, 'next 1 is already assigned'):
            content.load(self.root)

    def test_removing_marker_allows_wip_and_restores_priority_order(self):
        self.track({**self.defaults, 'area--sup--a#current': '{status: on hold, priority: p4}',
                    'area--sup--b': '{status: wip, priority: p1}'})
        model = content.load(self.root)
        rows = list(board.display_rows(board.lanes(model)))
        self.assertEqual([c['key'] for row in rows for c in row['cells']['on hold']],
                         ['area--sup--c', 'area--sup--a'])
        self.assertTrue(all(not c['next'] for row in rows for cell in row['cells'].values() for c in cell))

    def test_next_is_rejected_outside_central_tracking(self):
        for text in ('---\ntitle: B\nnext: 2\n---\n',
                     '---\ntitle: B\n---\n## Note {next=2}\n',
                     '---\ntitle: B\n---\n## Version {.version next=2}\n'):
            self.write('pfo/act/area/sup/b/b.md', text)
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'next.*(tracking|belong)'):
                content.load(self.root)
