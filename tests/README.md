# WoSIT tests

Run them from the root of the repository:

```bash
python -m pip install -e .
python -m pip install pytest
pytest
```

They run on Python 3.6 and later, and take less than a minute.

## Organization

The tests go from what a user sees down to the classes:

| File | What it covers |
|---|---|
| `test_examples.py` | Every example of `examples/`, built with the `wosit` command on a copy of it |
| `test_readme.py` | Every Python block of the main README, run as a `buildconfig.py` |
| `test_builder_cli.py` | The `wosit` command: default target, `-l`, `-f`, `-C`, `-j`, failures |
| `test_maker.py` | `Maker`: declaring rules, `$@` `$^` `$<`, paths, patterns, `getGraph()`, building, Python functions |
| `test_task.py` | `Task`: when it needs an update, its stages, how it runs its commands |
| `test_function_variable.py` | `Function` and `Variable`, including values passed between processes |
| `test_helpers.py` | `Token`, `pathutils`, `ProcessPool` and `ArgParser` |

`conftest.py` holds what they share:

- `wosit(*args, cwd=...)` runs the `wosit` command in a directory. It returns
  the exit code, the output, and `lines`: what was printed, without color codes.
- `example(name)` copies an example to a temporary directory and returns that copy.
- `buildconfig(text, files=...)` writes a `buildconfig.py` (and the files it
  needs) in a temporary directory, and returns that directory.
- `in_tmp` makes a test run in a temporary directory. Rules name their files
  from the current directory.
- `age(*paths)` makes files older, so that what is built from them looks up to date.

## Adding tests

- **A new example** in `examples/` gets its test in `test_examples.py`. Build it
  with `example(...)` and `wosit(...)`, never in place: the repository stays clean.
- **A new Python block in the README** makes `test_every_readme_example_is_tested`
  fail until it gets its own test in `test_readme.py`.
- **A behavior of the build** (what runs, in which order, from where) is tested
  through `Maker` in `test_maker.py`. A test of a single class goes with that class.
- A test checks what WoSIT does: files written, commands run, and errors raised
  with their message. It does not check how WoSIT does it.
- Keep Python 3.6 working. Use no `capture_output`, no `text=` and no walrus
  operator. Paths given to `os` and `subprocess` are `str(...)`.
