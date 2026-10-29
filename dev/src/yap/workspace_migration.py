"""Explicit, resumable migration of legacy machine bindings to source YAML."""

from dataclasses import dataclass
import json
import os
from pathlib import Path

from . import catalog, workspace_links as links


@dataclass(frozen=True)
class SourceChange:
    path: Path
    before: bytes
    after: bytes


@dataclass(frozen=True)
class Plan:
    root: Path
    config: Path
    before: bytes | None
    after: bytes | None
    sources: tuple
    navigation: tuple
    messages: tuple

    def preview(self):
        lines = ['Workspace-Migration / Workspace migration:']
        for change in self.sources:
            if change.before != change.after:
                lines.append(f'- YAML: {change.path.relative_to(self.root)}')
        for change in self.navigation:
            if change.target is None:
                lines.append(f'- Remove verified legacy shortcut: {change.path.relative_to(self.root)}')
            elif change.before != str(change.target):
                lines.append(f'- Link: {change.path.relative_to(self.root)} -> {change.target}')
        if self.before != self.after:
            lines.append('- Remove migrated links from .yap/cfg/machine.json (other settings preserved)')
        if len(lines) == 1:
            lines.append('- No changes.')
        lines.extend('Note: ' + message for message in self.messages)
        return '\n'.join(lines)


def plan(root):
    root = Path(root).resolve()
    config, before, settings = links.legacy(root)
    legacy = settings.get('links', {})
    entries = {key: entry for key, entry in catalog.discover(root).items()
               if entry['kind'] in {'activity', 'area'}}
    unknown = set(legacy) - set(entries)
    if unknown:
        raise ValueError(f'{config}: unknown activities/areas: {", ".join(sorted(unknown))}.')
    sources, navigation, messages = [], [], []
    for key, entry in entries.items():
        old = legacy.get(key, {})
        if not isinstance(old, dict) or set(old) - set(links.LEGACY_NAMES):
            raise ValueError(f'{config}: links[{key}] requires repo/shlf/zbox path bindings.')
        current, additions = entry['workspace'], {}
        for label, value in old.items():
            destination = links.target(root, value, f'{config}: links[{key}][{label}]')
            if any(item.casefold() == label.casefold() and item != label for item in current):
                raise ValueError(f'{entry["source"]}: case-insensitive workspace name conflict: {label}.')
            if label in current:
                if links.target(root, current[label]) != destination:
                    raise ValueError(f'{entry["source"]}: wsp[{label}] conflicts with machine.json; resolve explicitly.')
            else:
                additions[label] = value
        combined = dict(current, **additions)
        source_before = links.snapshot(entry['source'])
        source_after = links.add_bindings(source_before, entry['source'], additions)
        sources.append(SourceChange(entry['source'], source_before, source_after))
        for label in links.LEGACY_NAMES:
            path = entry['folder'] / label
            # Real legacy-named files are source material and are preserved.
            if not path.is_symlink():
                continue
            if label not in combined:
                raise ValueError(f'{path}: legacy shortcut has no declared binding; resolve explicitly.')
            destination = links.target(root, combined[label])
            state = links.link_state(path)
            if Path(os.path.abspath(path.parent / state)) != destination:
                raise ValueError(f'{path}: legacy shortcut points elsewhere; resolve explicitly.')
            navigation.append(links.Link(path, state, None))
        planned, warnings = links.plan_entry(root, entry, combined)
        for change in planned:
            if change.before is not None and Path(os.path.abspath(change.path.parent / change.before)) != change.target:
                raise ValueError(f'{change.path}: workspace shortcut points elsewhere; resolve explicitly.')
        navigation.extend(planned)
        messages.extend(warnings)
    links.validate_targets(navigation)
    after_settings = {key: value for key, value in settings.items() if key != 'links'}
    after = ((json.dumps(after_settings, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
             if 'links' in settings else before)
    return Plan(root, config, before, after, tuple(sources), tuple(navigation), tuple(messages))


def apply(proposal):
    """Validate the whole preview first; retain partial work for an explicit retry."""
    if plan(proposal.root) != proposal:
        raise ValueError('Workspace migration state changed since planning; preview again.')
    for change in proposal.sources:
        links.write(change.path, change.before, change.after)
    # New navigation must exist before retiring the verified root shortcuts.
    links.sync([change for change in proposal.navigation if change.target is not None])
    links.sync([change for change in proposal.navigation if change.target is None])
    # Keeping legacy settings until last makes a partially completed run resumable.
    if proposal.after is not None:
        links.write(proposal.config, proposal.before, proposal.after)
