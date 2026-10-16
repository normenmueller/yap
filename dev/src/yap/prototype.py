"""Isolated perspective prototype. No live migration or work provisioning."""

import argparse
import json
import os
from pathlib import Path
import sys

from . import perspectives as p, perspective_html


MARKER = '.yap/local/prototype.json'


def initialize(root):
    if root.exists():
        raise ValueError('Choose a new, absent directory for the isolated prototype')
    root.mkdir(parents=True)
    for relative in ('pfo/act', 'pfo/okr', 'pfo/nts', 'pov', '.yap/local'):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / MARKER).write_text(p.encode({'schema': 1}), encoding='utf-8')


def require_prototype(root):
    marker = p.real_path(root, MARKER)
    if not marker.is_file() or (root / 'pfo/act/act.md').exists():
        raise ValueError('Use an initialized isolated prototype; live sources are not supported')


def demo(root):
    initialize(root)
    examples = [('Explore', 'explore'), ('build', 'build'), ('launch', 'launch'),
                ('Evaluate', 'evaluate'), ('Coordinate', 'coordinate')]
    for title, key in examples:
        source = p.capture(root, title)
        if source.stem != key:
            old = source.parent
            new = old.with_name(key)
            source.write_text(source.read_text().replace('key: ' + json.dumps(source.stem), 'key: ' + json.dumps(key)))
            source.rename(old / (key + '.md'))
            old.rename(new)
    evaluate = root / 'pfo/act/evaluate/evaluate.md'
    evaluate.write_text(evaluate.read_text() + '## v0.2 {#v0.2 .version}\n\nFixture version.\n\n'
                   '## v0.3 {#v0.3 .version}\n\nFixture version.\n')
    resources = root / 'pfo/act/build/res'
    resources.mkdir()
    (resources / 'note.md').write_text('# Fixture resource\n\nLocal navigation example.\n')
    build = root / 'pfo/act/build/build.md'
    build.write_text(build.read_text() + '[Resource](res/note.md)\n')
    # One disposable existing directory, attached to two entries; no external writes.
    shared = root / '.yap/local/shared-work'
    shared.mkdir()
    (shared / 'README.md').write_text('Disposable shared working-directory fixture.\n')
    for key in ('launch', 'evaluate'):
        repo = root / 'pfo/act' / key / 'repo'
        repo.symlink_to(os.path.relpath(shared, repo.parent))

    def shortcut(name, relative, key, subpath=None):
        link = root / 'pov' / name / relative
        link.parent.mkdir(parents=True, exist_ok=True)
        target = root / 'pfo/act' / key
        if subpath:
            target /= subpath
        link.symlink_to(os.path.relpath(target, link.parent))

    shortcut('domain', 'Coordination/coordinate', 'coordinate')
    shortcut('domain', 'Coordination/build', 'build')
    shortcut('domain', 'Engineering/launch', 'launch')
    shortcut('domain', 'Engineering/evaluate', 'evaluate')
    (root / 'pov/domain/Empty').mkdir()
    shortcut('focus', 'Coordination', 'coordinate')
    shortcut('focus', 'build', 'build')
    shortcut('focus', 'build-note.md', 'build', 'res/note.md')
    shortcut('focus', 'evaluate.md', 'evaluate', 'evaluate.md')
    for name in ('domain', 'focus'):
        p.apply(p.plan(root, name, 'save'))
    definition = root / 'pov/focus' / p.DEFINITION
    saved = json.loads(definition.read_text())
    saved['entries'][0].update(alias='Coordination', display='card')
    definition.write_text(p.encode(saved))
    p.apply(p.plan(root, 'focus', 'save'))
    perspective_html.render(root)


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Isolated workspace / isolierter Arbeitsbereich')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init', help='Create empty fixture / leeres Beispiel anlegen')
    sub.add_parser('demo', help='Create five-entry demo / Beispiel mit fünf Einträgen anlegen')
    new = sub.add_parser('new', help='Capture a title / Titel erfassen')
    new.add_argument('title')
    sub.add_parser('render', help='Build saved presentations / gespeicherte Darstellungen bauen')
    check = sub.add_parser('check', help='Inspect local tree / lokale Struktur prüfen')
    check.add_argument('name')
    for operation in ('save', 'restore'):
        command = sub.add_parser(operation)
        command.add_argument('name')
        command.add_argument('--apply', action='store_true', help='Apply preview / Vorschau anwenden')
        command.add_argument('--choose', action='store_true', help='Explicitly choose this direction after conflict review / Richtung nach Konfliktprüfung wählen')
        if operation == 'save':
            command.add_argument('--match', action='append', default=[], metavar='NEW/PATH=OLD-ID')
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command in {'init', 'demo'}:
            (initialize if args.command == 'init' else demo)(root)
        else:
            require_prototype(root)
            if args.command == 'new':
                print(p.capture(root, args.title).relative_to(root))
            elif args.command == 'render':
                perspective_html.render(root)
            elif args.command == 'check':
                tree, _, warnings = p.scan(root, args.name, p.catalog(root))
                print(p.encode(dict(entries=tree, warnings=warnings)))
            else:
                matches = {}
                for value in getattr(args, 'match', []):
                    path, separator, identifier = value.rpartition('=')
                    if not separator or path in matches:
                        raise ValueError('Expected one distinct NEW/PATH=OLD-ID per match')
                    matches[path] = identifier
                plan = p.plan(root, args.name, args.command, choose=args.choose, matches=matches)
                print(plan.preview())
                if args.apply:
                    p.apply(plan)
    except (ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(cli())
