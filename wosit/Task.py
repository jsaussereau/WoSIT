import os
from subprocess import run

from wosit.Token import Token
from wosit.Function import Variable, Function



PRINT_COLOR_CODE = "96"


class Task:
    __id = None

    __target = None
    __sources = None
    __command = None
    __on_failure_command = None

    __parsed_stage = False
    __need_update = False

    __level = None


    def __init__(self, target, sources=None, command=None, on_failure_command=None, id=None, path=None):
        if sources is None:
            sources = []

        if not type(target) in [Token, Task]:
            raise ValueError("Target must be of type \"Task or Token\".")

        if not all(type(s) in [Token, Task] for s in sources):
            raise ValueError("Sources must be of type \"Task or Token\".")

        self.__target = target
        self.__sources = sources

        self.__command = command
        self.__on_failure_command = on_failure_command

        self.__id = id
        self.__path = path
    

    # Returns the mtime of the target
    def getmtime(self):
        if self.__target is None:
            return None
        return self.__target.getmtime()


    def getId(self):
        return self.__id


    def getName(self):
        if type(self.__target) is Token:
            return self.__target.get()
        # TODO: Find a way to get the name of a Task target
        return ""


    def getCommand(self):
        return self.__command


    def getOnFailureCommand(self):
        return self.__on_failure_command


    def getPath(self):
        return self.__path


    def getSources(self):
        return self.__sources or []


    def __addStage(self, stages, level, obj):
        if level in list(stages.keys()):
            stages[level].append(obj)
        else:
            stages.update({level:[obj]})

        return stages



    def getLevel(self):
        sources = self.__sources or []

        if not self.__level is None:
            return self.__level
        
        if len(sources) == 0:
            self.__level = 0
            return 0
        
        max_level = 0
        is_any_task = False
        for s in sources:
            if type(s) is Task:
                is_any_task = True
                slv = s.getLevel()
                max_level = max(max_level, slv)
        
        if not is_any_task:
            self.__level = 0
            return 0
        else:
            self.__level = max_level + 1
            return max_level + 1
    


    def buildNextStage(self, stages):
        sources = self.__sources or []

        # Do not add itself again if already parsed.
        if self.__parsed_stage is True:
            return self.__need_update

        need_update = False

        self_time = self.getmtime()
        if self_time is None:
            need_update = True
        
        src_update = False
        for s in sources:
            if type(s) is Task:
                # Recursively add sources to stages
                src_update |= s.buildNextStage(stages)
            elif type(s) is Token:
                source_time = s.getmtime()

                if not self_time is None:
                    if source_time is None:
                        src_update = True
                    else:
                        src_update |= (source_time > self_time) # If source newer than target
                        
        
        self.__parsed_stage = True

        need_update |= src_update

        self.__need_update = need_update

        if need_update:
            t_level = self.getLevel()

            self.__addStage(stages, t_level, self)
            return True
        
        return False



    # Same rule as buildNextStage, but always read from the files (no cache)
    def needsUpdate(self, _cache=None):
        if _cache is None:
            _cache = {}
        if id(self) in _cache:
            return _cache[id(self)]

        self_time = self.getmtime()
        need_update = self_time is None
        for s in self.getSources():
            if type(s) is Task:
                need_update |= s.needsUpdate(_cache)
            elif not self_time is None:
                source_time = s.getmtime()
                need_update |= source_time is None or source_time > self_time

        _cache[id(self)] = need_update
        return need_update



    def buildStages(self):
        stages = {}
        self.buildNextStage(stages)
        return stages



    def execute(self):
        if not self.__command is None:
            res = 1
            if type(self.__command) is str:
                res = self.__executeShell(self.__command)
            elif type(self.__command) is Function:
                res = self.__executeCallable(self.__command)

            if res != 0:
                fallback_res = self.__executeOnFailureCommand()
                if fallback_res == 0:
                    return 0
                if fallback_res is None:
                    return res
                return fallback_res
        
        return 0


    def __executeOnFailureCommand(self):
        if self.__on_failure_command is None:
            return None

        if type(self.__on_failure_command) is str:
            return self.__executeShell(self.__on_failure_command)
        elif type(self.__on_failure_command) is Function:
            return self.__executeCallable(self.__on_failure_command)

        return 1



    def __printCommand(self, text):
        print(f"\033[{PRINT_COLOR_CODE}m{text}\033[0m")


    def __formatColor(self, text):
        return f"\033[{PRINT_COLOR_CODE}m{text}\033[0m"


    # TODO: Add support for '\' splitting the shell commands
    def __formatCommand(self, command):
        cmdlines = command.split("\n")
        cmdlines = [ln.lstrip().rstrip() for ln in cmdlines]
        cmdlines = [l for l in cmdlines if l != ""]

        final_commands = []
        for c in cmdlines:
            if c[0] != "@":
                final_commands.append(f"echo \"{self.__formatColor(c)}\"")
            else:
                c = c[1:]

            final_commands.append(c)
        
        return " && ".join(final_commands)
    

    def __executeShell(self, command):
        cmd_to_exec = self.__formatCommand(command)
        
        proc = run(cmd_to_exec, shell=True, cwd=self.__path)

        if proc.returncode:
            return proc.returncode

        return 0


    def __argsToStr(self, args):
        olst = []
        for a in args:
            if type(a) is str:
                olst.append(f"\"{a}\"")
            else:
                olst.append(str(a))
        return olst


    # TODO: Check if change of cwd to match self.__path needed or not (to mimmick self.__executeShell behavior)
    def __executeCallable(self, command):
        func = command.function
        args = command.args
        if args is None:
            if not command.quiet:
                self.__printCommand(f"{func.__name__}()")
            retval = func()
        else:
            args = [a.get() if type(a) is Variable else a for a in args]

            strargs = self.__argsToStr(args)
            if not command.quiet:
                self.__printCommand(f"""{func.__name__}({", ".join(strargs)})""")
            retval = func(*args)

        if command.ret is not None:
            if type(command.ret) is Variable:
                command.setRet(retval)
        return 0