"""Thin command-line adapter for explicit, offline workspace setup."""

import json
from pathlib import Path


def add_parser(commands):
    workspace = commands.add_parser(
        'workspace', help='Arbeitsverzeichnis planen/einrichten / plan or set up a workspace')
    operations = workspace.add_subparsers(dest='workspace_operation', required=True)
    defaults = operations.add_parser('defaults', help='Vorbelegung anzeigen / show suggested inputs')
    defaults.add_argument('--template', choices=('general', 'db-gitlab'), required=True)
    migrate = operations.add_parser('migrate', help='Alte Bindungen überführen / migrate legacy bindings')
    migrate.add_argument('--apply', action='store_true')
    for operation in ('create', 'attach'):
        parser = operations.add_parser(operation)
        parser.add_argument('destination', type=Path)
        parser.add_argument('--bind', dest='binding_key', metavar='ACTIVITY-KEY')
        parser.add_argument('--name', dest='link_name', metavar='NAME')
        parser.add_argument('--lang', choices=('de', 'en'), default='de',
                            help='Ausgabesprache / interface language')
        parser.add_argument('--apply', action='store_true',
                            help='Angezeigten Plan ausführen / apply the displayed plan')
        if operation == 'create':
            parser.add_argument('--template', choices=('general', 'db-gitlab'))
            parser.add_argument('--inputs', type=Path, help='Bestätigte JSON-Eingaben / confirmed JSON inputs')
            parser.add_argument('--git', dest='initialize_git', action='store_true')
            parser.add_argument('--branch', default='trunk')
            parser.add_argument('--remote-url')
            parser.add_argument('--remote-name', default='origin')
            parser.add_argument('--resume', action='store_true',
                                help='Vorhandenes Teilergebnis prüfen und fortsetzen / inspect and resume a partial result')


def run(root, args):
    from . import repo_templates, workspace_setup
    if args.workspace_operation == 'migrate':
        from . import workspace_migration
        proposal = workspace_migration.plan(root)
        print(proposal.preview())
        if args.apply:
            workspace_migration.apply(proposal)
            print('Workspace-Migration abgeschlossen / Workspace migration complete.')
        else:
            print('Vorschau / Preview; --apply führt den Plan aus / executes the plan.')
        return 0
    if args.workspace_operation == 'defaults':
        inputs = repo_templates.defaults()
        inputs.update(title='My project', languages=['de'], primary_language='de',
                      purpose={}, maintainer={})
        if args.template == 'db-gitlab':
            inputs['db_confirmed'] = False
        else:
            inputs.pop('db_metadata', None)
        print(json.dumps(inputs, ensure_ascii=False, indent=2))
        return 0

    options = {}
    if args.workspace_operation == 'create':
        if bool(args.template) != bool(args.inputs):
            raise ValueError('--template and --inputs must be selected together')
        if args.template:
            inputs = json.loads(args.inputs.read_text(encoding='utf-8'))
            options.update(template_profile=args.template, template_inputs=inputs)
        options.update(initialize_git=args.initialize_git, branch=args.branch,
                       remote_url=args.remote_url, remote_name=args.remote_name,
                       resume=args.resume)
    requested = workspace_setup.plan(
        root, args.workspace_operation, args.destination,
        binding_key=args.binding_key, link_name=args.link_name, **options)
    if options.get('template_profile'):
        shown = repo_templates.resolved_inputs(inputs)
        heading = 'Template-Eingaben' if args.lang == 'de' else 'Template inputs'
        print(heading + ':')
        print(json.dumps(shown, ensure_ascii=False, indent=2))
    print(requested.preview(language=args.lang))
    if not args.apply:
        print('Vorschau; zum Ausführen --apply ergänzen.' if args.lang == 'de'
              else 'Preview only; add --apply to execute.')
        return 0
    result = workspace_setup.apply(requested)
    print(result.preview(language=args.lang))
    return 1 if result.error else 0
