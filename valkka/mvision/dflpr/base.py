"""
dflpr.py : Communicate with an external license plate recognition software using stdin, stdout and the filesystem

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    dflpt.py
@author  Sampsa Riikonen
@date    2018
@version 0.5.0 
@brief   Communicate with an external license plate recognition software using stdin, stdout and the filesystem
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
import os
import numpy
import importlib
from valkka.api2 import parameterInitCheck, typeCheck

# local imports
from valkka.mvision.base import Analyzer
from valkka.mvision.multiprocess import QValkkaOpenCVProcess
from valkka.mvision import tools, constant
from valkka.mvision.nix.base import ExternalDetector

assert(os.system("markus-lpr-check") < 1) # is this command installed ?

pre = "valkka.mvision.dflpr.base : "
        
        
class MVisionProcess(QValkkaOpenCVProcess):
    """A multiprocess that uses stdin, stdout and the filesystem to communicate with an external machine vision program
    """
    
    name = "Markus LPR"
    
    # The (example) process that gets executed.  You can find it in the module directory
    executable = os.path.join("markus-lpr-nix")
    
    incoming_signal_defs = {  # each key corresponds to a front- and backend method
        "stop_": []
    }

    outgoing_signal_defs = {
        "text": {"message": str},
    }

    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    #"""
    class Signals(QtCore.QObject):
        text = QtCore.Signal(object)
    #"""

    parameter_defs = {
        "n_buffer": (int, 10),
        "image_dimensions": (tuple, (1920 // 4, 1080 // 4)),
        "shmem_name": str,
        "verbose": (bool, False)
        }

    def __init__(self, **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(self.__class__.name, n_buffer = self.n_buffer, image_dimensions = self.image_dimensions, shmem_name = self.shmem_name)
        self.pre = self.__class__.__name__ + " : " + self.name+ " : "
        self.signals = self.Signals()
        typeCheck(self.image_dimensions[0], int)
        typeCheck(self.image_dimensions[1], int)
        
    def preRun_(self):
        super().preRun_()
        self.tmpfile = os.path.join(constant.tmpdir,"valkka-"+str(os.getpid())) # e.g. "/tmp/valkka-10968" 
        # its a good idea to instantiate the analyzer after the multiprocess has been spawned (like we do here)
        self.analyzer = ExternalDetector(
            executable = self.executable,
            image_dimensions = self.image_dimensions,
            tmpfile = self.tmpfile
            )
            
    def postRun_(self):
        self.analyzer.close() # release any resources acquired by the analyzer
        super().postRun_()

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
            
            if (result != ""):
                self.sendSignal_(name="text", message=result)
            
    def postRun_(self):
        self.analyzer.close()
        super().postRun_()


    # *** backend methods corresponding to incoming signals ***
    # *** i.e., how the signals are handled inside the running multiprocess
    
    def stop_(self):
        self.running = False

    # ** frontend methods launching incoming signals
    # *** you can call these after the multiprocess is started
    
    def stop(self):
        self.sendSignal(name="stop_")

    # ** frontend methods handling outgoing signals ***
    def text(self, message=""):
        self.report("At frontend: text got message", message)
        self.signals.text.emit(message)

    # *** This is used by the modules Qt Widget ***
    def text_slot(self, message=""): # receives a license plate
        self.recent_plates.append(message) # just take the plate, scrap confidence
        if (len(self.recent_plates)>10): # show 10 latest recognized license plates
            self.recent_plates.pop(0)
        st=""
        for plate in self.recent_plates:
            st += plate + "\n"
        self.widget.setText(st)
    
    # *** create a Qt widget for this machine vision module **
    def getWidget(self):
        self.widget = QtWidgets.QTextEdit()
        self.recent_plates = []
        self.signals.text.connect(self.text_slot) 
        return self.widget
    
    
def test1():
    """Dummy-testing the external detector
    """
    width = 1920
    height = 1080
    
    analyzer = ExternalDetector(
        verbose=True, 
        debug=True,
        executable = os.path.join(tools.getModulePath(),"example_process1.py"),
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
    import time
    
    width = 1920
    height = 1080
    
    p = MVisionProcess(
        shmem_name = "test3",
        verbose=True, 
        image_dimensions = (width, height)
        )
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
    p1 = MVisionProcess(shmem_name="test3.1")
    p1.start()
    t.addProcess(p1)
    time.sleep(5)
    
    print("Creating another multiprocess, informing thread")
    p2 = MVisionProcess(shmem_name="test3.2")
    p2.start()
    t.addProcess(p2)
    time.sleep(5)
    
    print("Remove multiprocesses")
    t.delProcess(p1)
    # t.delProcess(p2)
    
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

    shmem_name="test_studio_file"
    shmem_image_dimensions=(1920 // 4, 1080 // 4)
    shmem_image_interval=1000
    shmem_ringbuffer_size=5
    
    ps = MVisionProcess(
            shmem_name = shmem_name, 
            image_dimensions = shmem_image_dimensions,
            n_buffer = shmem_ringbuffer_size
        )
       
    app = QtWidgets.QApplication(["mvision test"])
    fg = FileGUI(mvision_process = ps, shmem_image_interval = shmem_image_interval)
    fg.show()
    app.exec_()
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
