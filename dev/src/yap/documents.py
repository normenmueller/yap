"""PDF documents from the shared, already parsed content model."""

from copy import deepcopy
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
import posixpath
import re


def pdf_target(identifier):
    """Keep simple public IDs; encode other names losslessly before Pandoc/TeX.

    Pandoc escapes Unicode in LaTeX labels independently of URL escaping.
    A separate ASCII namespace makes PDF targets and browser links agree.
    Authored/model identifiers always begin with act- or goal-.
    The historical destination namespace stays stable for existing deep links.
    """
    if re.fullmatch(r'(?:act|goal)-[A-Za-z0-9_-]+', identifier):
        return identifier
    from .instance import manifest
    return manifest().get('publication_prefix', 'yap-') + identifier.encode('utf-8').hex()


def inlines(text):
    result = []
    for line_number, line in enumerate(text.splitlines()):
        if line_number:
            result.append({'t': 'LineBreak'})
        for number, word in enumerate(line.split()):
            if number:
                result.append({'t': 'Space'})
            result.append({'t': 'Str', 'c': word})
    return result


def header(level, title, identifier, classes=(), attributes=None):
    return {'t': 'Header', 'c': [min(level, 6),
            [pdf_target(identifier), list(classes), list((attributes or {}).items())], inlines(title)]}


def walk(value, transform):
    if isinstance(value, list):
        return [walk(item, transform) for item in value]
    if isinstance(value, dict):
        value = {key: walk(item, transform) for key, item in value.items()}
        return transform(value)
    return value


def destination(path, nodes=()):
    """Use explicit publication roots, independent of current source filing."""
    path = Path(path)
    for node in nodes:
        if node.get('resource_root') is None:
            continue
        directory = Path(node['path']).parent / 'res'
        if path.is_relative_to(directory):
            return str(Path('res') / node['resource_root'] / path.relative_to(directory))
    return None


def body(blocks, source, identifier, level, nodes, stage, external=False, child_style=None, goals=(), resource_prefix='../../'):
    by_path = {node['path']: node for node in nodes}
    versions = {version['anchor']: version for version in by_path.get(source, {}).get('versions', [])}
    goals_by_path = {goal['path']: goal for goal in goals}
    goal_anchors = {goal['id']: goal['id'] for goal in goals}

    def attr(element):
        kind = element.get('t')
        if kind == 'Header':
            return element['c'][1]
        if kind in ('Div', 'Span', 'CodeBlock', 'Table', 'Figure'):
            return element['c'][0]

    def collect(element, goal_id):
        attributes = attr(element)
        if attributes and attributes[0]:
            goal_anchors[attributes[0]] = goal_id + '--' + attributes[0]
        return element

    for goal in goals:
        walk(goal['blocks'], lambda element: collect(element, goal['id']))

    def transform(element):
        kind = element.get('t')
        if kind in ('Para', 'Plain'):
            while element['c'] and element['c'][-1]['t'] == 'LineBreak':
                element['c'].pop()
        attributes = attr(element)
        if kind == 'Header' and 'version' in attributes[1] and attributes[0] in versions:
            version = versions[attributes[0]]
            attributes[2].extend((key, version[key]) for key in ('status', 'priority') if version[key])
        if attributes and attributes[0]:
            attributes[0] = pdf_target(identifier + '--' + attributes[0])
        if kind == 'Header':
            content = element['c']
            content[0] = min(6, content[0] + level - 1)
            if child_style:
                content[1][1].extend(child_style.get('classes', []))
                content[1][2].extend(child_style.get('attributes', {}).items())
        elif kind in ('Link', 'Image'):
            target = element['c'][2][0]
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                return element
            anchor = unquote(parsed.fragment)
            if not parsed.path:
                if (source == 'pfo/okr/goals.md' or source in goals_by_path) and anchor in goal_anchors:
                    element['c'][2][0] = '#' + pdf_target(goal_anchors[anchor])
                else:
                    element['c'][2][0] = '#' + pdf_target(identifier + ('--' + anchor if anchor else ''))
                return element
            resolved = posixpath.normpath(posixpath.join(str(Path(source).parent), unquote(parsed.path)))
            resource = destination(resolved, nodes)
            if resource:
                # Pandoc decodes image URIs for TeX; HTML and PDF links need
                # encoded paths so filename characters cannot become URL syntax.
                target = quote(str(stage / resource) if kind == 'Image' else resource_prefix + resource, safe='/')
                if anchor:
                    target += '#' + quote(anchor, safe="!$&'()*+,;=:@/?")
            elif resolved in by_path:
                ref = pdf_target(by_path[resolved]['id'] + ('--' + anchor if anchor else ''))
                target = ('Activity - Details.pdf#nameddest=' if external else '#') + ref
            elif resolved in goals_by_path:
                goal = goals_by_path[resolved]
                ref = pdf_target(goal['id'] if not anchor or anchor == goal['id'] else goal['id'] + '--' + anchor)
                target = ('#' if external else 'Performance - mPM.pdf#nameddest=') + ref
            elif resolved == 'pfo/okr/goals.md':
                ref = pdf_target(goal_anchors.get(anchor, anchor)) if anchor else ''
                target = ('#' if external else 'Performance - mPM.pdf#nameddest=') + ref if ref else 'Performance - mPM.pdf'
            else:
                raise ValueError(f'{source}: Unpublished local reference: {target}')
            element['c'][2][0] = target
        return element

    return walk(deepcopy(blocks), transform)


def activity(model, stage):
    blocks = []
    by_key = {node['key']: node for node in model['nodes']}
    emitted = set()
    for placement in model['report']['nodes']:
        source = by_key.get(placement['entry'])
        level = placement['depth']
        classes, attrs = [], {}
        if placement['document_style'] == 'chapter':
            classes.append('chapter-pages')
            if placement['subtree_map']:
                attrs['map'] = str(stage / 'views/activity-map' / placement['map_path'] / 'map.png')
        if placement['role'] == 'category' or placement['tone'] == 'strategy':
            if placement['role'] == 'category':
                classes.append('tone-heading')
            attrs['tone'] = {'support': 'violet', 'impact': 'green', 'governance': 'orange',
                             'epistemics': 'epistemics', 'strategy': 'yellow'}.get(placement['tone'], 'muted')
        if placement['document_style'] == 'card':
            classes.append('card')
        if not placement['document']:
            blocks.append(header(level, placement['title'], 'view-' + placement['placement'], classes, attrs))
            continue
        node = source
        if node['key'] in emitted:
            blocks.append({'t': 'Para', 'c': [{'t': 'Link', 'c': [
                ['', [], []], inlines(placement['label']), ['#' + pdf_target(node['id']), '']]}]})
            continue
        emitted.add(node['key'])
        for key in ('status', 'priority'):
            if node.get(key):
                attrs[key] = node[key]
        blocks.append(header(level, node['title'], node['id'], classes, attrs))
        if node.get('synonyms'):
            blocks.append({'t': 'Div', 'c': [['', ['synonyms'], []], [
                {'t': 'Para', 'c': inlines('Auch bekannt als: ' + ' · '.join(node['synonyms']))}]]})
        if node.get('subtitle'):
            blocks.append({'t': 'Para', 'c': [{'t': 'Emph', 'c': inlines(node['subtitle'])}]})
        if node.get('slogan'):
            value = node['meta']['slogan']
            slogan = value['c'] if value['t'] == 'MetaInlines' else inlines(node['slogan'])
            slogan = walk(slogan, lambda item: {'t': 'LineBreak'} if item['t'] == 'SoftBreak' else item)
            blocks.extend(body([{'t': 'BlockQuote', 'c': [{'t': 'Para', 'c': slogan}]}],
                               node['path'], node['id'], level, model['nodes'], stage,
                               goals=model['goals']))
        if node.get('url'):
            blocks.append({'t': 'Para', 'c': [{'t': 'Link', 'c': [
                ['', [], []], inlines('Quelle'), [node['url'], '']]}]})
        blocks.extend(body(node['blocks'], node['path'], node['id'], level,
                           model['nodes'], stage, goals=model['goals']))
    meta = deepcopy(model['meta'])
    meta['cover-map'] = {'t': 'MetaString', 'c': str(stage / 'views/activity-map/map.png')}
    if model.get('dgraph', {}).get('nodes'):
        meta['dependency-graph'] = {'t': 'MetaString', 'c': str(stage / 'views/dependency-graph/graph.pdf')}
    return {'pandoc-api-version': model['api'], 'meta': meta, 'blocks': blocks}


def goal_metadata(goal):
    """Render the authored timeframe and source in the objective PDF."""
    blocks = []
    if goal.get('timeline'):
        blocks.append({'t': 'Para', 'c': inlines('Zeitraum: ' + goal['timeline'])})
    if goal.get('url'):
        blocks.append({'t': 'Para', 'c': [{'t': 'Link', 'c': [
            ['', [], []], inlines('Quelle'), [goal['url'], '']]}]})
    return blocks


def mpm(model, stage):
    blocks = []
    for goal in model['goals']:
        attrs = {'priority': goal['priority']} if goal.get('priority') else {}
        blocks.append(header(1, goal['title'], goal['id'], attributes=attrs))
        if goal.get('status'):
            blocks.append({'t': 'Para', 'c': inlines(goal['status'])})
        blocks.extend(goal_metadata(goal))
        for block in body(goal['blocks'], goal['path'], goal['id'], 1,
                          model['nodes'], stage, external=True, goals=model['goals']):
            blocks.append(block)
            # Standalone bold labels introduce the following conversation entry.
            if block['t'] == 'Para' and len(block['c']) == 1 and block['c'][0]['t'] == 'Strong':
                blocks.append({'t': 'RawBlock', 'c': ['latex', r'\nopagebreak[4]']})
    meta = deepcopy(model['goal_meta'])
    meta['goal-report'] = {'t': 'MetaBool', 'c': True}
    return {'pandoc-api-version': model['api'], 'meta': meta, 'blocks': blocks}
