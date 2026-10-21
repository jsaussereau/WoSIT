"""Function and Variable: Python calls in rules, and the values they hand to each other."""

import pytest

from wosit.Function import Function, Variable
from wosit.ProcessPool import ProcessPool


def _add(a, b):
    return a + b


def test_a_variable_starts_with_its_initial_value():
    assert Variable().get() is None
    assert Variable("start").get() == "start"


def test_a_variable_gives_the_last_value_set():
    value = Variable("start")

    value.set("first")
    assert value.get() == "first"
    value.set("second")
    value.set("third")
    assert value.get() == "third"
    assert value.get() == "third"


def _set_in_child(value):
    value.set("from a task")
    return 0


def _read_in_child(value):
    return value.get()


def test_a_value_set_by_a_task_is_seen_by_the_others_and_by_the_build():
    value = Variable("start")

    ProcessPool(1).map(_set_in_child, [value])
    assert ProcessPool(1).map(_read_in_child, [value]) == ["from a task"]
    # Reading it in a task did not take it away
    assert value.get() == "from a task"


def test_a_function_keeps_what_it_calls():
    ret = Variable()
    function = Function(_add, args=(1, 2), ret=ret, quiet=True)

    assert function.getFunction() is _add
    assert function.getArgs() == (1, 2)
    assert function.ret is ret and function.quiet is True


def test_set_ret_sets_the_return_variable():
    ret = Variable()

    Function(_add, args=(1, 2), ret=ret).setRet(3)

    assert ret.get() == 3


def test_function_arguments_are_a_tuple():
    with pytest.raises(ValueError, match="Arguments must be passed as a tuple."):
        Function(_add, args=[1, 2])


def test_function_returns_into_a_variable():
    with pytest.raises(ValueError, match='Return argument "ret" must be of type "Variable".'):
        Function(_add, args=(1, 2), ret="wrong")
