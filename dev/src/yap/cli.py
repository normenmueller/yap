"""Generate reports, views and local navigation from yap sources."""

import argparse
import subprocess
import sys
import shutil
import os
import webbrowser
from pathlib import Path

from .build import main, SITE
from . import instance as instance_config
from . import perspectives as p


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', required=True, type=Path, help='Existing portfolio directory')
    sub = parser.add_subparsers(dest='command')
    from .workspace_cli import add_parser as add_workspace_parser
    add_workspace_parser(sub)
    for name in ('all', 'report', 'activity', 'mpm', 'views', 'resources', 'links', 'check', 'init', 'open'):
        sub.add_parser(name)
    new = sub.add_parser('new', help='Aktivität erfassen / capture an activity')
    new.add_argument('title')
    view = sub.add_parser('view', help='Perspektive speichern oder wiederherstellen / save or restore a perspective')
    view.add_argument('operation', choices=('save', 'restore', 'check'))
    view.add_argument('name')
    view.add_argument('--apply', action='store_true')
    view.add_argument('--choose', action='store_true')
    view.add_argument('--match', action='append', default=[], metavar='NEW/PATH=OLD-ID')
    export = sub.add_parser('export', help='Portable Ausgabe kopieren / copy a portable export')
    export.add_argument('destination', type=Path)
    demo = sub.add_parser('demo-date', help='Demo-Zeitraum verschieben / shift illustrative demo dates')
    demo.add_argument('date', metavar='YYYY-MM-DD')
    demo.add_argument('--apply', action='store_true', help='Änderung speichern / save the change')
    try:
        args = parser.parse_args()
        ROOT = args.instance.resolve()
        if not ROOT.is_dir():
            raise ValueError('Portfolio directory does not exist: ' + str(ROOT))
        os.chdir(ROOT)
        instance_config.verify_application(instance_config.manifest())
        command = args.command or 'all'
        if command == 'open':
            main('all', instance=ROOT)
            address = (ROOT / instance_config.entry()).as_uri()
            if not webbrowser.open(address):
                print('Open this portfolio in your browser: ' + address)
        elif command == 'workspace':
            from .workspace_cli import run
            return run(ROOT, args)
        elif command == 'demo-date':
            from .work_progress import refresh_date
            print(refresh_date(ROOT, args.date, apply=args.apply))
        elif command == 'new':
            print(p.capture(ROOT, args.title).relative_to(ROOT))
        elif command == 'view':
            if args.operation == 'check':
                tree, _, warnings = p.scan(ROOT, args.name, p.catalog(ROOT))
                print(p.encode(dict(entries=tree, warnings=warnings)))
            else:
                matches = {}
                for value in args.match:
                    name, separator, identifier = value.rpartition('=')
                    if not separator or name in matches:
                        raise ValueError('Expected distinct NEW/PATH=OLD-ID rename matches')
                    matches[name] = identifier
                plan = p.plan(ROOT, args.name, args.operation, choose=args.choose, matches=matches)
                print(plan.preview())
                if args.apply:
                    p.apply(plan)
        elif command == 'export':
            destination = args.destination.resolve()
            if destination.exists() or destination.is_relative_to(ROOT):
                raise ValueError('Choose a new export directory outside the checkout')
            main('all', instance=ROOT)
            shutil.copytree(ROOT / SITE, destination)
            print(destination / instance_config.entry())
        else:
            if command == 'init':
                plans = [p.plan(ROOT, path.parent.name, 'restore')
                         for path in sorted((ROOT / 'pov').glob('*/.perspective.yaml'))]
                for plan in plans:
                    p.apply(plan)
                command = 'all'
            main(command, instance=ROOT)
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0
