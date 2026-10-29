"""Reading a repository's files and settings, for the core in kinds."""

import stat
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import assert_never

import repo_settings
from cli_kit import proc
from cli_kit.outcome import Precondition
from repo_settings import Missing, Settings, Source, Unlocatable

from script_kinds import settings
from script_kinds.kinds import File, Kind
from script_kinds.settings import Version

SHEBANG_BYTES = 256


def root(directory: Path) -> Path:
    """The root of the worktree directory is in."""
    if not proc.succeeds("git", "-C", str(directory), "rev-parse", "--show-toplevel"):
        raise Precondition(f"Not in a git repository: {directory}")
    return Path(proc.output("git", "-C", str(directory), "rev-parse", "--show-toplevel"))


def files(here: Path, top: Path, pathspecs: Sequence[str]) -> list[File]:
    """The files in the worktree at top that git tracks or would, among pathspecs when given,
    which are read from here. Ignored files, symlinks and files deleted from the worktree aren't
    among them."""
    listing = proc.output(
        "git", "-C", str(here), "ls-files", "-z", "--full-name", "--cached", "--others",
        "--exclude-standard", "--", *pathspecs,
    )  # fmt: skip
    found = []
    for name in sorted(set(filter(None, listing.split("\0")))):
        file = _read(top, PurePosixPath(name))
        if file is not None:
            found.append(file)
    return found


def listed(top: Path) -> dict[PurePosixPath, Kind]:
    """The kinds the worktree's own settings give, so a branch can change them."""
    read = repo_settings.read(Source.LOCAL_THIS_WORKTREE, top, settings.PURPOSE, Version)
    match read:
        case Settings():
            pass
        case Missing():
            return {}
        case Unlocatable() | repo_settings.Invalid():
            raise Precondition(read.message, *read.details)
        case _:
            assert_never(read)
    match read.version:
        case Version.V1:
            kinds = settings.listed(read.table)
        case _:
            assert_never(read.version)
    if isinstance(kinds, settings.Invalid):
        raise Precondition(kinds.message, f"In {read.where}.")
    return kinds


def _read(top: Path, path: PurePosixPath) -> File | None:
    full = top / path
    try:
        mode = full.lstat().st_mode
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(mode):
        return None
    with full.open("rb") as stream:
        head = stream.read(SHEBANG_BYTES)
    line = head.split(b"\n", 1)[0].decode(errors="replace").rstrip() if head[:2] == b"#!" else None
    return File(path, line, bool(mode & 0o111))
