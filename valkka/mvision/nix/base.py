"""
nix.py : Communicate with your machine vision analyzer through stdout, stdin and the filesystem

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    nix.py
@author  Sampsa Riikonen
@date    2018
@version 0.5.0 
@brief   Communicate with your machine vision analyzer through stdout, stdin and the filesystem
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
import os
import numpy
# import cv2
import imutils
from valkka.api2 import parameterInitCheck, typeCheck

# local imports
from valkka.mvision.base import Analyzer
from valkka.mvision.multiprocess import QValkkaOpenCVProcess
from valkka.mvision import tools, constant

pre = "valkka.mvision.movement.base : "

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
        self.pre = self.__class__.__name__ + ":"
        self.init()

    def init(self):
        """Start the process
        """
        import subprocess
        import fcntl
        
        width = str(self.image_dimensions[0])
        height = str(self.image_dimensions[1])
        
        try:
            self.p = subprocess.Popen([self.executable, width, height, self.tmpfile], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        except Exception as e:
            print(self.pre, "Could not open external process.  Failed with '"+str(e)+"'")
            return
        
        """
        fd = self.p.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        """
        
        self.reset()


    def reset(self):
        """Tell the external analyzer to reset itself
        """
        self.report("sending reset")
        try:
            self.p.stdin.write(bytes("T\n","utf-8"))
            self.p.stdin.flush()
        except IOError:
            self.report("could not send reset command")


    def close(self):
        """Tell the process to exit
        """
        try:
            self.p.stdin.write(bytes("X\n","utf-8"))
            self.p.stdin.flush()
        except IOError:
            self.report("could not send exit command")
        self.p.wait() # wait until the process is closed
        os.remove(self.tmpfile) # clean up the temporary file

    
    def __call__(self, img):
        self.report("got frame :",img.shape)
        
        # before sending the new frame, collect results the analyzer produced from the previous frame
        self.report("waiting for external process")
        st = str(self.p.stdout.readline(),"utf-8")
        self.report("got >"+st+"<")
        
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
            self.report("could not send data")
            
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
        
        
class MVisionProcess(QValkkaOpenCVProcess):
    """A multiprocess that uses stdin, stdout and the filesystem to communicate with an external machine vision program
    """
    
    name = "Stdin, stdout and filesystem example" # NOTE: this class member is required, so that Valkka Live can find the class
    
    # The (example) process that gets executed.  You can find it in the module directory
    executable = os.path.join(tools.getModulePath(),"example_process1.py")
    
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
        "verbose": (bool, False),
        "deadtime": (int, 1)
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
        self.signals.text.emit(message+"\n")

    # *** create a widget for this machine vision module ***
    def getWidget(self):
        widget = QtWidgets.QLabel("NO TEXT YET")
        self.signals.text.connect(lambda message: widget.setText(message))
        return widget
        
    
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
