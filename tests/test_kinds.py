"""Behaviour of telling each script's kind, and what's wrong with where it is."""

from pathlib import PurePosixPath as P

from script_kinds.kinds import (
    Contradicted,
    File,
    Kind,
    Stale,
    Unplaced,
    WrongShebang,
    fix,
    interpreter,
    is_script,
    problems,
    tree_kind,
)

BASH = "#!/usr/bin/env bash"
SH = "#!/bin/sh"


def file(path: str, shebang: str | None, executable: bool) -> File:
    return File(P(path), shebang, executable)


# --- What counts as a script


def test_a_file_starting_with_a_shebang_is_a_script():
    assert is_script(file("tools/run", "#!/usr/bin/env php", False))


def test_an_executable_file_is_a_script():
    assert is_script(file("tools/run", None, True))


def test_a_file_ending_in_a_shell_suffix_is_a_script():
    assert is_script(file("lib/common.bash", None, False))


def test_a_plain_source_file_is_not_a_script():
    assert not is_script(file("src/App.php", None, False))


# --- Kind from the tree


def test_under_scripts_dev_a_script_is_dev_tooling():
    assert tree_kind(P("scripts/dev/lint.sh")) == Kind.DEV


def test_under_scripts_server_a_script_is_a_server_script():
    assert tree_kind(P("scripts/server/entrypoint.sh")) == Kind.SERVER


def test_the_trees_count_at_any_depth_so_each_app_in_a_monorepo_has_its_own():
    assert tree_kind(P("apps/api/scripts/server/migrate.sh")) == Kind.SERVER


def test_a_script_in_a_folder_under_a_tree_has_the_trees_kind():
    assert tree_kind(P("scripts/dev/hooks/pre-commit")) == Kind.DEV


def test_a_script_directly_in_scripts_has_no_kind():
    assert tree_kind(P("scripts/lint.sh")) is None


def test_a_file_named_like_a_kind_is_not_a_tree():
    assert tree_kind(P("scripts/dev")) is None


# --- Which program a shebang runs


def test_a_shebang_runs_the_program_it_names():
    assert interpreter("#!/bin/sh") == "sh"


def test_a_shebang_through_env_runs_the_program_env_finds():
    assert interpreter("#!/usr/bin/env -S bash -e") == "bash"


def test_no_shebang_runs_nothing():
    assert interpreter(None) is None


# --- Problems


def test_scripts_in_their_trees_with_their_kinds_shebangs_have_no_problems():
    files = [file("scripts/dev/lint.sh", BASH, True), file("scripts/server/run", SH, True)]
    assert problems(files, {}, True) == []


def test_a_script_outside_both_trees_is_unplaced():
    assert problems([file("tools/lint.sh", BASH, True)], {}, True) == [Unplaced(P("tools/lint.sh"))]


def test_files_that_are_not_scripts_are_not_checked():
    assert problems([file("src/App.php", None, False)], {}, True) == []


def test_a_script_outside_both_trees_takes_its_kind_from_the_settings():
    listed = {P(".husky/pre-commit"): Kind.DEV}
    assert problems([file(".husky/pre-commit", BASH, True)], listed, True) == []


def test_settings_that_contradict_a_scripts_tree_are_a_problem():
    listed = {P("scripts/dev/lint.sh"): Kind.SERVER}
    found = problems([file("scripts/dev/lint.sh", BASH, True)], listed, True)
    assert found == [Contradicted(P("scripts/dev/lint.sh"), Kind.DEV, Kind.SERVER)]


def test_settings_that_agree_with_a_scripts_tree_are_no_problem():
    listed = {P("scripts/dev/lint.sh"): Kind.DEV}
    assert problems([file("scripts/dev/lint.sh", BASH, True)], listed, True) == []


def test_a_dev_shell_script_must_start_with_envs_bash():
    found = problems([file("scripts/dev/lint.sh", SH, True)], {}, True)
    assert found == [WrongShebang(P("scripts/dev/lint.sh"), Kind.DEV, SH)]


def test_a_server_shell_script_must_start_with_bin_sh():
    found = problems([file("scripts/server/run", BASH, True)], {}, True)
    assert found == [WrongShebang(P("scripts/server/run"), Kind.SERVER, BASH)]


def test_a_shell_script_sourced_by_others_still_needs_its_kinds_shebang():
    found = problems([file("scripts/server/lib.sh", None, False)], {}, True)
    assert found == [WrongShebang(P("scripts/server/lib.sh"), Kind.SERVER, None)]


def test_a_script_in_another_language_keeps_its_own_shebang():
    php = file("scripts/server/warm-cache", "#!/usr/bin/env php", True)
    assert problems([php], {}, True) == []


def test_the_applications_own_entry_point_is_listed_as_app_and_keeps_its_own_shebang():
    console = file("bin/console", "#!/usr/bin/env php", True)
    assert problems([console], {P("bin/console"): Kind.APP}, True) == []


def test_an_app_entry_point_in_a_shell_needs_no_particular_shebang():
    assert problems([file("bin/run.sh", SH, True)], {P("bin/run.sh"): Kind.APP}, True) == []


def test_there_is_no_tree_for_app_entry_points():
    assert tree_kind(P("scripts/app/console")) is None


def test_a_listed_path_that_is_not_a_script_is_stale_when_the_whole_repository_is_checked():
    listed = {P("gone/hook"): Kind.DEV}
    assert problems([], listed, True) == [Stale(P("gone/hook"))]


def test_listed_paths_are_not_stale_when_only_some_files_are_checked():
    assert problems([], {P("gone/hook"): Kind.DEV}, False) == []


# --- Saying how to fix each


def test_an_unplaced_script_is_told_where_each_kind_goes():
    assert fix(Unplaced(P("tools/x.sh"))) == (
        "tools/x.sh: move it under scripts/dev/ if it runs on a developer's machine or in CI,"
        " or scripts/server/ if it runs on the target host; if a tool needs it where it is,"
        " or it's the application's own entry point, give it a kind in"
        " .config/ianf-script-kinds.toml."
    )


def test_a_wrong_shebang_is_told_the_right_one():
    assert fix(WrongShebang(P("scripts/server/run"), Kind.SERVER, BASH)) == (
        "scripts/server/run: start it with #!/bin/sh, as a server shell script;"
        " it starts with #!/usr/bin/env bash."
    )


def test_a_missing_shebang_is_told_the_right_one():
    assert fix(WrongShebang(P("scripts/dev/lib.sh"), Kind.DEV, None)) == (
        "scripts/dev/lib.sh: start it with #!/usr/bin/env bash, as a dev shell script;"
        " it has no shebang."
    )


def test_contradicting_settings_are_told_to_go():
    assert fix(Contradicted(P("scripts/dev/x"), Kind.DEV, Kind.SERVER)) == (
        "scripts/dev/x: remove it from .config/ianf-script-kinds.toml, which says server;"
        " it's under scripts/dev/, which says dev."
    )


def test_a_stale_listing_is_told_to_go():
    assert fix(Stale(P("gone/hook"))) == (
        ".config/ianf-script-kinds.toml: remove gone/hook, which isn't a script here."
    )
