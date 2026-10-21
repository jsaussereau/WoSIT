import os
import glob
import json


from wosit.Token import Token
from wosit.Task import Task
from wosit.Function import Variable, Function

from wosit.ProcessPool import ProcessPool

class Maker:
    __patterns = None
    __rules = None

    __parsed = None
    __pattern_rules = None

    __current_id = None


    def __init__(self):
        self.__rules = []
        self.__patterns = []
        self.__parsed = {}
        self.__pattern_rules = {}

        self.__current_id = 0


    def __epxandPath(self, path):
        return os.path.expanduser(os.path.expandvars(path))

    # The same file always gets the same name: "./obj/a.o" and "obj//a.o" are "obj/a.o"
    def __normPath(self, path):
        if type(path) is str and path != "":
            return os.path.normpath(path)
        return path

    def __expandPaths(self, paths):
        if type(paths) is not list:
            paths = [paths]

        ## Expand user and environment variables when possible
        paths = [os.path.expanduser(os.path.expandvars(p)) for p in paths if p is not None]

        ## Treat wildcards
        tp = []
        for p in paths:
            gp = glob.glob(p)
            if len(gp) == 0:
                tp.append(p)
            else:
                tp += gp
        paths = [self.__normPath(p) for p in tp]

        return paths



    def addRule(self, target, source=None, command=None, path=None, on_failure_command=None, phony=False):
        if not type(target) is list:
            target = [target]
        
        if not type(source) is list:
            source = [source]


        if command is None:
            command = ""

        
        source = self.__expandPaths(source)
        target = self.__expandPaths(target)


        target = [t for t in target]
        source = [s for s in source]

        if type(path) is str:
            path = self.__epxandPath(path)

            # Add path to targets
            tmp_target = []
            for t in target:
                fullpath = os.path.join(path, t)
                tmp_target.append(self.__normPath(fullpath))

            # Add path to sources
            tmp_source = []
            for s in source:
                fullpath = os.path.join(path, s)
                tmp_source.append(self.__normPath(fullpath))

            target = tmp_target
            source = tmp_source


        for t in target:
            if "%" in t:
                patterns_list = self.__getTargetsList(self.__patterns)
                if t in patterns_list:
                    raise ValueError(f"Pattern \"{t}\" is already defined.")
                self.__patterns.append({"pattern":t, "sources":source, "command":command, "on_failure_command":on_failure_command, "path":path, "phony":phony})

            else:
                if type(command) is str:
                    if "%" in command:
                        raise ValueError("Can't use % placeholder in non-pattern rules.")

                if type(on_failure_command) is str:
                    if "%" in on_failure_command:
                        raise ValueError("Can't use % placeholder in non-pattern rules.")
        
                if any("%" in s for s in source):
                        raise ValueError("Can't use % placeholder in non-pattern rules.")
                
                targets_list = self.__getTargetsList(self.__rules)
                if t in targets_list:
                    raise ValueError(f"Rule \"{t}\" is already defined.")
                

                if type(command) is Function:
                    # Add variables to source
                    if not command.args is None:
                        source += [a for a in command.args if type(a) is Variable]

                if type(on_failure_command) is Function:
                    # Add variables to source
                    if not on_failure_command.args is None:
                        source += [a for a in on_failure_command.args if type(a) is Variable]

                rule = self.__resolveSymbols({
                    "target": t,
                    "sources": source,
                    "command": command,
                    "on_failure_command": on_failure_command,
                    "path": path,
                    "phony": phony
                })
                self.__rules.append(rule)
        
        return target


    def __getTargetsList(self, rlist=None):
        if rlist is None:
            rlist = self.__rules

        lst = [r["target"] for r in rlist]
        return lst
    


    def getTargetsList(self):
        return self.__getTargetsList()
    


    def __resolveSymbols(self, rule):
        target = rule["target"]
        sources = rule["sources"]
        command = rule["command"]
        on_failure_command = rule.get("on_failure_command", None)

        if type(command) is str:
            c = command.replace("$@", target)
            if not None in sources and len(sources) > 0:
                c = c.replace("$^", " ".join(sources))
                c = c.replace("$<", sources[0])
            rule["command"] = c

        if type(on_failure_command) is str:
            c = on_failure_command.replace("$@", target)
            if not None in sources and len(sources) > 0:
                c = c.replace("$^", " ".join(sources))
                c = c.replace("$<", sources[0])
            rule["on_failure_command"] = c

        return rule



    ## Walk through the given pattern and string to check if they match.
    ## If match there is, the placeholder substring is returned.
    ## Otherwise None is returned.
    def __matchPattern(self, pattern, str):
        id_p = 0
        id_s = 0

        found_placeholders = []

        hit_placeholder = False
        placeholder = ""
        while id_p < len(pattern) and id_s < len(str):
            cp = pattern[id_p]
            cs = str[id_s]

            if cp == "%":
                hit_placeholder = True
                placeholder += cs
                id_p += 1
                id_s += 1
                
            elif cp != cs and hit_placeholder is False:
                return None

            elif hit_placeholder is True:
                if cp == cs:
                    hit_placeholder = False
                    found_placeholders.append(placeholder)
                    placeholder = ""
                    id_p += 1                
                else:
                    placeholder += cs
                id_s += 1

            else:
                id_p += 1
                id_s += 1
        
            ## Avoid going over pattern length when '%' char is at end of pattern.
            if id_p >= len(pattern):
                id_p = len(pattern) - 1
        

        ## If reached end of string and still searching for placeholder
        if hit_placeholder is True:
            found_placeholders.append(placeholder)

        ## All placeholders found are not the same.
        if len(set(found_placeholders)) != 1:
            return None        

        ## If there is a match, 
        if len(found_placeholders) > 0:
            return found_placeholders[0]
        else:
            return None
        


    # Returns a matching pattern to the given name, None if not match could be found.
    def __searchPattern(self, name):
        for p in self.__patterns:
            patmatch = self.__matchPattern(p["pattern"], name)
            
            if not patmatch is None:
                otarget = p["pattern"].replace("%", patmatch)
                osources = [s.replace("%", patmatch) for s in p["sources"]]
                if type(p["command"]) is str:
                    ocommand = p["command"].replace("%", patmatch)
                else:
                    ocommand = p["command"]

                if type(p.get("on_failure_command", None)) is str:
                    ofail = p["on_failure_command"].replace("%", patmatch)
                else:
                    ofail = p.get("on_failure_command", None)

                return {"target":otarget, "sources":osources, "command":ocommand, "on_failure_command":ofail, "path":p.get("path", None), "phony":p.get("phony", False)}
            
        return None
    


    # Returns the rule with the same name or None if it could
    # not be found and could not be constructed from a pattern.
    def __getRule(self, name):
        name = self.__normPath(name)
        for r in self.__rules:
            if name == r["target"]:
                return r

        # Built once from its pattern, like a rule: the same target is the same task
        if name in self.__pattern_rules:
            return self.__pattern_rules[name]

        match = self.__searchPattern(name)
        if match is None:
            return None
        
        rule = self.__resolveSymbols(match)
        self.__pattern_rules[name] = rule
        return rule




    def __buildTaskGraph(self, name):
        rule = self.__getRule(name)
        if rule is None:
            if not type(name) is Variable:
                if not os.path.isfile(name):
                    raise ValueError(f"Could not find rule or dependency \"{name}\".")
            
            tok = None
            if name in list(self.__parsed.keys()):
                tok = self.__parsed[name]
            else:
                tok = Token(name)
                self.__parsed.update({name:tok}) # TODO: This will maybe cause problems with parsed task id checks 
            return tok    

        if "id" in rule:
            # if rule["id"] in list(self.__parsed.keys()):
            return self.__parsed[rule["id"]]
        
        srclist = []
        for srcname in rule["sources"]:
            src = self.__buildTaskGraph(srcname)
            srclist.append(src)
        
        rule["id"] = self.__current_id
        self.__current_id += 1
        task = Task(
            target=Token(rule["target"], phony=rule["phony"]),
            sources=srclist,
            command=rule["command"],
            on_failure_command=rule.get("on_failure_command", None),
            id=rule["id"],
            path=rule["path"],
        )
        self.__parsed.update({rule["id"]:task})
        return task



    # Dummy function to call in a multiprocessing Pool
    def _taskExecute(self, task):
        return task.execute()



    def getStages(self, name=None, max_process=1) -> dict:
        if type(name) is list:
            if len(name) > 0:
                for n in name:
                    self.execute(n, max_process)
                return None
            else:
                self.execute(None, max_process)
                return None

        if name is None:
            name = "all"


        # Chain rules in a dependcy graph
        taskgraph = self.__buildTaskGraph(name)
        # Retrieve execution stages based on dependency and need for update
        stages = taskgraph.buildStages()

        stage_levels = list(stages.keys())
        if len(stage_levels) == 0:
            return None
        
        return stages

    # Returns {id: node} for every task the target depends on, with the ids of
    # the tasks it waits for in "sources"
    def getGraph(self, name=None):
        if name is None:
            name = "all"

        graph = {}
        cache = {}
        pending = [self.__buildTaskGraph(name)]
        while pending:
            task = pending.pop()
            if type(task) is not Task or task.getId() in graph:
                continue
            sources = [s for s in task.getSources() if type(s) is Task]
            graph[task.getId()] = {
                "target": task.getName(),
                "command": task.getCommand(),
                "on_failure_command": task.getOnFailureCommand(),
                "path": task.getPath(),
                "sources": [s.getId() for s in sources],
                "need_update": task.needsUpdate(cache),
            }
            pending.extend(sources)
        return graph

    def execute(self, name=None, max_process=1):

        stages = self.getStages(name, max_process)
        if stages is None:
            return

        # Execute every stage element
        with ProcessPool(max_process) as p:
            res = None
            for lvl, stage in sorted(stages.items()):
                res = p.map(self._taskExecute, stage)

                if any(r != 0 for r in res):
                    raise RuntimeError("The execution of a task failed.")


