"""
multiprocess.py : multiprocess / Qt intercommunication through pipes and signals

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    multiprocess.py
@author  Sampsa Riikonen
@date    2018
@version 0.4.0 
@brief   multiprocess / Qt intercommunication through pipes and signals
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
from valkka.api2 import ValkkaProcess, Namespace, safe_select, ShmemRGBClient
from valkka.api2.tools import *


class QValkkaProcess(ValkkaProcess):
    """A multiprocess with Qt signals
    """

    incoming_signal_defs = {  # each key corresponds to a front- and backend methods
        "test_": {"test_int": int, "test_str": str},
        "stop_": [],
        "ping_": {"message": str}
    }

    outgoing_signal_defs = {
        "pong_o": {"message": str}
    }

    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    class Signals(QtCore.QObject):
        # pong_o  =QtCore.pyqtSignal(object)
        pong_o = QtCore.Signal(object)

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.signals = self.Signals()

    def cycle_(self):
        # Do whatever your process should be doing, remember timeout every now
        # and then
        time.sleep(0.5)
        # print(self.pre,"hello!")

    # *** backend methods corresponding to incoming signals ***

    def stop_(self):
        self.running = False

    def test_(self, test_int=0, test_str="nada"):
        print(self.pre, "test_ signal received with", test_int, test_str)

    def ping_(self, message="nada"):
        print(
            self.pre,
            "At backend: ping_ received",
            message,
            "sending it back to front")
        self.sendSignal_(name="pong_o", message=message)

    # ** frontend methods launching incoming signals

    def stop(self):
        self.sendSignal(name="stop_")

    def test(self, **kwargs):
        dictionaryCheck(self.incoming_signal_defs["test_"], kwargs)
        kwargs["name"] = "test_"
        self.sendSignal(**kwargs)

    def ping(self, **kwargs):
        dictionaryCheck(self.incoming_signal_defs["ping_"], kwargs)
        kwargs["name"] = "ping_"
        self.sendSignal(**kwargs)

    # ** frontend methods handling received outgoing signals ***
    def pong_o(self, message="nada"):
        print("At frontend: pong got message", message)
        ns = Namespace()
        ns.message = message
        self.signals.pong_o.emit(ns)


class QValkkaOpenCVProcess(ValkkaProcess):
    """A multiprocess with Qt signals, using OpenCV.  Reads RGB images from shared memory
    """

    incoming_signal_defs = {  # each key corresponds to a front- and backend methods
        "test_": {"test_int": int, "test_str": str},
        "stop_": [],
        "ping_": {"message": str}
    }

    outgoing_signal_defs = {
        "pong_o": {"message": str}
    }

    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    class Signals(QtCore.QObject):
        # pong_o  =QtCore.pyqtSignal(object)
        pong_o = QtCore.Signal(object)

    parameter_defs = {
        "n_buffer"         : (int, 10),
        "image_dimensions" : tuple,
        "shmem_name"       : str,
        "verbose"          : (bool, False)
    }

    def __init__(self, name, affinity=-1, **kwargs):
        super().__init__(name, affinity, **kwargs)
        self.signals = self.Signals()
        parameterInitCheck(QValkkaOpenCVProcess.parameter_defs, kwargs, self)
        typeCheck(self.image_dimensions[0], int)
        typeCheck(self.image_dimensions[1], int)
        
        
    def report(self, *args):
        if (self.verbose):
            print(self.pre, *args)

    
    def preRun_(self):
        """Create the shared memory client after fork
        """
        self.report("preRun_")
        super().preRun_()
        self.client = ShmemRGBClient(
            name=self.shmem_name,
            n_ringbuffer=self.n_buffer,   # size of ring buffer
            width=self.image_dimensions[0],
            height=self.image_dimensions[1],
            # client timeouts if nothing has been received in 1000 milliseconds
            mstimeout=1000,
            verbose=False
        )

    def cycle_(self):
        index, isize = self.client.pull()
        if (index is None):
            print(self.pre, "Client timed out..")
        else:
            print(self.pre, "Client index, size =", index, isize)
            data = self.client.shmem_list[index]
            img = data.reshape(
                (self.image_dimensions[1], self.image_dimensions[0], 3))
            """ # WARNING: the x-server doesn't like this, i.e., we're creating a window from a separate python multiprocess, so the program will crash
            print(self.pre,"Visualizing with OpenCV")
            cv2.imshow("openCV_window",img)
            cv2.waitKey(1)
            """
            print(self.pre, ">>>", data[0:10])

            # res=self.analyzer(img) # does something .. returns something ..

    # *** backend methods corresponding to incoming signals ***

    def stop_(self):
        self.running = False

    def test_(self, test_int=0, test_str="nada"):
        print(self.pre, "test_ signal received with", test_int, test_str)

    def ping_(self, message="nada"):
        print(
            self.pre,
            "At backend: ping_ received",
            message,
            "sending it back to front")
        self.sendSignal_(name="pong_o", message=message)

    # ** frontend methods launching incoming signals

    def stop(self):
        self.sendSignal(name="stop_")

    def test(self, **kwargs):
        dictionaryCheck(self.incoming_signal_defs["test_"], kwargs)
        kwargs["name"] = "test_"
        self.sendSignal(**kwargs)

    def ping(self, **kwargs):
        dictionaryCheck(self.incoming_signal_defs["ping_"], kwargs)
        kwargs["name"] = "ping_"
        self.sendSignal(**kwargs)

    # ** frontend methods handling received outgoing signals ***
    def pong_o(self, message="nada"):
        print(self.pre, "At frontend: pong got message", message)
        ns = Namespace()
        ns.message = message
        self.signals.pong_o.emit(ns)


class QValkkaThread(QtCore.QThread):
    """A QThread that sits between multiprocesses message pipe and Qt's signal system

    The processes have methods that launch ingoing signals (like ping(message="hello")) and Qt signals that can be connected to slots (e.g. process.signals.pong_o.connect(slot))
    
    The processes should be started before passing them to addProcess
    
    """

    def __init__(self, timeout=1, verbose=False):
        super().__init__()
        self.verbose = verbose
        self.pre = self.__class__.__name__ + " : "
        self.timeout = timeout
        self.processes = []
        self.process_by_pipe = {}
        
        self.add_list = []
        self.del_list = []
        self.mutex = QtCore.QMutex()
            
            
    def report(self, *args):
        if (self.verbose):
            print(self.pre, *args)

            
    def preRun(self):
        # self.mutex = QtCore.QMutex()
        pass

    def postRun(self):
        self.del_list = self.processes
        # print(self.pre, "postRun: del_list", self.del_list)
        self.handleProcesses()
            
            
    def run(self):
        self.preRun()
        self.loop = True

        self.rlis = []
        self.wlis = []
        self.elis = []
        for key in self.process_by_pipe:
            self.rlis.append(key)

        while self.loop:
            tlis = safe_select(self.rlis, self.wlis, self.elis, timeout=self.timeout)
            for pipe in tlis[0]:
                # let's find the process that sent the message to the pipe
                p = self.process_by_pipe[pipe]
                # print("receiving from",p,"with pipe",pipe)
                st = pipe.recv()  # get signal from the process
                # print("got from  from",p,"with pipe",pipe,":",st)
                p.handleSignal(st)

            self.handleProcesses()
            
        self.postRun()
        # print(self.pre, "bye!")

    def stop(self):
        self.loop = False
        self.wait()

    def addProcess(self, p): # p: valkka.api2.multiprocess.ValkkaProcess derived class
        # print(self.pre, "addProcess :", p)
        assert(issubclass(p.__class__, ValkkaProcess))
        self.mutex.lock()
        # print(self.pre, "addProcess : add", p)
        self.add_list.append(p)
        self.mutex.unlock()
        # print(self.pre, "addProcess : added", p)
    
    def delProcess(self, p):
        assert(issubclass(p.__class__, ValkkaProcess))
        self.mutex.lock()
        self.del_list.append(p)
        self.mutex.unlock()

    def handleProcesses(self):
        self.mutex.lock()
        for p in self.add_list:
            self.processes.append(p)
            self.process_by_pipe[p.getPipe()] = p
            self.rlis.append(p.getPipe())
            # print(self.pre, "handleProcess : starting multiprocess", p)
            # p.start() # for some reason, this sucks
            # p.run() # debugging
            # print(self.pre, "handleProcess : started multiprocess", p)
        self.add_list = []
            
        for p in self.del_list:
            # print(self.pre, "handleProcess : removing multiprocess", p)
            try:
                self.processes.remove(p)
            except ValueError:
                pass
            else:
                self.process_by_pipe.pop(p.getPipe())
                self.rlis.remove(p.getPipe())
                print(self.pre, "handleProcess: stopping", p)
                p.stop()
        self.del_list=[]
        self.mutex.unlock()
        #"""
        #print(self.pre, "handleProcess : bye")
        #for p in self.processes:
        #    print(self.pre, "handleProcess :",p)
        #"""


    """
    def __getattr__(self, attr):
        return self.process_by_name[attr]
    """

    def __getitem__(self, i):
        return self.processes[i]


class MyGui(QtWidgets.QMainWindow):
    """An example demo GUI
    """

    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.initVars()
        self.setupUi()

    def initVars(self):
        self.process1 = QValkkaProcess("process1")
        self.process2 = QValkkaProcess("process2")

        self.process1.start()
        self.process2.start()

        self.thread = QValkkaThread(processes=[self.process1, self.process2])
        self.thread.start()

    def setupUi(self):
        self.setGeometry(QtCore.QRect(100, 100, 500, 500))
        self.w = QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)

        self.lay = QtWidgets.QGridLayout(self.w)

        self.button1 = QtWidgets.QPushButton("Button 1", self.w)
        self.button2 = QtWidgets.QPushButton("Button 2", self.w)

        self.check1 = QtWidgets.QRadioButton(self.w)
        self.check2 = QtWidgets.QRadioButton(self.w)

        self.lay.addWidget(self.button1, 0, 0)
        self.lay.addWidget(self.check1, 0, 1)
        self.lay.addWidget(self.button2, 1, 0)
        self.lay.addWidget(self.check2, 1, 1)

        self.button1.clicked.connect(self.button1_slot)
        self.button2.clicked.connect(self.button2_slot)

        self.process1.signals.pong_o.connect(self.pong1_slot)
        self.process2.signals.pong_o.connect(self.pong2_slot)

    def button1_slot(self):
        self.process1.ping(message="<sent ping from button1>")
        self.check1.setChecked(True)

    def button2_slot(self):
        self.process2.ping(message="<sent ping from button2>")
        self.check2.setChecked(True)

    def pong1_slot(self, ns):
        print("pong1_slot: message=", ns.message)

    def pong2_slot(self, ns):
        print("pong2_slot: message=", ns.message)

    def closeEvent(self, e):
        print("closeEvent!")
        self.process1.stop()
        self.process2.stop()
        self.thread.stop()
        super().closeEvent(e)


def main():
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()
