"""Behaviour of reading the kinds in .config/ianf-script-kinds.toml, and its schema agreeing."""

import json
import tomllib
from pathlib import Path
from pathlib import PurePosixPath as P

import jsonschema

from script_kinds.kinds import Kind
from script_kinds.settings import Invalid, listed

SCHEMA = json.loads(
    (Path(__file__).parent.parent / "schema" / "ianf-script-kinds.v1.json").read_text()
)


def test_each_path_gets_its_kind():
    table = {"kinds": {".husky/pre-commit": "dev", "docker/entrypoint": "server"}}
    assert listed(table) == {P(".husky/pre-commit"): Kind.DEV, P("docker/entrypoint"): Kind.SERVER}


def test_a_file_with_no_kinds_lists_none():
    assert listed({}) == {}


def test_a_kind_other_than_dev_server_or_app_is_invalid():
    assert listed({"kinds": {"x": "ci"}}) == Invalid('kinds."x" must be "dev", "server" or "app".')


def test_kinds_that_are_not_a_table_are_invalid():
    assert isinstance(listed({"kinds": ["x"]}), Invalid)


def test_a_path_outside_the_repository_is_invalid():
    assert isinstance(listed({"kinds": {"../x": "dev"}}), Invalid)
    assert isinstance(listed({"kinds": {"/x": "dev"}}), Invalid)


def test_a_path_that_is_not_written_plainly_is_invalid_as_it_would_never_match():
    assert isinstance(listed({"kinds": {"./x": "dev"}}), Invalid)
    assert isinstance(listed({"kinds": {"a//x": "dev"}}), Invalid)


def test_the_schema_accepts_what_the_reader_does():
    jsonschema.validate(
        tomllib.loads('version = 1\n[kinds]\n".husky/pre-commit" = "dev"\n'), SCHEMA
    )


def test_the_schema_rejects_an_unknown_kind_and_a_path_outside_the_repository():
    for text in ('version = 1\n[kinds]\nx = "ci"\n', 'version = 1\n[kinds]\n"../x" = "dev"\n'):
        validator = jsonschema.Draft202012Validator(SCHEMA)
        assert not validator.is_valid(tomllib.loads(text))
