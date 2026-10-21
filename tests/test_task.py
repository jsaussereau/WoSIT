"""Task: when it needs an update, its stages, and how it runs its commands."""

import pytest

from wosit.Function import Function, Variable
from wosit.Task import Task
from wosit.Token import Token
from conftest import age


def _file(tmp_path, name, text="x"):
    path = tmp_path / name
    path.write_text(text)
    return path


def _task(target, sources=(), **kwargs):
    return Task(Token(str(target)), sources=list(sources), **kwargs)


def test_needs_an_update_when_the_target_is_missing(tmp_path):
    assert _task(tmp_path / "missing").needsUpdate() is True


def test_needs_an_update_when_a_source_is_newer(tmp_path):
    source, target = _file(tmp_path, "a.c"), _file(tmp_path, "a.o")
    age(target)

    assert _task(target, [Token(str(source))]).needsUpdate() is True


def test_is_up_to_date_when_the_target_is_newer(tmp_path):
    source, target = _file(tmp_path, "a.c"), _file(tmp_path, "a.o")
    age(source)

    assert _task(target, [Token(str(source))]).needsUpdate() is False


def test_needs_an_update_when_a_source_file_is_missing(tmp_path):
    target = _file(tmp_path, "a.o")

    assert _task(target, [Token(str(tmp_path / "gone.c"))]).needsUpdate() is True


def test_needs_an_update_when_a_task_it_needs_does(tmp_path):
    source, middle, target = _file(tmp_path, "a.c"), _file(tmp_path, "a.o"), _file(tmp_path, "app")
    age(middle, target)
    middle_task = _task(middle, [Token(str(source))])

    # app is newer than a.o, but a.o is out of date
    assert _task(target, [middle_task]).needsUpdate() is True


def test_a_phony_target_always_needs_an_update(tmp_path):
    _file(tmp_path, "clean")

    assert Task(Token(str(tmp_path / "clean"), phony=True)).needsUpdate() is True


def test_needs_update_reads_the_files_again_on_each_call(tmp_path):
    source, target = _file(tmp_path, "a.c"), _file(tmp_path, "a.o")
    age(source)
    task = _task(target, [Token(str(source))])
    assert task.needsUpdate() is False

    source.write_text("changed")

    assert task.needsUpdate() is True


def test_needs_update_visits_a_shared_source_once(tmp_path, monkeypatch):
    calls = []
    getmtime = Token.getmtime
    monkeypatch.setattr(Token, "getmtime", lambda self: calls.append(self.get()) or getmtime(self))

    base = _task(_file(tmp_path, "base"), [Token(str(_file(tmp_path, "base.c")))])
    left = _task(_file(tmp_path, "left"), [base])
    right = _task(_file(tmp_path, "right"), [base])
    _task(_file(tmp_path, "top"), [left, right]).needsUpdate()

    assert calls.count(str(tmp_path / "base.c")) == 1


def test_the_level_of_a_task_is_one_more_than_its_deepest_source(tmp_path):
    a = _task(tmp_path / "a")
    b = _task(tmp_path / "b", [a])
    c = _task(tmp_path / "c", [a, b, Token("file")])

    assert (a.getLevel(), b.getLevel(), c.getLevel()) == (0, 1, 2)


def test_stages_hold_what_needs_an_update_by_level(tmp_path):
    fresh = _file(tmp_path, "fresh")
    up_to_date = _task(fresh)
    a = _task(tmp_path / "a", [up_to_date])
    b = _task(tmp_path / "b", [a])

    assert b.buildStages() == {1: [a], 2: [b]}


def test_stages_are_empty_when_everything_is_up_to_date(tmp_path):
    source, target = _file(tmp_path, "a.c"), _file(tmp_path, "a.o")
    age(source)

    assert _task(target, [Token(str(source))]).buildStages() == {}


def test_a_shell_command_runs_in_the_path(tmp_path):
    task = _task(tmp_path / "out", command="pwd > out", path=str(tmp_path))

    assert task.execute() == 0
    assert (tmp_path / "out").read_text().strip() == str(tmp_path)


def test_each_line_of_a_command_runs_and_is_echoed_unless_it_starts_with_at(tmp_path, capfd):
    task = _task(tmp_path / "out", command="""
        echo one >> out
        @echo two >> out
    """, path=str(tmp_path))

    assert task.execute() == 0
    assert (tmp_path / "out").read_text().split() == ["one", "two"]
    printed = capfd.readouterr().out
    assert "echo one >> out" in printed
    assert "echo two >> out" not in printed


def test_a_line_that_fails_stops_the_command(tmp_path):
    task = _task(tmp_path / "out", command="""
        false
        echo never > out
    """, path=str(tmp_path))

    assert task.execute() != 0
    assert not (tmp_path / "out").exists()


def test_the_on_failure_command_decides_the_result(tmp_path):
    def run(fallback):
        return _task(tmp_path / "out", command="exit 3", on_failure_command=fallback, path=str(tmp_path)).execute()

    assert run(None) == 3
    assert run("true") == 0
    assert run("exit 5") == 5


def test_the_on_failure_command_only_runs_on_failure(tmp_path):
    task = _task(tmp_path / "out", command="true", on_failure_command="echo ran > log", path=str(tmp_path))

    assert task.execute() == 0
    assert not (tmp_path / "log").exists()


def test_a_task_without_command_succeeds(tmp_path):
    assert _task(tmp_path / "all").execute() == 0


def _add(a, b):
    return a + b


def test_a_function_gets_the_values_of_its_variables_and_sets_its_return(tmp_path, capfd):
    result = Variable()
    task = _task(tmp_path / "t", command=Function(_add, args=(Variable(2), 3), ret=result))

    assert task.execute() == 0
    assert result.get() == 5
    assert "_add(2, 3)" in capfd.readouterr().out


def test_a_quiet_function_is_not_echoed(tmp_path, capfd):
    task = _task(tmp_path / "t", command=Function(_add, args=(1, 2), quiet=True))

    assert task.execute() == 0
    assert "_add" not in capfd.readouterr().out


def test_the_accessors_give_back_what_the_task_was_made_with(tmp_path):
    source = Token("a.c")
    task = Task(Token("a.o"), sources=[source], command="cc", on_failure_command="rm", id=7, path="src")

    assert (task.getName(), task.getCommand(), task.getOnFailureCommand(), task.getId(), task.getPath()) == (
        "a.o", "cc", "rm", 7, "src")
    assert task.getSources() == [source]


def test_a_task_is_made_of_tokens_and_tasks():
    with pytest.raises(ValueError, match='Target must be of type "Task or Token".'):
        Task("a.o")
    with pytest.raises(ValueError, match='Sources must be of type "Task or Token".'):
        Task(Token("a.o"), sources=["a.c"])
