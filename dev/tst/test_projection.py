"""Saved placement structure projects content without creating domain facts."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from yap import activity_map, board, catalog, dgraph, documents, palette, performance_lanes, projection, views


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='yap projection ')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()
        for collection,key,kind in [('act','cpp','activity'),('act','sfe','activity'),('nts','context','note')]:
            folder=self.root/'pfo'/collection/key
            folder.mkdir(parents=True)
            (folder/(key+'.md')).write_text(f'---\nkind: {kind}\nkey: {key}\ntitle: Full {key}\n---\n')
        self.entries=catalog.discover(self.root)
        self.definition={'schema':1,'title':'Report','entries':[
            {'id':'p000001','name':'arbitrary','alias':'Area','entries':[
                {'id':'p000002','name':'ordinary-note','target':{'entry':'context'}},
                {'id':'p000003','name':'category','entries':[
                    {'id':'p000004','name':'system','entries':[
                        {'id':'p000005','name':'description','target':{'entry':'cpp'}},
                        {'id':'p000006','name':'module','target':{'entry':'sfe'}}]}]}]}],
            'presentation':{'placements':{
                'p000001':{'role':'context','heading-source':'p000002','document-style':'chapter','map':'subtree'},
                'p000003':{'role':'category','category':'support','tone':'support'},
                'p000004':{'role':'lane','heading-source':'p000005','document-style':'card'},
                'p000005':{'board-card':'tracked'},
                'p000006':{'tone':'strategy'}},'board':{'category-order':['support']}}}

    def project(self):
        return projection.outline(self.definition,self.entries)

    def test_explicit_heading_leaf_is_consumed_once_without_group_identity(self):
        before=deepcopy(self.entries)
        result=self.project()['nodes']
        self.assertEqual([n['placement'] for n in result],['p000001','p000003','p000004','p000006'])
        context,lane=result[0],result[2]
        self.assertEqual((context['label'],context['title']),('Area','Full context'))
        self.assertEqual(context['board_card'],'never')
        self.assertEqual((lane['entry'],lane['source_placement'],lane['board_card']),('cpp','p000005','tracked'))
        self.assertEqual(self.entries,before)
        self.assertNotIn('parent',self.entries['cpp'])
        self.assertEqual(result[3]['tone'],'strategy')

    def test_names_and_source_location_do_not_define_projection_semantics(self):
        before=self.project()
        self.definition['entries'][0]['name']='unrelated-name'
        # Explicit alias and placement annotations remain authoritative.
        self.assertEqual(self.project(),before)
        old=self.entries['sfe']['folder']
        new=self.root/'pfo/act/cpp/sfe'
        old.rename(new)
        self.entries=catalog.discover(self.root)
        self.assertEqual(self.project(),before)

    def test_board_grouping_and_label_orientation_are_explicit(self):
        self.definition['presentation']['board'] = {'grouping': 'overview'}
        self.definition['presentation']['placements']['p000004']['board-label'] = 'vertical'
        report = self.project()
        self.assertEqual(report['board_grouping'], 'overview')
        self.assertEqual(next(p for p in report['nodes'] if p['placement'] == 'p000004')['board_label'], 'vertical')
        for invalid in ('diagonal', None):
            self.definition['presentation']['placements']['p000004']['board-label'] = invalid
            with self.assertRaisesRegex(ValueError, 'board-label'):
                self.project()
        self.definition['presentation']['placements']['p000004']['board-label'] = 'vertical'
        self.definition['presentation']['board']['category-order'] = ['support']
        with self.assertRaisesRegex(ValueError, 'inherits'):
            self.project()

    def test_flow_columns_reference_unique_activity_placements(self):
        self.definition['presentation']['flow'] = {'columns': [['p000004']]}
        self.assertEqual(self.project()['graph_columns'], [['cpp']])
        for columns in ([['p000004'], ['p000004']], [['p000001']], [['missing']], [[]], 'cpp'):
            with self.subTest(columns=columns):
                self.definition['presentation']['flow']['columns'] = columns
                with self.assertRaisesRegex(ValueError, 'Flow columns'):
                    self.project()

    def test_flow_lane_bindings_and_ports_are_explicit_and_validated(self):
        flow = dict(columns=[['p000004']], lanes=[
            dict(key='sup', label='Support', tone='support', columns=[1])],
            **{'edge-ports': [dict(source='p000004', target='p000006', exit='top', entry='bottom')],
               'align-centers': [['p000006', 'p000004']]})
        self.definition['presentation']['flow'] = flow
        result = self.project()
        self.assertEqual(result['graph_edge_ports'], [dict(source='cpp', target='sfe', exit='top', entry='bottom')])
        self.assertEqual(result['graph_align_centers'], [['sfe', 'cpp']])
        self.definition['presentation']['flow'] = dict(flow, **{'node-order': ['p000006', 'p000004']})
        ordered = self.project()
        self.assertEqual(ordered['graph_node_order'], ['sfe', 'cpp'])
        self.assertEqual(ordered['nodes'], result['nodes'])
        self.definition['presentation']['flow'] = dict(flow, **{'offset-y': {'p000004': -16}})
        self.assertEqual(self.project()['graph_offset_y'], {'cpp': -16})
        positioned = dict(flow['edge-ports'][0], **{'exit-position': .25, 'entry-position': .5})
        self.definition['presentation']['flow'] = dict(flow, **{'edge-ports': [positioned]})
        self.assertEqual(self.project()['graph_edge_ports'][0]['exit_position'], .25)
        for value in (0, 1, True, 'middle', float('nan')):
            positioned['exit-position'] = value
            with self.assertRaisesRegex(ValueError, 'port positions'):
                self.project()
        for field, value in [('lanes', [dict(key='sup', label='Support', tone='support', columns=[2])]),
                             ('edge-ports', [dict(source='p000004', target='p000006', exit='diagonal')]),
                             ('align-centers', [['p000004', 'p000004']]),
                             ('node-order', ['p000006', 'p000006']),
                             ('node-order', ['missing']), ('node-order', 'p000006'),
                             ('offset-y', {'missing': 0}), ('offset-y', {'p000004': True}),
                             ('offset-y', {'p000004': 'up'})]:
            with self.subTest(field=field):
                self.definition['presentation']['flow'] = dict(flow, **{field: value})
                with self.assertRaisesRegex(ValueError, 'Flow'):
                    self.project()

    def test_realm_lanes_require_explicit_groups_and_own_the_layout(self):
        realms = [{'placement': 'p000001', 'sections': ['p000003']}]
        self.definition['presentation']['flow'] = {'realm-lanes': realms}
        self.assertEqual(self.project()['graph_realms'], realms)
        self.definition['presentation']['flow']['align-centers'] = [['p000006', 'p000004']]
        self.assertEqual(self.project()['graph_align_centers'], [['sfe', 'cpp']])
        self.definition['presentation']['flow']['unframe'] = ['p000004']
        self.definition['presentation']['flow']['offset-y'] = {'p000006': 12}
        self.definition['presentation']['flow']['edge-ports'] = [
            dict(source='p000006', target='p000004', exit='right', entry='bottom')]
        self.assertEqual(self.project()['graph_offset_y'], {'sfe': 12})
        self.assertEqual(self.project()['graph_edge_ports'][0]['entry'], 'bottom')
        self.assertEqual(self.project()['graph_unframe'], ['cpp'])
        for invalid in (['missing'], ['p000004', 'p000004'], 'p000004'):
            self.definition['presentation']['flow']['unframe'] = invalid
            with self.assertRaisesRegex(ValueError, 'Flow unframe'):
                self.project()
        for invalid in ([{'placement': 'p000001', 'sections': ['p000006']}],
                        [{'placement': 'p000001', 'sections': ['p000003', 'p000003']}],
                        [{'placement': 'p000003', 'sections': ['p000001']}]):
            self.definition['presentation']['flow'] = {'realm-lanes': invalid}
            with self.assertRaisesRegex(ValueError, 'Flow realm-lanes'):
                self.project()
        self.definition['presentation']['flow'] = {'realm-lanes': realms, 'columns': [['p000004']]}
        with self.assertRaisesRegex(ValueError, 'owns its layout'):
            self.project()

    def test_epistemics_tone_overrides_support_and_survives_other_presentations(self):
        fields = self.definition['presentation']['placements']
        fields['p000004']['tone'] = 'epistemics'
        del fields['p000006']['tone']
        nodes = [dict(key=key, id='act-' + key, title=entry['title'], kind=entry['kind'],
                      path=str(entry['source']), blocks=[], meta={}, status='wip', priority='p1')
                 for key, entry in self.entries.items()]
        model = dict(api=[1, 23, 1], meta={}, nodes=nodes, goals=[], members={}, report=self.project())
        before = deepcopy(model)
        rows = board.lanes(model)
        self.assertEqual(rows[0]['tone'], 'namViolet')
        nested = rows[0]['sublanes'][0]['sublanes'][0]
        self.assertEqual(nested['tone'], 'namEpistemics')
        self.assertEqual([n['tone'] for n in model['report']['nodes'][-2:]],
                         ['epistemics', 'epistemics'])
        self.assertIn('namEpistemics', board.tex(rows))
        board.render_html(rows, self.root)
        self.assertIn('class="board-row labelled lane-namEpistemics" data-lane="p000004"',
                      (self.root/'index.html').read_text())
        self.assertIn('tone-epistemics', activity_map.render(model))
        self.assertIn('namEpistemics', views.map_tex(model))
        self.assertIn('--kr-tone:#' + palette.HEX['namEpistemics'],
                      performance_lanes.render(model, ['sfe']))
        meta = {'dgraph': {'t': 'MetaMap', 'c': {'spec': {'t': 'MetaString', 'c': 'cpp -> sfe'}}}}
        graph = dgraph.parse(meta, nodes, {}, model['report'])
        self.assertTrue(all(n['color'] == palette.HEX['namEpistemics'] for n in graph['nodes']))
        for output in (dgraph.svg(graph), dgraph.tex(graph)):
            self.assertIn(palette.HEX['namEpistemics'], output)
        fields['p000003']['tone'] = 'epistemics'
        category_model = dict(model, report=self.project())
        headers = documents.activity(category_model, self.root)['blocks']
        category = next(h for h in headers if h['t'] == 'Header' and 'tone-heading' in h['c'][1][1])
        self.assertEqual(dict(category['c'][1][2])['tone'], 'epistemics')
        self.assertEqual(model, before)

    def test_subtree_map_publication_path_is_explicit_safe_and_unique(self):
        fields = self.definition['presentation']['placements']['p000001']
        fields['map-path'] = 'rnd'
        self.assertEqual(self.project()['nodes'][0]['map_path'], 'rnd')
        for invalid in ('../rnd', '/rnd', 'rnd/submap', '', [], [1], 1, {'name': 'rnd'}, 'rnd#extra', 'rnd?extra', 'rnd%20extra', 'index.html', 'map.pdf', 'map.png'):
            fields['map-path'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.project()
        fields['map-path'] = 'rnd'
        other = self.definition['presentation']['placements']['p000004']
        other.update({'map': 'subtree', 'map-path': 'RND'})
        with self.assertRaisesRegex(ValueError, 'duplicate map-path'):
            self.project()
        del other['map']
        with self.assertRaisesRegex(ValueError, 'requires a subtree map'):
            self.project()

    def test_repeated_source_body_has_only_one_canonical_destination(self):
        self.definition['entries'].append({'id':'p000007','name':'again','target':{'entry':'sfe'}})
        nodes=[n for n in self.project()['nodes'] if n['entry']=='sfe']
        self.assertEqual([n['render_body'] for n in nodes],[True,False])

    def test_document_shortcuts_do_not_default_to_activity_cards(self):
        self.definition['entries'].append({'id':'p000007','name':'document',
                                          'display':'document','target':{'entry':'sfe','path':'sfe.md'}})
        self.assertEqual(self.project()['nodes'][-1]['board_card'],'never')

    def test_consumed_leaf_annotations_cannot_disappear_silently(self):
        fields=self.definition['presentation']['placements']['p000005']
        for name,value in (('tone','strategy'),('document-style','chapter')):
            fields[name]=value
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'display annotations belong on group'):
                self.project()
            del fields[name]

    def test_no_heading_source_convention_or_implicit_category(self):
        self.definition['presentation']={}
        self.definition['entries'][0]['entries'][0]['name']='_entry'
        result=self.project()['nodes']
        self.assertIsNone(result[0]['entry'])
        self.assertEqual(result[0]['role'],'group')
        self.assertEqual(result[1]['placement'],'p000002')
        self.assertTrue(all(not n['category'] for n in result))

    def test_removing_a_description_preserves_group_pdf_presentation(self):
        def render():
            nodes = [dict(key=key, id='act-' + key, title=entry['title'],
                          path=str(entry['source']), blocks=[], meta={})
                     for key, entry in self.entries.items()]
            model = dict(api=[1, 23, 1], meta={}, nodes=nodes, goals=[], report=self.project())
            return documents.activity(model, Path('site'))['blocks']

        before = render()[0]['c'][1]
        del self.definition['presentation']['placements']['p000001']['heading-source']
        del self.definition['entries'][0]['entries'][0]
        del self.entries['context']
        blocks = render()
        heading = blocks[0]['c'][1]
        self.assertEqual(heading[0], documents.pdf_target('view-p000001'))
        self.assertEqual(heading[1:], before[1:])
        self.assertIn('chapter-pages', heading[1])
        self.assertEqual(dict(heading[2])['map'], 'site/views/activity-map/p000001/map.png')
        category = blocks[1]['c'][1]
        self.assertIn('tone-heading', category[1])
        self.assertEqual(dict(category[2])['tone'], 'violet')
        self.assertNotIn('act-context', str(blocks))

    def test_unknown_nonchild_and_resource_heading_sources_fail(self):
        fields=self.definition['presentation']['placements']['p000001']
        for selected in ('p999999','p000003','p000006'):
            fields['heading-source']=selected
            with self.subTest(selected=selected),self.assertRaisesRegex(ValueError,'direct child source leaf'):
                self.project()
        fields['heading-source']='p000002'
        note=self.entries['context']['folder']/'res/note.txt'
        note.parent.mkdir()
        note.write_text('Attachment')
        self.definition['entries'][0]['entries'][0]['target']['path']='res/note.txt'
        with self.assertRaisesRegex(ValueError,'complete source document'):
            self.project()

    def test_unknown_annotations_and_duplicate_context_categories_fail(self):
        self.definition['presentation']['placements']['p999999']={}
        with self.assertRaisesRegex(ValueError,'Unknown presentation placements'):
            self.project()
        del self.definition['presentation']['placements']['p999999']
        self.definition['entries'][0]['entries'].append({'id':'p000007','name':'duplicate','entries':[]})
        self.definition['presentation']['placements']['p000007']={'role':'category','category':'support'}
        with self.assertRaisesRegex(ValueError,'duplicate category'):
            self.project()

    def test_malformed_annotation_values_have_actionable_validation_errors(self):
        for field in ('role','tone','document-style','board-card'):
            saved=deepcopy(self.definition)
            self.definition['presentation']['placements']['p000001'][field]=[]
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.project()
            self.definition=saved
        self.definition['presentation']['placements']['p000005']=None
        with self.assertRaisesRegex(ValueError,'requires a mapping'):
            self.project()
