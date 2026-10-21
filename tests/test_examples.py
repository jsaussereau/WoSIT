"""The examples of the repository, built with the wosit command as their buildconfig says."""

import shutil
import time

import pytest

from conftest import age


def test_paths_runs_the_rule_in_its_path(example, wosit):
    root = example("paths")

    result = wosit("all", cwd=root)

    assert result.returncode == 0, result.stderr
    assert (root / "d1" / "t1.txt").read_text().strip() == "This is target 1."
    assert (root / "t2.txt").read_text().strip() == "This is target 2."
    # "cat s1.txt" found it: the command of the rule ran in d1
    assert "This is source 1." in result.lines


def test_paths_builds_nothing_when_up_to_date(example, wosit):
    root = example("paths")
    assert wosit("all", cwd=root).returncode == 0

    result = wosit("all", cwd=root)

    assert result.returncode == 0, result.stderr
    assert result.lines == []


def test_path_symbols_writes_the_symbols_from_the_path(example, wosit):
    root = example("path_symbols")

    result = wosit("all", "-j", "2", cwd=root)

    assert result.returncode == 0, result.stderr
    assert "tr a-z A-Z < alpha.txt > alpha.up" in result.lines
    assert "tr a-z A-Z < beta.txt > beta.up" in result.lines
    assert "cat ../include/header.txt alpha.up beta.up > joined.txt" in result.lines
    assert "cp src/joined.txt result.txt" in result.lines
    assert (root / "result.txt").read_text().split() == ["header", "ALPHA", "BETA"]


def test_path_symbols_builds_a_pattern_target_once(example, wosit):
    # src/alpha.up is needed by joined.txt and, spelled ./src/alpha.up, by result.txt
    root = example("path_symbols")

    result = wosit("all", cwd=root)

    assert result.lines.count("tr a-z A-Z < alpha.txt > alpha.up") == 1


def test_path_symbols_rebuilds_only_what_a_change_reaches(example, wosit):
    root = example("path_symbols")
    assert wosit("all", cwd=root).returncode == 0
    built = [root / "src" / name for name in ("alpha.up", "beta.up", "joined.txt")] + [root / "result.txt"]
    age(*[root / "src" / "alpha.txt", root / "src" / "beta.txt", root / "include" / "header.txt"], seconds=200)
    age(*built)
    (root / "src" / "beta.txt").write_text("gamma\n")

    result = wosit("all", cwd=root)

    assert result.returncode == 0, result.stderr
    assert result.lines == [
        "tr a-z A-Z < beta.txt > beta.up",
        "cat ../include/header.txt alpha.up beta.up > joined.txt",
        "cp src/joined.txt result.txt",
    ]
    assert (root / "result.txt").read_text().split() == ["header", "ALPHA", "GAMMA"]


def test_path_symbols_clean_removes_what_all_built(example, wosit):
    root = example("path_symbols")
    assert wosit("all", cwd=root).returncode == 0

    assert wosit("clean", cwd=root).returncode == 0

    assert sorted(p.name for p in (root / "src").iterdir()) == ["alpha.txt", "beta.txt"]
    assert not (root / "result.txt").exists()


def test_on_failure_runs_the_fallback_and_succeeds(example, wosit):
    result = wosit(cwd=example("on_failure"))

    assert result.returncode == 0, result.stderr
    assert "Fallback executed due to failure" in result.lines


def test_on_failure_fails_without_a_fallback(example, wosit):
    result = wosit("fail", cwd=example("on_failure"))

    assert result.returncode != 0
    assert "The execution of a task failed." in result.stderr


def test_callables_pass_a_returned_value_to_the_next_rule(example, wosit):
    result = wosit(cwd=example("callables"))

    assert result.returncode == 0, result.stderr
    printed = [line for line in result.lines if not line.endswith(")")]
    assert printed == [
        "Also works with class methods!",
        "This function",
        "returns something",
        # Set by "returnvalue" in its own process, read by "all"
        "This is a returned value",
    ]


def test_parallel_runs_the_rules_at_once(example, wosit):
    start = time.time()

    result = wosit("-j", "40", cwd=example("parallel"))

    assert result.returncode == 0, result.stderr
    assert result.lines[-1] == "Finished everything else!!!!"
    # 40 rules sleeping 1 s each
    assert time.time() - start < 20


@pytest.mark.skipif(shutil.which("g++") is None, reason="needs g++")
def test_cpp_compiles_links_and_runs(example, wosit):
    root = example("C++")

    result = wosit("run", cwd=root)

    assert result.returncode == 0, result.stderr
    assert "Seems like working great!" in result.lines
    assert sorted(p.name for p in (root / "obj").iterdir()) == ["main.o", "toinclude.o"]

    assert wosit("clean", cwd=root).returncode == 0
    assert list((root / "obj").iterdir()) == []
