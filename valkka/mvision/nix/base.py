"""
nix.py : Communicate with your machine vision analyzer through stdout, stdin and the filesystem

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    nix.py
@author  Sampsa Riikonen
@date    2018
@version 0.14.1 
@brief   Communicate with your machine vision analyzer through stdout, stdin and the filesystem
"""

# from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot # Qt5
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
from valkka.mvision.tools import getModulePath
from valkka.mvision import constant


class ExternalDetector(Analyzer):
    """A demo analyzer, using an external program
    """

    parameter_defs = {
        "verbose":          (bool, False),
        "debug":            (bool, False),
        "executable":       str,
        "image_dimensions": (tuple, (1920 // 4, 1080 // 4)),
        "tmpfile":          str
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # checks that kwargs is consistent with parameter_defs.  Attaches
        # parameters as attributes to self
        parameterInitCheck(self.parameter_defs, kwargs, self)
        self.init()


    def init(self):
        """Start the process
        """
        import subprocess
        import fcntl
        
        width = str(self.image_dimensions[0])
        height = str(self.image_dimensions[1])
        
        comlist = self.executable.split() + [width, height, self.tmpfile] # e.g. "python3", "example_process1.py", etc.
        
        try:
            self.p = subprocess.Popen(comlist, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        except Exception as e:
            print(self.pre, "Could not open external process.  Failed with '"+str(e)+"'")
            return
        
        self.reset()


    def reset(self):
        """Tell the external analyzer to reset itself
        """
        self.logger.info("sending reset")
        try:
            self.p.stdin.write(bytes("T\n","utf-8"))
            self.p.stdin.flush()
        except IOError:
            self.logger.info("could not send reset command")


    def close(self):
        """Tell the process to exit
        """
        try:
            self.p.stdin.write(bytes("X\n","utf-8"))
            self.p.stdin.flush()
        except IOError:
            self.logger.info("could not send exit command")
        self.p.wait() # wait until the process is closed
        try:
            os.remove(self.tmpfile) # clean up the temporary file
        except FileNotFoundError:
            pass

    
    def __call__(self, img):
        self.logger.info("got frame : %s",img.shape)
        
        # before sending the new frame, collect results the analyzer produced from the previous frame
        self.logger.info("waiting for external process")
        st = str(self.p.stdout.readline(),"utf-8")
        self.logger.info("got >"+st+"<")
        
        if (st=="C\n"):
            result=""
        else:
            result=st[0:-1]
        
        # write the new frame into a tmpfile
        img.dump(self.tmpfile)
        
        # inform the external process that there is a new frame available
        try:
            self.p.stdin.write(bytes("R\n","utf-8"))
            self.p.stdin.flush()
        except IOError:
            self.logger.info("could not send data")
            
        # the data from the previous frame: format here the string into a data structure if you need to
        return result


    def readStdout(self):
        """Not used
        """
        btt = bytes()
        while True:
            bt = self.p.stdout.read(1)
            if bt:
                btt += bt
            else:
                # print("!")
                break
            """
            if (bt == "\n"):
                break
            """
        return btt[0:-1].decode("utf-8")



class MVisionProcess(MVisionBaseProcess):
    """A multiprocess that uses stdin, stdout and the filesystem to communicate with an external machine vision program
    """
    name = "Stdin, stdout and filesystem example"
    tag  = "nix"
    auto_menu = True # append automatically to valkka live machine vision menu or not
    max_instances = 3
    
    # The (example) process that gets executed.  You can find it in the module directory
    executable = "python3 "+os.path.join(getModulePath(),"example_process1.py")
    
    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    #"""
    class Signals(QtCore.QObject):
        pong = Signal(object)
        shmem_server = Signal(object) # launched when the mvision process has established a shared mem server
        text = Signal(object)
    #"""

    parameter_defs = {
        "verbose": (bool, False)
    }

    def __init__(self, name = "MVisionProcess", **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(name = name)
        self.analyzer = None
        
    def preRun_(self):
        super().preRun_()
        self.analyzer = None
        
    def postRun_(self):
        if (self.analyzer): self.analyzer.close()
        super().postRun_() # calls deactivate_ => preDeactivate

    def postActivate_(self):
        """Create temporary file for image dumps and the analyzer itself
        """
        super().postActivate_()
        self.tmpfile = os.path.join(constant.tmpdir,"valkka-"+str(os.getpid())) # e.g. "/tmp/valkka-10968" 
        self.analyzer = ExternalDetector(
            executable = self.executable,
            image_dimensions = self.image_dimensions,
            tmpfile = self.tmpfile,
            verbose = self.verbose
            )
        
    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client
        """
        super().preDeactivate_()
        if (self.analyzer): self.analyzer.close()
        self.analyzer = None
    
    def cycle_(self):
        # NOTE: enable this to see if your multiprocess is alive
        self.logger.info("cycle_ starts")
        """
        index, isize = self.client.pull()
        if (index is None):
            self.logger.info("Client timed out..")
            pass
        else:
            self.logger.info("Client index, size =",index, isize)
            data = self.client.shmem_list[index]
            img = data.reshape(
                (self.image_dimensions[1], self.image_dimensions[0], 3))
            result = self.analyzer(img)
        """
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
        self.logger.debug("got frame %s", img.shape)
        result = self.analyzer(img) # does something .. returns something ..

        if self.qt_server is not None:
            self.logger.info("pushing frame to server")
            self.qt_server.pushFrame(
                img,
                meta.slot,
                meta.mstimestamp
            )

        if (result != ""):
            self.send_out__(MessageObject("text", message = result))
            # self.sendSignal_(name="text", message=result)

    
    # *** create a widget for this machine vision module ***
    def getWidget(self):
        widget = QtWidgets.QLabel("NO TEXT YET")
        widget.setStyleSheet(style.detector_test)
        self.signals.text.connect(lambda message_object:\
            widget.setText(message_object["message"]))
        return widget
        
    
    
def test1():
    """Dummy-testing the external detector
    """
    width = 1920
    height = 1080
    
    analyzer = ExternalDetector(
        verbose=True, 
        debug=True,
        executable = os.path.join(getModulePath(),"example_process1.py"),
        image_dimensions = (width, height),
        tmpfile = "/tmp/valkka-debug"
        )

    img = numpy.zeros((height, width, 3), dtype=numpy.uint8)
    
    for i in range(10):
        img[:,:,:]=i
        result = analyzer(img)
        # time.sleep(1)
        print("result =", result)
    
    analyzer.close()



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

    print("not tested for nix")
    """
    test_with_file(
        MVisionProcess, 
        ["valkka.mvision"],
        shmem_image_interval = 10,
        init_filename = init_filename)
    """



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
