"""Test suite for the ai launcher Python port."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import ai

# ---------------------------------------------------------------------------
# Argument parser tests
# ---------------------------------------------------------------------------


def test_parse_no_args_uses_claude_default(fake_home: Path) -> None:
    cmd, env, toggles, passthrough = ai.parse_argv(
        [], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert cmd[0] == "/bin/claude"
    assert "--model" in cmd and "opus" in cmd
    assert "--dangerously-skip-permissions" in cmd
    assert env == {}
    assert toggles == {
        "mitm": False,
        "control": False,
        "checks": True,
        "change_dir": True,
    }
    assert passthrough == []


def test_parse_droid(fake_home: Path) -> None:
    cmd, _env, _t, passthrough = ai.parse_argv(
        ["--droid"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert cmd == ["droid"]
    assert passthrough == []


def test_parse_opencode(fake_home: Path) -> None:
    cmd, _env, _t, _p = ai.parse_argv(
        ["--opencode"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert cmd == ["opencode"]


def test_parse_npx(fake_home: Path) -> None:
    cmd, _env, _t, _p = ai.parse_argv(["--npx"], home=fake_home, claude_binary=Path("/bin/claude"))
    assert cmd[:2] == ["npx", "@anthropic-ai/claude-code"]
    assert "--dangerously-skip-permissions" in cmd


def test_sandbox_wraps_default(fake_home: Path) -> None:
    cmd, _env, _t, _p = ai.parse_argv(
        ["--sandbox"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert cmd[:3] == ["docker", "sandbox", "run"]
    assert cmd[3] == "/bin/claude"


def test_nix_wraps_default(fake_home: Path) -> None:
    cmd, _env, _t, _p = ai.parse_argv(["--nix"], home=fake_home, claude_binary=Path("/bin/claude"))
    assert cmd[:3] == ["nix", "develop", "--command"]
    assert cmd[3] == "/bin/claude"


def test_sandbox_then_droid_order(fake_home: Path) -> None:
    """`--sandbox --droid`: sandbox wraps default, then droid replaces."""
    cmd, _env, _t, _p = ai.parse_argv(
        ["--sandbox", "--droid"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    # --droid replaces the wrapped cmd entirely
    assert cmd == ["droid"]


def test_droid_then_sandbox_order(fake_home: Path) -> None:
    """`--droid --sandbox`: droid first, then sandbox wraps droid."""
    cmd, _env, _t, _p = ai.parse_argv(
        ["--droid", "--sandbox"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert cmd == ["docker", "sandbox", "run", "droid"]


def test_litellm_requires_model_arg(fake_home: Path) -> None:
    with pytest.raises(ai.UsageError):
        ai.parse_argv(["--litellm"], home=fake_home, claude_binary=Path("/bin/claude"))


def test_litellm_validates_model_arg(fake_home: Path, fake_pass: dict[str, str]) -> None:
    fake_pass["litellm.vulcan.lan"] = "secret-token"
    with pytest.raises(ai.UsageError):
        ai.parse_argv(
            ["--litellm", "rm -rf /"],
            home=fake_home,
            claude_binary=Path("/bin/claude"),
        )


def test_litellm_sets_env_and_appends_model(fake_home: Path, fake_pass: dict[str, str]) -> None:
    fake_pass["litellm.vulcan.lan"] = "tok-123"
    cmd, env, _t, _p = ai.parse_argv(
        ["--litellm", "openai/gpt-4o"],
        home=fake_home,
        claude_binary=Path("/bin/claude"),
    )
    assert env["ANTHROPIC_AUTH_TOKEN"] == "tok-123"
    assert env["ANTHROPIC_BASE_URL"] == ai.LITELLM_BASE_URL
    for v in ai.GATEWAY_ANTHROPIC_VARS:
        assert env[v] == "openai/gpt-4o"
    assert cmd[-2:] == ["--model", "openai/gpt-4o"]


def test_llama_cpp_sets_env(fake_home: Path) -> None:
    cmd, env, _t, _p = ai.parse_argv(
        ["--llama-cpp", "qwen2.5"],
        home=fake_home,
        claude_binary=Path("/bin/claude"),
    )
    assert env["ANTHROPIC_AUTH_TOKEN"] == "llama-cpp"
    assert env["ANTHROPIC_BASE_URL"] == ai.LLAMA_CPP_BASE_URL
    assert env["ANTHROPIC_MODEL"] == "qwen2.5"
    assert cmd[-2:] == ["--model", "qwen2.5"]


def test_ollama_sets_env(fake_home: Path) -> None:
    cmd, env, _t, _p = ai.parse_argv(
        ["--ollama", "llama3.2"],
        home=fake_home,
        claude_binary=Path("/bin/claude"),
    )
    assert env["ANTHROPIC_AUTH_TOKEN"] == "ollama"
    assert env["ANTHROPIC_BASE_URL"] == ai.OLLAMA_BASE_URL
    assert env["ANTHROPIC_MODEL"] == "llama3.2"
    assert cmd[-2:] == ["--model", "llama3.2"]


def test_passthrough_after_unknown_token(fake_home: Path) -> None:
    cmd, _env, _t, passthrough = ai.parse_argv(
        ["--mitm", "unknown", "--droid"],
        home=fake_home,
        claude_binary=Path("/bin/claude"),
    )
    # --mitm consumed; "unknown" stops parsing; --droid is passthrough
    assert passthrough == ["unknown", "--droid"]
    # cmd stayed at the default (claude)
    assert cmd[0] == "/bin/claude"


def test_passthrough_with_double_dash(fake_home: Path) -> None:
    """`--` is itself an unknown token to the walker, so it stops there."""
    _cmd, _env, _t, passthrough = ai.parse_argv(
        ["--", "--droid"],
        home=fake_home,
        claude_binary=Path("/bin/claude"),
    )
    assert passthrough == ["--", "--droid"]


def test_help_flag_prints_and_exits(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ei:
        ai.parse_argv(["--help"], home=fake_home, claude_binary=Path("/bin/claude"))
    assert ei.value.code == 0
    captured = capsys.readouterr()
    assert "Usage:" in captured.out


def test_short_help_flag_exits(fake_home: Path) -> None:
    with pytest.raises(SystemExit):
        ai.parse_argv(["-h"], home=fake_home, claude_binary=Path("/bin/claude"))


def test_mitm_sets_proxy_env(fake_home: Path) -> None:
    _cmd, _env, toggles, _p = ai.parse_argv(
        ["--mitm"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert toggles["mitm"] is True


def test_here_disables_change_dir(fake_home: Path) -> None:
    _cmd, _env, toggles, _p = ai.parse_argv(
        ["--here"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert toggles["change_dir"] is False


def test_no_check_disables_checks(fake_home: Path) -> None:
    _cmd, _env, toggles, _p = ai.parse_argv(
        ["--no-check"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert toggles["checks"] is False


def test_local_uses_opencode_with_litellm_model(fake_home: Path) -> None:
    cmd, _env, _t, _p = ai.parse_argv(
        ["--local"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert cmd[0] == "opencode"
    assert "--model" in cmd
    assert any("litellm/" in t for t in cmd)


def test_work_and_personal_set_config_dir(fake_home: Path) -> None:
    _cmd, env, _t, _p = ai.parse_argv(["--work"], home=fake_home, claude_binary=Path("/bin/claude"))
    assert env["CLAUDE_CONFIG_DIR"] == str(fake_home / ".config/claude/positron")
    _cmd, env, _t, _p = ai.parse_argv(
        ["--personal"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert env["CLAUDE_CONFIG_DIR"] == str(fake_home / ".config/claude/personal")
    _cmd, env, _t, _p = ai.parse_argv(
        ["--git-ai"], home=fake_home, claude_binary=Path("/bin/claude")
    )
    assert env["CLAUDE_CONFIG_DIR"] == str(fake_home / ".config/claude/git-ai")


# ---------------------------------------------------------------------------
# Context detection
# ---------------------------------------------------------------------------


def test_detect_context_positron_path(tmp_path: Path) -> None:
    pwd = Path("/Users/john/src/positron/foo")
    ctx = ai.detect_context(pwd, tmp_path, {"positron": True, "git-ai": False, "personal": False})
    assert ctx is ai.Context.POSITRON


def test_detect_context_pos_short_path(tmp_path: Path) -> None:
    pwd = Path("/Users/john/src/pos/foo")
    ctx = ai.detect_context(pwd, tmp_path, {"positron": True, "git-ai": False, "personal": False})
    assert ctx is ai.Context.POSITRON


def test_detect_context_tron_path(tmp_path: Path) -> None:
    pwd = Path("/Users/john/src/tron/foo")
    ctx = ai.detect_context(pwd, tmp_path, {"positron": True, "git-ai": False, "personal": False})
    assert ctx is ai.Context.POSITRON


def test_detect_context_git_ai_path(tmp_path: Path) -> None:
    pwd = Path("/Users/john/src/git-ai/repo")
    ctx = ai.detect_context(pwd, tmp_path, {"positron": False, "git-ai": True, "personal": False})
    assert ctx is ai.Context.GIT_AI


def test_detect_context_personal_default(tmp_path: Path) -> None:
    pwd = Path("/tmp/elsewhere")
    ctx = ai.detect_context(pwd, tmp_path, {"positron": False, "git-ai": False, "personal": True})
    assert ctx is ai.Context.PERSONAL


def test_detect_context_normal_when_dirs_missing(tmp_path: Path) -> None:
    pwd = Path("/tmp/elsewhere")
    ctx = ai.detect_context(pwd, tmp_path, {"positron": False, "git-ai": False, "personal": False})
    assert ctx is ai.Context.NORMAL


def test_detect_context_positron_path_but_dir_missing(tmp_path: Path) -> None:
    pwd = Path("/Users/john/src/positron/foo")
    ctx = ai.detect_context(pwd, tmp_path, {"positron": False, "git-ai": False, "personal": False})
    # Falls through to NORMAL because positron dir absent (mirrors Bash)
    assert ctx is ai.Context.NORMAL


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


def test_redact_env_redacts_secrets() -> None:
    env = {
        "ANTHROPIC_AUTH_TOKEN": "sk-secret",
        "EXTENSION_SECRET": "my-secret",
        "API_KEY": "abc",
        "ADMIN_PASSWORD": "hunter2",
        "ANTHROPIC_MODEL": "opus",
        "COLORTERM": "truecolor",
    }
    out = ai.redact_env(env)
    assert out["ANTHROPIC_AUTH_TOKEN"] == "<REDACTED>"
    assert out["EXTENSION_SECRET"] == "<REDACTED>"
    assert out["API_KEY"] == "<REDACTED>"
    assert out["ADMIN_PASSWORD"] == "<REDACTED>"
    assert out["ANTHROPIC_MODEL"] == "opus"
    assert out["COLORTERM"] == "truecolor"


def test_validate_model_rejects_shell_metas() -> None:
    bad = ["rm -rf /", "model;ls", "model$(whoami)", "a b", "model|cat", ""]
    for s in bad:
        with pytest.raises(ai.UsageError):
            ai.validate_model_arg(s)


def test_validate_model_accepts_normal_names() -> None:
    good = [
        "opus",
        "gpt-4o",
        "openai/gpt-4o",
        "hera/omlx/Qwen3.6-27B-MLX-8bit",
        "model:tag",
        "anthropic.claude-3-5-sonnet-v2:0",
    ]
    for s in good:
        assert ai.validate_model_arg(s) == s


def test_run_pass_fails_closed_on_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/pass")

    def fake_run(*_a, **_kw):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(["pass", "x"], 1, "", "decryption failed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ai.ConfigError):
        ai.run_pass("x")


def test_run_pass_fails_closed_on_empty_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/pass")

    def fake_run(*_a, **_kw):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(["pass", "x"], 0, "\n", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ai.ConfigError):
        ai.run_pass("x")


def test_run_pass_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(ai.ConfigError):
        ai.run_pass("anything")


def test_run_pass_returns_first_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/pass")

    def fake_run(*_a, **_kw):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(["pass", "x"], 0, "first-line\nsecond-line\n", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert ai.run_pass("x") == "first-line"


# ---------------------------------------------------------------------------
# Asahi rg fix
# ---------------------------------------------------------------------------


def test_asahi_fix_noop_on_other_arch(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeUname:
        machine = "x86_64"

    monkeypatch.setattr(os, "uname", lambda: FakeUname())
    # Should silently no-op (not raise, not error).
    ai.fix_ripgrep_for_asahi()


def test_asahi_fix_noop_on_arm64_non_16k_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeUname:
        machine = "aarch64"

    monkeypatch.setattr(os, "uname", lambda: FakeUname())
    monkeypatch.setattr(os, "sysconf", lambda key: 4096)
    ai.fix_ripgrep_for_asahi()


def test_asahi_fix_path_traversal_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A symlink that escapes ~/.npm/_npx must not be touched."""

    class FakeUname:
        machine = "aarch64"

    home = tmp_path / "home"
    npx_cache = home / ".npm/_npx"
    bad_dir = npx_cache / "abc/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/arm64-linux"
    bad_dir.mkdir(parents=True)

    # Outside-of-cache target the symlink will point at
    outside = tmp_path / "outside" / "rg"
    outside.parent.mkdir(parents=True)
    outside.write_text("#!/bin/sh\nexit 1\n")
    outside.chmod(0o755)

    rg_path = bad_dir / "rg"
    os.symlink(outside, rg_path)

    monkeypatch.setattr(os, "uname", lambda: FakeUname())
    monkeypatch.setattr(os, "sysconf", lambda key: 16384)
    monkeypatch.setattr(Path, "home", lambda: home)
    # Provide a system rg path so we get past that gate
    sys_rg = tmp_path / "sysrg"
    sys_rg.write_text("ok")
    sys_rg.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda name: str(sys_rg) if name == "rg" else None)

    # Run the fixer; it should NOT replace the symlink (because it's already
    # a symlink AND it escapes the cache root)
    ai.fix_ripgrep_for_asahi()
    # The rg path is still the original symlink to `outside`
    assert rg_path.is_symlink()
    assert os.readlink(rg_path) == str(outside)


# ---------------------------------------------------------------------------
# EXEC_TRACE smoke test (single-process)
# ---------------------------------------------------------------------------


def test_exec_trace_outputs_argv_and_redacted_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fake_home: Path,
) -> None:
    monkeypatch.setenv("EXEC_TRACE", "1")
    # Avoid changing dir / preflight noise
    monkeypatch.chdir(fake_home)
    rc = ai.main(["--here", "--no-check", "--droid", "extra"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("ARGV: droid extra\n")
    # Default ANTHROPIC_MODEL should be present
    assert "ANTHROPIC_MODEL=" in out
    # COLORTERM should be present
    assert "COLORTERM=truecolor" in out


def test_exec_trace_redacts_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fake_home: Path,
) -> None:
    monkeypatch.setenv("EXEC_TRACE", "1")
    monkeypatch.chdir(fake_home)
    rc = ai.main(["--here", "--no-check", "--llama-cpp", "qwen2.5"])
    assert rc == 0
    out = capsys.readouterr().out
    # Token must be redacted
    assert "ANTHROPIC_AUTH_TOKEN=<REDACTED>" in out
    assert "llama-cpp" not in out.split("ANTHROPIC_AUTH_TOKEN=", 1)[1].split("\n", 1)[0]


# ---------------------------------------------------------------------------
# Parity tests against the Bash script (running in subprocess)
# ---------------------------------------------------------------------------


PARITY_CASES = [
    [],
    ["--droid"],
    ["--opencode"],
    ["--npx"],
    ["--sandbox"],
    ["--sandbox", "--droid"],
    ["--droid", "--sandbox"],
    ["--mitm"],
    ["--no-check"],
    ["--positron"],
    ["--personal"],
    ["--git-ai"],
    ["--llama-cpp", "qwen2.5"],
    ["--ollama", "llama3.2"],
    ["--droid", "extra1", "extra2"],
    ["--", "--droid"],
    ["unknown-token", "--mitm"],
    ["--no-check", "--here"],
    ["--nix"],
    ["--nix", "--sandbox"],
    ["--local"],
]


def _run(prog: list[str], args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "EXEC_TRACE": "1",
        # Stable HOME so both runs see same paths
        "HOME": os.environ.get("HOME", str(Path.home())),
        # Force C locale so Bash `sort` uses byte order (matches Python sorted()).
        "LC_ALL": "C",
        "LANG": "C",
    }
    return subprocess.run(
        [*prog, *args], cwd=cwd, capture_output=True, text=True, env=env, check=False
    )


@pytest.mark.parametrize("args", PARITY_CASES)
def test_parity_with_bash(args: list[str], repo_root: Path) -> None:
    if not (repo_root / "ai").exists():
        pytest.skip("Bash ai script not present")
    if shutil.which("bash") is None:
        pytest.skip("bash not available")
    # --here suppresses cd; --no-check suppresses preflight (which goes to
    # different streams in Bash vs Python). Both leave EXEC_TRACE output as
    # the only stdout content, which is what we compare.
    full = ["--here", "--no-check", *args]
    bash = _run(["bash", str(repo_root / "ai")], full, repo_root)
    py = _run([sys.executable, str(repo_root / "ai.py")], full, repo_root)
    assert bash.returncode == 0, f"bash failed: {bash.stderr}"
    assert py.returncode == 0, f"py failed: {py.stderr}"
    # Bash's printf produces a trailing space when passthrough is empty
    # (we replicate this in Python). Compare line-by-line, rstripping each.
    bash_lines = [ln.rstrip() for ln in bash.stdout.splitlines()]
    py_lines = [ln.rstrip() for ln in py.stdout.splitlines()]
    assert bash_lines == py_lines, (
        f"args={args}\n--- bash ---\n{bash.stdout}\n--- py ---\n{py.stdout}"
    )
