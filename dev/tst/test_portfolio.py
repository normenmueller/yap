"""Canonical membership, tracking and addresses survive location changes."""

from pathlib import Path
import tempfile
import unittest

from yap import portfolio


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yap portfolio ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.control('')
        self.entry('pfo/act/cpp', 'cpp')
        self.entry('pfo/act/cpp/sfe', 'sfe', body='## v1 {#v1 .version}\n')
        self.entry('pfo/act/elsewhere/fnd', 'fnd')
        self.entry('pfo/nts/context', 'context', kind='note')

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def control(self, extra):
        self.write('pfo/act/act.md', '---\ntitle: Activity\ntracking:\n  "sfe#v1": {status: released}\n'+extra+'\n---\n')

    def entry(self, folder, key, kind='activity', body=''):
        return self.write(f'{folder}/{Path(folder).name}.md',
                          f'---\nkind: {kind}\nkey: {key}\ntitle: {key}\n---\n'+body)

    def test_membership_tracking_and_publication_survive_source_move(self):
        self.control('members:\n  cpp: [sfe, fnd]\npublication:\n  sfe:\n    id: act-dbf--sup--cpp--sfe\n    resource-root: dbf/sup/cpp/sfe')
        before = portfolio.load(self.root)
        folder = self.root / 'pfo/act/cpp/sfe'
        moved = self.root / 'pfo/act/sfe'
        folder.rename(moved)
        after = portfolio.load(self.root)
        self.assertEqual(before['members'], after['members'])
        original = {n['key']: dict(n) for n in before['nodes']}
        changed = {n['key']: dict(n) for n in after['nodes']}
        self.assertNotEqual(original['sfe'].pop('path'), changed['sfe'].pop('path'))
        self.assertEqual(original, changed)
        self.assertEqual(changed['sfe']['id'], 'act-dbf--sup--cpp--sfe')
        self.assertEqual(changed['sfe']['resource_root'], 'dbf/sup/cpp/sfe')
        self.assertNotIn('parent', changed['sfe'])
        self.assertNotIn('depth', changed['sfe'])

    def test_filing_and_presentation_do_not_create_membership(self):
        model = portfolio.load(self.root)
        self.assertEqual(model['members'], {})
        self.assertEqual(portfolio.leaf_selection(model['members'], ['cpp'], {'cpp','sfe','fnd'}), {'cpp'})
        self.write('pov/arbitrary/.perspective.yaml', '{"entries":[]}')
        self.assertEqual(portfolio.load(self.root), model)

    def test_consumer_specific_leaf_eligibility_and_shared_members(self):
        members = {'context':['cpp','other'], 'cpp':['sfe','fnd'], 'other':['sfe']}
        self.assertEqual(portfolio.leaf_selection(members, ['context'], {'cpp','sfe','fnd','other'}), {'sfe','fnd'})
        self.assertEqual(portfolio.leaf_selection(members, ['context'], {'cpp','other'}), {'cpp','other'})
        self.assertEqual(portfolio.descendants(members,'context'), ['cpp','sfe','fnd','other'])

    def test_membership_rejects_unknown_duplicate_and_cyclic_references(self):
        for spec, message in (
            ('  missing: [sfe]', 'unknown entry'),
            ('  cpp: [missing]', 'unknown member'),
            ('  cpp: [sfe, sfe]', 'duplicate member'),
            ('  cpp: [sfe]\n  sfe: [cpp]', 'cycle'),
        ):
            self.control('members:\n'+spec)
            with self.subTest(spec=spec), self.assertRaisesRegex(ValueError, message):
                portfolio.load(self.root)

    def test_notes_have_no_tracking_versions_or_implicit_resource_export(self):
        model=portfolio.load(self.root)
        note=next(n for n in model['nodes'] if n['key']=='context')
        self.assertIsNone(note['resource_root'])
        self.write('pfo/act/act.md', '---\ntitle: Activity\ntracking:\n  context: {status: wip}\n---\n')
        with self.assertRaisesRegex(ValueError, 'unknown activity'):
            portfolio.load(self.root)
        self.control('')
        self.entry('pfo/nts/context', 'context', kind='note', body='## Version {.version}\n')
        with self.assertRaisesRegex(ValueError, 'notes cannot own activity versions'):
            portfolio.load(self.root)

    def test_publication_rejects_duplicate_ids_and_unsafe_routes(self):
        for spec, message in (
            ('  sfe: {id: act-cpp}', 'duplicate publication ID'),
            ('  sfe: {resource-root: ../escape}', 'safe relative'),
            ('  sfe: {resource-root: shared//route}', 'safe relative'),
            ('  sfe: {resource-root: shared/}', 'safe relative'),
            ('  sfe: {resource-root: cpp}', 'duplicate resource-root'),
            ('  sfe: {resource-root: CPP}', 'duplicate resource-root'),
            ('  ghost: {id: act-ghost}', 'unknown entry'),
        ):
            self.control('publication:\n'+spec)
            with self.subTest(spec=spec), self.assertRaisesRegex(ValueError, message):
                portfolio.load(self.root)

    def test_reclassifying_area_preserves_addresses_and_members_but_not_tracking(self):
        source = self.entry('pfo/act/area', 'area')
        self.control('members:\n  area: [cpp, fnd]\npublication:\n  cpp: {id: act-legacy-cpp}')
        before = portfolio.load(self.root)
        source.write_text(source.read_text().replace('kind: activity', 'kind: area'))
        after = portfolio.load(self.root)
        self.assertEqual(before['members'], after['members'])
        self.assertEqual([(n['key'], n['id'], n['resource_root']) for n in before['nodes']],
                         [(n['key'], n['id'], n['resource_root']) for n in after['nodes']])
        eligible = {n['key'] for n in after['nodes'] if n['kind'] == 'activity'}
        self.assertEqual(portfolio.leaf_selection(after['members'], ['area'], eligible), {'cpp', 'fnd'})
        self.write('pfo/act/act.md', '---\ntracking:\n  area: {status: wip}\n---\n')
        with self.assertRaisesRegex(ValueError, 'unknown activity'):
            portfolio.load(self.root)
        self.control('')
        source.write_text(source.read_text() + '\n## v1 {.version}\n')
        with self.assertRaisesRegex(ValueError, 'areas cannot own activity versions'):
            portfolio.load(self.root)
