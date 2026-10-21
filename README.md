# WoSIT (Workflow Script Interpreter Tool)

**WoSIT** is an automation tool made to replace **make** in many instances. It is written in pure Python and is built to ease integration of other Python scripts in automation workflows.

## Using WoSIT
Similarly to Makefiles, WoSIT's way of describing automation workflows is through **buildconfig.py** files. Those are Python files, and as such allow for the use of the full scripting capabilities offered by Python and its packages. This fact makes it closer to **generating** automation workflows based on the given script, compared to make which uses workflows **descriptions**.

### Basic Usage

Executing a WoSIT workflow is as simple as typing `wosit` in a directory where a `buildconfig.py` file is present. By default, WoSIT will execute the `all` rule.

Similarly to Make, parallel execution can be achieved with the -j flag followed by the maximum number of processes to use.


### Basic Example
The following script defines a Python function named `genMyRules()` to generate a number of rules. Each rule depends on the previous one, and will use the shell `echo` command to print its own id in the terminal.
The script then generates those rules by calling the function.

The rule with target `all` is added with its source set to the last generated rule. This target is special as it is executed by default when no other target is specified.

```python
from wosit.builder import *

def genMyRules(nbrules):
    addRule(
        target = f"rule_0",
        command = f"echo This is a rule with id 0"
    )
    for i in range(1, nbrules):
        addRule(
            target = f"rule_{i}",
            source = f"rule_{i-1}",
            command = f"echo This is a rule with id {i}"
        )

nb_rules = 10
genMyRules(nb_rules)

addRule(
    target = "all",
    source = f"rule_{nb_rules-1}"
)

addRule(
    target="clean",
    command=f"""
    echo Clean commands should go here.
    """
)
```

### Run a Command on Failure

You can pass `on_failure_command` to execute a fallback command when `command` fails.

```python
from wosit.builder import *

addRule(
    target="build",
    command="python3 build.py",
    on_failure_command="echo Build failed && python3 collect_logs.py"
)
```

`on_failure_command` can be either a shell command string or a `Function(...)`, just like `command`.



### Python Functions Example

WoSIT is capable of executing Python functions. The syntax is the same as defining any other rule, with the exception that the function must be passed to the `command` argument through WoSIT's `Function()` object.

```python
from wosit.builder import *

addRule(
    target = "rule_0",
    command = Function(print, args=("This is rule 0.",))
)

addRule(
    target = "rule_1",
    command = Function(print, args=("This is rule 1.",))
)


addRule(
    target = "all",
    source = ["rule_0", "rule_1"]
)
```



### More Examples

More examples are available in the `examples` folder of this repository.

## Automated Tests

You can run the regression test suite with `pytest`.

```bash
python -m pip install -e .
python -m pip install pytest
pytest
```
