"""Local navigation and the generated resource tree."""

from pathlib import Path
import os
import shutil
import json


LINK_ROLES = ('repo', 'shlf', 'zbox')
# The retired work name remains private; its old configuration is not supported.
LOCAL_NAMES = (*LINK_ROLES, 'wsp', 'work')


def source_files(directory, local_names=LOCAL_NAMES):
    """Walk authored files only; never enter local locations or symlinks."""
    for current, directories, files in os.walk(directory, followlinks=False):
        base = Path(current)
        directories[:] = sorted(name for name in directories
                                if name not in local_names and not name.startswith('.')
                                and not (base / name).is_symlink())
        for name in sorted(files):
            path = base / name
            if name not in local_names and not name.startswith('.') and not path.is_symlink() and path.is_file():
                yield path


def source_shape(directory, local_names=LOCAL_NAMES):
    """Include empty/new folders and unexpected links in discovery invalidation."""
    result = []
    for current, directories, files in os.walk(directory, followlinks=False):
        base = Path(current)
        directories[:] = sorted(name for name in directories if name not in local_names and not name.startswith('.'))
        for name in [*directories, *files]:
            if name not in local_names and not name.startswith('.'):
                path = base / name
                result.append((str(path), 'link' if path.is_symlink() else 'dir' if path.is_dir()
                               else 'file' if path.is_file() else 'other'))
    return sorted(result)


def link_plan(root):
    """Plan private area/activity locations without loading goals or presentations."""
    plan, messages = [], []
    from .catalog import discover
    from .perspectives import real_path
    root = Path(root).resolve()
    config = real_path(root, '.yap/cfg/machine.json')
    settings = json.loads(config.read_text()) if config.exists() else {}
    if not isinstance(settings, dict) or set(settings) - {'links'} or not isinstance(settings.get('links', {}), dict):
        raise ValueError('.yap/cfg/machine.json: expected links: {activity: {repo/shlf/zbox: path}}.')
    entries = {key: entry for key, entry in discover(root).items() if entry['kind'] in {'area', 'activity'}}
    bindings = settings.get('links', {})
    unknown = set(bindings) - set(entries)
    if unknown:
        raise ValueError('.yap/cfg/machine.json: unknown activities: ' + ', '.join(sorted(unknown)))
    for key, entry in sorted(entries.items()):
        roles = bindings.get(key, {})
        if not isinstance(roles, dict) or set(roles) - set(LINK_ROLES):
            raise ValueError(f'.yap/cfg/machine.json: links[{key}] allows only repo, shlf and zbox.')
        folder = entry['folder']
        workspace = real_path(root, (folder / 'wsp').relative_to(root))
        if workspace.exists() and not workspace.is_dir():
            raise ValueError(f'{workspace.relative_to(root)}: expected a workspace directory.')
        has_modules = any(other['kind'] == 'activity' and folder / 'mod' in other['folder'].parents
                          for other in entries.values())
        active, inactive = (workspace, folder) if has_modules else (folder, workspace)
        for role in LINK_ROLES:
            link = active / role
            value = roles.get(role)
            if role in roles and (not isinstance(value, str) or not value.strip() or '\0' in value):
                raise ValueError(f'.yap/cfg/machine.json: links[{key}][{role}] requires a nonempty path.')
            target = None
            if value:
                target = Path(value).expanduser()
                if not target.is_absolute():
                    target = root / target
                target = target.absolute()
                if link.exists() and not link.is_symlink():
                    raise ValueError(f'{link.relative_to(root)}: already exists and is not a symlink.')
                if not target.is_dir():
                    messages.append(f'{key}/{role}: local target unavailable ({value}).')
            plan.append((link, target))
            plan.append((inactive / role, None))
    return plan, messages


def sync_links(plan):
    for link, target in plan:
        if target is None:
            if link.is_symlink():
                link.unlink()
        elif not link.is_symlink() or os.readlink(link) != str(target):
            if link.is_symlink():
                link.unlink()
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target, target_is_directory=True)
    for directory in {link.parent for link, _ in plan if link.parent.name == 'wsp'}:
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()


def resource_plan(root, model):
    plan = {}
    for node in model['nodes']:
        if node['resource_root'] is None:
            continue
        directory = (root / node['path']).parent / 'res'
        if directory.is_symlink():
            raise ValueError(f'{directory.relative_to(root)}: resources must be local files.')
        if not directory.exists():
            continue
        for current, directories, names in os.walk(directory, followlinks=False):
            base = Path(current)
            directories[:] = [name for name in directories if name not in LOCAL_NAMES and not name.startswith('.')]
            for name in [*directories, *names]:
                if name in LOCAL_NAMES or name.startswith('.'):
                    continue
                path = base / name
                if path.is_symlink():
                    raise ValueError(f'{path.relative_to(root)}: symlinks are not published.')
                if not path.is_file():
                    continue
                target = Path('res') / node['resource_root'] / path.relative_to(directory)
                if any(str(target).casefold() == existing.casefold() for existing in plan):
                    raise ValueError(f'{target}: two resources have the same output path.')
                plan[str(target)] = path
    return plan


def copy_resources(plan, stage):
    for relative, source in plan.items():
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def publish(stage, destination):
    """Reconcile the generated site only after selected renderers succeeded."""
    expected = {path.relative_to(stage) for path in stage.rglob('*') if path.is_file()}
    destination.mkdir(exist_ok=True)
    for relative in sorted(expected):
        source, target = stage / relative, destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != source.read_bytes():
            temporary = target.with_name('.' + target.name + '.tmp')
            shutil.copyfile(source, temporary)
            temporary.replace(target)
    for path in sorted(destination.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if path.is_file() and path.relative_to(destination) not in expected:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
