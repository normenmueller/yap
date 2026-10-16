"""Canonical activity selection and saved placement projection for overview maps."""


def activity_nodes(model):
    return [node for node in model['nodes'] if node['kind'] == 'activity']


def map_text(node):
    """Activity cards share Board labels; area/group headings retain their context."""
    if node.get('kind') == 'activity':
        caption = ' '.join(node.get('board-caption', '').split())
        return node.get('acronym') or node['title'], caption
    return node['title'], node.get('subtitle', '')


def map_nodes(model):
    """Keep activities/areas and their grouping context, excluding note entries."""
    sources = {node['key']: node for node in model['nodes']}
    result = []
    for placement in model['report']['nodes']:
        source = sources.get(placement['entry'], {})
        result.append(dict(source, key=placement['placement'], parent=placement['parent'],
                           depth=placement['depth'], title=placement['title'],
                           tone=placement['tone'], subtree_map=placement['subtree_map'],
                           map_path=placement['map_path']))
    by_key = {node['key']: node for node in result}
    kept = set()
    for node in result:
        if node.get('kind') not in ('activity', 'area'):
            continue
        key = node['key']
        while key:
            ancestor = by_key[key]
            if ancestor.get('kind') != 'note':
                kept.add(key)
            key = ancestor['parent']
    visible = []
    depths = {}
    for node in result:
        if node['key'] not in kept:
            continue
        parent = node['parent']
        while parent and parent not in kept:
            parent = by_key[parent]['parent']
        depths[node['key']] = depths.get(parent, 0) + 1
        visible.append(dict(node, parent=parent, depth=depths[node['key']]))
    return visible
