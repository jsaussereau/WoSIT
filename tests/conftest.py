import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples"


class Result:
    def __init__(self, proc):
        self.returncode = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr

    @property
    def lines(self):
        """The lines printed, without the color codes of the echoed commands."""
        out = []
        for line in self.stdout.splitlines():
            for code in ("\033[96m", "\033[0m"):
                line = line.replace(code, "")
            if line.strip():
                out.append(line.strip())
        return out


def run_wosit(*args, cwd):
    """
    Run the wosit command in `cwd`. Through main() rather than "python -m
    wosit.builder": run as __main__, the builder would be a second module, and
    the buildconfig would fill the Maker of the other one.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(PROJECT_ROOT), env.get("PYTHONPATH", "")) if p)
    proc = subprocess.run(
        [sys.executable, "-c", "import sys; sys.argv[0] = 'wosit'; from wosit.builder import main; main()"]
        + [str(a) for a in args],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=120,
    )
    return Result(proc)


@pytest.fixture
def wosit():
    return run_wosit


@pytest.fixture
def example(tmp_path):
    """A copy of an example of the repository, to build without touching it."""
    def copy(name):
        dest = tmp_path / name
        shutil.copytree(str(EXAMPLES_DIR / name), str(dest),
                        ignore=shutil.ignore_patterns("__pycache__", "obj", "*.o"))
        return dest
    return copy


@pytest.fixture
def buildconfig(tmp_path):
    """Write a buildconfig.py in a fresh directory, and return that directory."""
    def write(text, files=None):
        for name, content in (files or {}).items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        (tmp_path / "buildconfig.py").write_text(textwrap.dedent(text))
        return tmp_path
    return write


@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    """Run in a fresh directory: rules name their files relative to the current one."""
    monkeypatch.chdir(str(tmp_path))
    return tmp_path


def age(*paths, seconds=100):
    """Make files older, so that what is made from them is newer."""
    when = time.time() - seconds
    for path in paths:
        os.utime(str(path), (when, when))
