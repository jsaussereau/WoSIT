import os

from wosit.Function import *


class Token:
    __object = None
    __type = None


    def __init__(self, object, phony=False):
        self.__object = object
        self.__phony = phony

        if type(object) is str:
            if os.path.exists(object):
                self.__type = "file"
        else:
            self.__type = None



    def get(self):
        return self.__object
    
    def set(self, object):
        self.__object = object

    

    def __getmtime(self, obj):
        if self.__phony is True:
            return None
        if type(obj) is Variable:
            return None
        if not os.path.exists(obj):
            return None
        
        return os.path.getmtime(obj)
        

    def getmtime(self):
        return self.__getmtime(self.__object)