"""Local navigation and the generated resource tree."""

from pathlib import Path
import os
import shutil
from . import workspace_links


# The retired work name remains private; its old configuration is not supported.
LOCAL_NAMES = (*workspace_links.LEGACY_NAMES, 'wsp', 'work')


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
    from .catalog import discover
    return workspace_links.plan(root, discover(root))


def sync_links(plan):
    workspace_links.sync(plan)


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
