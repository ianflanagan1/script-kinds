"""The script-kinds command that uv installs into .venv/bin, run against real throwaway
repositories."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BIN = Path(sys.prefix) / "bin" / "script-kinds"


def git(*args: str | Path) -> None:
    subprocess.run(["git", *map(str, args)], check=True, capture_output=True)


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("NO_COLOR", "1")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    git("init", "--quiet", "--initial-branch", "main", repo)
    return repo


def write(repo: Path, path: str, text: str, executable: bool) -> Path:
    full = repo / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(text)
    full.chmod(0o755 if executable else 0o644)
    return full


def launch(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BIN, *args], capture_output=True, text=True, cwd=cwd, env=os.environ.copy()
    )


def test_a_repository_whose_scripts_all_have_their_kinds_passes(repo: Path):
    write(repo, "scripts/dev/lint.sh", "#!/usr/bin/env bash\n", True)
    write(repo, "scripts/server/entrypoint", "#!/bin/sh\n", True)
    write(repo, "src/app.py", "print()\n", False)
    result = launch("check", cwd=repo)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        "➖ Every script has its kind and shebang.\n",
        "",
    )


def test_a_script_outside_both_trees_fails_with_how_to_fix_it(repo: Path):
    write(repo, "tools/lint.sh", "#!/usr/bin/env bash\n", True)
    result = launch("check", cwd=repo)
    assert (result.returncode, result.stdout) == (1, "")
    assert result.stderr.splitlines()[:2] == [
        "❌ Check failed.",
        "Some scripts have no kind, or the wrong shebang.",
    ]
    assert result.stderr.splitlines()[2].startswith("tools/lint.sh: move it under scripts/dev/")


def test_untracked_scripts_are_checked_but_ignored_ones_are_not(repo: Path):
    write(repo, ".gitignore", "build/\n", False)
    write(repo, "build/generated.sh", "", False)
    write(repo, "new.sh", "#!/bin/sh\n", False)
    result = launch("check", cwd=repo)
    assert "new.sh:" in result.stderr
    assert "build/" not in result.stderr


def test_the_settings_give_a_kind_to_a_script_a_tool_needs_elsewhere(repo: Path):
    write(repo, ".husky/pre-commit", "#!/usr/bin/env bash\n", True)
    write(
        repo,
        ".config/ianf-script-kinds.toml",
        'version = 1\n\n[kinds]\n".husky/pre-commit" = "dev"\n',
        False,
    )
    assert launch("check", cwd=repo).returncode == 0


def test_given_paths_only_the_scripts_among_them_are_checked(repo: Path):
    write(repo, "tools/old.sh", "#!/bin/sh\n", True)
    write(repo, "scripts/dev/new.sh", "#!/usr/bin/env bash\n", True)
    assert launch("check", "scripts/dev/new.sh", cwd=repo).returncode == 0


def test_given_paths_are_read_from_the_directory_it_runs_in(repo: Path):
    write(repo, "app/scripts/server/run", "#!/usr/bin/env bash\n", True)
    result = launch("check", "scripts/server/run", cwd=repo / "app")
    assert "app/scripts/server/run: start it with #!/bin/sh" in result.stderr


def test_invalid_settings_stop_it_before_checking(repo: Path):
    write(repo, ".config/ianf-script-kinds.toml", 'version = 1\n[kinds]\nx = "ci"\n', False)
    result = launch("check", cwd=repo)
    assert result.returncode == 1
    assert result.stderr.startswith('⚠️ kinds."x" must be "dev", "server" or "app".\n')


def test_outside_a_repository_it_says_so(tmp_path: Path):
    result = launch("check", cwd=tmp_path)
    assert result.returncode == 1
    assert result.stderr.startswith("⚠️ Not in a git repository:")
