import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("dispatch-agent-note")


def load_subject():
    loader = importlib.machinery.SourceFileLoader(
        "dispatch_agent_note_under_test", str(SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


subject = load_subject()


def extraction(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "version": 1,
        "trigger": True,
        "model": None,
        "machine": None,
        "project": None,
        "worktree": None,
        "worktree_mode": "none",
        "repo_slug": "paris-sunset",
        "title": "Find Paris sunset",
    }
    value.update(overrides)
    return value


def alias_document(
    *,
    default: str = "gpt sol",
    aliases: dict[str, dict[str, str]] | None = None,
    default_machine: str = "hera",
    machines: dict[str, dict[str, str | None]] | None = None,
    projects: dict[str, dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "version": 1,
        "defaultAlias": default,
        "aliases": aliases
        or {
            "deepseek": {
                "harness": "pi",
                "provider": "omlx-hera",
                "model": "GLM-5.3-Flash-MLX-oQ4-MTP",
                "thinking": "max",
            },
            "gpt sol": {
                "harness": "pi",
                "provider": "openai-codex",
                "model": "gpt-5.6-sol",
                "thinking": "max",
            },
        },
        "defaultMachine": default_machine,
        "machines": machines
        or {
            "andoria-08": {"remote": "andoria-08"},
            "hera": {"remote": None},
        },
        "projects": projects
        or {
            "agent-cat": {"machine": "hera", "path": "~/src/agent-cat"},
            "ares": {"machine": "hera", "path": "~/hera/ares/main"},
            "nix": {"machine": "hera", "path": "~/src/nix"},
            "tron": {"machine": "andoria-08", "path": "~/tron/main"},
        },
    }


def write_aliases(path: Path, document: dict[str, object] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document or alias_document()), encoding="utf-8")


def make_config(tmp_path: Path, **overrides: object):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    aliases_path = home / "agent-model-aliases.json"
    values: dict[str, object] = {
        "home": home,
        "project_root": home / "src",
        "state_root": home / "state",
        "llm_route": home / "route.json",
        "aliases_path": aliases_path,
        "transcribe": "transcribe",
        "pi": "pi",
        "agent_deck": "agent-deck",
        "git": shutil.which("git") or "git",
        "ssh": shutil.which("ssh") or "ssh",
    }
    write_aliases(aliases_path)
    values.update(overrides)
    return subject.Config(**values)


def git(*args: object, cwd: Path | None = None) -> None:
    subprocess.run(
        [shutil.which("git") or "git", *(str(arg) for arg in args)],
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    git("init", "--quiet", path)
    git("config", "user.email", "test@example.invalid", cwd=path)
    git("config", "user.name", "Test", cwd=path)
    git("commit", "--allow-empty", "-m", "initial", cwd=path)


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def cli_environment(
    tmp_path: Path, extraction_value: dict[str, object]
) -> tuple[dict[str, str], Path]:
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    fixture = tmp_path / "extraction.json"
    stub_state = tmp_path / "agent-deck-stub"
    home.mkdir()
    bin_dir.mkdir()
    stub_state.mkdir()
    remote_home = tmp_path / "remote-home"
    init_repo(remote_home / "tron/main")
    fixture.write_text(json.dumps(extraction_value), encoding="utf-8")
    aliases_path = home / "agent-model-aliases.json"
    write_aliases(aliases_path)

    write_executable(
        bin_dir / "transcribe",
        """#!/usr/bin/env python3
import json, os, shutil, sys
args = sys.argv[1:]
log = os.environ['STUB_DIR'] + '/transcribe-calls.jsonl'
with open(log, 'a', encoding='utf-8') as handle:
    handle.write(json.dumps(args) + '\\n')
if os.environ.get('TRANSCRIBE_FAIL') == '1':
    raise SystemExit(23)
out = args[args.index('--output') + 1]
shutil.copyfile(os.environ['EXTRACTION_JSON'], out)
""",
    )
    write_executable(
        bin_dir / "pi",
        """#!/usr/bin/env python3
import os
print('provider    model                                  context  max-out  thinking  images')
print('openai-codex gpt-5.6-sol                            1.0M     128K     yes       yes')
if os.environ.get('STUB_REMOTE') != '1':
    print('omlx-hera   GLM-5.3-Flash-MLX-oQ4-MTP     262.1K   65.5K   no        no')
""",
    )
    write_executable(
        bin_dir / "agent-deck",
        """#!/usr/bin/env python3
import json, os, pathlib, sys
raw_args = sys.argv[1:]
remote = os.environ.get('STUB_REMOTE') == '1'
root = pathlib.Path(os.environ['STUB_DIR'])
if raw_args[:3] == ['remote', 'list', '--json']:
    print(json.dumps([{
        'name':'andoria-08', 'host':'test@andoria-08',
        'agent_deck_path':sys.argv[0], 'profile':'default'
    }]))
    raise SystemExit(0)
args = raw_args[2:] if raw_args[:2] == ['-p', 'default'] else raw_args
prefix = 'remote-' if remote else ''
db_path = root / f'{prefix}sessions.json'
events_path = root / f'{prefix}agent-deck-calls.jsonl'
sessions = json.loads(db_path.read_text()) if db_path.exists() else []
with events_path.open('a', encoding='utf-8') as handle:
    handle.write(json.dumps(args) + '\\n')
def save(): db_path.write_text(json.dumps(sessions), encoding='utf-8')
def value(flag): return args[args.index(flag) + 1]
def record_prompt(session_id, message_file):
    text = (sys.stdin.read() if message_file == '-' else pathlib.Path(message_file).read_text(encoding='utf-8')).rstrip('\\r\\n')
    directory = pathlib.Path.home() / '.pi' / 'agent-deck' / session_id
    directory.mkdir(parents=True, exist_ok=True)
    entry = {'type':'message','message':{'role':'user','content':[{'type':'text','text':text}]}}
    with (directory / 'session.jsonl').open('a', encoding='utf-8') as handle:
        if remote and os.environ.get('REMOTE_HISTORY_MALFORMED') == '1':
            handle.write('{malformed\\n')
        handle.write(json.dumps(entry) + '\\n')
if args[:2] == ['list', '--json']:
    print(json.dumps(sessions)); raise SystemExit(0)
if args and args[0] == 'launch':
    session_id = 'remote-voice-session-1' if remote else 'voice-session-1'
    session = {'id':session_id,'title':value('--title'),'path':args[1],
               'tool':'pi','command':value('--cmd'),'status':'waiting'}
    sessions.append(session); save()
    mode = os.environ.get('AGENT_DECK_MODE', '')
    if mode == 'fail-before-prompt': raise SystemExit(31)
    if mode == 'success-without-prompt':
        print(json.dumps({'success':True,'id':session_id,'session_id':session_id,
                          'path':session['path'],'tool':'pi'})); raise SystemExit(0)
    record_prompt(session_id, value('--message-file'))
    if mode == 'fail-after-prompt': raise SystemExit(32)
    print(json.dumps({'success':True,'id':session_id,'session_id':session_id,
                      'path':session['path'],'tool':'pi'})); raise SystemExit(0)
if args[:2] in (['session','send'], ['session','start']):
    session_id = args[2]
    record_prompt(session_id, value('--message-file'))
    if os.environ.get('AGENT_DECK_MODE') == 'send-fail-after-prompt': raise SystemExit(33)
    print(json.dumps({'success':True,'id':session_id})); raise SystemExit(0)
raise SystemExit(90)
""",
    )
    write_executable(
        bin_dir / "ssh",
        """#!/usr/bin/env python3
import json, os, shlex, subprocess, sys
args = sys.argv[1:]
command = shlex.split(args[-1])
with open(os.environ['STUB_DIR'] + '/ssh-calls.jsonl', 'a', encoding='utf-8') as handle:
    handle.write(json.dumps({'host':args[-2], 'command':command}) + '\\n')
environment = os.environ.copy()
environment['HOME'] = os.environ['REMOTE_HOME']
environment['STUB_REMOTE'] = '1'
result = subprocess.run(command, input=sys.stdin.read(), text=True, capture_output=True, env=environment)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
raise SystemExit(result.returncode)
""",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "PATH": f"{bin_dir}:{environment['PATH']}",
            "AGENT_NOTE_PROJECT_ROOT": str(home / "src"),
            "AGENT_NOTE_STATE_DIR": str(home / "state"),
            "AGENT_NOTE_LLM_ROUTE": str(home / "route.json"),
            "AGENT_NOTE_MODEL_ALIASES": str(aliases_path),
            "AGENT_NOTE_TRANSCRIBE": str(bin_dir / "transcribe"),
            "AGENT_NOTE_PI": str(bin_dir / "pi"),
            "AGENT_NOTE_AGENT_DECK": str(bin_dir / "agent-deck"),
            "AGENT_NOTE_SSH": str(bin_dir / "ssh"),
            "EXTRACTION_JSON": str(fixture),
            "STUB_DIR": str(stub_state),
            "REMOTE_HOME": str(remote_home),
        }
    )
    return environment, stub_state


def run_cli(env: dict[str, str], *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def test_trigger_and_strict_extraction_contract() -> None:
    assert subject.TRIGGER.match("\n  CREATE an AGENT using deepseek to work")
    assert not subject.TRIGGER.match("Please create an agent to work")
    parsed = subject.parse_extraction(json.dumps(extraction(model="deepseek")))
    assert parsed.model == "deepseek"
    assert parsed.repo_slug == "paris-sunset"
    with pytest.raises(subject.DispatchError, match="wrong fields"):
        subject.parse_extraction(json.dumps({**extraction(), "extra": True}))
    with pytest.raises(subject.DispatchError, match="requires project"):
        subject.parse_extraction(
            json.dumps(extraction(worktree="feature/x", worktree_mode="new"))
        )


def test_model_alias_and_catalog_resolution(tmp_path: Path) -> None:
    pi = tmp_path / "pi"
    write_executable(
        pi,
        """#!/bin/sh
printf '%s\n' 'provider model context max-out thinking images' \
  'openai-codex gpt-5.6-sol 1 1 yes yes' \
  'openai-codex gpt-5.4 1 1 yes yes' \
  'omlx-hera GLM-5.3-Flash-MLX-oQ4-MTP 1 1 no no' \
  'omlx-hera evil;touch 1 1 no no' \
  'provider-a shared-id 1 1 no no' \
  'provider-b shared-id 1 1 no no'
""",
    )
    config = make_config(tmp_path, pi=str(pi))
    assert subject.resolve_model(config, None) == subject.ModelTarget(
        "pi", "openai-codex", "gpt-5.6-sol", "max"
    )
    assert subject.resolve_model(config, "  GPT   SOL ") == subject.ModelTarget(
        "pi", "openai-codex", "gpt-5.6-sol", "max"
    )
    assert subject.resolve_model(config, "DEEPSEEK") == subject.ModelTarget(
        "pi", "omlx-hera", "GLM-5.3-Flash-MLX-oQ4-MTP", "max"
    )
    assert subject.resolve_model(config, "openai-codex/gpt-5.4") == subject.ModelTarget(
        "pi", "openai-codex", "gpt-5.4", "off"
    )
    assert subject.resolve_model(config, "gpt-5.4") == subject.ModelTarget(
        "pi", "openai-codex", "gpt-5.4", "off"
    )
    with pytest.raises(subject.DispatchError, match="ambiguous"):
        subject.resolve_model(config, "shared-id")
    with pytest.raises(subject.DispatchError, match="unavailable"):
        subject.resolve_model(config, "missing")

    write_aliases(
        config.aliases_path,
        alias_document(
            default="quoted",
            aliases={
                "quoted": {
                    "harness": "pi",
                    "provider": "omlx-hera",
                    "model": "evil;touch",
                    "thinking": "off",
                }
            },
        ),
    )
    quoted = subject.make_plan(
        config,
        subject.Extraction(
            "quoted", None, None, None, "none", "quoted-model", "Quoted"
        ),
        "Create an agent using an unusual exact model.",
        "a" * 64,
    )
    assert quoted["command"] == (
        "pi --provider omlx-hera --model 'evil;touch' --thinking off "
        "--exclude-tools subagent,workflow"
    )


def test_model_alias_registry_accepts_managed_file_symlink(tmp_path: Path) -> None:
    target = tmp_path / "store-aliases.json"
    write_aliases(target)
    link = tmp_path / "agent-model-aliases.json"
    link.symlink_to(target)

    registry = subject.load_aliases(link)

    assert registry.default_alias == "gpt sol"
    assert registry.aliases["deepseek"].provider == "omlx-hera"
    assert registry.default_machine == "hera"
    assert registry.machines["andoria-08"].remote == "andoria-08"
    assert registry.projects["tron"] == subject.ProjectTarget(
        "andoria-08", "~/tron/main"
    )


def test_model_alias_registry_rejects_duplicates_and_non_pi(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.aliases_path.write_text(
        '{"version":1,"defaultAlias":"deepseek","aliases":{'
        '"deepseek":{"harness":"pi","provider":"a","model":"b","thinking":"off"},'
        '"deepseek":{"harness":"pi","provider":"a","model":"c","thinking":"off"}}}',
        encoding="utf-8",
    )
    with pytest.raises(subject.DispatchError, match="duplicate"):
        subject.load_aliases(config.aliases_path)

    write_aliases(
        config.aliases_path,
        alias_document(
            default="other",
            aliases={
                "other": {
                    "harness": "codex",
                    "provider": "openai-codex",
                    "model": "gpt-5.6-sol",
                    "thinking": "max",
                }
            },
        ),
    )
    with pytest.raises(subject.DispatchError, match="Pi harness"):
        subject.load_aliases(config.aliases_path)

    write_aliases(
        config.aliases_path,
        alias_document(
            projects={"bad": {"machine": "hera", "path": "~/src/../private"}}
        ),
    )
    with pytest.raises(subject.DispatchError, match="project alias target"):
        subject.load_aliases(config.aliases_path)


def test_project_and_worktree_resolution_rejects_ambiguity_and_traversal(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    project = config.project_root / "sample-project"
    init_repo(project)
    worktree = config.home / "worktrees" / "feature-one"
    worktree.parent.mkdir()
    git("worktree", "add", "-b", "feature/one", worktree, cwd=project)

    assert (
        subject.resolve_project(config, "sample project", "in sample project")
        == project
    )
    assert (
        subject.resolve_existing_worktree(
            config, project, "feature/one", "use worktree feature/one"
        )
        == worktree
    )
    with pytest.raises(subject.DispatchError, match="not grounded"):
        subject.resolve_existing_worktree(
            config, project, "feature/one", "use the main checkout"
        )
    with pytest.raises(subject.DispatchError, match="not grounded"):
        subject.resolve_project(config, "sample project", "work in another repository")
    assert subject.validate_new_branch(config, "feature/two") == "feature/two"
    linked = config.project_root / "linked-project"
    linked.symlink_to(project, target_is_directory=True)
    with pytest.raises(subject.DispatchError, match="symlinks"):
        subject.resolve_project(config, str(linked), f"in {linked}")

    duplicate = config.project_root / "sample_project"
    init_repo(duplicate)
    with pytest.raises(subject.DispatchError, match="ambiguous"):
        subject.resolve_project(config, "sample project", "in sample project")
    with pytest.raises(subject.DispatchError):
        subject.resolve_project(config, "../sample-project", "in ../sample-project")


def test_new_repository_rejects_symlinked_project_root(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    outside = config.home / "outside"
    outside.mkdir()
    config.project_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(subject.DispatchError, match="symlink"):
        subject.create_repository(config, "unsafe", "a" * 64)

    assert not list(outside.iterdir())


def test_new_repository_rejects_symlinked_project_root_ancestor(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    outside = home / "outside"
    outside_root = outside / "src"
    outside_root.mkdir(parents=True)
    linked = home / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    config = make_config(tmp_path, project_root=linked / "src")

    with pytest.raises(subject.DispatchError, match="symlink"):
        subject.create_repository(config, "unsafe", "a" * 64)

    assert not list(outside_root.iterdir())


def test_interrupted_new_worktree_launch_reuses_created_git_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = make_config(tmp_path)
    project = config.project_root / "sample-project"
    init_repo(project)
    created = config.home / "worktrees" / "voice-branch"
    created.parent.mkdir()
    git("worktree", "add", "-b", "voice/branch", created, cwd=project)
    request = tmp_path / "request.txt"
    request.write_text("Create an agent in a new worktree.\n", encoding="utf-8")
    plan = {
        "path": str(project),
        "launch_path": str(project),
        "worktree_mode": "new",
        "branch": "voice/branch",
        "title": "Worktree [voice-deadbeef]",
        "command": "pi --provider openai-codex --model gpt-5.6-sol --thinking max",
    }
    calls: list[list[str]] = []

    def fake_agent_deck(
        _config: object,
        arguments: list[str],
        remote: str | None = None,
        timeout: int = 720,
        stdin: object = None,
    ) -> subprocess.CompletedProcess[str]:
        del remote, timeout, stdin
        calls.append(arguments)
        return subprocess.CompletedProcess(
            arguments,
            0,
            stdout=json.dumps({"session_id": "session-1"}),
            stderr="",
        )

    monkeypatch.setattr(subject, "run_agent_deck", fake_agent_deck)
    assert subject.launch_session(config, plan, request) == "session-1"
    assert calls[-1][1] == str(created)
    assert "--worktree" not in calls[-1]

    git("worktree", "remove", "--force", created, cwd=project)
    assert subject.launch_session(config, plan, request) == "session-1"
    assert calls[-1][1] == str(project)
    assert calls[-1][calls[-1].index("--worktree") + 1] == "voice/branch"
    assert "--new-branch" not in calls[-1]


def test_matching_session_accepts_agent_deck_pi_wrapper_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = make_config(tmp_path)
    project = config.project_root / "sample-project"
    init_repo(project)
    session_id = "session-1"
    title = "Wrapped [voice-deadbeef]"
    command = (
        "pi --provider omlx-hera --model GLM-5.3-Flash-MLX-oQ4-MTP "
        "--thinking max --exclude-tools subagent,workflow"
    )
    summary = {
        "id": session_id,
        "title": title,
        "path": str(project),
        "tool": "pi",
        "command": "pi",
        "status": "running",
    }
    details = {
        **summary,
        "wrapper": (
            "{command} --provider omlx-hera "
            "--model GLM-5.3-Flash-MLX-oQ4-MTP --thinking max "
            "--exclude-tools subagent,workflow"
        ),
    }
    plan = {
        "path": str(project),
        "worktree_mode": "none",
        "title": title,
        "command": command,
    }

    monkeypatch.setattr(
        subject, "agent_deck_sessions", lambda _config, _remote=None: [summary]
    )
    monkeypatch.setattr(
        subject,
        "run_agent_deck",
        lambda _config, arguments, remote=None, timeout=720, stdin=None: (
            subprocess.CompletedProcess(
                arguments, 0, stdout=json.dumps(details), stderr=""
            )
        ),
    )

    assert subject.matching_session(config, plan) == details


def test_non_trigger_does_not_call_extractor(tmp_path: Path) -> None:
    env, stub = cli_environment(tmp_path, extraction())
    transcript = tmp_path / "note.txt"
    transcript.write_text("Ordinary agenda note.\n", encoding="utf-8")

    result = run_cli(env, "submit", "--transcript", transcript)

    assert result.returncode == 0
    assert "status=ignored" in result.stdout
    assert not (stub / "transcribe-calls.jsonl").exists()
    assert not (stub / "sessions.json").exists()


@pytest.mark.parametrize("mode", ["existing", "new"])
def test_submit_routes_existing_project_worktrees(tmp_path: Path, mode: str) -> None:
    value = extraction(
        project="sample-project",
        worktree="voice/branch",
        worktree_mode=mode,
        repo_slug=None,
    )
    env, stub = cli_environment(tmp_path, value)
    project = Path(env["AGENT_NOTE_PROJECT_ROOT"]) / "sample-project"
    init_repo(project)
    existing = Path(env["HOME"]) / "worktrees" / "voice-branch"
    if mode == "existing":
        existing.parent.mkdir()
        git("worktree", "add", "-b", "voice/branch", existing, cwd=project)
    transcript = tmp_path / "note.txt"
    transcript.write_text(
        f"Create an agent in sample-project using {mode} worktree voice/branch to test.\n",
        encoding="utf-8",
    )

    result = run_cli(env, "submit", "--transcript", transcript)

    assert result.returncode == 0, result.stderr
    calls = [
        json.loads(line)
        for line in (stub / "agent-deck-calls.jsonl").read_text().splitlines()
    ]
    launch = next(call for call in calls if call[0] == "launch")
    assert launch[1] == str(existing if mode == "existing" else project)
    assert launch[launch.index("--cmd") + 1] == (
        "pi --provider openai-codex --model gpt-5.6-sol --thinking max "
        "--exclude-tools subagent,workflow"
    )
    if mode == "new":
        assert launch[launch.index("--worktree") + 1] == "voice/branch"
        assert "--new-branch" in launch
    else:
        assert "--worktree" not in launch


def test_new_worktree_requires_explicit_grounded_intent(tmp_path: Path) -> None:
    value = extraction(
        project="sample-project",
        worktree="voice/branch",
        worktree_mode="new",
        repo_slug=None,
    )
    env, stub = cli_environment(tmp_path, value)
    project = Path(env["AGENT_NOTE_PROJECT_ROOT"]) / "sample-project"
    init_repo(project)
    transcript = tmp_path / "note.txt"
    transcript.write_text(
        "Create an agent in sample-project using worktree voice/branch to test.\n",
        encoding="utf-8",
    )

    result = run_cli(env, "submit", "--transcript", transcript)

    assert result.returncode == 1
    assert "worktree_unresolved" in result.stderr
    assert not (stub / "sessions.json").exists()


def test_submit_launches_once_with_exact_prompt_and_deepseek(tmp_path: Path) -> None:
    env, stub = cli_environment(tmp_path, extraction(model="deepseek"))
    transcript = tmp_path / "note.txt"
    text = (
        "Create an agent using the deepseek model to find tomorrow’s approximate "
        "sunset time in Paris.\n"
    )
    transcript.write_text(text, encoding="utf-8")

    first = run_cli(env, "submit", "--transcript", transcript)
    assert first.returncode == 0, first.stderr
    assert "completed=1" in first.stdout
    completion_events = [
        json.loads(line.removeprefix("agent-note "))
        for line in first.stdout.splitlines()
        if line.startswith("agent-note {")
    ]
    assert len(completion_events) == 1
    completion = completion_events[0]
    assert completion["status"] == "completed"
    assert completion["session_id"] == "voice-session-1"
    assert completion["path"].endswith("/paris-sunset")
    assert completion["provider"] == "omlx-hera"
    assert completion["model"] == "GLM-5.3-Flash-MLX-oQ4-MTP"
    assert completion["source_sha256"]
    assert completion["transcript_sha256"]
    assert text.strip() not in first.stdout
    repo = Path(env["AGENT_NOTE_PROJECT_ROOT"]) / "paris-sunset"
    assert (repo / ".git").is_dir()
    sessions = json.loads((stub / "sessions.json").read_text())
    assert len(sessions) == 1
    assert sessions[0]["path"] == str(repo)
    assert sessions[0]["command"] == (
        "pi --provider omlx-hera --model GLM-5.3-Flash-MLX-oQ4-MTP "
        "--thinking max --exclude-tools subagent,workflow"
    )
    calls = [
        json.loads(line)
        for line in (stub / "agent-deck-calls.jsonl").read_text().splitlines()
    ]
    launch = next(call for call in calls if call[0] == "launch")
    assert "--message-file" in launch
    assert text.strip() not in launch
    transcript_calls = (stub / "transcribe-calls.jsonl").read_text().splitlines()
    assert len(transcript_calls) == 1
    extraction_args = json.loads(transcript_calls[0])
    extraction_prompt = extraction_args[extraction_args.index("--prompt") + 1]
    assert '"deepseek"' in extraction_prompt
    assert '"gpt sol"' in extraction_prompt
    assert '"hera"' in extraction_prompt
    assert '"nix": "hera"' in extraction_prompt
    assert "provider/model" in extraction_prompt
    receipts = list((Path(env["AGENT_NOTE_STATE_DIR"]) / "done").iterdir())
    receipt = json.loads(receipts[0].read_text())
    assert receipt["harness"] == "pi"
    assert receipt["machine"] == "hera"
    assert receipt["thinking"] == "max"
    session_file = Path(env["HOME"]) / ".pi/agent-deck/voice-session-1/session.jsonl"
    messages = [json.loads(line) for line in session_file.read_text().splitlines()]
    assert len(messages) == 1
    assert messages[0]["message"]["content"][0]["text"] == text.rstrip("\n")

    second = run_cli(env, "submit", "--transcript", transcript)
    assert second.returncode == 0, second.stderr
    assert len((stub / "transcribe-calls.jsonl").read_text().splitlines()) == 1
    sessions = json.loads((stub / "sessions.json").read_text())
    assert len(sessions) == 1
    assert len(session_file.read_text().splitlines()) == 1


def test_submit_routes_nix_alias_to_hera_with_deepseek(tmp_path: Path) -> None:
    env, stub = cli_environment(
        tmp_path, extraction(model="deepseek", project="nix", repo_slug=None)
    )
    project = Path(env["HOME"]) / "src/nix"
    init_repo(project)
    transcript = tmp_path / "note.txt"
    transcript.write_text(
        "Create an agent using deepseek in my nix project to update a package.\n",
        encoding="utf-8",
    )

    result = run_cli(env, "submit", "--transcript", transcript)

    assert result.returncode == 0, result.stderr
    receipt = json.loads(
        next((Path(env["AGENT_NOTE_STATE_DIR"]) / "done").iterdir()).read_text()
    )
    assert receipt["machine"] == "hera"
    assert receipt["path"] == str(project)
    assert receipt["provider"] == "omlx-hera"
    sessions = json.loads((stub / "sessions.json").read_text())
    assert sessions[0]["path"] == str(project)


def test_submit_routes_tron_alias_over_agent_deck_ssh(tmp_path: Path) -> None:
    env, stub = cli_environment(tmp_path, extraction(project="tron", repo_slug=None))
    transcript = tmp_path / "note.txt"
    text = "Create an agent in my tron project to inspect the renderer.\n"
    transcript.write_text(text, encoding="utf-8")
    env["REMOTE_HISTORY_MALFORMED"] = "1"

    result = run_cli(env, "submit", "--transcript", transcript)

    assert result.returncode == 0, result.stderr
    receipt = json.loads(
        next((Path(env["AGENT_NOTE_STATE_DIR"]) / "done").iterdir()).read_text()
    )
    remote_project = Path(env["REMOTE_HOME"]) / "tron/main"
    assert receipt["machine"] == "andoria-08"
    assert receipt["path"] == str(remote_project)
    sessions = json.loads((stub / "remote-sessions.json").read_text())
    assert sessions[0]["path"] == str(remote_project)
    calls = [
        json.loads(line)
        for line in (stub / "remote-agent-deck-calls.jsonl").read_text().splitlines()
    ]
    launch = next(call for call in calls if call[0] == "launch")
    assert launch[launch.index("--message-file") + 1] == "-"
    assert text.strip() not in launch
    ssh_calls = [
        json.loads(line) for line in (stub / "ssh-calls.jsonl").read_text().splitlines()
    ]
    assert all(call["host"] == "test@andoria-08" for call in ssh_calls)
    session_file = (
        Path(env["REMOTE_HOME"]) / ".pi/agent-deck/remote-voice-session-1/session.jsonl"
    )
    history = session_file.read_text().splitlines()
    assert history[0] == "{malformed"
    message = json.loads(history[1])
    assert message["message"]["content"][0]["text"] == text.rstrip("\n")


def test_remote_model_is_validated_on_destination(tmp_path: Path) -> None:
    env, stub = cli_environment(
        tmp_path, extraction(model="deepseek", project="tron", repo_slug=None)
    )
    transcript = tmp_path / "note.txt"
    transcript.write_text(
        "Create an agent using deepseek in my tron project to inspect routing.\n",
        encoding="utf-8",
    )

    result = run_cli(env, "submit", "--transcript", transcript)

    assert result.returncode == 1
    assert "model_unresolved" in result.stderr
    assert not (stub / "remote-sessions.json").exists()


def test_project_alias_rejects_conflicting_machine(tmp_path: Path) -> None:
    env, stub = cli_environment(
        tmp_path, extraction(machine="hera", project="tron", repo_slug=None)
    )
    transcript = tmp_path / "note.txt"
    transcript.write_text(
        "Create an agent in my tron project on hera to inspect routing.\n",
        encoding="utf-8",
    )

    result = run_cli(env, "submit", "--transcript", transcript)

    assert result.returncode == 1
    assert "machine_unresolved" in result.stderr
    assert not (stub / "remote-sessions.json").exists()


def test_successful_launch_without_pi_history_is_not_completed(
    tmp_path: Path,
) -> None:
    env, stub = cli_environment(tmp_path, extraction())
    transcript = tmp_path / "note.txt"
    transcript.write_text(
        "Create an agent to inspect missing prompt evidence.\n", encoding="utf-8"
    )
    env["AGENT_DECK_MODE"] = "success-without-prompt"

    result = run_cli(env, "submit", "--transcript", transcript)

    assert result.returncode == 0, result.stderr
    assert "awaiting=1" in result.stdout
    pending = next((Path(env["AGENT_NOTE_STATE_DIR"]) / "pending").iterdir())
    state = json.loads((pending / "state.json").read_text())
    assert state["phase"] == "launched"
    assert not list((Path(env["AGENT_NOTE_STATE_DIR"]) / "done").iterdir())
    assert len(json.loads((stub / "sessions.json").read_text())) == 1


def test_failed_extraction_is_durable_and_retryable(tmp_path: Path) -> None:
    env, stub = cli_environment(tmp_path, extraction())
    transcript = tmp_path / "note.txt"
    transcript.write_text("Create an agent to inspect a test.\n", encoding="utf-8")
    env["TRANSCRIBE_FAIL"] = "1"
    failed = run_cli(env, "submit", "--transcript", transcript)
    assert failed.returncode == 1
    pending = list((Path(env["AGENT_NOTE_STATE_DIR"]) / "pending").iterdir())
    assert len(pending) == 1
    state = json.loads((pending[0] / "state.json").read_text())
    assert state["last_error"] == "extractor_failed"

    env.pop("TRANSCRIBE_FAIL")
    retried = run_cli(env, "drain")
    assert retried.returncode == 0, retried.stderr
    assert "completed=1" in retried.stdout
    assert len(json.loads((stub / "sessions.json").read_text())) == 1


def test_launch_crash_never_resends_without_authoritative_receipt(
    tmp_path: Path,
) -> None:
    env, stub = cli_environment(tmp_path, extraction())
    transcript = tmp_path / "note.txt"
    transcript.write_text(
        "Create an agent to inspect a launch crash.\n", encoding="utf-8"
    )
    env["AGENT_DECK_MODE"] = "fail-before-prompt"
    failed = run_cli(env, "submit", "--transcript", transcript)
    assert failed.returncode == 1
    assert len(json.loads((stub / "sessions.json").read_text())) == 1
    pending = next((Path(env["AGENT_NOTE_STATE_DIR"]) / "pending").iterdir())
    persisted = json.loads((pending / "state.json").read_text())
    assert persisted["phase"] == "planned"
    assert persisted["extraction"]["repo_slug"] == "paris-sunset"

    env.pop("AGENT_DECK_MODE")
    found = run_cli(env, "drain")
    assert found.returncode == 0, found.stderr
    assert "awaiting=1" in found.stdout
    state_path = pending / "state.json"
    state = json.loads(state_path.read_text())
    state["evidence_not_before"] = 0
    state_path.write_text(json.dumps(state), encoding="utf-8")

    uncertain = run_cli(env, "drain")
    assert uncertain.returncode == 1
    assert "delivery_uncertain" in uncertain.stderr
    calls = [
        json.loads(line)
        for line in (stub / "agent-deck-calls.jsonl").read_text().splitlines()
    ]
    assert sum(call[0] == "launch" for call in calls) == 1
    assert sum(call[:2] == ["session", "send"] for call in calls) == 0
    assert len((stub / "transcribe-calls.jsonl").read_text().splitlines()) == 1
    state = json.loads(state_path.read_text())
    assert state["last_error"] == "delivery_uncertain"


def test_launch_crash_after_prompt_uses_pi_history_as_receipt(tmp_path: Path) -> None:
    env, stub = cli_environment(tmp_path, extraction())
    transcript = tmp_path / "note.txt"
    text = "Create an agent to inspect a delivered launch crash.\n"
    transcript.write_text(text, encoding="utf-8")
    env["AGENT_DECK_MODE"] = "fail-after-prompt"
    assert run_cli(env, "submit", "--transcript", transcript).returncode == 1

    env.pop("AGENT_DECK_MODE")
    recovered = run_cli(env, "drain")
    assert recovered.returncode == 0, recovered.stderr
    assert "completed=1" in recovered.stdout
    calls = [
        json.loads(line)
        for line in (stub / "agent-deck-calls.jsonl").read_text().splitlines()
    ]
    assert sum(call[0] == "launch" for call in calls) == 1
    assert sum(call[:2] == ["session", "send"] for call in calls) == 0
    session_file = Path(env["HOME"]) / ".pi/agent-deck/voice-session-1/session.jsonl"
    assert len(session_file.read_text().splitlines()) == 1
