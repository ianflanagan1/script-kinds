"""`script-kinds check [<path>...]`: every script has one kind, and each shell script its kind's
shebang."""

import argparse
from pathlib import Path

from cli_kit import cli
from cli_kit.outcome import Failure, NothingToDo

from script_kinds import kinds, repo


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "check",
        help="fail unless every script has one kind, and each shell script its kind's shebang",
        description=(
            "A script is a file git tracks, or would, that starts with #!, is executable or ends\n"
            "in a shell suffix. Under scripts/dev/ it's dev tooling and a shell script starts\n"
            f"with {kinds.shebang(kinds.Kind.DEV)}; under scripts/server/ it's a server script"
            f" and starts\nwith {kinds.shebang(kinds.Kind.SERVER)}. A script a tool needs"
            f" elsewhere takes its kind from\n{kinds.SETTINGS_FILE}.\n\n"
            "With paths, checks only the scripts among them, as lint-file does; without, the\n"
            "whole repository, and the settings' paths too."
        ),
    )
    parser.add_argument("paths", nargs="*", metavar="<path>", help="default: the whole repository")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> NothingToDo:
    here = Path.cwd()
    top = repo.root(here)
    found = kinds.problems(repo.files(here, top, args.paths), repo.listed(top), not args.paths)
    if found:
        raise Failure("Some scripts have no kind, or the wrong shebang.", *map(kinds.fix, found))
    return NothingToDo("Every script has its kind and shebang.")
