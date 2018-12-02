"""
base.py : A movement analyzer and the associated multiprocess

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 0.8.0 
@brief   A movement analyzer and the associated multiprocess
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
import os
import numpy
import imutils
import importlib
import cv2
from valkka.api2 import parameterInitCheck, typeCheck
from valkka.mvision.base import Analyzer
from valkka.mvision.multiprocess import QValkkaShmemProcess2
from valkka.live import style

pre = "valkka.mvision.movement.base : "


class MovementDetector(Analyzer):
    """A demo movement detector, written using OpenCV
    """

    # return values:
    state_same = 0  # no state change
    state_start = 1  # movement started
    state_stop = 2  # movement stopped

    parameter_defs = {
        # :param verbose:  Verbose output or not?  Default: False.
        "verbose": (bool, False),
        # :param debug:    When this is True, will visualize on screen what the analyzer is doing.  Uses OpenCV highgui.  WARNING: this will not work with multithreading/processing.
        "debug": (bool, False),
        # :param deadtime: Movement inside this time interval belong to the same event
        "deadtime": (int, 3),
        # :param treshold: How much movement is an event (area of the image place)
        "treshold": (float, 0.001)
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # checks that kwargs is consistent with parameter_defs.  Attaches
        # parameters as attributes to self
        parameterInitCheck(self.parameter_defs, kwargs, self)
        self.pre = self.__class__.__name__ + " : "
        self.init()
            

    def init(self):
        self.reset()
        
    def reset(self):
        """Reset analyzer state
        """
        self.prevframe = None
        self.wasmoving = False
        self.t0 = 0
        self.ismoving = False
        
    def isMoving(self):
        return self.ismoving
        
    def __call__(self, img):
        self.report("got frame :",img.shape)

        # NOTE: this is where all the image analysis takes place.  Implement your own
    
        modframe = imutils.resize(img, width=500)
        self.ismoving = False

        if (self.debug):
            cv2.imshow("SimpleMovementDetector_channels-modframe", modframe)

        modframe = cv2.GaussianBlur(modframe, (21, 21), 0)

        if (self.prevframe.__class__ is None.__class__):  # first frame
            self.prevframe = modframe.copy()
            self.report("First image found!")
            result = self.state_same

        else:  # second or n:th frame
            delta = cv2.absdiff(self.prevframe.max(2), modframe.max(2))
            if (self.debug):
                cv2.imshow("SimpleMovementDetector_channels-delta0", delta)
            delta = cv2.threshold(delta, 100, 1, cv2.THRESH_BINARY)[
                1]  # TODO: how much treshold here..?
            val = delta.sum() / (delta.shape[0] * delta.shape[1])
            # print(self.pre,"MovementDetector: val=",val)
            self.prevframe = modframe.copy()

            if (val >= self.treshold):  # one promille ok .. there is movement
                self.t0 = time.time()
                self.report("==>MOVEMENT!")
                self.ismoving = True
                if (self.wasmoving):
                    result = self.state_same
                else:
                    self.t0_event = self.t0
                    self.wasmoving = True
                    self.report("==> NEW MOVEMENT EVENT!")
                    result = self.state_start

            else:  # no movement
                dt = time.time() - self.t0  # how much time since the last movement event
                # lets close this event ..
                if (dt >= self.deadtime and self.wasmoving):
                    dt_event = time.time() - self.t0_event
                    self.wasmoving = False
                    result = self.state_stop
                    self.report("==> MOVEMENT STOPPED!")
                else:
                    result = self.state_same

            if (self.debug):
                cv2.imshow("SimpleMovementDetector_channels-delta", delta * 255)

        if (self.debug):
            # cv2.waitKey(40*25) # 25 fps
            # cv2.waitKey(self.frametime)
            cv2.waitKey(1)

        return result



class MVisionProcess(QValkkaShmemProcess2):
    """ NOTE: the name of the class must always be MVisionProcess, so that Valkka Live can find the class
    
    This is a python multiprocess that runs on the background in its own isolated memory space.
    
    It has "frontend" methods that you can call after it has been started.  The "backend" methods are internal and are running in the background.  They are designated with "_"
    
    The method "cycle_" is a backend method, and implements the machine vision.  From backend, they only way to communicate with the frontend and the outside world is by calling the "sendSignal_" method.
    
    To send a signal from frontend to backend, you must use the "sendSignal" method.  If you use sendSignal("mytest_") then you should implement a backend method "mytest_"
    
    If you define a new signal in "outgoing_signal_defs", you also need to implement a frontend method with the same name.
    
    This is what goes on under-the-hood:
    
    ::
    
        sendSignal_(name = "start_move") sends a signal to an interprocess communication pipe 
        => that pipe is read by a valkka.mvision.multiprocess.QValkkaThread => QValkkaThread gets a signal_string
        => QValkkaThread calls handleSignal(signal_string) method from this class (inherited from ValkkaProcess)
        => ValkkaProcess.handleSignal searches for a frontend method in this class, corresponding to signal_string
        
        
    Purely python-based machine vision modules need multiprocessing, shared memory and semaphores.  Expect framerates in the 1 fps range to work.  If you need something more serious, write the whole thing in cpp and use valkka cpp infrastructures (see the repository "valkka-cpp-examples")
    """
    
    name = "Simple Movement Detector" # NOTE: this class member is required, so that Valkka Live can find the class
    tag  = "movement" # NOTE: name identifying the detector group
    max_instances = 5 # NOTE: how many detectors belonging to the same group can be instantiated
    
    incoming_signal_defs = {  # each key corresponds to a front- and backend method
        
        # don't touch these three..
        "activate_"     : {"n_buffer": int, "image_dimensions": tuple, "shmem_name": str},
        "deactivate_"   : [],
        "stop_"         : [],

        "test_"         : {"test_int": int, "test_str": str},
        "ping_"         : {"message": str}
    }

    outgoing_signal_defs = {
        "pong_o"        : {"message": str},
        "start_move"    : {},
        "stop_move"     : {}
    }

    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    #"""
    class Signals(QtCore.QObject):
        pong_o = QtCore.Signal(object)
        start_move = QtCore.Signal()
        stop_move = QtCore.Signal()
    #"""

    parameter_defs = {
        "verbose": (bool, False),
        "deadtime": (int, 1)
    }

    def __init__(self, **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(self.__class__.name)
        self.pre = self.__class__.__name__ + ":" + self.name+ " : "
        self.signals = self.Signals()
        
    def preRun_(self):
        super().preRun_()
        # its a good idea to instantiate the analyzer after the multiprocess has been spawned (like we do here)
        self.analyzer = MovementDetector(
            treshold    =0.0001,
            verbose     =self.verbose,
            deadtime    =self.deadtime
        )
        
    def postRun_(self):
        self.analyzer.close() # release any resources acquired by the analyzer
        super().postRun_()
        
    
    def postActivate_(self):
        """Whatever you need to do after creating the shmem client
        """
        pass
        
    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client
        """
        pass
        

    def cycle_(self):
        # NOTE: enable this to see if your multiprocess is alive
        self.report("cycle_ starts")
        index, isize = self.client.pull()
        if (index is None):
            self.report("Client timed out..")
            pass
        else:
            self.report("Client index, size =",index, isize)
            data = self.client.shmem_list[index]
            img = data.reshape(
                (self.image_dimensions[1], self.image_dimensions[0], 3))
            result = self.analyzer(img)
            # NOTE: you could use and combine several analyzers here, say first see if there is movement and then do the rest
            # print(self.pre,">>>",data[0:10])

            if (result == MovementDetector.state_same):
                pass
            elif (result == MovementDetector.state_start):
                self.sendSignal_(name="start_move")
            elif (result == MovementDetector.state_stop):
                self.sendSignal_(name="stop_move")


    # *** backend methods corresponding to incoming signals ***
    # *** i.e., how the signals are handled inside the running multiprocess
    
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
    # *** you can call these after the multiprocess is started
    
    def test(self, **kwargs):
        dictionaryCheck(self.incoming_signal_defs["test_"], kwargs)
        kwargs["name"] = "test_"
        self.sendSignal(**kwargs)

    def ping(self, **kwargs):
        dictionaryCheck(self.incoming_signal_defs["ping_"], kwargs)
        kwargs["name"] = "ping_"
        self.sendSignal(**kwargs)


    # ** frontend methods handling outgoing signals ***
    
    def pong_o(self, message="nada"):
        print(self.pre, "At frontend: pong got message", message)
        ns = Namespace()
        ns.message = message
        self.signals.pong_o.emit(ns)

    def start_move(self):
        print(self.pre, "At frontend: got movement")
        self.signals.start_move.emit()

    def stop_move(self):
        print(self.pre, "At frontend: movement stopped")
        self.signals.stop_move.emit()


    # *** create a widget for this machine vision module ***
    def getWidget(self):
        """Some ideas for your widget:
        - Textual information (alert, license place number)
        - Check boxes : if checked, send e-mail to your mom when the analyzer spots something
        - .. or send an sms to yourself
        - You can include the cv2.imshow window to the widget to see how the analyzer proceeds
        """
        widget = QtWidgets.QLabel("NO MOVEMENT YET")
        widget.setStyleSheet(style.detector_test)
        self.signals.start_move.connect(lambda : widget.setText("MOVEMENT START"))
        self.signals.stop_move. connect(lambda : widget.setText("MOVEMENT STOP"))
        return widget
        
    
    
def test1():
    """Dummy-testing the movement analyzer
    """
    analyzer = MovementDetector(verbose=True, debug=True)

    img = numpy.zeros((1080 // 4, 1920 // 4, 3))
    result = analyzer(img)
    print("\nresult =", result, "\n")

    img = numpy.zeros((1080 // 4, 1920 // 4, 3))
    result = analyzer(img)
    print("\nresult =", result, "\n")

    img = numpy.ones((1080 // 4, 1920 // 4, 3)) * 100
    result = analyzer(img)
    print("\nresult =", result, "\n")


def test2():
    """Demo here the OpenCV highgui with valkka
    """
    pass


def test3():
    """Test the multiprocess
    """
    import time
    
    p = MVisionProcess()
    p.start()
    time.sleep(5)
    p.stop()
    
    
def test4():
    """Test multiprocess with outgoing signals
    """
    import time
    from valkka.mvision import QValkkaThread
    
    t = QValkkaThread()
    t.start()
    time.sleep(1)
    # t.stop(); return
    
    print("Creating multiprocess, informing thread")
    p1 = MVisionProcess()
    p1.start()
    t.addProcess(p1)
    time.sleep(5)
    
    print("Creating another multiprocess, informing thread")
    p2 = MVisionProcess()
    p2.start()
    t.addProcess(p2)
    time.sleep(5)
    
    print("Remove multiprocesses")
    t.delProcess(p1)
    # t.delProcess(p2)
    
    p1.stop()
    p2.stop()
    
    print("bye")
    
    t.stop()
    
    
def test5():
    """Test the analyzer process with files
    
    They must be encoded and muxed correctly, i.e., with:
    
    ::
    
        ffmpeg -i your_video_file -c:v h264 -an outfile.mkv
    
    """
    import time
    from valkka.mvision.file import FileGUI

    # from valkka.mvision import QValkkaThread
    
    #t = QValkkaThread()
    #t.start()
    
    # """
    ps = MVisionProcess()
    # """
       
    #t.addProcess(ps)
    #time.sleep(5)
    #t.stop()
    #return

    app = QtWidgets.QApplication(["mvision test"])
    fg = FileGUI(
        mvision_process = ps, 
        shmem_name              ="test_studio_file",
        shmem_image_dimensions  =(1920 // 2, 1080 // 2),
        shmem_image_interval    =1000,
        shmem_ringbuffer_size   =5
        )
    # fg = FileGUI(MVisionProcess, shmem_image_interval = shmem_image_interval)
    fg.show()
    app.exec_()
    ps.stop()
    print("bye from app!")
    
    
    
def main():
    pre = "main :"
    print(pre, "main: arguments: ", sys.argv)
    if (len(sys.argv) < 2):
        print(pre, "main: needs test number")
    else:
        st = "test" + str(sys.argv[1]) + "()"
        exec(st)


if (__name__ == "__main__"):
    main()
