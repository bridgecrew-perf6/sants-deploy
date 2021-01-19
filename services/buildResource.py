from abc import ABCMeta, abstractmethod

class buildResource(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def deploy(self):
        pass

    @abstractmethod
    def bar(self):
        pass

    @abstractmethod
    def delete(self):
        pass