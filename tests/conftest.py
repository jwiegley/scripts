"""pytest fixtures for ai launcher tests."""

from __future__ import annotations

import shutil as _shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    return home


@pytest.fixture
def fake_pass(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Mock subprocess.run so that calls to `pass <name>` return secrets[name].

    All other subprocess.run calls fall through to the real implementation.
    """
    secrets: dict[str, str] = {}
    real_run = subprocess.run

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if args and isinstance(args, (list, tuple)) and len(args) >= 1:
            prog = str(args[0])
            if prog == "pass" or prog.endswith("/pass"):
                name = args[1] if len(args) > 1 else ""
                if name in secrets:
                    return subprocess.CompletedProcess(list(args), 0, secrets[name] + "\n", "")
                return subprocess.CompletedProcess(list(args), 1, "", f"pass: {name}: not found")
        return real_run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    # Make `pass` resolvable via shutil.which so run_pass doesn't bail early.
    real_which = _shutil.which

    def fake_which(name, *a, **kw):  # type: ignore[no-untyped-def]
        if name == "pass":
            return "/usr/bin/pass"
        return real_which(name, *a, **kw)

    monkeypatch.setattr(_shutil, "which", fake_which)
    return secrets
