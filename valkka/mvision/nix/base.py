"""
nix.py : Communicate with your machine vision analyzer through stdout, stdin and the filesystem

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    nix.py
@author  Sampsa Riikonen
@date    2018
@version 0.8.0 
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
from valkka.live import style
from valkka.mvision.base import Analyzer
from valkka.mvision.multiprocess import QValkkaShmemProcess2
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
        try:
            os.remove(self.tmpfile) # clean up the temporary file
        except FileNotFoundError:
            pass

    
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



class MVisionProcess(QValkkaShmemProcess2):
    """A multiprocess that uses stdin, stdout and the filesystem to communicate with an external machine vision program
    """
    name = "Stdin, stdout and filesystem example"
    tag  = "nix"
    max_instances = 3
    
    # The (example) process that gets executed.  You can find it in the module directory
    executable = "python3 "+os.path.join(tools.getModulePath(),"example_process1.py")
    
    incoming_signal_defs = {  # each key corresponds to a front- and backend method
        # don't touch these three..
        "activate_"     : {"n_buffer": int, "image_dimensions": tuple, "shmem_name": str},
        "deactivate_"   : [],
        "stop_"         : []
    }

    outgoing_signal_defs = {
        "text": {"message": str}
    }

    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    #"""
    class Signals(QtCore.QObject):
        text = QtCore.Signal(object)
    #"""

    parameter_defs = {
        "verbose": (bool, False)
    }

    def __init__(self, **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(self.__class__.name)
        self.pre = self.__class__.__name__ + ":" + self.name+ " : "
        self.signals = self.Signals()
        
        
    def preRun_(self):
        self.analyzer = None
        super().preRun_() # calls deactivate_ => preDeactivate_
        
    def postRun_(self):
        if (self.analyzer): self.analyzer.close()
        super().postRun_() # calls deactivate_ => preDeactivate

    def postActivate_(self):
        """Create temporary file for image dumps and the analyzer itself
        """
        self.tmpfile = os.path.join(constant.tmpdir,"valkka-"+str(os.getpid())) # e.g. "/tmp/valkka-10968" 
        self.analyzer = ExternalDetector(
            executable = self.executable,
            image_dimensions = self.image_dimensions,
            tmpfile = self.tmpfile
            )
        
    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client
        """
        if (self.analyzer): self.analyzer.close()
        self.analyzer = None
    
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
        widget.setStyleSheet(style.detector_test)
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
