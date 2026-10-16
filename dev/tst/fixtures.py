"""Authored test arrangements, separate from canonical source discovery.

Renderer tests use readable path-like labels to specify an example arrangement.
Only this fixture builder expands them into explicit membership and placements;
production consumers never infer these relationships from an activity key.
"""
from pathlib import Path
import json


def source_text(name, text):
    path = Path(name)
    if str(path).startswith('pfo/act/') and path.name != 'act.md' and path.suffix == '.md' and path.stem == path.parent.name and text.startswith('---\n'):
        key = '/'.join(path.parts[2:-1]).replace('/', '--')
        if '\nkind:' not in text.split('---', 2)[1]:
            text = '---\nkind: activity\nkey: ' + json.dumps(key) + '\n' + text[4:]
    return text


def report_model(model):
    """Supply an explicit illustrative report tree for renderer unit fixtures."""
    nodes = model['nodes']
    keys = {n['key'] for n in nodes}
    members = {n['key']: [c['key'] for c in nodes if c['key'].rpartition('/')[0] == n['key']]
               for n in nodes}
    placements = []
    tones = {'ace': 'support', 'sup': 'support', 'imp': 'impact', 'ops': 'impact', 'gov': 'governance'}
    for n in nodes:
        key = n['key']; parts = key.split('/'); depth = len(parts)
        n.setdefault('kind', 'activity')
        category = parts[1] if depth >= 2 else ''
        role = 'context' if depth == 1 and members[key] else 'category' if depth == 2 and members[key] else 'lane' if members[key] else 'leaf'
        parent = key.rpartition('/')[0]
        if parent not in keys:
            parent = ''
        placements.append(dict(placement=key, parent=parent, depth=depth, role=role,
                               entry=key, source_placement=None, target={'entry': key}, document=True,
                               render_body=True, label=parts[0].upper() if role == 'context' else n['title'],
                               title=n['title'], context=parts[0] if parts[0] in keys and depth > 1 else '',
                               category=category, tone='strategy' if parts[-1]=='sfe' else tones.get(category, 'neutral'),
                               document_style='plain', subtree_map=depth==1, map_path=key,
                               board_card='never' if n['kind']=='note' else 'tracked' if members[key] else 'always'))
    model['members'] = members
    model['report'] = dict(nodes=placements, category_order=model.get('board_sequence', list(dict.fromkeys(p['category'] for p in placements if p['category']))),
                           flow=[['sup','imp'],['gov','imp']])
    return model
