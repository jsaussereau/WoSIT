"""Maker: rules, their symbols, paths and patterns, the graph, and what a build runs."""

import os

import pytest

from wosit.Function import Function, Variable
from wosit.Maker import Maker
from conftest import age


def _commands(maker, name):
    """Command of every task of the graph of `name`, by target."""
    return {node["target"]: node["command"] for node in maker.getGraph(name).values()}


def _edges(maker, name):
    graph = maker.getGraph(name)
    return {node["target"]: sorted(graph[s]["target"] for s in node["sources"]) for node in graph.values()}


# -- declaring rules ------------------------------------------------------------

def test_add_rule_returns_the_targets_it_declared():
    assert Maker().addRule(["a", "b"], command="true") == ["a", "b"]


def test_targets_are_listed_in_the_order_they_were_declared():
    maker = Maker()
    maker.addRule("all", "b")
    maker.addRule(["b", "a"], command="true")

    assert maker.getTargetsList() == ["all", "b", "a"]


def test_a_target_is_declared_once():
    maker = Maker()
    maker.addRule("all", command="echo ok")

    with pytest.raises(ValueError, match='Rule "all" is already defined.'):
        maker.addRule("all", command="echo again")


def test_a_pattern_is_declared_once():
    maker = Maker()
    maker.addRule("%.o", "%.c", "cc $<")

    with pytest.raises(ValueError, match='Pattern "%.o" is already defined.'):
        maker.addRule("%.o", "%.cpp", "c++ $<")


@pytest.mark.parametrize("rule", [
    dict(command="echo %"),
    dict(command="true", on_failure_command="echo %"),
    dict(source="%.c", command="true"),
])
def test_percent_is_only_for_pattern_rules(rule):
    with pytest.raises(ValueError, match="Can't use % placeholder in non-pattern rules."):
        Maker().addRule("all", **rule)


def test_sources_expand_wildcards(in_tmp):
    for name in ("b.c", "a.c"):
        (in_tmp / name).write_text(name)
    maker = Maker()
    maker.addRule("all", "*.c", "cat $^")

    assert sorted(_commands(maker, "all")["all"].split()[1:]) == ["a.c", "b.c"]


def test_paths_expand_the_environment(in_tmp, monkeypatch):
    monkeypatch.setenv("WOSIT_TEST_DIR", "out")
    maker = Maker()

    assert maker.addRule("$WOSIT_TEST_DIR/x", command="true") == ["out/x"]


# -- symbols --------------------------------------------------------------------

def test_symbols_are_the_target_the_sources_and_the_first_source(in_tmp):
    for name in ("a.c", "b.c"):
        (in_tmp / name).write_text(name)
    maker = Maker()
    maker.addRule("app", ["a.c", "b.c"], "cc $^ -o $@ # first: $<", on_failure_command="rm -f $@")

    node = maker.getGraph("app")[0]
    assert node["command"] == "cc a.c b.c -o app # first: a.c"
    assert node["on_failure_command"] == "rm -f app"


def test_symbols_are_written_from_the_path_of_the_rule(in_tmp):
    (in_tmp / "src").mkdir()
    (in_tmp / "lib").mkdir()
    (in_tmp / "src" / "a.c").write_text("a")
    (in_tmp / "lib" / "l.h").write_text("l")
    maker = Maker()
    maker.addRule("a.o", ["a.c", "../lib/l.h"], "cc $^ -o $@", path="src")

    node = maker.getGraph("src/a.o")[0]
    # The command runs in src: from there, the files are a.c, ../lib/l.h and a.o
    assert node["command"] == "cc a.c ../lib/l.h -o a.o"
    assert node["path"] == "src"


def test_absolute_paths_stay_absolute_in_the_symbols(in_tmp):
    source = in_tmp / "a.c"
    source.write_text("a")
    maker = Maker()
    maker.addRule("a.o", str(source), "cc $< -o $@", path="src")

    assert maker.getGraph("src/a.o")[0]["command"] == "cc {} -o a.o".format(source)


# -- paths ----------------------------------------------------------------------

def test_the_same_file_spelled_differently_is_the_same_target(in_tmp):
    maker = Maker()
    maker.addRule("a.o", command="touch a.o", path=".")
    maker.addRule("obj//b.o", command="touch obj/b.o")
    maker.addRule("app", ["./a.o", "obj/./b.o"], "cat $^ > $@")

    assert _edges(maker, "./app") == {"app": ["a.o", "obj/b.o"], "a.o": [], "obj/b.o": []}


def test_a_directory_target_is_up_to_date_once_built(in_tmp):
    (in_tmp / "design.v").write_text("module m; endmodule")
    maker = Maker()
    maker.addRule("run", "design.v", "mkdir -p run && cp design.v run/")

    assert maker.getGraph("run")[0]["need_update"] is True
    maker.execute("run")
    age(in_tmp / "design.v")
    assert maker.getGraph("run")[0]["need_update"] is False


def test_a_source_without_rule_can_be_a_directory(in_tmp):
    (in_tmp / "rtl").mkdir()
    maker = Maker()
    maker.addRule("all", "rtl", "true")

    assert [node["target"] for node in maker.getGraph("all").values()] == ["all"]


def test_a_source_without_rule_must_exist(in_tmp):
    maker = Maker()
    maker.addRule("all", "missing.c", "true")

    with pytest.raises(ValueError, match='Could not find rule or dependency "missing.c".'):
        maker.getGraph("all")


def test_an_unknown_target_is_an_error(in_tmp):
    with pytest.raises(ValueError, match='Could not find rule or dependency "nothing".'):
        Maker().execute("nothing")


# -- patterns -------------------------------------------------------------------

def test_a_pattern_makes_the_rule_of_a_matching_target(in_tmp):
    (in_tmp / "src").mkdir()
    (in_tmp / "src" / "item.in").write_text("hello")
    maker = Maker()
    maker.addRule("out/%.out", "src/%.in", "mkdir -p out && cp $< $@")

    maker.execute("out/item.out")

    assert (in_tmp / "out" / "item.out").read_text() == "hello"


def test_a_pattern_target_is_one_task_whoever_needs_it(in_tmp):
    (in_tmp / "a.c").write_text("a")
    maker = Maker()
    maker.addRule("%.o", "%.c", "cp $< $@")
    maker.addRule("x", "a.o", "cp a.o x")
    maker.addRule("y", "./a.o", "cp a.o y")
    maker.addRule("all", ["x", "y"], phony=True)

    graph = maker.getGraph("all")

    assert sorted(node["target"] for node in graph.values()) == ["a.o", "all", "x", "y"]


def test_a_pattern_keeps_its_path(in_tmp):
    (in_tmp / "d").mkdir()
    (in_tmp / "d" / "a.c").write_text("a")
    maker = Maker()
    maker.addRule("%.o", "%.c", "cp $< $@", path="d")

    maker.execute("d/a.o")

    assert (in_tmp / "d" / "a.o").read_text() == "a"
    assert maker.getGraph("d/a.o")[0]["path"] == "d"


def test_a_pattern_replaces_the_placeholder_in_its_command(in_tmp):
    (in_tmp / "a.c").write_text("a")
    maker = Maker()
    maker.addRule("%.o", "%.c", "echo % > %.o")

    maker.execute("a.o")

    assert (in_tmp / "a.o").read_text().strip() == "a"


def test_a_pattern_does_not_match_another_target(in_tmp):
    maker = Maker()
    maker.addRule("%.o", "%.c", "true")

    with pytest.raises(ValueError, match="Could not find rule"):
        maker.getGraph("a.txt")


# -- the graph ------------------------------------------------------------------

def test_the_graph_holds_every_task_a_target_needs(in_tmp):
    (in_tmp / "a.c").write_text("a")
    maker = Maker()
    maker.addRule("a.o", "a.c", "cp a.c a.o")
    maker.addRule("b.o", command="touch b.o", on_failure_command="echo ko")
    maker.addRule("app", ["a.o", "b.o"], "cat a.o b.o > app")
    maker.addRule("unrelated", command="true")

    graph = maker.getGraph("app")

    assert _edges(maker, "app") == {"app": ["a.o", "b.o"], "a.o": [], "b.o": []}
    by_target = {node["target"]: node for node in graph.values()}
    assert by_target["b.o"]["on_failure_command"] == "echo ko"
    assert set(by_target["app"]) == {"target", "command", "on_failure_command", "path", "sources", "need_update"}
    # Ids are the keys, and the sources name them
    assert all(key in graph for node in graph.values() for key in node["sources"])


def test_the_graph_defaults_to_all():
    maker = Maker()
    maker.addRule("all", command="true")

    assert [node["target"] for node in maker.getGraph().values()] == ["all"]


def test_the_graph_says_what_needs_an_update_each_time_it_is_read(in_tmp):
    (in_tmp / "a.c").write_text("a")
    (in_tmp / "b.c").write_text("b")
    maker = Maker()
    maker.addRule("a.o", "a.c", "cp a.c a.o")
    maker.addRule("b.o", "b.c", "cp b.c b.o")
    maker.addRule("app", ["a.o", "b.o"], "cat a.o b.o > app")

    def need():
        return {node["target"]: node["need_update"] for node in maker.getGraph("app").values()}

    assert need() == {"app": True, "a.o": True, "b.o": True}
    maker.execute("app")
    age(in_tmp / "a.c", in_tmp / "b.c", seconds=200)
    age(in_tmp / "a.o", in_tmp / "b.o", in_tmp / "app")
    assert need() == {"app": False, "a.o": False, "b.o": False}
    (in_tmp / "b.c").write_text("changed")
    assert need() == {"app": True, "a.o": False, "b.o": True}


# -- building -------------------------------------------------------------------

def test_a_build_runs_the_sources_first(in_tmp):
    maker = Maker()
    maker.addRule("first", command="echo first >> log")
    maker.addRule("second", "first", "echo second >> log")
    maker.addRule("all", "second", "echo all >> log")

    maker.execute()

    assert (in_tmp / "log").read_text().split() == ["first", "second", "all"]


def test_a_build_runs_only_what_is_out_of_date(in_tmp):
    (in_tmp / "a.c").write_text("a")
    (in_tmp / "b.c").write_text("b")
    maker = Maker()
    maker.addRule("a.o", "a.c", "cp a.c a.o && echo a >> log")
    maker.addRule("b.o", "b.c", "cp b.c b.o && echo b >> log")
    maker.addRule("all", ["a.o", "b.o"], phony=True)
    maker.execute()
    age(in_tmp / "a.c", in_tmp / "b.c", seconds=200)
    age(in_tmp / "a.o", in_tmp / "b.o")
    (in_tmp / "b.c").write_text("changed")

    # A Maker computes what to do once: a new build is a new Maker
    maker = Maker()
    maker.addRule("a.o", "a.c", "cp a.c a.o && echo a >> log")
    maker.addRule("b.o", "b.c", "cp b.c b.o && echo b >> log")
    maker.addRule("all", ["a.o", "b.o"], phony=True)
    maker.execute()

    assert (in_tmp / "log").read_text().split() == ["a", "b", "b"]


def test_a_phony_target_always_runs(in_tmp):
    (in_tmp / "clean").write_text("a file named like the rule")
    maker = Maker()
    maker.addRule("clean", command="echo ran > log", phony=True)

    maker.execute("clean")

    assert (in_tmp / "log").read_text().strip() == "ran"


def test_several_targets_are_built_one_after_the_other(in_tmp):
    maker = Maker()
    maker.addRule("a", command="echo a >> log")
    maker.addRule("b", command="echo b >> log")

    maker.execute(["a", "b"])

    assert (in_tmp / "log").read_text().split() == ["a", "b"]


def test_a_failure_stops_the_build(in_tmp):
    maker = Maker()
    maker.addRule("broken", command="false")
    maker.addRule("all", "broken", "echo never > log")

    with pytest.raises(RuntimeError, match="The execution of a task failed."):
        maker.execute()
    assert not (in_tmp / "log").exists()


def test_the_on_failure_command_saves_the_build(in_tmp):
    maker = Maker()
    maker.addRule("broken", command="false", on_failure_command="echo recovered > log")
    maker.addRule("all", "broken", "echo after >> log")

    maker.execute()

    assert (in_tmp / "log").read_text().split() == ["recovered", "after"]


def test_rules_run_in_parallel_within_a_stage(in_tmp):
    maker = Maker()
    # Each one waits for the other's file: they only both end when run at once
    maker.addRule("a", command="touch a.started; for i in $(seq 50); do [ -e b.started ] && exit 0; sleep 0.1; done; exit 1")
    maker.addRule("b", command="touch b.started; for i in $(seq 50); do [ -e a.started ] && exit 0; sleep 0.1; done; exit 1")
    maker.addRule("all", ["a", "b"], phony=True)

    maker.execute(max_process=2)


# -- Python functions -----------------------------------------------------------

def _write(path, text):
    with open(path, "w") as f:
        f.write(text)


def test_a_rule_can_call_a_function(in_tmp):
    maker = Maker()
    maker.addRule("all", command=Function(_write, args=("out.txt", "written")))

    maker.execute()

    assert (in_tmp / "out.txt").read_text() == "written"


def test_a_function_can_be_the_on_failure_command(in_tmp):
    maker = Maker()
    maker.addRule("all", command="false", on_failure_command=Function(_write, args=("out.txt", "fallback")))

    maker.execute()

    assert (in_tmp / "out.txt").read_text() == "fallback"


def _upper(text):
    return text.upper()


def test_a_returned_value_reaches_the_rules_after(in_tmp):
    value = Variable()
    maker = Maker()
    maker.addRule("produce", command=Function(_upper, args=("made",), ret=value))
    maker.addRule("all", "produce", Function(_write, args=("out.txt", value)))

    maker.execute()

    assert (in_tmp / "out.txt").read_text() == "MADE"
    assert value.get() == "MADE"
