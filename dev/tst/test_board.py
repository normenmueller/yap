"""Board grouping, ordering, escaping and source-only notes."""

from fixtures import report_model

from pathlib import Path
import tempfile
import unittest

from yap import board, content, performance_lanes


def node(key, status='', priority='', title=None):
    return dict(key=key, parent=key.rpartition('/')[0], id='act-' + key.replace('/', '--'),
                title=title or key.rsplit('/', 1)[-1], status=status, priority=priority)


class BoardTests(unittest.TestCase):
    def test_unassigned_status_is_visible_and_distinct_from_authored_icebox(self):
        model = report_model({'nodes': [node('unassigned'), node('icebox', 'ibx')]})
        rows = board.lanes(model)
        self.assertEqual([c['key'] for row in board.display_rows(rows) for c in row['cells']['']], ['unassigned'])
        self.assertEqual([c['key'] for row in board.display_rows(rows) for c in row['cells']['ibx']], ['icebox'])
        self.assertEqual(len(board.columns(rows)), 5)
        with tempfile.TemporaryDirectory() as temp:
            board.render_html(rows, Path(temp))
            html = (Path(temp) / 'index.html').read_text()
        for output in (html, board.tex(rows), performance_lanes.render(model, ['unassigned'])):
            self.assertIn('Ohne Status', output)
        self.assertIn('--status-count:5', html)
        model['nodes'][0]['status'] = 'wip'
        self.assertEqual(board.columns(board.lanes(model)), board.COLUMNS)

    def test_released_cards_omit_priority_in_all_board_outputs(self):
        for status, priority, label in (('released', '', ''), ('on hold', 'p2', 'Priorität p2'),
                                        ('wip', '', 'Ohne Prio')):
            for versioned in (False, True):
                with self.subTest(status=status, priority=priority, versioned=versioned):
                    activity = node('rnd/gov/item', status, priority)
                    if versioned:
                        activity['versions'] = [dict(anchor='v1', label='v1', status=status, priority=priority)]
                    model = {'nodes': [node('rnd'), node('rnd/gov'), activity]}
                    model = report_model(model)
                    rows = board.lanes(model)
                    with tempfile.TemporaryDirectory() as temp:
                        board.render_html(rows, Path(temp))
                        html = (Path(temp) / 'index.html').read_text()
                    embedded = performance_lanes.render(model, ['rnd/gov/item'])
                    tex = board.tex(rows)
                    if not label:
                        self.assertNotIn('class="priority"', html)
                        self.assertNotIn('class="kr-activity-priority"', embedded)
                        self.assertNotIn('Ohne Prio', tex)
                        self.assertNotIn(r'\\[3pt]{\small\color{namMuted}', tex)
                    else:
                        self.assertIn('class="priority"', html)
                        self.assertIn('class="kr-activity-priority"', embedded)
                        for output in (html, embedded):
                            self.assertIn('title="' + label + '" aria-label="' + label + '"', output)
                            self.assertNotIn('>' + label + '</span>', output)
                        marker = board.card_tex_parts(board.activity_cards(activity)[0])[2]
                        self.assertNotIn(label, marker)
                        if priority:
                            self.assertIn(r'\textbullet', marker)
                        else:
                            self.assertEqual(marker, '')

    def test_shared_categories_follow_first_occurrence_in_source_sequence(self):
        rnd = [node(key) for key in ('rnd', 'rnd/sup', 'rnd/sup/ace',
                                    'rnd/gov', 'rnd/gov/noEA')]
        dbf = [node(key) for key in ('dbf', 'dbf/imp', 'dbf/imp/cio-fv',
                                    'dbf/gov', 'dbf/gov/bkitd', 'dbf/sup', 'dbf/sup/cpp')]
        for nodes, expected, contexts in ((rnd+dbf, ['sup', 'gov', 'imp'], ['RND', 'DBF']),
                                           (dbf+rnd, ['imp', 'gov', 'sup'], ['DBF', 'RND'])):
            with self.subTest(expected=expected):
                lanes = board.lanes(report_model({'nodes': nodes, 'board_sequence': expected}))
                self.assertEqual([lane['key'] for lane in lanes], expected)
                governance = next(lane for lane in lanes if lane['key'] == 'gov')
                self.assertEqual([lane['title'] for lane in governance['sublanes']], contexts)

    def test_distinct_lanes_leaves_tracked_parents_and_priority_sort(self):
        model = {'nodes': [node('rnd'), node('rnd/gov'), node('rnd/gov/parent'),
            node('rnd/gov/parent/child', 'wip', 'p3'), node('rnd/gov/low', 'wip', 'p4'),
            node('rnd/gov/first', 'wip', 'p1'), node('rnd/gov/second', 'wip', 'p1'),
            node('rnd/gov/unassigned', 'wip'), node('rnd/gov/ice'),
            node('rnd/gov/tracked', 'on hold'), node('rnd/gov/tracked/child', 'ibx', 'p2'),
            node('dbf'), node('dbf/gov'), node('dbf/gov/item', 'on hold'), dict(node('misc'), kind='note')]}
        model = report_model(model)
        rows = board.lanes(model)
        self.assertEqual([lane['key'] for lane in rows], ['gov'])
        self.assertEqual([lane['title'] for lane in rows[0]['sublanes']], ['RND', 'DBF'])
        rows = rows[0]['sublanes']
        self.assertEqual([card['key'] for card in rows[0]['cells']['wip']],
            ['rnd/gov/first', 'rnd/gov/second', 'rnd/gov/low', 'rnd/gov/unassigned'])
        self.assertEqual([card['key'] for card in rows[0]['cells']['']],
                         ['rnd/gov/ice'])
        projects = rows[0]['sublanes']
        self.assertEqual([project['key'] for project in projects], ['rnd/gov/parent', 'rnd/gov/tracked'])
        self.assertEqual(projects[0]['cells']['wip'][0]['key'], 'rnd/gov/parent/child')
        self.assertEqual(projects[1]['cells']['on hold'][0]['key'], 'rnd/gov/tracked')
        self.assertEqual(projects[1]['cells']['ibx'][0]['key'], 'rnd/gov/tracked/child')
        self.assertEqual(rows[0]['description'], 'rnd')
        self.assertEqual(rows[1]['description'], 'dbf')
        self.assertIn('ibx', content.STATUSES)

    def test_html_and_tex_share_cards_and_escape_authored_text(self):
        rows = board.lanes(report_model({'nodes': [node('rnd'), node('rnd/ace'),
            node('rnd/ace/x', 'ibx', 'p2', '<script>& 50%_#'),
            node('rnd/ace/other', 'ibx', 'p4')]}))
        with tempfile.TemporaryDirectory() as temp:
            board.render_html(rows, Path(temp))
            html = (Path(temp) / 'index.html').read_text()
        self.assertNotIn('<script>', html.replace(board.FOLD_SCRIPT, ''))
        self.assertIn('&lt;script&gt;&amp; 50%_#', html)
        self.assertIn('../../acc/pdf/Activity - Details.pdf#nameddest=act-rnd--ace--x', html)
        self.assertIn('dot p2', html)
        self.assertIn('dot p4', html)
        self.assertIn('ibx · Icebox', html)
        self.assertNotIn('Ohne Status', html)
        tex = board.tex(rows)
        self.assertIn(r'\& 50\%\_\#', tex)
        self.assertIn(r'\textcolor{namMarkerOrange}{\textbullet}', tex)
        self.assertIn(r'\textcolor{namPriorityLow}{\textbullet}', tex)
        self.assertLess(tex.index('50'), tex.index('other'))

    def test_board_caption_is_the_only_source_of_lane_and_card_captions(self):
        project = node('rnd/gov/project', title='Full project title')
        project.update(acronym='P', subtitle='Not a board caption', synonyms=['Not a board alias'])
        child = node('rnd/gov/project/child', title='Child')
        model = {'nodes': [node('rnd'), node('rnd/gov'), project, child]}
        model = report_model(model)
        rows = board.lanes(model)
        self.assertEqual(rows[0]['sublanes'][0]['sublanes'][0]['title'], 'P')
        self.assertEqual(rows[0]['sublanes'][0]['sublanes'][0]['caption'], '')
        self.assertNotIn('Not a board', board.tex(rows))
        project['board-caption'] = 'Project <note> & 50%'
        child['board-caption'] = 'Child caption'
        rows = board.lanes(model)
        self.assertEqual(rows[0]['sublanes'][0]['sublanes'][0]['caption'], project['board-caption'])
        with tempfile.TemporaryDirectory() as temp:
            board.render_html(rows, Path(temp))
            html = (Path(temp) / 'index.html').read_text()
        self.assertIn('Project &lt;note&gt; &amp; 50%', html)
        self.assertIn('class="card-caption">Child caption', html)
        self.assertNotIn('Not a board', html)
        tex = board.tex(rows)
        self.assertIn(r'\& 50\%', tex)
        self.assertIn('Child caption', tex)
        del project['board-caption']
        self.assertEqual(board.lanes(model)[0]['sublanes'][0]['sublanes'][0]['caption'], '')

    def test_projects_with_modules_get_sublanes_and_independent_tracking(self):
        model = {'nodes': [node('rnd'), node('rnd/ace', title='ACE'),
                          node('rnd/ace/ai4X'), node('rnd/gov', title='Governance'),
                          node('rnd/gov/noEA'), node('rnd/gov/noEA/o2i', 'wip', 'p1')]}
        model = report_model(model)
        rows = board.lanes(model)
        self.assertEqual([row['title'] for row in rows], ['ACE', 'Governance'])
        self.assertEqual(rows[0]['sublanes'][0]['cells'][''][0]['title'], 'ai4X')
        self.assertEqual(rows[0]['sublanes'][0]['cells'][''][0]['context'], '')
        project = rows[1]['sublanes'][0]['sublanes'][0]
        self.assertEqual(project['title'], 'noEA')
        self.assertEqual(project['cells']['wip'][0]['context'], '')
        self.assertEqual(project['cells']['wip'][0]['key'], 'rnd/gov/noEA/o2i')
        self.assertEqual(project['cells']['ibx'], [])
        self.assertEqual(rows[0]['sublanes'][0]['sublanes'], [])
        model['nodes'][4]['status'] = 'on hold'
        rows = board.lanes(model)
        project = rows[1]['sublanes'][0]['sublanes'][0]
        self.assertEqual(project['cells']['on hold'][0]['title'], 'noEA')
        self.assertEqual(project['cells']['on hold'][0]['priority'], '')
        self.assertEqual(project['cells']['wip'][0]['priority'], 'p1')
        with tempfile.TemporaryDirectory() as temp:
            board.render_html(rows, Path(temp))
            html = (Path(temp) / 'index.html').read_text()
        self.assertIn('data-lane="rnd/gov/noEA"', html)
        self.assertNotIn('<div class="card-context">noEA</div>', html)
        self.assertIn('Governance', board.tex(rows))
        self.assertIn(r'{\normalsize\bfseries\color{namOrange}noEA}', board.tex(rows))

    def test_multiple_projects_keep_modules_separate_and_sort_within_sublanes(self):
        model = {'nodes': [node('rnd'), node('rnd/gov'), node('rnd/gov/b'),
            node('rnd/gov/b/low', 'wip', 'p4'), node('rnd/gov/b/high', 'wip', 'p1'),
            node('rnd/gov/b/tie', 'wip', 'p1'), node('rnd/gov/b/part'),
            node('rnd/gov/b/part/child', 'ibx'), node('rnd/gov/a'),
            node('rnd/gov/a/item', 'wip', 'p2'), node('rnd/gov/direct', 'wip', 'p1')]}
        model = report_model(model)
        rows = board.lanes(model)
        projects = rows[0]['sublanes'][0]['sublanes']
        self.assertEqual([p['title'] for p in projects], ['b', 'a'])
        self.assertEqual([c['title'] for c in projects[0]['cells']['wip']], ['high', 'tie', 'low'])
        self.assertEqual(projects[0]['sublanes'][0]['cells']['ibx'][0]['title'], 'child')
        self.assertEqual([c['title'] for c in projects[1]['cells']['wip']], ['item'])
        self.assertEqual([c['title'] for c in rows[0]['sublanes'][0]['cells']['wip']], ['direct'])
        shown = list(board.display_rows(rows))
        self.assertEqual([r['key'] for r in shown], ['rnd', 'rnd/gov/b', 'rnd/gov/b/part', 'rnd/gov/a'])
        cards = [c['key'] for r in shown for cell in r['cells'].values() for c in cell]
        self.assertEqual(len(cards), len(set(cards)))
        self.assertEqual(len(cards), 6)
        model['nodes'].pop()  # Without direct cards, the rail starts at the first project.
        rows = board.lanes(model)
        shown = list(board.display_rows(rows))
        self.assertEqual(len(shown), 3)
        self.assertEqual(shown[0]['rails'][-1]['title'], 'b')
        with tempfile.TemporaryDirectory() as temp:
            board.render_html(rows, Path(temp))
            html = (Path(temp) / 'index.html').read_text()
        self.assertEqual(html.count('class="lane category '), 1)
        self.assertEqual(html.count('class="lane context '), 1)
        self.assertEqual(board.tex(rows).count('rotate=90'), 3)

    def test_impact_preserves_intermediate_lanes_and_module_cards(self):
        model = {'nodes': [node('dbf'), node('dbf/imp'),
            node('dbf/imp/cio-fv'), node('dbf/imp/cio-fv/itd-fv'),
            node('dbf/imp/cio-fv/dbia', 'on hold', 'p2'),
            node('dbf/imp/ops-fv'), node('dbf/imp/ops-fv/tmtv'),
            node('dbf/imp/ops-fv/tmtv/lift', 'on hold', 'p4'),
            node('dbf/imp/ops-fv/tmtv/pps', 'on hold', 'p3')]}
        model = report_model(model)
        lanes = board.lanes(model)
        self.assertEqual([lane['key'] for lane in lanes], ['imp'])
        shown = list(board.display_rows(lanes))
        self.assertEqual([[rail['key'] for rail in row['rails']] for row in shown],
                         [['imp', 'dbf'], ['imp', 'dbf', 'dbf/imp/ops-fv']])
        self.assertEqual(shown[0]['label']['title'], 'cio-fv')
        self.assertEqual(shown[1]['label']['title'], 'tmtv')
        self.assertEqual([[card['title'] for card in row['cells']['on hold']] for row in shown],
                         [['dbia'], ['pps', 'lift']])
        self.assertEqual(len([card for row in shown for cell in row['cells'].values() for card in cell]), 4)
        with tempfile.TemporaryDirectory() as temp:
            board.render_html(lanes, Path(temp))
            html = (Path(temp) / 'index.html').read_text()
        self.assertIn('data-lane="dbf/imp/cio-fv"', html)
        self.assertIn('data-group="dbf/imp/ops-fv"', html)
        self.assertEqual(board.tex(lanes).count('rotate=90'), 3)


if __name__ == '__main__':
    unittest.main()
