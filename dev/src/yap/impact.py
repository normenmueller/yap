"""Derive each Objective's managed activities from its validated KR contributions."""


def assign(goals, key_results, nodes):
    """Keep first occurrence in KR order; references never create managed activities."""
    by_key = {node['key']: node for node in nodes}
    for goal in goals:
        keys = dict.fromkeys(
            entry
            for kr in key_results.get(goal['key'], [])
            for entry in kr['activities']
            if isinstance(entry, str)
        )
        goal['activities'] = [dict(key=key, anchor='', label=by_key[key]['title']) for key in keys]
