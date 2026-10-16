"""Explicit local workspace setup, independent of capture and report builds."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import json
import os
import re
import subprocess
import tempfile

from . import catalog
from .files import LINK_ROLES


def _safe(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f'{part}: symlinks are not allowed in setup paths.')
        if part != path and part.exists() and not part.is_dir():
            raise ValueError(f'{part}: expected a directory.')


def _git(target, *args, check=True):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_SYSTEM=os.devnull, GIT_TERMINAL_PROMPT='0')
    command = ['git', '-c', 'core.hooksPath=' + os.devnull]
    if target is not None:
        command += ['-C', str(target)]
    result = subprocess.run(command + list(args), env=env, capture_output=True, text=True)
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or f'Git failed: {args[0]}')
    return result


def _starter_files(files):
    result = {}
    for name, content in (files or {}).items():
        if (not isinstance(name, str) or not name or '\\' in name or ':' in name
                or any(ord(char) < 32 for char in name)):
            raise ValueError('Starter paths must be nonempty relative POSIX paths.')
        path = PurePosixPath(name)
        if (not path.parts or path.is_absolute() or str(path) != name or any(
                part in {'.', '..'} or part.casefold() in {'.git', '.gitmodules', 'hooks'}
                for part in path.parts)):
            raise ValueError(f'{name}: unsafe starter path or Git metadata/hook.')
        if not isinstance(content, (str, bytes)):
            raise ValueError(f'{name}: expected text or bytes, not a source path.')
        result[name] = content.encode('utf-8') if isinstance(content, str) else content
    seen = {}
    for name in sorted(result):
        for part in [PurePosixPath(name), *PurePosixPath(name).parents[:-1]]:
            folded = str(part).casefold()
            if folded in seen and seen[folded] != str(part):
                raise ValueError(f'{name}: case-insensitive starter path collision.')
            seen[folded] = str(part)
        if any(str(parent) in result for parent in PurePosixPath(name).parents):
            raise ValueError(f'{name}: starter file is also used as a directory.')
    return result


def _snapshot(path):
    _safe(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f'{path}: expected a regular file.')
    return path.read_bytes()


def _target_state(target, operation, files, resume, allow_git):
    _safe(target)
    if operation == 'attach':
        if not target.is_dir():
            raise ValueError(f'{target}: attach requires an existing directory.')
        stat = target.stat()
        return ('attach', stat.st_dev, stat.st_ino)
    if not target.exists():
        if not target.parent.is_dir():
            raise ValueError(f'{target.parent}: create the parent directory first.')
        return None
    if not target.is_dir() or not resume:
        raise ValueError(f'{target}: already exists; inspect it and explicitly resume.')
    expected_dirs = {str(parent) for name in files for parent in PurePosixPath(name).parents
                     if str(parent) != '.'}
    state = []
    for current, directories, names in os.walk(target, followlinks=False):
        base = Path(current)
        for name in sorted([*directories, *names]):
            path = base / name
            relative = path.relative_to(target).as_posix()
            if relative == '.git' and allow_git:
                if path.is_symlink() or not path.is_dir():
                    raise ValueError(f'{path}: worktrees and redirected Git metadata are not resumable.')
                directories.remove(name)
                continue
            _safe(path)
            if path.is_dir() and relative in expected_dirs:
                state.append((relative, None))
            elif path.is_file() and relative in files and path.read_bytes() == files[relative]:
                state.append((relative, files[relative]))
            else:
                raise ValueError(f'{path}: unexpected or changed starter content; inspect before resuming.')
    return tuple(sorted(state))


def _git_state(target, initialize, branch, remote_url, remote_name):
    if not initialize and remote_url is None:
        return None
    if not isinstance(branch, str) or not branch or branch.startswith('-'):
        raise ValueError('Initial branch must be a valid explicit branch name.')
    if _git(None, 'check-ref-format', 'refs/heads/' + branch, check=False).returncode:
        raise ValueError(f'{branch}: invalid initial branch name.')
    if remote_url is not None:
        if (not isinstance(remote_url, str) or not remote_url.strip() or
                any(char in remote_url for char in '\0\n\r')):
            raise ValueError('Remote URL must be nonempty and contain no line breaks.')
        if not isinstance(remote_name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', remote_name):
            raise ValueError('Remote name must contain letters, digits, hyphens or underscores.')
    for parent in target.parents:
        if (parent / '.git').exists() or (parent / '.git').is_symlink():
            raise ValueError(f'{target}: inside an existing Git repository at {parent}.')
        if (parent / 'HEAD').is_file() and (parent / 'objects').is_dir():
            raise ValueError(f'{target}: inside bare Git metadata at {parent}.')
    metadata = target / '.git'
    if metadata.exists() or metadata.is_symlink():
        _safe(metadata)
        if not metadata.is_dir():
            raise ValueError(f'{metadata}: existing worktree or redirected metadata is unsupported.')
        for current, directories, names in os.walk(metadata, followlinks=False):
            for name in [*directories, *names]:
                path = Path(current) / name
                if path.is_symlink() or name in {'commondir', 'gitdir'}:
                    raise ValueError(f'{path}: redirected Git metadata is unsupported.')
        top = _git(target, 'rev-parse', '--show-toplevel').stdout.strip()
        if Path(top).resolve() != target.resolve():
            raise ValueError(f'{target}: is not the actual Git working tree root.')
        head = None
        if initialize:
            head = _git(target, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False).stdout.strip()
            if head != branch:
                raise ValueError(f'{target}: existing branch {head or "(detached HEAD)"} differs from requested {branch}; no rename is performed.')
        config = _snapshot(metadata / 'config')
        listing = _git(target, 'config', '--local', '--no-includes', '--name-only', '--list').stdout
        if any(line.lower().startswith(('include.', 'includeif.')) for line in listing.splitlines()):
            raise ValueError(f'{metadata}: included Git configuration is unsupported for setup.')
        existing = _git(target, 'config', '--local', '--no-includes', '--get-all',
                        f'remote.{remote_name}.url', check=False).stdout.splitlines() if remote_url is not None else []
        if existing and existing != [remote_url]:
            raise ValueError(f'{remote_name}: remote already has a different URL; resolve it explicitly.')
        return (config, bool(existing), head)
    if remote_url is not None and not initialize:
        raise ValueError('Configuring a remote requires an existing Git root or selected Git initialization.')
    return (None, False, None)


def _link_state(path):
    _safe(path.parent)
    if path.is_symlink():
        return os.readlink(path)
    if path.exists():
        raise ValueError(f'{path}: navigation path contains real content.')
    return None


def _binding(root, key, role, target):
    if key is None:
        return None
    if target == root or target in root.parents:
        raise ValueError('Binding to this checkout or its ancestors would create a navigation cycle.')
    if role not in LINK_ROLES:
        raise ValueError(f'{role}: expected repo, shlf or zbox.')
    entries = catalog.discover(root)
    if key not in entries or entries[key]['kind'] not in {'area', 'activity'}:
        raise ValueError(f'{key}: expected a known activity or area key.')
    config = root / '.yap/cfg/machine.json'
    before = _snapshot(config)
    settings = json.loads(before) if before is not None else {}
    if not isinstance(settings, dict) or not isinstance(settings.get('links', {}), dict):
        raise ValueError(f'{config}: expected a links mapping.')
    links = settings.setdefault('links', {})
    roles = links.setdefault(key, {})
    if not isinstance(roles, dict) or set(roles) - set(LINK_ROLES):
        raise ValueError(f'{key}: expected repo/shlf/zbox mapping.')
    existing = roles.get(role)
    if role in roles:
        if not isinstance(existing, str) or not existing.strip():
            raise ValueError(f'{key}/{role}: existing binding is invalid.')
        bound = Path(existing).expanduser()
        if not bound.is_absolute():
            bound = root / bound
        if Path(os.path.abspath(bound)) != target:
            raise ValueError(f'{key}/{role}: already bound elsewhere; resolve explicitly.')
    else:
        roles[role] = str(target)
    folder = entries[key]['folder']
    if target == folder or target in folder.parents:
        raise ValueError('Binding target would contain its own navigation link.')
    workspace = folder / 'wsp'
    _safe(workspace)
    if workspace.exists() and not workspace.is_dir():
        raise ValueError(f'{workspace}: expected a directory.')
    has_modules = any(entry['kind'] == 'activity' and folder / 'mod' in entry['folder'].parents
                      for entry in entries.values())
    active, inactive = (workspace, folder) if has_modules else (folder, workspace)
    paths = (active / role, inactive / role)
    if any(target == path or target in path.parents for path in paths):
        raise ValueError('Binding target would contain its own navigation link.')
    states = tuple(_link_state(path) for path in paths)
    for path, state in zip(paths, states):
        if state is not None and Path(os.path.abspath(path.parent / state)) != target:
            raise ValueError(f'{path}: existing navigation points elsewhere; resolve explicitly.')
    after = before if existing is not None else (json.dumps(settings, indent=2, ensure_ascii=False) + '\n').encode()
    return dict(config=config, before=before, after=after, paths=paths, states=states)


@dataclass
class Plan:
    root: Path
    operation: str
    target: Path
    files: dict
    initialize_git: bool
    branch: str
    remote_url: str | None
    remote_name: str
    binding_key: str | None
    role: str
    resume: bool
    target_state: object
    git_state: object
    binding: object
    steps: tuple

    def preview(self, language='en'):
        heading = 'Geplante lokale Schritte' if language == 'de' else 'Planned local steps'
        if self.operation == 'attach':
            heading = ('Vorhandenen Arbeitsort verknüpfen (Ziel bleibt unverändert)' if language == 'de'
                       else 'Attach existing location (target remains unchanged)')
        details = [str(self.target)]
        if self.initialize_git:
            details.append(('Vorgeschlagener initialer Branch: ' if language == 'de' else 'Proposed initial branch: ') + self.branch)
        if self.remote_url is not None:
            details.append(f'Remote {self.remote_name}: {self.remote_url}')
        if self.binding_key is not None:
            details.append(('Arbeitsort: ' if language == 'de' else 'Binding: ') + f'{self.binding_key}/{self.role}')
        return heading + ':\n' + '\n'.join(f'- {_label(step, language)}' for step in self.steps) + '\n' + '\n'.join(details)


def _label(step, language):
    if language != 'de':
        return step
    if step.startswith('write '):
        return 'Datei schreiben: ' + step[6:]
    return {'create directory': 'Verzeichnis anlegen', 'initialize Git': 'Git initialisieren',
            'configure remote': 'Remote eintragen', 'save binding': 'Arbeitsort speichern',
            'update navigation': 'Navigation aktualisieren'}.get(step, step)


@dataclass
class Result:
    target: Path
    completed: list
    pending: list
    error: str | None = None

    @property
    def success(self):
        return self.error is None

    def preview(self, language='en'):
        done, pending, error = ('Erledigt', 'Offen', 'Fehler') if language == 'de' else ('Completed', 'Pending', 'Error')
        text = str(self.target) + f'\n{done}: ' + (', '.join(_label(s, language) for s in self.completed) or '—')
        text += f'\n{pending}: ' + (', '.join(_label(s, language) for s in self.pending) or '—')
        return text + (f'\n{error}: {self.error}' if self.error else '')


def plan(root, operation, target, files=None, initialize_git=False, branch='trunk',
         remote_url=None, remote_name='origin', binding_key=None, role='repo', resume=False,
         *, template_profile=None, template_inputs=None):
    """Validate all requested operations without changing files or Git state."""
    root, target = Path(root).resolve(), Path(os.path.abspath(Path(target).expanduser()))
    if operation not in {'create', 'attach'}:
        raise ValueError('Operation must be create or attach.')
    if template_profile is not None:
        if files is not None:
            raise ValueError('Select rendered files or a template, not both.')
        from .repo_templates import render_template
        files = render_template(template_profile, template_inputs or {})
        if (template_profile == 'db-gitlab' and initialize_git
                and branch not in template_inputs['db_metadata']['protected-branches']):
            raise ValueError('Initial branch must match confirmed DB protected-branches metadata.')
    elif template_inputs is not None:
        raise ValueError('Template inputs require a selected template profile.')
    files = _starter_files(files)
    if operation == 'attach' and (files or initialize_git or remote_url is not None or resume):
        raise ValueError('Attach does not generate files, initialize Git, configure remotes or resume creation.')
    state = _target_state(target, operation, files, resume, initialize_git or remote_url is not None)
    git_state = _git_state(target, initialize_git, branch, remote_url, remote_name)
    binding = _binding(root, binding_key, role, target)
    steps = []
    if operation == 'create':
        if state is None:
            steps.append('create directory')
        steps.extend(f'write {name}' for name in sorted(files) if not (target / name).exists())
        if initialize_git and git_state[0] is None:
            steps.append('initialize Git')
        if remote_url is not None and not git_state[1]:
            steps.append('configure remote')
    if binding:
        if binding['before'] != binding['after']:
            steps.append('save binding')
        if binding['states'] != (str(target), None):
            steps.append('update navigation')
    return Plan(root, operation, target, files, initialize_git, branch, remote_url, remote_name,
                binding_key, role, resume, state, git_state, binding, tuple(steps))


def _save_binding(binding):
    config = binding['config']
    _safe(config)
    config.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=config.parent, prefix='.machine-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(binding['after'])
        if _snapshot(config) != binding['before']:
            raise ValueError('Private settings changed during setup; inspect and resume.')
        temporary.replace(config)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def apply(proposal):
    """Recheck a plan, retain partial results, and never roll back user material."""
    completed, pending = [], list(proposal.steps)
    try:
        fresh = plan(proposal.root, proposal.operation, proposal.target, proposal.files,
                     proposal.initialize_git, proposal.branch, proposal.remote_url, proposal.remote_name,
                     proposal.binding_key, proposal.role, proposal.resume)
        if fresh != proposal:
            raise ValueError('Workspace state changed since planning; inspect and create a new plan.')
        for step in proposal.steps:
            _safe(proposal.target)
            if step == 'create directory':
                proposal.target.mkdir()
            elif step.startswith('write '):
                name = step[len('write '):]
                destination = proposal.target / name
                _safe(destination)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as stream:
                    stream.write(proposal.files[name])
            elif step == 'initialize Git':
                if _git_state(proposal.target, True, proposal.branch, None, proposal.remote_name)[0] is not None:
                    raise ValueError('Git metadata appeared during setup; inspect and resume.')
                with tempfile.TemporaryDirectory(prefix='yap-empty-git-') as template:
                    _git(proposal.target, 'init', '--template=' + template, '--initial-branch=' + proposal.branch)
            elif step == 'configure remote':
                state = _git_state(proposal.target, False, proposal.branch, proposal.remote_url, proposal.remote_name)
                if not state[1]:
                    _git(proposal.target, 'remote', 'add', '--', proposal.remote_name, proposal.remote_url)
            elif step in {'save binding', 'update navigation'}:
                binding = _binding(proposal.root, proposal.binding_key, proposal.role, proposal.target)
                expected = proposal.binding
                if step == 'save binding':
                    if binding != expected:
                        raise ValueError('Binding or navigation changed during setup; inspect and resume.')
                    _save_binding(binding)
                else:
                    if (binding['paths'] != expected['paths'] or binding['states'] != expected['states']
                            or binding['before'] != expected['after']):
                        raise ValueError('Binding or navigation changed during setup; inspect and resume.')
                    active, inactive = binding['paths']
                    if _link_state(active) != str(proposal.target):
                        if active.is_symlink():
                            active.unlink()
                        active.parent.mkdir(parents=True, exist_ok=True)
                        active.symlink_to(proposal.target, target_is_directory=True)
                    if inactive.is_symlink():
                        inactive.unlink()
            completed.append(step)
            pending.pop(0)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return Result(proposal.target, completed, pending, str(error))
    return Result(proposal.target, completed, pending)
