from multiprocessing import Queue
from queue import Empty


class Variable:
    __value = None
    __queue = None

    # The queue carries the values set in the processes running the tasks.
    # A put only reaches it a moment later, so the value set here is also kept here.
    def __init__(self, init_value=None):
        self.__queue = Queue()
        self.__value = init_value


    def __drain(self):
        drained = False
        while True:
            try:
                self.__value = self.__queue.get_nowait()
                drained = True
            except Empty:
                return drained


    # What a process reads stays for the others
    def get(self):
        if self.__drain():
            self.__queue.put(self.__value)
        return self.__value
    

    def set(self, value):
        self.__drain()
        self.__value = value
        self.__queue.put(value)



class Function:
    function = None
    args = None
    ret = None
    quiet = False

    def __init__(self, function, args=None, ret=None, quiet=False):
        self.function = function

        if args is not None:
            if type(args) is not tuple:
                raise ValueError("Arguments must be passed as a tuple.")
        self.args = args

        if not ret is None:
            if not type(ret) is Variable:
                raise ValueError("Return argument \"ret\" must be of type \"Variable\".")
            self.ret = ret

        self.quiet = quiet


    def getFunction(self):
        return self.function
    

    def getArgs(self):
        return self.args
    
    def setRet(self, retvalue):
        self.ret.set(retvalue)