# script-kinds

`devbox run check` runs ruff and the tests; run it before finishing. `devbox run lint-file <files>` formats and fixes the Python files given.

The decisions are in `kinds.py` and `settings.py`, pure functions of plain values; keep git and the filesystem out of them, and test them with plain values. `repo.py` and the command are the shell, covered by tests against real throwaway repositories in `tests/test_entry_point.py`.
