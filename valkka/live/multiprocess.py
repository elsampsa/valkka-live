"""
NAME.py :

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    NAME.py
@author  Sampsa Riikonen
@date    2018
@version 0.14.0 
@brief   
"""

from multiprocessing import Process, Pipe
import select
import errno
import time
import sys
import logging

from PySide2 import QtCore, QtWidgets
from valkka.live.tools import getLogger, setLogger

logger = getLogger(__name__)


class MessageObject:

    def __init__(self, command, **kwargs):
        self.command = command
        self.kwargs = kwargs

    def __str__(self):
        return "<MessageObject: %s: %s>" % (self.command, self.kwargs)

    def __getitem__(self, key):
        return self.kwargs[key]



def safe_select(l1, l2, l3, timeout = None):
    """
    print("safe_select: enter")
    select.select(l1,l2,l3,0)
    print("safe_select: return")
    return True
    """
    try:
        if timeout is None:
            res = select.select(l1, l2, l3) # blocks
        else:
            res = select.select(l1, l2, l3, timeout) # timeout 0 is just a poll
        # print("safe_select: ping")
    except (OSError, select.error) as e:
        if e.errno != errno.EINTR:
            raise
        else: # EINTR doesn't matter
            # print("select : giving problems..")
            return [[], [], []]  # dont read socket
    else:
        # print("select : returning true!")
        return res  # read socket
    # print("select : ?")


class QFrontThread(QtCore.QThread):
    """A QThread that is used to read messages MessageObjects coming from multiprocess & turning them into Qt signals
    """
    def __init__(self, signals, pipe):
        self.pre = __name__ + "." + self.__class__.__name__
        self.logger = getLogger(self.pre)
        super().__init__()
        self.signals = signals
        self.pipe = pipe
        self.loop = True
        # self.setDebug()


    def setDebug(self):
        setLogger(self.logger, logging.DEBUG)

    def run(self):
        while self.loop:
            self.readPipes__(timeout = None)
        self.logger.debug("QFrontThread: bye!")

    def readPipes__(self, timeout):
        """URGENT

        ::

            OpenGLThread: handleFifo: DISCARDING late frame  -11 <1596451483966> 
            Traceback (most recent call last):
            File "/home/sampsa/python3_packages/valkka_live/valkka/live/multiprocess.py", line 93, in run
                self.readPipes__(timeout = None)
            File "/home/sampsa/python3_packages/valkka_live/valkka/live/multiprocess.py", line 97, in readPipes__
                obj = self.pipe.recv()
            File "/usr/lib/python3.6/multiprocessing/connection.py", line 251, in recv
                return _ForkingPickler.loads(buf.getbuffer())
            AttributeError: Recursively add dependencies of package to depends_set.
            [Thread 0x7fffa1527700 (LWP 27397) exited]
            AnalyzerWindow: showEvent

        """
        try:
            obj = self.pipe.recv()
        except Exception as e:
            self.logger.critical("QFrontThread: reading from multiprocess failed with %s", e)
            return

        if obj is None:
            self.loop = False
            return
        # convert a messages from the multiprocess into a Qt signal
        if hasattr(self.signals, obj.command):
            signal = getattr(self.signals, obj.command)
            self.logger.debug("QFrontThread: emitting signal %s", signal)
            if len(obj.kwargs) < 1:
                signal.emit() # no kwargs, so send signal without an object
            else:
                signal.emit(obj.kwargs) # signal carries a dictionary
        else:
            self.logger.info("QFrontThread: no signal for %s.  Available signals: %s",
                obj.command, self.signals)



class QMultiProcess(Process):
    """
    Multiprocessing scheme with one multiprocess and a "frontend thread" for listening the multiprocess

    ::

        self.front_pipe      : write messages to multiprocess / read messages from multiprocess
        self.back_pipe       : multiprocess reads / writes messages to frontend
        self.qt_front_thread : watches self.front_pipe to read MessageObject instances from multiprocess and turns them into Qt signals

        slots write directly to self.front_pipe

        - Multiprocess expects MessageObject instances from self.back_pipe
        - MessageObject coming from self.back_pipe is mapped into a backend method
        
        - Backend sends MessageObject instances to self.back_pipe => self.front_pipe
        - These are being read by self.qt_front_thread [QFrontThread]


    Here outgoing messages are mapped to Qt signals.  Without Qt, could use normal threading.Thread and mapping of messages to callbacks
    """

    timeout = 1.0

    class Signals(QtCore.QObject):
        pong = QtCore.Signal(object) # demo outgoing signal


    # **** define here backend methods that correspond to incoming slots
    # **** 

    def c__ping(self, lis = []):
        print("c__ping:", lis)
        self.send_out__(MessageObject("pong", lis = [1,2,3]))

    # ****


    def __init__(self, name = "QMultiProcess"):
        self.name = name
        self.pre = self.__class__.__name__ + "." + self.name
        self.logger = getLogger(self.pre)
        super().__init__()
        self.signals = self.Signals()
        print("class, signals:", self.__class__.__name__, self.signals)
        self.front_pipe, self.back_pipe = Pipe() # incoming messages
        self.qt_front_thread = QFrontThread(self.signals, self.front_pipe)
        self.loop = True
        self.listening = False # are we listening something else than just the intercom pipes?

    def __str__(self):
        return "<"+self.pre+">"

    def setDebug(self):
        setLogger(self.logger, logging.DEBUG)
        # self.qt_front_thread.setDebug() # lets not do this..


    # **** backend ****

    def run(self):
        while self.loop:
            if self.listening:
                self.readPipes__(timeout = 0) # timeout = 0 == just poll
            else:
                self.readPipes__(timeout = self.timeout) # timeout of 1 sec

        # indicate front end qt thread to exit
        self.back_pipe.send(None)
        self.logger.debug("bye!")


    def readPipes__(self, timeout):
        """Multiplex all intercom pipes
        """
        rlis = [self.back_pipe]
        r, w, e = safe_select(rlis, [], [], timeout = timeout) # timeout = 0 == this is just a poll
        # handle the main intercom pipe
        if self.back_pipe in r:
            obj = self.back_pipe.recv()
            r.remove(self.back_pipe)
            self.routeMainPipe__(obj)
        # in your subclass, handle rest of the pipes


    def routeMainPipe__(self, obj):
        """Object from main pipe:
            
        - object.command
        - object.kwargs
        
        => route to "c__command(**kwargs)"
        """
        if obj is None:
            self.loop = False
            return

        method_name = "c__%s" % (obj.command)
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            try:
                method(**obj.kwargs)
            except TypeError:
                self.logger.warning("routeMainPipe : could not call method %s with parameters %s" % (method_name, obj.kwargs))
                raise
        else:
            self.logger.warning("routeMainPipe : no such method %s" %(method_name))


    def send_out__(self, obj):
        """Pickle obj & send to outgoing pipe
        """
        # print("send_out__", obj)
        self.back_pipe.send(obj) # these are mapped to Qt signals



    # **** frontend ****

    def sendMessageToBack(self, message: MessageObject):
        self.front_pipe.send(message)

    def go(self):
        self.qt_front_thread.start()
        self.start()

    def requestStop(self):
        self.sendMessageToBack(None)
        
    def waitStop(self):
        self.join()
        self.qt_front_thread.wait()

    def stop(self):
        self.requestStop()
        self.waitStop()

    # **** slots ****

    def ping_slot(self):
        self.sendMessageToBack(MessageObject("ping", lis = [1,2,3]))
        


def test1():
    mp = QMultiProcess()
    mp.go()
    time.sleep(3)
    print("try ping")
    mp.ping_slot()
    time.sleep(3)
    print("exit")
    mp.requestStop()
    mp.waitStop()



if __name__ == "__main__":
    import logging    
    setLogger(logger, logging.DEBUG)
    test1()
    """TODO

    - Test with Qt window: press button => mp => outgoing signal to qlabel
    - Create multiprocess (yolo) listening to several client processes.  Use pipe_handller.
    """
