"""The repository's .config/ianf-script-kinds.toml: the kind of each script a tool requires
outside scripts/dev/ and scripts/server/, and of each of the application's own entry points."""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import PurePosixPath
from typing import final

from script_kinds.kinds import Kind

PURPOSE = "script-kinds"


class Version(IntEnum):
    """The versions of ianf-script-kinds.toml's format script-kinds reads."""

    V1 = 1


@final
@dataclass(frozen=True)
class Invalid:
    message: str


def listed(table: dict[str, object]) -> dict[PurePosixPath, Kind] | Invalid:
    """The kinds in version 1 of the file, by path from the repository's root."""
    kinds = table.get("kinds", {})
    if not isinstance(kinds, dict):
        return Invalid("kinds must be a table of paths, each with its kind.")
    found: dict[PurePosixPath, Kind] = {}
    for path, kind in kinds.items():
        if kind not in Kind:
            return Invalid(f'kinds."{path}" must be "dev", "server" or "app".')
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts or str(relative) != path:
            return Invalid(f'kinds."{path}" must be a plain path from the repository\'s root.')
        found[relative] = Kind(kind)
    return found
