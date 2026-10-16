"""Compile real reports: public deep links must name real PDF destinations."""

from fixtures import source_text

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from yap import board, content, documents, publication_links


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(all(shutil.which(tool) for tool in
                         ('pandoc', 'latexmk', 'lualatex', 'pdfinfo')),
                     'PDF integration requires the report toolchain')
class PdfDestinationTests(unittest.TestCase):
    def test_real_reports_expose_activity_objective_and_body_targets(self):
        with tempfile.TemporaryDirectory(prefix='yap-pdf-targets-') as temp:
            root = Path(temp)
            sources = {
                'pfo/act/act.md': '---\ntitle: Activity\ntracking:\n  "x#v0.2": {status: released}\n  "x#v0.3": {status: wip}\n  "cpp/sfe#v1": {status: on hold, priority: p1, next: 1}\n---\n',
                'pfo/act/qualified/qualified.md': '---\nkind: activity\nkey: cpp/sfe\ntitle: Qualified module\n---\n## v1 {#v1 .version}\n',
                'pfo/act/x/x.md': '''---
title: Example activity
---
## Überblick {#überblick}

::: {#entscheidung}

[Maßstab]{#maßstab}

:::

[Heading](#überblick), [Div](#entscheidung), [Span](#maßstab).
[Objective](../../okr/obj/a.md#nächster-schritt).

## v0.2 {#v0.2 .version}

Released version.

## v0.3 {#v0.3 .version}

Current version.
''',
                'pfo/okr/goals.md': '''---
title: Performance
tracking:
  a: {status: active}
---
''',
                'pfo/okr/obj/a.md': '''---
title: Example objective
key: a
---
## Nächster Schritt {#nächster-schritt}

::: {#evidenz}

[Ergebnis]{#ergebnis}

:::

[Heading](#nächster-schritt), [Div](#evidenz), [Span](#ergebnis).
[Activity](../../act/x/x.md#überblick).
''',
            }
            for name, text in sources.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source_text(name, text))
            model = content.load(root)
            env = dict(os.environ, TEXMFVAR=str(root / 'tex-cache'),
                       TEXMFCACHE=str(root / 'tex-cache'), TEXINPUTS=str(ROOT / 'dev/acc/templates/tex') + os.pathsep)

            def run(*args):
                result = subprocess.run(args, cwd=root, env=env, text=True,
                                        capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-4000:])
                return result.stdout

            for name, ast, ids, source in (
                ('activity', documents.activity(model, Path('.yap/local/site')),
                 ('act-x', 'act-x--überblick', 'act-x--entscheidung', 'act-x--maßstab',
                  'act-cpp/sfe', 'act-cpp/sfe--v1'),
                 next(n for n in model['nodes'] if n['key'] == 'x')),
                ('performance', documents.mpm(model, Path('.yap/local/site')),
                 ('goal-a', 'goal-a--nächster-schritt', 'goal-a--evidenz', 'goal-a--ergebnis'),
                 model['goals'][0]),
            ):
                # This fixture builds reports only, without generated map/Flow assets.
                # Retain the actual templates and filters for destination checks.
                ast['meta'].pop('cover-map', None)
                ast['meta'].pop('dependency-graph', None)
                (root / (name + '.json')).write_text(json.dumps(ast))
                arguments = ['pandoc', name + '.json', '-f', 'json', '-t', 'latex-smart',
                             '--standalone', '--template=' + str(ROOT / 'dev/acc/templates/tex/report.tex'),
                             '--lua-filter=' + str(ROOT / 'dev/acc/templates/lua/status.lua')]
                if name == 'activity':
                    arguments.append('--lua-filter=' + str(ROOT / 'dev/acc/templates/lua/layout.lua'))
                run(*arguments, '-o', name + '.tex')
                run('latexmk', '-silent', '-lualatex', '-interaction=nonstopmode',
                    '-halt-on-error', name + '.tex')
                destinations = set(re.findall(r'"([^"]+)"', run('pdfinfo', '-dests', name + '.pdf')))
                self.assertTrue({documents.pdf_target(key) for key in ids} <= destinations,
                                (ids, destinations))
                link = publication_links.activity_pdf(source, 'überblick') if name == 'activity' else publication_links.objective_pdf(source)
                self.assertIn(parse_qs(urlsplit(link).fragment)['nameddest'][0], destinations)
                if name == 'activity':
                    cards = board.activity_cards(source)
                    self.assertEqual(len(cards), 2)
                    for card in cards:
                        target = parse_qs(urlsplit(publication_links.activity_pdf(card)).fragment)['nameddest'][0]
                        self.assertIn(target, destinations)
                    qualified = next(n for n in model['nodes'] if n['key'] == 'cpp/sfe')
                    for card in board.activity_cards(qualified):
                        target = parse_qs(urlsplit(publication_links.activity_pdf(card)).fragment)['nameddest'][0]
                        self.assertIn(target, destinations)
                log = (root / (name + '.log')).read_text()
                self.assertNotRegex(log, r'duplicate|referenced but does not exist')
                tex = (root / (name + '.tex')).read_text()
                for target in re.findall(r'\\hyperref\[([^]]+)\]', tex):
                    self.assertIn(target, destinations)

    def test_target_namespace_is_lossless_and_preserves_existing_simple_ids(self):
        values = ('act-x', 'goal-a', 'act-x--next_step', 'act-x--nächster',
                  'act-x--nuxe4chster', 'act-x--#detail', 'act-x--100%',
                  'act-x--a.b', 'act-x--a:b')
        targets = [documents.pdf_target(value) for value in values]
        self.assertEqual(targets[:3], list(values[:3]))
        self.assertEqual(len(targets), len(set(targets)))
        self.assertTrue(all(re.fullmatch(r'[A-Za-z0-9_-]+', target) for target in targets))
