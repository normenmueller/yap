"""Bound generated publication to one instance without following redirected paths."""

import os
from pathlib import Path
import shutil
import stat
import tempfile


def _path(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    if not candidate.is_relative_to(root) or '..' in candidate.parts or candidate == root:
        raise ValueError(f'{path}: generated output must stay beneath the instance root.')
    current = root
    for part in candidate.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f'{current}: symlinks are not allowed in generated output.')
        if current != candidate and current.exists() and not current.is_dir():
            raise ValueError(f'{current}: expected a generated output directory.')
    return candidate


def validate_tree(root: Path, directory: Path) -> Path:
    """Preflight an output subtree before reading, writing or removing its contents.

    This rejects preexisting redirection; it does not lock out a noncooperating
    process changing the filesystem concurrently.
    """
    root = root.resolve()
    directory = _path(root, directory)
    if not directory.exists():
        return directory
    if not directory.is_dir():
        raise ValueError(f'{directory}: expected a generated output directory.')

    def failed(error: OSError) -> None:
        raise ValueError(f'{directory}: cannot inspect generated output: {error}') from error

    for current, directories, files in os.walk(directory, followlinks=False, onerror=failed):
        for name in (*directories, *files):
            child = Path(current) / name
            status = child.lstat()
            mode = status.st_mode
            if not stat.S_ISDIR(mode) and not stat.S_ISREG(mode):
                raise ValueError(f'{child}: generated output requires regular files and directories; symlinks are not allowed.')
            if stat.S_ISREG(mode) and status.st_nlink > 1:
                raise ValueError(f'{child}: hardlinks are not allowed in generated output.')
    return directory


def write_text(path: Path, text: str, *, root: Path) -> None:
    """Replace one generated text file without writing through an existing hardlink."""
    root = root.resolve()
    target = _path(root, path)
    if target.exists() and not target.is_file():
        raise ValueError(f'{target}: expected a regular generated file.')
    if target.exists() and target.read_text(encoding='utf-8') == text:
        return
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else None
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=target.parent, prefix='.write-', delete=False,
        ) as outgoing:
            temporary = Path(outgoing.name)
            outgoing.write(text)
        if mode is not None:
            temporary.chmod(mode)
        _path(root, target)
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def publish(stage: Path, destination: Path, *, root: Path) -> None:
    """Reconcile a successful stage after validating the complete owned output tree."""
    root = root.resolve()
    stage = validate_tree(root, stage)
    destination = validate_tree(root, destination)
    if not stage.is_dir():
        raise ValueError(f'{stage}: expected an existing publication stage.')
    if stage.is_relative_to(destination) or destination.is_relative_to(stage):
        raise ValueError('Publication stage and destination must be separate trees.')
    expected = {path.relative_to(stage) for path in stage.rglob('*') if path.is_file()}
    # Diagnose file/directory conflicts before the first published change.
    for relative in expected:
        target = _path(root, destination / relative)
        if target.exists() and not target.is_file():
            raise ValueError(f'{target}: expected a regular generated file.')
    destination.mkdir(parents=True, exist_ok=True)
    for relative in sorted(expected):
        source = _path(root, stage / relative)
        target = _path(root, destination / relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() == source.read_bytes():
            continue
        temporary: Path | None = None
        try:
            with source.open('rb') as incoming, tempfile.NamedTemporaryFile(
                dir=target.parent, prefix='.publish-', delete=False,
            ) as outgoing:
                temporary = Path(outgoing.name)
                shutil.copyfileobj(incoming, outgoing)
            temporary.chmod(stat.S_IMODE(source.stat().st_mode))
            _path(root, target)
            temporary.replace(target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    for path in sorted(destination.rglob('*'), key=lambda item: len(item.parts), reverse=True):
        _path(root, path)
        if path.is_file() and path.relative_to(destination) not in expected:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
