"""The examples of the README, run as the buildconfig.py they are."""

import re

import pytest

from conftest import PROJECT_ROOT


def _readme_examples():
    text = (PROJECT_ROOT / "README.md").read_text()
    return re.findall(r"```python\n(.*?)```", text, re.S)


def _example(fragment):
    found = [code for code in _readme_examples() if fragment in code]
    assert len(found) == 1, "no single README example holds {!r}".format(fragment)
    return found[0]


def test_every_readme_example_is_tested():
    assert len(_readme_examples()) == 3


def test_basic_example_runs_the_generated_rules_in_order(buildconfig, wosit):
    root = buildconfig(_example("def genMyRules"))

    result = wosit(cwd=root)

    assert result.returncode == 0, result.stderr
    printed = [line for line in result.lines if not line.startswith("echo ")]
    assert printed == ["This is a rule with id {}".format(i) for i in range(10)]


def test_basic_example_lists_its_targets(buildconfig, wosit):
    root = buildconfig(_example("def genMyRules"))

    result = wosit("-l", cwd=root)

    assert result.lines == ["rule_{}".format(i) for i in range(10)] + ["all", "clean"]


@pytest.mark.parametrize("build_ok, expected", [
    (True, ["built"]),
    (False, ["Build failed", "logs collected"]),
])
def test_on_failure_example_falls_back_when_the_build_fails(buildconfig, wosit, build_ok, expected):
    root = buildconfig(_example("on_failure_command"), files={
        "build.py": "print('built')\n" + ("" if build_ok else "raise SystemExit(1)\n"),
        "collect_logs.py": "print('logs collected')\n",
    })

    result = wosit("build", cwd=root)

    assert result.returncode == 0, result.stderr
    printed = [line for line in result.lines if not line.startswith(("python3 ", "echo "))]
    if not build_ok:
        expected = ["built"] + expected
    assert printed == expected


def test_functions_example_calls_print(buildconfig, wosit):
    root = buildconfig(_example("Function(print"))

    result = wosit(cwd=root)

    assert result.returncode == 0, result.stderr
    assert "This is rule 0." in result.lines
    assert "This is rule 1." in result.lines
