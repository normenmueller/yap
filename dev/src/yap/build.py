#!/usr/bin/env python3
"""Read once, render changed outputs, publish only a complete successful build."""

from copy import deepcopy
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote

from . import activity_map, palette, board, browser, content, dgraph, documents, home, navigation, overview, views, perspective_html, perspectives, selections
from .files import LOCAL_NAMES, source_files, source_shape, link_plan, sync_links, resource_plan, copy_resources, publish


from .resources import APPLICATION, TEMPLATES
from . import instance as instance_config

ROOT = None
BUILD = Path('.yap/local/build')
STAGE = BUILD / 'stage/site'
SITE = Path('.yap/local/site')
PDF_NAMES = {'Activity': 'acc/pdf/Activity - Details.pdf', 'mPM': 'acc/pdf/Performance - mPM.pdf'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def hashes(paths):
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != text:
        path.write_text(text)


def run(arguments):
    result = subprocess.run([str(arg) for arg in arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(' '.join(map(str, arguments)) + '\n' + result.stdout[-6000:] + result.stderr[-6000:])
    return result.stdout


def tex_pdf(path):
    run(['latexmk', '-silent', '-lualatex', '-interaction=nonstopmode',
         '-halt-on-error', '-file-line-error', '-outdir=' + str(path.parent), path])
    return path.with_suffix('.pdf')


def render_maps(model):
    for selected in selections.activities(model):
        render_map_selection(selected)


def render_map_selection(model):
    selection = model.get('selection')
    roots = [node for node in overview.map_nodes(model) if node['subtree_map']] if not selection or not selection['key'] else []
    for key, route in [('', ''), *((node['key'], node['map_path']) for node in roots)]:
        work = BUILD / 'work/maps' / selections.filename(selection, key or 'all')
        path = work / 'map.tex'
        write(path, views.map_tex(model, key))
        pdf = tex_pdf(path)
        output = STAGE / 'views/activity-map' / route
        output.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf, output / selections.filename(selection, 'map.pdf'))
        run(['pdftocairo', '-r', '180', '-singlefile', '-png', '-transp', pdf, output / selections.filename(selection, 'map')])
    write(STAGE / 'views/activity-map' / selections.filename(selection), activity_map.render(model))


def render_pdf(model, name):
    ast = documents.activity(model, STAGE) if name == 'Activity' else documents.mpm(model, STAGE)
    source = BUILD / 'work' / name / (name + '.json')
    write(source, json.dumps(ast, ensure_ascii=False))
    tex = source.with_suffix('.tex')
    arguments = ['pandoc', '-f', 'json', '-t', 'latex-smart', '--standalone',
                 '--template=' + str(TEMPLATES / 'tex/report.tex'), '--lua-filter=' + str(TEMPLATES / 'lua/status.lua')]
    if name == 'Activity':
        arguments.append('--lua-filter=' + str(TEMPLATES / 'lua/layout.lua'))
    arguments.extend([source, '-o', tex])
    run(arguments)
    shutil.copyfile(tex_pdf(tex), STAGE / PDF_NAMES[name])


def render_overview(model):
    work = BUILD / 'work/overview'
    image = work / 'board.png'
    browser.screenshot(STAGE / 'views/activity-board/index.html', image)
    path = work / 'overview.tex'
    write(path, r'\documentclass[border=0pt]{standalone}\usepackage{graphicx}'
          r'\begin{document}\includegraphics[width=40cm]{' + str(image) + r'}\end{document}')
    shutil.copyfile(tex_pdf(path), STAGE / 'acc/pdf/Activity - Overview.pdf')


def render_board(model):
    for selected in selections.activities(model):
        render_board_selection(selected)


def render_board_selection(model):
    selection = model.get('selection')
    rows = board.lanes(model)
    output = STAGE / 'views/activity-board'
    board.render_html(rows, output, selection=selection)
    browser.fit_cards(output / selections.filename(selection))
    path = BUILD / 'work/board' / selections.filename(selection, 'board.tex')
    title = 'Activity Board' + (' · ' + selection['label'] if selection and selection['key'] else '')
    write(path, board.tex(rows, title=title))
    pdf = tex_pdf(path)
    run(['pdftocairo', '-r', '180', '-singlefile', '-png', pdf, output / selections.filename(selection, 'board')])


def render_dgraph(model):
    for selected in selections.activities(model):
        render_graph_selection(selected)


def render_graph_selection(model):
    selection = model.get('selection')
    graph = model['dgraph']
    output = STAGE / 'views/dependency-graph'
    dgraph.render_html(graph, output, selection=selection)
    if graph['nodes']:
        path = BUILD / 'work/dgraph' / selections.filename(selection, 'graph.tex')
        write(path, dgraph.tex(graph))
        pdf = tex_pdf(path)
        shutil.copyfile(pdf, output / selections.filename(selection, 'graph.pdf'))
        run(['pdftocairo', '-r', '180', '-singlefile', '-png', pdf, output / selections.filename(selection, 'graph')])


def group_files(directory, group):
    if group == 'overview':
        path = directory / 'acc/pdf/Activity - Overview.pdf'
        return [path] if path.is_file() else []
    if group == 'home':
        return [directory / path for path in (*home.pages(), *home.assets())
                if (directory / path).is_file()]
    prefix = {'maps': 'views/activity-map', 'board': 'views/activity-board',
              'dgraph': 'views/dependency-graph', 'views': 'views/mPM-ish',
              'perspectives': 'views/perspectives', 'resources': 'res'}.get(group)
    if prefix:
        return [path for path in (directory / prefix).rglob('*') if path.is_file()]
    path = directory / 'acc/pdf' / ('Activity - Details.pdf' if group == 'activity' else 'Performance - mPM.pdf')
    return [path] if path.is_file() else []


def main(command, instance=None):
    root = Path(instance if instance is not None else ROOT).resolve() if instance is not None or ROOT is not None else None
    if root is None or not root.is_dir():
        raise ValueError('Select an existing portfolio with --instance PATH.')
    return _main(command, root)


def _main(command, ROOT):
    os.chdir(ROOT)
    os.environ['TEXINPUTS'] = str(TEMPLATES / 'tex') + os.pathsep + os.environ.get('TEXINPUTS', '')
    BUILD.mkdir(parents=True, exist_ok=True)
    os.environ['TEXMFVAR'] = str(ROOT / BUILD / 'tex-cache')
    os.environ['TEXMFCACHE'] = os.environ['TEXMFVAR']
    for tool in ('pandoc',) if command == 'links' else ('pandoc', 'latexmk', 'lualatex', 'pdftocairo'):
        if not shutil.which(tool):
            raise ValueError(f'Required tool not found: {tool}')

    if command == 'links':
        links, messages = link_plan(ROOT)
        for message in messages:
            print('Note:', message)
        sync_links(links)
        print('Lokale repo/shlf/zbox-Links abgeglichen / Local repo/shlf/zbox links reconciled.')
        return

    state_path = BUILD / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    from .aspirations import resolve
    aspiration_paths = resolve(ROOT)
    sources = hashes([*source_files(Path('pfo/act')), aspiration_paths.goals,
                      *Path('.yap/cfg').glob('progress-preview.json'),
                      *Path('.').glob('yap.json'),
                      *source_files(aspiration_paths.objectives, local_names=()), *source_files(Path('pfo/nts')),
                      *sorted(Path('pov').glob('*/.perspective.yaml'))])
    code = hashes(path for base in (APPLICATION / 'dev/src', TEMPLATES / 'tex', TEMPLATES / 'lua')
                  for path in source_files(Path(base))
                  if path.suffix in ('.py', '.js', '.lua', '.tex') and not path.name.startswith('test_'))
    code = dict(code, instance_configuration=digest(instance_config.manifest()))
    source_signature = digest([sources, source_shape(Path('pfo/act')), source_shape(aspiration_paths.root, local_names=()), source_shape(Path('pfo/nts')), code])
    cache = BUILD / 'model.json'
    if command != 'check' and state.get('source') == source_signature and cache.exists():
        model = json.loads(cache.read_text())
    else:
        model = content.load(ROOT)

    links, messages = link_plan(ROOT)
    resources = resource_plan(ROOT, model)
    for message in messages:
        print('Note:', message)
    if command == 'check':
        entries = perspectives.catalog(ROOT)
        for path in sorted(Path('pov').glob('*/.perspective.yaml')):
            saved = json.loads(path.read_text())
            perspectives.validate(saved, entries)
            tree, _, warnings = perspectives.scan(ROOT, path.parent.name, entries)
            for warning in warnings:
                print('Note:', warning)
            if perspectives.literal(tree) != perspectives.literal(saved['entries']):
                print('Note:', path.parent, 'differs from its saved definition.')
        print(f'Checked: {len(model["nodes"])} areas/activities, {len(model["goals"])} objectives, {len(resources)} resources.')
        return
    sync_links(links)

    # Local navigation metadata never participates in rendered content.
    published = deepcopy(model)
    for node in published['nodes']:
        for field in (*LOCAL_NAMES, 'file'):
            node.pop(field, None)
            node.get('meta', {}).pop(field, None)
    nodes = published['nodes']
    visible = {node['key'] for node in overview.activity_nodes(published)}
    resource_hashes = hashes(resources.values())
    selections.prepare(ROOT, published)
    activity_models = list(selections.activities(published))
    activity_options = [(item['selection']['key'], item['selection']['label']) for item in activity_models]
    graph_data = [item['dgraph'] for item in activity_models]
    board_data = [board.lanes(item) for item in activity_models]
    signatures = {
        'home': digest([code, instance_config.manifest(), hashes(home.asset_sources())]),
        'maps': digest([[overview.map_nodes(item) for item in activity_models], activity_options, code]),
        'dgraph': digest([graph_data, activity_options, code]),
        'board': digest([board_data, graph_data, activity_options, code]),
        'overview': digest([board.lanes(published), model['dgraph'], activity_options, hashes([home.asset_source(Path(navigation.logo()))]), code]),
        'activity': digest([nodes, model['report'], model['meta'], model['goals'], resource_hashes, code]),
        'mpm': digest([model['goals'], model['goal_meta'], nodes, resource_hashes, code]),
        'views': digest([model['report'], model['members'], model['goals'], model['goal_meta'], model['key_results'], model.get('work_preview'), nodes, sorted(visible), code]),
        'resources': digest([resource_hashes, sorted(resources)]),
        'perspectives': digest([sources, code, hashes(sorted(Path('pov').glob('*/.perspective.yaml'))),
                                perspective_html.draft_state(ROOT)]),
    }
    # PDF cross-links and view links always have accompanying documents.
    # The browser capture needs the shared navigation logo before loading the Board.
    selected = ['resources', 'home', 'maps', 'dgraph', 'board', 'overview', 'activity', 'mpm', 'perspectives']
    if command in ('all', 'report', 'views'):
        selected.append('views')
    if command == 'resources':
        selected = ['resources']

    outputs = state.get('outputs', {})
    dirty = []
    for group in selected:
        actual = hashes(group_files(Path('.yap/local/site'), group))
        if (outputs.get(group) != {'signature': signatures[group], 'files': actual}
                or (not actual and group != 'resources')):
            dirty.append(group)
    if not dirty:
        write(cache, json.dumps(model, ensure_ascii=False))
        state['source'] = source_signature
        write(state_path, json.dumps(state, indent=2))
        home.root_entry(SITE, Path(instance_config.entry()))
        print('Up to date — no outputs rebuilt.')
        return

    if STAGE.parent.exists():
        shutil.rmtree(STAGE.parent)
    STAGE.mkdir(parents=True)
    (STAGE / 'acc/pdf').mkdir(parents=True)
    # Preserve valid unselected products; default make refreshes every product.
    for group in ('resources', 'maps', 'dgraph', 'board', 'overview', 'activity', 'mpm', 'views', 'home', 'perspectives'):
        if group not in dirty:
            for path in group_files(Path('.yap/local/site'), group):
                destination = STAGE / path.relative_to(SITE)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
    for group in dirty:
        print('Build:', group, flush=True)
        if group == 'resources':
            copy_resources(resources, STAGE)
        elif group == 'maps':
            render_maps(published)
        elif group == 'board':
            render_board(published)
        elif group == 'overview':
            render_overview(published)
        elif group == 'dgraph':
            render_dgraph(published)
        elif group == 'activity':
            render_pdf(published, 'Activity')
        elif group == 'mpm':
            render_pdf(published, 'mPM')
        elif group == 'views':
            views.render_mpm(published, STAGE / 'views/mPM-ish')
            for page in (STAGE / 'views/mPM-ish').glob('*.html'):
                browser.fit_cards(page)
        elif group == 'home':
            home.render(STAGE)
        elif group == 'perspectives':
            perspective_html.render(ROOT, destination=STAGE / 'views/perspectives', model=published)
    publish(STAGE, Path('.yap/local/site'))
    home.root_entry(SITE, Path(instance_config.entry()))
    for group in dirty:
        outputs[group] = {'signature': signatures[group], 'files': hashes(group_files(Path('.yap/local/site'), group))}
    write(cache, json.dumps(model, ensure_ascii=False))
    write(state_path, json.dumps({'source': source_signature, 'outputs': outputs}, indent=2))
    print('Done: ' + instance_config.entry() + ' / .yap/local/site/')
