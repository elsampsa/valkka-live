from valkka import core
from multiprocessing import Pipe, Event

class IPCElement:

    def __init__(self):
        self.event_fd = core.EventFd()
        self.pipe1, self.pipe2 = Pipe()
        self.event = Event()
        self.event.clear()


class IPC:

    num = 10

    def __init__(self):
        self.lis = []
        self.indices = []
        for i in range(self.num):
            self.lis.append(IPCElement())
            self.indices.append(i)

    def get1(self, i):
        el = self.lis[i]
        return el.event_fd, el.pipe1

    def get2(self, i):
        el = self.lis[i]
        return el.event_fd, el.pipe2
    
    def reserve(self):
        return self.indices.pop(0)

    def release(self, i):
        self.indices.append(i)
    
    def wait(self, i):
        el = self.lis[i]
        el.event.wait()

    def set(self, i):
        el = self.lis[i]
        el.event.set()

    def clear(self, i):
        el = self.lis[i]
        el.event.clear()

