"""The wosit command: which buildconfig, which targets, how many at once."""

import time


RULES = """
from wosit.builder import addRule, Function, Variable

addRule("all", "b", "echo all >> log")
addRule("b", command="echo b >> log")
addRule("other", command="echo other >> log")
"""


def _log(root):
    path = root / "log"
    return path.read_text().split() if path.exists() else []


def test_builds_all_by_default(buildconfig, wosit):
    root = buildconfig(RULES)

    result = wosit(cwd=root)

    assert result.returncode == 0, result.stderr
    assert _log(root) == ["b", "all"]


def test_builds_the_targets_it_is_given_in_order(buildconfig, wosit):
    root = buildconfig(RULES)

    assert wosit("other", "b", cwd=root).returncode == 0

    assert _log(root) == ["other", "b"]


def test_lists_the_targets(buildconfig, wosit):
    result = wosit("--list", cwd=buildconfig(RULES))

    assert result.returncode == 0, result.stderr
    assert result.lines == ["all", "b", "other"]


def test_reads_another_buildconfig(tmp_path, wosit):
    (tmp_path / "rules.py").write_text(RULES)

    assert wosit("-f", "rules.py", "other", cwd=tmp_path).returncode == 0

    assert _log(tmp_path) == ["other"]


def test_runs_in_another_directory(buildconfig, wosit, tmp_path_factory):
    root = buildconfig(RULES)

    assert wosit("-C", str(root), "b", cwd=tmp_path_factory.mktemp("elsewhere")).returncode == 0

    assert _log(root) == ["b"]


def test_fails_without_a_buildconfig(tmp_path, wosit):
    assert wosit("-f", "missing.py", cwd=tmp_path).returncode != 0


def test_fails_when_a_rule_fails(buildconfig, wosit):
    root = buildconfig("""
        from wosit.builder import addRule
        addRule("all", command="false")
    """)

    result = wosit(cwd=root)

    assert result.returncode != 0
    assert "The execution of a task failed." in result.stderr


def test_jobs_run_the_independent_rules_at_once(buildconfig, wosit):
    root = buildconfig("""
        from wosit.builder import addRule
        addRule("all", ["a", "b", "c", "d"], phony=True)
        for name in "abcd":
            addRule(name, command="sleep 1")
    """)

    start = time.time()
    assert wosit("-j", "4", cwd=root).returncode == 0
    assert time.time() - start < 3.5


def test_the_buildconfig_can_import_its_neighbours(buildconfig, wosit):
    root = buildconfig("""
        from wosit.builder import addRule
        import rules_helper
        addRule("all", command=rules_helper.COMMAND)
    """, files={"rules_helper.py": "COMMAND = 'echo helped > log'\n"})

    assert wosit(cwd=root).returncode == 0

    assert _log(root) == ["helped"]
