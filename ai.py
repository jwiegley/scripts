#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""ai - wrapper launcher for Claude Code, Droid, OpenCode, and friends.

Ports the Bash `ai` script to Python with stricter safety guarantees:
- shell=False subprocess everywhere
- fail-closed on `pass` secret retrieval
- path-traversal guard on Asahi ripgrep workaround
- argv as list[str] end-to-end (no shell tokenization)
- os.execvpe for final hand-off (preserves signals/exit codes)

Set EXEC_TRACE=1 to print resolved argv + redacted env and exit 0
instead of execvpe (used for parity testing against the Bash version).
"""

from __future__ import annotations

import enum
import os
import re
import shutil
import signal
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, NoReturn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OMLX_MODEL: Final[str] = "Qwen3.6-27B-MLX-8bit"
DEFAULT_LITELLM_MODEL: Final[str] = f"hera/omlx/{DEFAULT_OMLX_MODEL}"

WORK_DIR: Final[Path] = Path("/etc/nixos")

CLAUDE_DEFAULT_ARGS: Final[tuple[str, ...]] = (
    "--model",
    "opus",
    "--effort",
    "max",
    "--dangerously-skip-permissions",
)

MODEL_ARG_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9._/:-]+$")
SECRET_NAME_RE: Final[re.Pattern[str]] = re.compile(r"(TOKEN|SECRET|KEY|PASSWORD)", re.IGNORECASE)

GATEWAY_ANTHROPIC_VARS: Final[tuple[str, ...]] = (
    "ANTHROPIC_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
)

PASS_TIMEOUT: Final[float] = 10.0
PROBE_TIMEOUT: Final[float] = 5.0

# Asahi Linux ships aarch64 with 16KB pages, which breaks the bundled rg's jemalloc.
ASAHI_PAGE_SIZE: Final[int] = 16384

LITELLM_BASE_URL: Final[str] = "https://litellm.vulcan.lan"
LLAMA_CPP_BASE_URL: Final[str] = "http://localhost:8080"
OLLAMA_BASE_URL: Final[str] = "http://localhost:11434"
MITM_PROXY: Final[str] = "http://localhost:9999"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AIError(Exception):
    """Base class for ai launcher errors."""


class ConfigError(AIError):
    """Raised when configuration / external state is wrong."""


class BackendNotFoundError(AIError):
    """Raised when the chosen backend binary cannot be exec'd."""


class UsageError(AIError):
    """Raised when the user supplies invalid arguments."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Context(enum.Enum):
    NORMAL = "normal"
    POSITRON = "positron"
    GIT_AI = "git-ai"
    PERSONAL = "personal"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def detect_context(pwd: Path, home: Path, config_dirs_exist: dict[str, bool]) -> Context:
    """Mirror the Bash L9-20 PWD-based context detection.

    `home` is accepted to keep the function pure / testable, even though
    it is not used in the current logic (kept to mirror the Bash env).
    """
    del home  # currently unused but documents intent
    s = str(pwd)
    if (
        re.search(r"/pos(itron)?/", s)
        or re.search(r"/tron/", s)
        or re.search(r"/home/jwiegley/", s)
    ):
        if config_dirs_exist.get("positron"):
            return Context.POSITRON
    elif "/git-ai/" in s:
        if config_dirs_exist.get("git-ai"):
            return Context.GIT_AI
    elif config_dirs_exist.get("personal"):
        return Context.PERSONAL
    return Context.NORMAL


def find_claude_binary() -> Path:
    """Mirror the Bash L54-60 precedence."""
    candidates: tuple[Path, ...] = (
        Path("/etc/profiles/per-user/johnw/bin/claude"),
        Path.home() / ".nix-profile/bin/claude",
    )
    for cand in candidates:
        if os.access(cand, os.X_OK):
            return cand
    found = shutil.which("claude")
    if found:
        return Path(found)
    return Path("claude")


def validate_model_arg(s: str) -> str:
    """Reject anything that doesn't look like a model identifier.

    The character class allows '.', '/', ':', '-', '_'; we additionally
    reject any '..' segment (path traversal) and reject leading/trailing slashes.
    """
    if not MODEL_ARG_RE.fullmatch(s):
        raise UsageError(f"invalid model name: {s!r}")
    if ".." in s.split("/") or s.startswith("/") or s.endswith("/"):
        raise UsageError(f"invalid model name (path-like component): {s!r}")
    return s


def redact_env(env: Mapping[str, str]) -> dict[str, str]:
    """Replace values of secret-shaped keys with <REDACTED>."""
    return {k: ("<REDACTED>" if SECRET_NAME_RE.search(k) else v) for k, v in env.items()}


# ---------------------------------------------------------------------------
# Config dataclass (frozen end-state) + builder
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class Config:
    cmd: tuple[str, ...]
    env_overrides: tuple[tuple[str, str], ...]
    change_dir: bool
    enable_mitm: bool
    enable_control: bool
    enable_checks: bool
    passthrough: tuple[str, ...]


# ---------------------------------------------------------------------------
# `pass` secret retrieval
# ---------------------------------------------------------------------------


def run_pass(secret_name: str) -> str:
    """Retrieve a secret from `pass`. Fails closed on any error / empty."""
    pass_bin = shutil.which("pass")
    if pass_bin is None:
        raise ConfigError("`pass` command not found in PATH")
    try:
        result = subprocess.run(
            [pass_bin, secret_name],
            capture_output=True,
            text=True,
            timeout=PASS_TIMEOUT,
            check=False,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired as e:
        raise ConfigError(f"`pass {secret_name}` timed out after {PASS_TIMEOUT}s") from e
    if result.returncode != 0:
        raise ConfigError(
            f"`pass {secret_name}` failed (exit {result.returncode}): "
            f"{result.stderr.strip() or '<no stderr>'}"
        )
    first_line = result.stdout.split("\n", 1)[0].strip()
    if not first_line:
        raise ConfigError(f"`pass {secret_name}` returned empty value")
    return first_line


# ---------------------------------------------------------------------------
# Argv walker (Bash parity: stop at first unknown token)
# ---------------------------------------------------------------------------


def parse_argv(
    argv: Sequence[str],
    *,
    home: Path,
    claude_binary: Path,
    droid_cmd: str = "droid",
    opencode_cmd: str = "opencode",
) -> tuple[list[str], dict[str, str], dict[str, bool], list[str]]:
    """Parse launcher arguments left-to-right.

    Returns ``(cmd, env_overrides, toggles, passthrough)``.

    - ``cmd`` is the argv list to exec (without passthrough appended).
    - ``env_overrides`` is the set of environment variables to set/override.
    - ``toggles`` keys: ``mitm``, ``control``, ``checks``, ``change_dir``.
    - ``passthrough`` is everything after the first unknown token.
    """
    cmd: list[str] = [str(claude_binary), *CLAUDE_DEFAULT_ARGS]
    env: dict[str, str] = {}
    toggles: dict[str, bool] = {
        "mitm": False,
        "control": False,
        "checks": True,
        "change_dir": True,
    }

    i = 0
    n = len(argv)
    while i < n:
        a = argv[i]
        if a == "--droid":
            cmd = [droid_cmd]
            i += 1
        elif a == "--opencode":
            cmd = [opencode_cmd]
            i += 1
        elif a == "--npx":
            cmd = ["npx", "@anthropic-ai/claude-code", *CLAUDE_DEFAULT_ARGS]
            i += 1
        elif a == "--sandbox":
            cmd = ["docker", "sandbox", "run", *cmd]
            i += 1
        elif a == "--nix":
            cmd = ["nix", "develop", "--command", *cmd]
            i += 1
        elif a in ("--work", "--positron"):
            env["CLAUDE_CONFIG_DIR"] = str(home / ".config/claude/positron")
            i += 1
        elif a == "--personal":
            env["CLAUDE_CONFIG_DIR"] = str(home / ".config/claude/personal")
            i += 1
        elif a == "--git-ai":
            env["CLAUDE_CONFIG_DIR"] = str(home / ".config/claude/git-ai")
            i += 1
        elif a == "--local":
            cmd = [opencode_cmd, "--model", f"litellm/{DEFAULT_LITELLM_MODEL}"]
            i += 1
        elif a in ("--litellm", "--llama-cpp", "--ollama"):
            if i + 1 >= n:
                raise UsageError(f"{a} requires a model argument")
            model = validate_model_arg(argv[i + 1])
            if a == "--litellm":
                token = run_pass("litellm.vulcan.lan")
                env["ANTHROPIC_AUTH_TOKEN"] = token
                env["ANTHROPIC_BASE_URL"] = LITELLM_BASE_URL
            elif a == "--llama-cpp":
                env["ANTHROPIC_AUTH_TOKEN"] = "llama-cpp"  # noqa: S105 (sentinel, not a secret)
                env["ANTHROPIC_BASE_URL"] = LLAMA_CPP_BASE_URL
            else:  # --ollama
                env["ANTHROPIC_AUTH_TOKEN"] = "ollama"  # noqa: S105 (sentinel, not a secret)
                env["ANTHROPIC_BASE_URL"] = OLLAMA_BASE_URL
            for v in GATEWAY_ANTHROPIC_VARS:
                env[v] = model
            cmd = [*cmd, "--model", model]
            i += 2
        elif a == "--mitm":
            toggles["mitm"] = True
            i += 1
        elif a == "--control":
            toggles["control"] = True
            i += 1
        elif a == "--here":
            toggles["change_dir"] = False
            i += 1
        elif a == "--no-check":
            toggles["checks"] = False
            i += 1
        elif a in ("-h", "--help"):
            print_usage()
            sys.exit(0)
        else:
            break

    passthrough = list(argv[i:])
    return cmd, env, toggles, passthrough


# ---------------------------------------------------------------------------
# Asahi ripgrep workaround
# ---------------------------------------------------------------------------


def fix_ripgrep_for_asahi() -> None:
    """Workaround for Asahi-aarch64-16KB-page broken bundled rg.

    Hardened: path-traversal guard, race-tolerant, atomic-ish.
    No-op on every other platform.
    """
    if os.uname().machine != "aarch64":
        return
    try:
        page_size = os.sysconf("SC_PAGESIZE")
    except (ValueError, OSError):
        return
    if page_size != ASAHI_PAGE_SIZE:
        return
    npx_cache = Path.home() / ".npm/_npx"
    if not npx_cache.is_dir():
        return
    cache_root = npx_cache.resolve()
    sys_rg = shutil.which("rg")
    if not sys_rg:
        return
    sys_rg_path = Path(sys_rg).resolve()
    if not (sys_rg_path.is_absolute() and os.access(sys_rg_path, os.X_OK)):
        return
    pattern = "*/node_modules/@anthropic-ai/claude-code/vendor/ripgrep/arm64-linux/rg"
    for rg_path in sorted(npx_cache.glob(pattern)):
        try:
            resolved = rg_path.resolve(strict=True)
        except (FileNotFoundError, RuntimeError, OSError):
            continue
        try:
            resolved.relative_to(cache_root)
        except ValueError:
            continue
        if rg_path.is_symlink():
            continue
        try:
            probe = subprocess.run(
                [str(rg_path), "--version"],
                capture_output=True,
                timeout=PROBE_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            probe = None
        if probe is not None and probe.returncode == 0:
            continue
        broken = Path(str(rg_path) + ".broken")
        try:
            rg_path.rename(broken)
        except (FileNotFoundError, OSError):
            continue
        try:
            rg_path.symlink_to(sys_rg_path)
        except (FileExistsError, OSError):
            continue


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------


def _probe_version(cmd_name: str) -> str | None:
    """Return version string if found, '' if found but unparseable, None if missing."""
    if not shutil.which(cmd_name):
        return None
    try:
        result = subprocess.run(
            [cmd_name, "--version"],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    m = re.search(r"\d+\.\d+\.\d+", result.stdout or "")
    return m.group(0) if m else ""


def _check_git_wrapped() -> bool:
    if not shutil.which("whither"):
        return False
    try:
        result = subprocess.run(
            ["whither", "git"],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "git-ai" in (result.stdout or "")


def preflight_checks(claude_config_dir: Path) -> None:
    """Stderr-only diagnostics."""
    results: list[str] = []
    warnings: list[str] = []

    mem_root = claude_config_dir / "plugins/cache/thedotmack/claude-mem"
    if mem_root.is_dir():
        versions = sorted(p for p in mem_root.iterdir() if p.is_dir())
        if versions:
            results.append(f"Claude-mem {versions[-1].name}")
        else:
            warnings.append("Claude-mem plugin not found")
    else:
        warnings.append("Claude-mem plugin not found")

    coz_ver = _probe_version("cozempic")
    if coz_ver is not None:
        results.append(f"Cozempic {coz_ver or '?'}")
    else:
        warnings.append("Cozempic not found")

    gitai_ver = _probe_version("git-ai")
    if gitai_ver is not None:
        wrapped = _check_git_wrapped()
        if wrapped:
            results.append(f"git-ai {gitai_ver or '?'} (wrapping git)")
        else:
            results.append(f"git-ai {gitai_ver or '?'}")
            warnings.append("git is not wrapped by git-ai")
    else:
        warnings.append("git-ai not found")

    print("Preflight:", file=sys.stderr)
    for r in results:
        print(f"  ✓ {r}", file=sys.stderr)
    for w in warnings:
        print(f"  ✗ {w}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------


def print_usage() -> None:
    prog = Path(sys.argv[0]).name if sys.argv else "ai"
    print(
        f"""Usage: {prog} [OPTIONS] [ARGS...]

Options:
    --claude        Use Claude Code
    --droid         Use Factory Droid
    --sandbox       Use sandbox command instead of direct
    --mitm          Enable MITM proxy on localhost:9999
    --control       Enable browser control extension
    --here          Stay in current directory (don't cd to {WORK_DIR})
    --no-check      Skip preflight tool checks
    --help, -h      Show this help message

Arguments:
    All remaining arguments are passed to the underlying command

Examples:
    {prog} --mitm
    {prog} sandbox --control
    {prog} --help
"""
    )


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def _print_exec_trace(
    cmd: Sequence[str], passthrough: Sequence[str], final_env: Mapping[str, str]
) -> None:
    """Match the Bash EXEC_TRACE output format precisely.

    Bash uses ``printf '%s\\n' "ARGV: $cmd $*"`` which emits a trailing space
    between ``$cmd`` and ``$*`` even when ``$*`` is empty. We replicate that
    quirk so byte-for-byte parity holds.
    """
    pass_str = " ".join(passthrough)
    print(f"ARGV: {' '.join(cmd)} {pass_str}")
    key_re = re.compile(
        r"^(ANTHROPIC_|CLAUDE_|COLORTERM|HTTP_PROXY|HTTPS_PROXY|"
        r"NODE_TLS_REJECT_UNAUTHORIZED|EXTENSION_SECRET)"
    )
    for k in sorted(final_env):
        if not key_re.match(k):
            continue
        line = f"{k}={final_env[k]}"
        line = re.sub(r"(TOKEN|SECRET|KEY|PASSWORD)=.*", r"\1=<REDACTED>", line)
        print(line)


def main(argv: list[str]) -> int:
    home = Path.home()
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))

    cwd = Path.cwd()
    config_dirs_exist = {
        "positron": (config_root / "claude/positron").is_dir(),
        "git-ai": (config_root / "claude/git-ai").is_dir(),
        "personal": (config_root / "claude/personal").is_dir(),
    }
    context = detect_context(cwd, home, config_dirs_exist)

    change_dir = "/etc/srp" not in str(cwd)

    env_overrides: dict[str, str] = {
        "ANTHROPIC_MODEL": "sonnet",
        "COLORTERM": "truecolor",
        "CLAUDE_CODE_EFFORT_LEVEL": "high",
        "CLAUDE_CONFIG_DIR": str(home / ".claude"),
    }
    if context is Context.PERSONAL:
        env_overrides["ANTHROPIC_MODEL"] = "opus"
        env_overrides["CLAUDE_CONFIG_DIR"] = str(config_root / "claude/personal")
    elif context is Context.POSITRON:
        env_overrides["ANTHROPIC_MODEL"] = "opus"
        env_overrides["CLAUDE_CONFIG_DIR"] = str(config_root / "claude/positron")
    elif context is Context.GIT_AI:
        env_overrides["CLAUDE_CONFIG_DIR"] = str(config_root / "claude/git-ai")

    claude_binary = find_claude_binary()

    cmd, parsed_env, toggles, passthrough = parse_argv(argv, home=home, claude_binary=claude_binary)

    if not toggles["change_dir"]:
        change_dir = False
    env_overrides.update(parsed_env)

    if toggles["mitm"]:
        env_overrides["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        env_overrides["HTTP_PROXY"] = MITM_PROXY
        env_overrides["HTTPS_PROXY"] = MITM_PROXY
        print("WARNING: TLS verification disabled (--mitm)", file=sys.stderr)

    if toggles["control"]:
        env_overrides["EXTENSION_SECRET"] = run_pass("browser-control.mcp")

    if change_dir and WORK_DIR.is_dir():
        try:
            os.chdir(WORK_DIR)
        except OSError as e:
            raise AIError(f"Failed to change directory to {WORK_DIR}: {e}") from e

    fix_ripgrep_for_asahi()

    if toggles["checks"]:
        preflight_checks(Path(env_overrides["CLAUDE_CONFIG_DIR"]))

    final_env = os.environ.copy()
    final_env.update(env_overrides)

    final_argv = [*cmd, *passthrough]

    if os.environ.get("EXEC_TRACE") == "1":
        _print_exec_trace(cmd, passthrough, final_env)
        return 0

    try:
        os.execvpe(final_argv[0], final_argv, final_env)  # noqa: S606
    except FileNotFoundError as e:
        raise BackendNotFoundError(f"backend not found: {final_argv[0]}") from e
    # execvpe does not return on success
    return 0  # pragma: no cover


def _entrypoint() -> NoReturn:
    try:
        rc = main(sys.argv[1:])
        sys.exit(rc if isinstance(rc, int) else 0)
    except UsageError as e:
        print(f"Usage error: {e}", file=sys.stderr)
        sys.exit(2)
    except (ConfigError, BackendNotFoundError, AIError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    _entrypoint()
