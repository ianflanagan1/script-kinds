"""`script-kinds <command> ...`: which kind each script is, dev tooling or server, by where it
runs."""

import sys

from cli_kit import cli

from script_kinds.commands import check

COMMANDS = [check]


def main(argv: list[str] | None = None) -> int:
    return cli.run(
        "script-kinds",
        "Which kind each script is, dev tooling or server, by where it runs.",
        COMMANDS,
        sys.argv[1:] if argv is None else argv,
    )


if __name__ == "__main__":
    sys.exit(main())
