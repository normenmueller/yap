"""Illustrative work evidence stays separate from authored tracking and KR results."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yap import work_progress, performance


class WorkProgressTests(unittest.TestCase):
    def setUp(self):
        self.model = dict(
            nodes=[dict(key=k, id='act-'+k, kind='activity', title=k, status=s, priority=p)
                   for k, s, p in [('busy','wip','p1'), ('other','wip','p2'), ('paused','on hold','p1')]],
            goals=[dict(key='one', id='goal-one', activities=[dict(key='busy')]),
                   dict(key='two', id='goal-two', activities=[dict(key='busy'),dict(key='other')])],
            key_results={k:[dict(key='result',activities=activities,target=1)]
                         for k,activities in [('one',['busy']),('two',['busy','other','paused'])]},
            work_preview=dict(provenance='illustrative-not-collected',as_of='2026-10-13',quips=[
                dict(id=str(i),activity=k,date=d,kind='Draft',title='Refined draft')
                for i,(k,d) in enumerate([('busy','2026-10-12'),('busy','2026-10-13'),
                                          ('other','2026-10-13'),('paused','2026-10-13')])]))

    def test_counts_scope_and_priority_use_one_evidence_set_without_changing_results(self):
        original=deepcopy(self.model)
        scene=work_progress.project(self.model)
        self.assertEqual((scene['today'],scene['total'],scene['focus']), (2,3,2))
        self.assertEqual([r['node']['key'] for r in scene['rows']], ['busy','other'])
        self.assertEqual(sum(sum(r['counts']) for r in scene['rows']),scene['total'])
        html=work_progress.render(self.model)
        self.assertIn('67<span>%',html)
        self.assertIn('data-work-select="busy" aria-pressed="true"',html)
        self.assertNotIn('data-work-select="paused"',html)
        self.assertEqual(self.model,original)
        self.model['selection']={'key':'active'}
        self.model['goals']=self.model['goals'][:1]
        self.model['key_results'].pop('two')
        scene=work_progress.project(self.model)
        self.assertEqual((scene['today'],scene['total'],scene['focus']), (1,2,2))
        self.model['nodes'][0]['priority']='p2'
        self.assertEqual(work_progress.project(self.model)['focus'],0)
        self.model['nodes'][0]['status']='on hold'
        self.assertEqual(work_progress.project(self.model)['total'],0)
        self.assertIn('Für diese Auswahl liegen keine quips vor.',work_progress.render(self.model))

    def test_unknown_is_empty_and_authored_text_is_escaped(self):
        self.model['work_preview']=None
        self.assertEqual(work_progress.render(self.model),'')
        self.setUp()
        self.model['work_preview']['quips'][0]['title']='<script>alert(1)</script>'
        html=work_progress.render(self.model)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)

    def test_unassigned_work_is_visible_only_in_unfiltered_scene(self):
        self.model['nodes'].append(dict(key='side', id='side', kind='activity', title='Side', status='wip', priority='p3'))
        self.model['work_preview']['quips'].append(dict(id='weekend', activity='side',
            date='2026-10-11', weekday='sun', kind='Draft', title='Refined home page'))
        scene = work_progress.project(self.model)
        self.assertEqual((scene['total'], scene['today'], scene['focus']), (4, 2, 2))
        self.assertEqual(next(r for r in scene['rows'] if r['node']['key']=='side')['counts'], [0,0,0,0,1,0,0])
        html = work_progress.render(self.model)
        self.assertIn('Freie quips', html)
        self.assertIn('<span class="work-you">Du</span>', html)
        feed = work_progress._feed(self.model, scene, 'side')
        self.assertNotIn('href="#goal-', feed)
        for scope in ('active', 'paused', 'closed'):
            self.model['selection'] = {'key': scope}
            self.assertNotIn('side', [r['node']['key'] for r in work_progress.project(self.model)['rows']])
        self.model.pop('selection')
        self.model['nodes'][-1]['status'] = 'on hold'
        self.assertNotIn('side', [r['node']['key'] for r in work_progress.project(self.model)['rows']])

    def test_refresh_retains_explicit_sunday_and_validates_weekday(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / work_progress.PREVIEW
            path.parent.mkdir(parents=True)
            self.model['work_preview']['quips'][0].update(date='2026-10-11', weekday='sun')
            path.write_text(json.dumps(self.model['work_preview']))
            work_progress.load_preview(root, self.model['nodes'])
            with patch('yap.content.load', return_value=self.model):
                work_progress.refresh_date(root, '2026-10-23', apply=True)
            updated = work_progress.load_preview(root, self.model['nodes'])
            self.assertEqual(updated['quips'][0]['date'], '2026-10-18')
            updated['quips'][0]['weekday'] = 'sat'
            path.write_text(json.dumps(updated))
            with self.assertRaisesRegex(ValueError, 'weekday'):
                work_progress.load_preview(root, self.model['nodes'])

    def test_demo_refresh_is_explicit_repeatable_and_preserves_non_date_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / work_progress.PREVIEW
            path.parent.mkdir(parents=True)
            self.model['work_preview']['results'] = {'one/result': dict(reached=True, detail='Available')}
            original = deepcopy(self.model)
            path.write_text(json.dumps(original['work_preview']))
            before = path.read_bytes()
            with patch('yap.content.load', return_value=self.model):
                preview = work_progress.refresh_date(root, '2026-10-23')
                self.assertIn('2026-10-17 – 2026-10-23', preview)
                self.assertEqual(path.read_bytes(), before)
                work_progress.refresh_date(root, '2026-10-23', apply=True)
                self.assertEqual(self.model, original)
            updated = json.loads(path.read_text())
            self.assertEqual(updated['as_of'], '2026-10-23')
            self.assertEqual(updated['quips'][0]['date'], '2026-10-22')
            for old, new in zip(original['work_preview']['quips'], updated['quips']):
                self.assertEqual({k:v for k,v in old.items() if k != 'date'},
                                 {k:v for k,v in new.items() if k != 'date'})
            self.assertEqual(updated['results'], original['work_preview']['results'])
            self.assertEqual(updated['provenance'], 'illustrative-not-collected')
            self.model['work_preview'] = updated
            before = path.read_bytes()
            with patch('yap.content.load', return_value=self.model):
                work_progress.refresh_date(root, '2026-10-23', apply=True)
                self.assertEqual(path.read_bytes(), before)
                work_progress.refresh_date(root, '2026-10-13', apply=True)
                self.assertEqual(json.loads(path.read_text()), original['work_preview'])
                before = path.read_bytes()
                with self.assertRaises(ValueError):
                    work_progress.refresh_date(root, '2026-02-30', apply=True)
                self.assertEqual(path.read_bytes(), before)
            with patch('yap.content.load', side_effect=ValueError('Invalid fixture')):
                with self.assertRaisesRegex(ValueError, 'Invalid fixture'):
                    work_progress.refresh_date(root, '2026-10-23', apply=True)
                self.assertEqual(path.read_bytes(), before)

    def test_illustrative_results_only_affect_rendering_copies(self):
        self.model['work_preview']['results'] = {
            'one/result': dict(reached=True, detail='The evaluation is available.'),
            'two/result': dict(reached=False, detail='Alignment remains open.')}
        original = deepcopy(self.model)
        rows = work_progress.result_view(self.model)
        self.assertEqual(rows['one'][0]['current'], 1)
        self.assertEqual(rows['two'][0]['current'], 0)
        self.assertEqual(self.model, original)
        self.assertIn('Erreicht', performance._metric(rows['one'][0], True))
        self.assertIn('Noch offen', performance._metric(rows['two'][0], True))
        self.model['key_results']['one'][0].update(current=0, previous=0)
        rows = work_progress.result_view(self.model)
        self.assertEqual(rows['one'][0]['current'], 0)
        self.assertNotIn('_presentation_outcome', rows['one'][0])

    def test_illustrative_outcomes_require_known_binary_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / work_progress.PREVIEW
            path.parent.mkdir(parents=True)
            data = deepcopy(self.model['work_preview'])
            data['results'] = {'one/result': dict(reached=True, detail='Available')}
            path.write_text(json.dumps(data))
            results = {'one': [dict(key='result', target=1, unit='assessment')]}
            self.assertEqual(work_progress.load_preview(root, self.model['nodes'], results), data)
            for invalid in ({}, {'one': [dict(key='result', target=100, unit='%')]}):
                with self.assertRaises(ValueError):
                    work_progress.load_preview(root, self.model['nodes'], invalid)
            data['results']['one/result']['reached'] = 0.5
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                work_progress.load_preview(root, self.model['nodes'], results)

    def test_preview_requires_explicit_provenance_known_unique_entries_and_fixed_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=root/work_progress.PREVIEW
            path.parent.mkdir(parents=True)
            self.assertIsNone(work_progress.load_preview(root,self.model['nodes']))
            data=self.model['work_preview']
            path.write_text(json.dumps(data))
            self.assertEqual(work_progress.load_preview(root,self.model['nodes']),data)
            variants=[]
            bad=deepcopy(data);bad['provenance']='observed';variants.append(bad)
            bad=deepcopy(data);bad['quips'].append(bad['quips'][0]);variants.append(bad)
            bad=deepcopy(data);bad['quips'][0]['activity']='unknown';variants.append(bad)
            bad=deepcopy(data);bad['quips'][0]['date']='2026-10-14';variants.append(bad)
            bad=deepcopy(data);bad['quips'][0]['date']='2026-10-06';variants.append(bad)
            for bad in variants:
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    work_progress.load_preview(root,self.model['nodes'])
