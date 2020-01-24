"""
base.py : Yolo v3 object detector for Valkka Live

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 0.12.1 
@brief   Yolo v3 object detector for Valkka Live
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
import logging

from valkka.api2 import parameterInitCheck, typeCheck
from valkka.live.multiprocess import MessageObject
from valkka.mvision.multiprocess import test_process, test_with_file, MVisionClientBaseProcess
from valkka.live import style
from valkka.live.tools import getLogger, setLogger


class MVisionClientProcess(MVisionClientBaseProcess):

    name = "YOLO v3 client"
    tag = "yolo3client"
    max_instances = 5
    master = "yolo3master" # name tag of the required master process
    auto_menu = True # append automatically to valkka live machine vision menu or not
    
    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    class Signals(QtCore.QObject):
        pong = QtCore.Signal(object) # demo outgoing signal
        shmem_server = QtCore.Signal(object) # launched when the mvision process has established a shared mem server
        objects = QtCore.Signal(object)
        bboxes  = QtCore.Signal(object)

    parameter_defs = {
        "verbose": (bool, False)
    }

    def __init__(self, **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(name = self.__class__.name)
        # self.setDebug()

    def preRun_(self):
        super().preRun_()
        retval, self.baseline = cv2.getTextSize("A", cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        print("retval, baseline", retval, self.baseline)


    def postRun_(self):
        super().postRun_()


    def cycle_(self):
        lis=[]
        self.logger.debug("cycle_ starts")
        index, meta = self.client.pullFrame()
        if (index is None):
            self.logger.debug("Client timed out..")
            return
        
        self.logger.debug("Client index = %s", index)
        if meta.size < 1:
            return

        data = self.client.shmem_list[index][0:meta.size]
        img = data.reshape(
            (meta.height, meta.width, 3))

        scale = numpy.array([meta.height, meta.width])
        self.logger.debug("cycle_: got frame %s", img.shape)

        img_ = img.copy()

        if self.server is not None:
            self.logger.debug("cycle_ : pushing to server")
            self.server.pushFrame(
                img,
                meta.slot,
                meta.mstimestamp
            )
            # receive results from master process
            replies = self.master_pipe.recv()
            self.logger.debug("reply from master process: %s", replies)
            if replies is not None:
                object_list = []
                bbox_list = []
                for reply in replies:
                    if isinstance(reply, str):
                        object_list.append(reply)
                    else:
                        tag = reply[0]
                        x0 = reply[1] 
                        x1 = reply[2]
                        y0 = reply[3]
                        y1 = reply[4]

                        object_list.append(tag)
                        bbox_list.append((x0, x1, y0, y1))
                        # yolo: origo at left lower corner
                        y0 = 1 - y0 # numpy / opencv: origo at left upper corner
                        y1 = 1 - y1

                        # start: lower left corner of the box
                        start = (int(x0 * meta.width), int(y0 * meta.height))
                        # end: upper right corner of the box
                        end = (int( x1 * meta.width), int( y1 * meta.height))
                        
                        linew = 3 # object box linewidth
                        label = (int(x0 * meta.width), int(y1 * meta.height) + self.baseline + linew + 2) # object label coordinates
                        """
                        print(">", x0, x1, y0, y1)
                        print("width, height", meta.width, meta.height)
                        print("start", start)
                        print("end", end)
                        """
                        color = (255, 0, 0)
                        img_ = cv2.rectangle(img_, start, end, color, linew)
                        cv2.putText(img_, tag, label, cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)

                self.send_out__(MessageObject("objects", object_list = object_list))
                self.send_out__(MessageObject("bboxes", bbox_list = bbox_list))

        """
        reply can be:
        
        - None
        - A list
            - a tuple
                (nametag, x, y, w, h)
            - string
        """
        if self.qt_server is not None:
            self.logger.info("pushing frame to server")
            self.qt_server.pushFrame(
                img_,
                meta.slot,
                meta.mstimestamp
            )


    # *** create a widget for this machine vision module ***
    def getWidget(self):
        """Some ideas for your widget:
        - Textual information (alert, license place number)
        - Check boxes : if checked, send e-mail to your mom when the analyzer spots something
        - .. or send an sms to yourself
        - You can include the cv2.imshow window to the widget to see how the analyzer proceeds
        """
        self.widget = QtWidgets.QTextEdit()
        self.widget.setStyleSheet(style.detector_test)
        self.widget.setReadOnly(True)
        self.signals.objects.connect(self.objects_slot)
        return self.widget
    
    def objects_slot(self, message_object):
        txt=""
        for o in message_object["object_list"]:
            txt += str(o) + "\n"
        self.widget.setText(txt)
        
        
def test1():
    """nada
    """
    pass

def test2():
    """Demo here the OpenCV highgui with valkka
    """
    pass


def test3():
    """Test the multiprocess
    """
    import time
    test_process(MVisionClientProcess)

    
def test4():
    test_with_file(MVisionClientProcess)


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
