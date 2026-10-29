# script-kinds

Fails a repository's check unless every script is one of two kinds, by where it runs, so review guidance and linters can tell which rules apply to it:

| Kind | Runs | Lives under | A shell script starts with |
|---|---|---|---|
| dev | on a developer's machine or in CI, under devbox | `scripts/dev/` | `#!/usr/bin/env bash` |
| server | on the target host or image, unattended | `scripts/server/` | `#!/bin/sh` |

```
$ script-kinds check
❌ Check failed.
Some scripts have no kind, or the wrong shebang.
tools/lint.sh: move it under scripts/dev/ if it runs on a developer's machine or in CI, or scripts/server/ if it runs on the target host; if a tool needs it where it is, give it a kind in .config/ianf-script-kinds.toml.
```

Runs on macOS and Linux. Built on [cli-kit](https://github.com/ianflanagan1/cli-kit).

## Why by where it runs

The two kinds need different rules because their environments differ. Dev tooling gets devbox's pinned tools, and a developer sees it fail and reruns it. A server script gets only what ships in the image, runs unattended, often as root and against production data, so it must be POSIX, idempotent and non-interactive. A script that *performs* a deploy from CI is dev tooling; one that runs *on* the server, such as an entrypoint or a migration runner, is a server script.

The kind is in the path, not in a comment in the file, because a path can't be left out or go stale, and every tool already matches on paths: Claude Code loads the matching rules file by its `paths:`, and a project's `lint-file` can `case` on it. Ship `scripts/server/` into the image whole, and nothing else from `scripts/`, so a server script filed anywhere else can't run on the server.

## What it checks

A script is a file git tracks, or would (ignored files aren't), that starts with `#!`, has an executable bit, or ends in `.sh`, `.bash`, `.dash`, `.ksh` or `.zsh`. The application's own entry point, such as Symfony's `bin/console` or Laravel's `artisan`, looks like one but is application code, which its language's rules cover: list it in the settings as `app`.

- Each script is under a `scripts/dev/` or `scripts/server/` directory, at any depth, so each app in a monorepo can have its own; the innermost one counts.
- A script a tool requires somewhere else, such as a hook framework's, takes its kind from `.config/ianf-script-kinds.toml`. It's never left without one.
- A shell script, by its suffix or its shebang, starts with its kind's shebang, sourced ones too, so ShellCheck checks it in that dialect. A script in another language keeps its own.
- With no paths, every listed path in the settings is a script, so the list can't go stale.

## The settings

`.config/ianf-script-kinds.toml`, read from the worktree you're in, as [repo-settings](../repo-settings) describes. Leave it out when every script is in a tree.

```toml
#:schema https://raw.githubusercontent.com/ianflanagan1/script-kinds/main/schema/ianf-script-kinds.v1.json
version = 1

# Scripts a tool needs outside scripts/dev/ and scripts/server/, each with its kind, and the
# application's own entry points.
[kinds]
".husky/pre-commit" = "dev"
"bin/console" = "app"
```

Paths are from the repository's root, and must be scripts there. A path under a tree must not contradict it. An `app` entry point needs no particular shebang.

## In a project

`check` runs it on the whole repository, and `lint-file` on the files it's given:

```json
"check": "script-kinds check && …",
"lint-file": "script-kinds check \"$@\" && …"
```

With paths, it checks only the scripts among them, read from the directory it runs in, and skips the settings' staleness check.

## Setup

```sh
cd ~/projects/cli/script-kinds
devbox run setup   # uv sync, then links script-kinds into ~/.local/bin
```

## Development

```sh
devbox run check   # ruff, then pytest
```

## License

MIT
