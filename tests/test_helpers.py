"""The helpers: Token, pathutils, ProcessPool and ArgParser."""

import time

import pytest

from wosit import pathutils
from wosit.ArgParser import ArgParser
from wosit.Function import Variable
from wosit.ProcessPool import ProcessPool
from wosit.Token import Token


# -- Token ----------------------------------------------------------------------

def test_a_token_gives_the_date_of_its_file(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("a")

    assert Token(str(path)).getmtime() == path.stat().st_mtime


@pytest.mark.parametrize("token", [
    lambda tmp: Token(str(tmp / "missing.txt")),
    lambda tmp: Token(Variable("value")),
    lambda tmp: Token(str(tmp), phony=False),  # a directory is not a file
])
def test_a_token_has_no_date_when_it_is_not_a_file(tmp_path, token):
    assert token(tmp_path).getmtime() is None


def test_a_phony_token_has_no_date_even_if_the_file_exists(tmp_path):
    path = tmp_path / "clean"
    path.write_text("a")

    assert Token(str(path), phony=True).getmtime() is None


def test_a_token_holds_what_it_stands_for():
    token = Token("a")
    token.set("b")

    assert token.get() == "b"


# -- pathutils ------------------------------------------------------------------

def test_get_basename_takes_a_path_or_a_list():
    assert pathutils.getBasename("dir/a.txt") == "a.txt"
    assert pathutils.getBasename(["dir/a.txt", "b.txt"]) == ["a.txt", "b.txt"]


def test_list_files_gives_the_names_matching_a_wildcard(tmp_path):
    for name in ("a.txt", "b.txt", "c.log"):
        (tmp_path / name).write_text(name)

    assert sorted(pathutils.listFiles(str(tmp_path / "*.txt"))) == ["a.txt", "b.txt"]


# -- ProcessPool ----------------------------------------------------------------

def _double(value):
    return value * 2


def _sleep(seconds):
    time.sleep(seconds)
    return seconds


def test_a_pool_has_at_least_one_process():
    with pytest.raises(ValueError, match='Argument "processes" must be equal or higher than 1.'):
        ProcessPool(0)


def test_a_pool_returns_the_results_in_order():
    with ProcessPool(processes=2) as pool:
        assert pool.map(_double, [1, 2, 3, 4]) == [2, 4, 6, 8]


def test_a_pool_runs_as_many_processes_at_once_as_it_is_given():
    start = time.time()
    with ProcessPool(processes=4) as pool:
        pool.map(_sleep, [0.5] * 4)
    assert time.time() - start < 1.5

    start = time.time()
    with ProcessPool(processes=1) as pool:
        pool.map(_sleep, [0.3] * 3)
    assert time.time() - start >= 0.9


# -- ArgParser ------------------------------------------------------------------

def test_arg_parser_splits_targets_and_assignments(monkeypatch):
    monkeypatch.setattr("sys.argv", ["wosit", "all", "clean", "MODE=debug", "-ignored"])

    parser = ArgParser()

    assert parser.getTargets() == ["all", "clean"]
    assert parser.getArgs() == {"MODE": "debug"}
    assert parser.getArg("MODE") == "debug"
    assert parser.getArg("missing") is None


@pytest.mark.parametrize("argv, message", [
    (["all", "all"], 'Target "all" already in list.'),
    (["A=1", "A=2"], 'Argument "A" already defined.'),
])
def test_arg_parser_refuses_twice_the_same(monkeypatch, argv, message):
    monkeypatch.setattr("sys.argv", ["wosit"] + argv)

    with pytest.raises(ValueError, match=message):
        ArgParser()
