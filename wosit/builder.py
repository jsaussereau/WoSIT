
from wosit import Maker
from wosit.Function import Function, Variable

import argparse
import os

import importlib.util
import sys

#sys.path.append(os.path.abspath(os.path.join(os.path.dirname("__file__"), '..')))

global build
build = Maker()

global addRule
def addRule(target, source=None, command=None, path=None, on_failure_command=None, phony=False):
    build.addRule(target=target, source=source, command=command, path=path, on_failure_command=on_failure_command, phony=phony)

def importModule(path):
    dirpath = os.path.abspath(os.path.dirname(path))
    if dirpath not in sys.path:
        sys.path.insert(0, dirpath)

    name = os.path.basename(path).split(".py")[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rule", type=str, nargs="*")
    parser.add_argument("-l", "--list", action="store_true", help="List targets.")
    parser.add_argument("-j", "--jobs", type=int, default=1, help="Allow N jobs at once.")
    parser.add_argument("-f", "--file", type=str, help="Use the specified buildconfig file.")
    parser.add_argument("-C", "--directory", type=str, help="Change the directory before doing anything.")

    parsed_args = parser.parse_args()

    if parsed_args.directory is not None:
        os.chdir(parsed_args.directory)


    if parsed_args.file is None:
        importModule(os.path.join(os.getcwd(), "buildconfig.py"))
    else:
        fpath = os.path.expanduser(os.path.expandvars(parsed_args.file))
        if not os.path.isfile(fpath):
            raise ValueError("File not found.")
        importModule(fpath)

    if parsed_args.list is True:
        tnames = build.getTargetsList()
        print("\n".join(tnames))
    else:
        build.execute(parsed_args.rule, max_process=parsed_args.jobs)


if __name__ == "__main__":
    main()
