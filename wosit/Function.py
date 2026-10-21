from multiprocessing import Lock, Queue, RawValue


class Variable:
    __value = None
    __queue = None
    __count = None
    __lock = None

    # The queue carries the values set in the processes running the tasks.
    # A put only reaches it a moment later, so the number of values in it is counted
    # and they are waited for, rather than missed.
    def __init__(self, init_value=None):
        self.__queue = Queue()
        self.__count = RawValue('i', 0)
        self.__lock = Lock()
        self.__value = init_value


    def __drain(self):
        drained = self.__count.value > 0
        for _ in range(self.__count.value):
            self.__value = self.__queue.get()
        self.__count.value = 0
        return drained


    def __put(self, value):
        self.__queue.put(value)
        self.__count.value = 1


    # What a process reads stays for the others
    def get(self):
        with self.__lock:
            if self.__drain():
                self.__put(self.__value)
            return self.__value


    def set(self, value):
        with self.__lock:
            self.__drain()
            self.__value = value
            self.__put(value)



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