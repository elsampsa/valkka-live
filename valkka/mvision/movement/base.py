"""
base.py : A movement analyzer and the associated multiprocess

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 1.0.0 
@brief   A movement analyzer and the associated multiprocess
"""

# from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot # Qt5
from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot
import sys
import time
import os
import numpy
import imutils
import importlib
import cv2
import logging

from valkka.api2 import parameterInitCheck, typeCheck
from valkka.mvision.base import Analyzer
from valkka.live.multiprocess import MessageObject
from valkka.mvision.multiprocess import test_process, test_with_file, MVisionBaseProcess
from valkka.live import style
from valkka.live.tools import getLogger, setLogger
from valkka.live.qt.widget import SimpleVideoWidget, LineCrossingVideoWidget


class MovementVideoWidget(SimpleVideoWidget):
    """Receives QPixMaps to a slot & draws them

    TODO: mouse gestures, draw lines, boxes, etc.
    """
        
    def __init__(self, def_pixmap = None, parent = None):
        super().__init__(def_pixmap = def_pixmap, parent = parent)

    def drawWidget(self, qp):
        super().drawWidget(qp) # draws the bitmap on the background
        # TODO: draw something more

    def initVars(self):
        self.on = False

    def handle_move(self, info):
        print("MovementVideoWidget: handle_move")

    def handle_left_single_click(self, info):
        self.on = not self.on
        if self.on:
            self.setTracking()
        else:
            self.unSetTracking()

    def handle_right_single_click(self, info):
        print("MovementVideoWidget: handle_right_single_click: sending parameters to analyzer")
        self.signals.update_analyzer_parameters.emit({"some_new":"parameters"})
        # pass

    def handle_left_double_click(self, info):
        pass

    def handle_right_double_click(self, info):
        pass



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
        # self.setDebug()
        if self.debug:
            self.logger.warning("Enabling OpenCV high-gui.  That requires opencv installed with apt-get.  Otherwise, get ready for a segfault..")
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
        self.logger.info("got frame : %s",img.shape)

        # NOTE: this is where all the image analysis takes place.  Implement your own
    
        modframe = imutils.resize(img, width=500)
        self.ismoving = False

        if (self.debug):
            cv2.imshow("SimpleMovementDetector_channels-modframe", modframe)

        modframe = cv2.GaussianBlur(modframe, (21, 21), 0)

        if (self.prevframe.__class__ is None.__class__):  # first frame
            self.prevframe = modframe.copy()
            self.logger.info("First image found!")
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
                self.logger.info("==>MOVEMENT!")
                self.ismoving = True
                if (self.wasmoving):
                    result = self.state_same
                else:
                    self.t0_event = self.t0
                    self.wasmoving = True
                    self.logger.info("==> NEW MOVEMENT EVENT!")
                    result = self.state_start

            else:  # no movement
                dt = time.time() - self.t0  # how much time since the last movement event
                # lets close this event ..
                if (dt >= self.deadtime and self.wasmoving):
                    dt_event = time.time() - self.t0_event
                    self.wasmoving = False
                    result = self.state_stop
                    self.logger.info("==> MOVEMENT STOPPED!")
                else:
                    result = self.state_same

            if (self.debug):
                cv2.imshow("SimpleMovementDetector_channels-delta", delta * 255)

        if (self.debug):
            # cv2.waitKey(40*25) # 25 fps
            # cv2.waitKey(self.frametime)
            cv2.waitKey(1)

        return result



class MVisionProcess(MVisionBaseProcess):
    """ NOTE: the name of the class must always be MVisionProcess, so that Valkka Live can find the class
    
    This is a python multiprocess that runs on the background in its own isolated memory space.
    
    It has "frontend" methods that you can call after it has been started.  The "backend" methods are internal and are running in the background.  They are designated with "_"
    
    The method "cycle_" is a backend method, and implements the machine vision.  From backend, they only way to communicate with the frontend and the outside world is by calling the "sendSignal_" method.
    
    To send a signal from frontend to backend, you must use the "sendSignal" method.  If you use sendSignal("mytest_") then you should implement a backend method "mytest_"
    
    If you define a new signal in "outgoing_signal_defs", you also need to implement a frontend method with the same name.    
        
    Purely python-based machine vision modules need multiprocessing, shared memory and semaphores.  Expect framerates in the 1 fps range to work.  If you need something more serious, write the whole thing in cpp and use valkka cpp infrastructures (see the repository "valkka-cpp-examples")
    """
    
    name = "Simple Movement Detector" # NOTE: this class member is required, so that Valkka Live can find the class
    tag  = "movement" # NOTE: name identifying the detector group
    auto_menu = True # append automatically to valkka live machine vision menu or not
    max_instances = 5 # NOTE: how many detectors belonging to the same group can be instantiated
    # analyzer_video_widget_class = MovementVideoWidget # use this widget class to define parameters for your machine vision (line crossing, zone intrusion, etc.)
    analyzer_video_widget_class = LineCrossingVideoWidget # testing this one ..

    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    #"""
    class Signals(QtCore.QObject):
        pong = Signal(object)
        shmem_server = Signal(object) # launched when the mvision process has established a shared mem server
        start_move = Signal()
        stop_move = Signal()
    #"""

    # backend method

    parameter_defs = {
        "verbose" : (bool, False),
        "deadtime": (int, 1)
    }

    def __init__(self, name = "MVisionProcess", **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(name = name)
        # self.setDebug()
        

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
        
        
    def cycle_(self):
        # NOTE: enable this to see if your multiprocess is alive
        self.logger.debug("cycle_ starts")
        index, meta = self.client.pullFrame()
        if (index is None):
            self.logger.debug("cycle_ : client timed out..")
            return
        
        self.logger.debug("cycle_ : client index = %s", index)
        if meta.size < 1:
            return

        data = self.client.shmem_list[index][0:meta.size]
        img = data.reshape(
            (meta.height, meta.width, 3))
        """ # WARNING: the x-server doesn't like this, i.e., we're creating a window from a separate python multiprocess, so the program will crash
        print(self.pre,"Visualizing with OpenCV")
        cv2.imshow("openCV_window",img)
        cv2.waitKey(1)
        """
        self.logger.debug("cycle_ : got frame %s", img.shape)
        result = self.analyzer(img)

        img_ = img.copy()

        if self.parameters:
            # what we have in parameters, depends on the 
            # analyzer video widget class, i.e. on the widget that
            # interacts with the user for defining the machine vision parameters
            # the class is defined in the class member "analyzer_video_widget_class"
            # and instantiated by MVisionContainer
            # here we're using
            # valkka.live.qt.widget.LineCrossingVideoWidget
            if "line" in self.parameters:
                line = self.parameters["line"]
                # print("line",line)
                start = (int(line[0][0]*img_.shape[1]), int((line[0][1])*img_.shape[0]))
                end =   (int(line[1][0]*img_.shape[1]), int((line[1][1])*img_.shape[0]))
                # print("start", start)
                # print("end",end)
                # # cross-check the line defined in the interactive qt widget
                cv2.line(img_, start, end, (0,255,0), 8)

        if self.qt_server is not None:
            self.logger.info("cycle_ : pushing frame to server")
            # print(">>", img_[0:10])
            self.qt_server.pushFrame(
                img_,
                meta.slot,
                meta.mstimestamp
            )

        # NOTE: you could use and combine several analyzers here, say first see if there is movement and then do the rest
        # print(self.pre,">>>",data[0:10])
        if (result == MovementDetector.state_same):
            pass
        elif (result == MovementDetector.state_start):
            self.send_out__(MessageObject("start_move"))
        elif (result == MovementDetector.state_stop):
            self.send_out__(MessageObject("stop_move"))


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
    test_process(MVisionProcess)

    
def test4():

    if (len(sys.argv) > 2):
        init_filename = sys.argv[2]
    else:
        init_filename = None

    test_with_file(
        MVisionProcess, 
        ["valkka.mvision"],
        shmem_image_interval = 10,
        init_filename = init_filename)



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
