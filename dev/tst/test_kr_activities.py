"""Explicit contribution forms preserve strict paths and honest graph identity."""

from fixtures import report_model

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yap import content, goaltree, kr_activities, performance


class KRActivitiesTests(unittest.TestCase):
    def setUp(self):
        self.nodes = [dict(key='work', id='act-work', title='Work', depth=1, parent='', status='wip', priority='')]

    def parse(self, entries):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'result.md'
            path.write_text('---\nkey: result\ntitle: Result\nmeasure: Confirmed result\n'
                            'unit: outcomes\ntarget: 1\nactivities:\n' + entries + '\n---\n')
            return performance.parse(content.read(path)['meta'], self.nodes, str(path))

    def test_mixed_forms_and_deduplication_preserve_paths(self):
        kr = self.parse('  - work\n  - "[Historical work](https://example.org/commit/work.md)"\n'
                        '  - title: Earlier contribution\n  - work')
        self.assertEqual(kr['activities'], ['work',
                         dict(title='Historical work', url='https://example.org/commit/work.md'),
                         dict(title='Earlier contribution')])
        html = kr_activities.render(report_model(dict(nodes=self.nodes, board_sequence=[])), kr['activities'])
        self.assertIn('data-activity="work"', html)
        self.assertIn('href="https://example.org/commit/work.md"', html)
        self.assertIn('<li>Earlier contribution</li>', html)

    def test_unmanaged_entries_do_not_create_status_or_document_links(self):
        kr = self.parse('  - title: DispoBuddy')
        html = kr_activities.render(dict(nodes=self.nodes), kr['activities'])
        self.assertIn('<li>DispoBuddy</li>', html)
        for unwanted in ('href=', 'Icebox', 'kr-board-empty', 'data-activity='):
            self.assertNotIn(unwanted, html)

    def test_unknown_paths_and_malformed_explicit_forms_still_fail(self):
        entries = ['  - missing', '  - work/deleted', '  - DispoBuddy',
                   '  - "[Work](javascript:alert)"', '  - "[Work](file:///tmp/work.md)"',
                   '  - "[Work](../deleted.md)"', '  - "Before [Work](https://example.org)"',
                   '  - "wo[rk](https://example.org)"',
                   '  - "[Work](https://example.org:notaport)"',
                   '  - title: ""', '  - {title: Work, status: released}',
                   '  - {title: Work, url: https://example.org}', '  - {path: work}']
        for entry in entries:
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                self.parse(entry)

    def test_shared_links_and_local_notes_have_distinct_identity(self):
        kr = self.parse('  - "[Same name](https://example.org/commit/work.md)"\n  - title: Same name')
        model = dict(nodes=self.nodes,
                     goals=[dict(key=key, id='goal-' + key, title=key) for key in ('one', 'two')],
                     key_results={key: [deepcopy(kr)] for key in ('one', 'two')})
        model = report_model(model)
        before = deepcopy(model)
        data = goaltree.graph_data(model)
        self.assertEqual(model, before)
        work = [node for node in data['nodes'] if node['kind'] == 'activity']
        self.assertEqual(len(work), 3)
        linked = [node for node in work if 'url' in node]
        self.assertEqual(len(linked), 1)
        self.assertEqual(sum(to == linked[0]['id'] for _, to in data['edges']), 2)
        notes = [node for node in work if node.get('source') == 'note']
        self.assertEqual(len(notes), 2)
        self.assertNotEqual(notes[0]['id'], notes[1]['id'])
        kr_activities.check_link_titles(model['key_results'])
        model['key_results']['two'][0]['activities'][0]['title'] = 'Conflicting name'
        with self.assertRaisesRegex(ValueError, 'conflicting titles'):
            kr_activities.check_link_titles(model['key_results'])


if __name__ == '__main__':
    unittest.main()
