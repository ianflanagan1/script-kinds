"""Which kind each script in a repository is, by where it runs, and what's wrong with where it is.

A script is a file that starts with a shebang, has an executable bit, or ends in a shell suffix.
Its kind comes from its path: under a `scripts/dev/` directory it's dev tooling, run on a
developer's machine or in CI; under `scripts/server/` it's a server script, run on the target
host or image. A script a tool requires elsewhere, such as a hook framework's, takes its kind
from the repository's settings, as does the application's own entry point, such as a framework's
console, which isn't a script at all. Every script has exactly one kind, and every shell script
starts with its kind's shebang.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import assert_never, final

TREE = "scripts"
SHELL_SUFFIXES = (".sh", ".bash", ".dash", ".ksh", ".zsh")
SHELLS = ("sh", "bash", "dash", "ash", "ksh", "mksh", "zsh")
SETTINGS_FILE = ".config/ianf-script-kinds.toml"


class Kind(StrEnum):
    DEV = "dev"
    SERVER = "server"
    APP = "app"
    """The application's own entry point, such as a framework's console: its language's rules
    apply, not a script kind's. Only the settings give it, as there's no tree for it."""


TREES = (Kind.DEV, Kind.SERVER)


def shebang(kind: Kind) -> str | None:
    """The shebang every shell script of kind starts with, or None when kind sets none."""
    match kind:
        case Kind.DEV:
            # devbox's bash, not macOS's bash 3.2
            return "#!/usr/bin/env bash"
        case Kind.SERVER:
            # POSIX sh, as minimal images such as Alpine's have no bash
            return "#!/bin/sh"
        case Kind.APP:
            return None
        case _:
            assert_never(kind)


@final
@dataclass(frozen=True)
class File:
    """What a tracked or untracked file says about whether it's a script."""

    path: PurePosixPath
    """From the repository's root."""
    shebang: str | None
    """Its first line, when that starts with #!."""
    executable: bool


@final
@dataclass(frozen=True)
class Unplaced:
    """A script outside both trees that the settings don't give a kind."""

    path: PurePosixPath


@final
@dataclass(frozen=True)
class Contradicted:
    """A script the settings give a different kind from its tree's."""

    path: PurePosixPath
    tree: Kind
    listed: Kind


@final
@dataclass(frozen=True)
class WrongShebang:
    """A shell script that doesn't start with its kind's shebang."""

    path: PurePosixPath
    kind: Kind
    found: str | None


@final
@dataclass(frozen=True)
class Stale:
    """A path the settings give a kind that isn't a script in the repository."""

    path: PurePosixPath


type Problem = Unplaced | Contradicted | WrongShebang | Stale


def is_script(file: File) -> bool:
    return file.shebang is not None or file.executable or file.path.suffix in SHELL_SUFFIXES


def is_shell(file: File) -> bool:
    return file.path.suffix in SHELL_SUFFIXES or interpreter(file.shebang) in SHELLS


def interpreter(line: str | None) -> str | None:
    """The program a shebang line runs, by name: `bash` for `#!/usr/bin/env bash`."""
    if line is None:
        return None
    words = line.removeprefix("#!").split()
    if words and PurePosixPath(words[0]).name == "env":
        words = [word for word in words[1:] if not word.startswith("-")]
    return PurePosixPath(words[0]).name if words else None


def tree_kind(path: PurePosixPath) -> Kind | None:
    """The kind of the innermost scripts/dev/ or scripts/server/ directory path is under."""
    found = None
    folders = path.parts[:-1]
    for parent, child in zip(folders, folders[1:], strict=False):
        if parent == TREE and child in TREES:
            found = Kind(child)
    return found


def problems(
    files: Sequence[File], listed: Mapping[PurePosixPath, Kind], every_file: bool
) -> list[Problem]:
    """What's wrong with the scripts among files, given the kinds the settings list.

    With every_file, files are the whole repository, so a listed path that isn't among its
    scripts is stale; otherwise they're some of it, such as the files an editor just changed.
    """
    scripts = [file for file in files if is_script(file)]
    found: list[Problem] = []
    for file in scripts:
        tree = tree_kind(file.path)
        named = listed.get(file.path)
        if tree is not None and named is not None and named != tree:
            found.append(Contradicted(file.path, tree, named))
            continue
        kind = tree or named
        if kind is None:
            found.append(Unplaced(file.path))
        elif is_shell(file) and (wanted := shebang(kind)) and file.shebang != wanted:
            found.append(WrongShebang(file.path, kind, file.shebang))
    if every_file:
        paths = {file.path for file in scripts}
        found.extend(Stale(path) for path in sorted(listed) if path not in paths)
    return found


def fix(problem: Problem) -> str:
    """How to fix problem, for a person to read."""
    match problem:
        case Unplaced(path):
            return (
                f"{path}: move it under {TREE}/dev/ if it runs on a developer's machine or in CI,"
                f" or {TREE}/server/ if it runs on the target host; if a tool needs it where it"
                f" is, or it's the application's own entry point, give it a kind in"
                f" {SETTINGS_FILE}."
            )
        case Contradicted(path, tree, listed):
            return (
                f"{path}: remove it from {SETTINGS_FILE}, which says {listed}; it's under"
                f" {TREE}/{tree}/, which says {tree}."
            )
        case WrongShebang(path, kind, found):
            starts = f"it starts with {found}" if found else "it has no shebang"
            return f"{path}: start it with {shebang(kind)}, as a {kind} shell script; {starts}."
        case Stale(path):
            return f"{SETTINGS_FILE}: remove {path}, which isn't a script here."
        case _:
            assert_never(problem)
