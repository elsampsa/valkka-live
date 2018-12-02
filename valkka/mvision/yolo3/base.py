"""
base.py : Yolo v3 object detector for Valkka Live

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 0.8.0 
@brief   Yolo v3 object detector for Valkka Live
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
import os
import numpy
# import imutils
import importlib
from valkka.live import style
from valkka.live.tools import getFreeGPU_MB
from valkka.api2 import parameterInitCheck, typeCheck
from valkka.mvision.base import Analyzer
from valkka.mvision.multiprocess import QValkkaShmemProcess2

pre = "valkka.mvision.yolo3.base : "

# if the following works, then darknet is available and the weights file has been downloaded ok
from darknet.api2.constant import get_yolov2_weights_file, get_yolov3_weights_file, get_yolov3_tiny_weights_file
fname = get_yolov3_weights_file()

from valkka.live.version import MIN_DARKNET_VERSION_MAJOR, MIN_DARKNET_VERSION_MINOR, MIN_DARKNET_VERSION_PATCH
from darknet.core import VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH
assert(VERSION_MAJOR >= MIN_DARKNET_VERSION_MAJOR)
assert(VERSION_MINOR >= MIN_DARKNET_VERSION_MINOR)
assert(VERSION_PATCH >= MIN_DARKNET_VERSION_PATCH)


class YoloV3Analyzer(Analyzer):
    """The celebrated Yolo v3 object detector
    """

    parameter_defs = {
        "verbose": (bool, False),   # :param verbose:  Verbose output or not?  Default: False.
        "debug": (bool, False)     
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # checks that kwargs is consistent with parameter_defs.  Attaches
        # parameters as attributes to self
        parameterInitCheck(self.parameter_defs, kwargs, self)
        self.pre = self.__class__.__name__ + " : "
        self.init()
            
            
    def init(self):
        # from darknet.api2.error import WeightMissingError
        from darknet.api2.predictor import get_YOLOv3_Predictor, get_YOLOv3_Tiny_Predictor, get_YOLOv2_Predictor
        self.predictor = get_YOLOv3_Predictor()
        # self.predictor = get_YOLOv3_Tiny_Predictor()
        # self.predictor = get_YOLOv2_Predictor()
        self.reset()
        
    def reset(self):
        pass
        
    def __call__(self, img):
        self.report("analyzing frame :",img.shape)    
        lis = self.predictor(img)
        """
        lis = [ # debugging ..
            ('dog', 99, 134, 313, 214, 542), 
            ('truck', 91, 476, 684, 81, 168),
            ('bicycle', 99, 99, 589, 124, 447)
            ]
        """
        """
        lis = [ # debugging ..
            ('dog', 99, img.shape[0]*0.25, img.shape[0]*0.75, img.shape[1]*0.25, img.shape[1]*0.75)
            ]
        """
        self.report("finished analyzing frame")
        return lis



class MVisionProcess(QValkkaShmemProcess2):
    """
    YOLO v3 object detector
    
    See:
    
    https://github.com/elsampsa/darknet-python
    
    """
    
    name = "YOLO v3 object detector"
    tag = "yolov3"
    max_instances = 1       # just one instance allowed .. this is kinda heavy detector
    
    required_mb = 2700      # required GPU memory in MB
    
    incoming_signal_defs = {  # each key corresponds to a front- and backend method
        # don't touch these three..
        "activate_"     : {"n_buffer": int, "image_dimensions": tuple, "shmem_name": str},
        "deactivate_"   : [],
        "stop_"         : [],
    }

    outgoing_signal_defs = {
        "objects" : {"object_list" : list},
        "bboxes"  : {"bbox_list"   : list}
    }

    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    class Signals(QtCore.QObject):
        objects = QtCore.Signal(object)
        bboxes  = QtCore.Signal(object)

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
        super().preRun_()
        
    def postRun_(self):
        if (self.analyzer): self.analyzer.close() # release any resources acquired by the analyzer
        super().postRun_()
        
        
    def requiredGPU_MB(self, n):
        """Required GPU memory in MBytes
        """
        from darknet.core import darknet_with_cuda
        if (darknet_with_cuda()): # its using cuda
            free = getFreeGPU_MB()
            print("Yolo: requiredGPU_MB: required, free", n, free)
            if (free == -1): # could not detect ..
                return True
            return (free>=n)
        else:
            return True
        
    def postActivate_(self):
        """Whatever you need to do after creating the shmem client
        """
        if (self.requiredGPU_MB(self.required_mb)):
            self.analyzer = YoloV3Analyzer(verbose = self.verbose)
        else:
            self.warning_message = "WARNING: not enough GPU memory!"
            self.analyzer = None
            
        
    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client
        """
        if (self.analyzer): self.analyzer.close()
        self.analyzer = None
        

    def cycle_(self):
        lis=[]
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
            
            if (self.analyzer!=None):
                lis = self.analyzer(img)
            
            """
            print("img.shape=",img.shape)
            for l in lis:
                print(l)
            """
            
            """ # list looks like this:
            [ ('dog', 99, 134, 313, 214, 542), 
            ('truck', 91, 476, 684, 81, 168),
            ('bicycle', 99, 99, 589, 124, 447)
            ]
            """
            
        object_list=[]
        bbox_list=[]
        for l in lis:
            object_list.append(l[0])
            # """
            bbox_list.append((
                l[2]/img.shape[1],  # from pixels to fractional coordinates
                l[3]/img.shape[1],
                l[4]/img.shape[0],
                l[5]/img.shape[0]
            ))
            # """
            
            
        if (hasattr(self, "warning_message")):
            object_list.append(self.warning_message)
  
        # print("YoloV3",bbox_list)
        #if (len(lis)>0):
        self.sendSignal_(name="objects", object_list=object_list)
        self.sendSignal_(name="bboxes",  bbox_list=bbox_list)

    # *** backend methods corresponding to incoming signals ***
    # *** i.e., how the signals are handled inside the running multiprocess
    
    # nada

    # ** frontend methods launching incoming signals
    # *** you can call these after the multiprocess is started
    
    # nada

    # ** frontend methods handling outgoing signals ***
    
    def objects(self, object_list):
        self.signals.objects.emit(object_list)
        
    def bboxes(self, bbox_list):
        self.signals.bboxes.emit(bbox_list)

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
    
    def objects_slot(self, object_list):
        txt=""
        for o in object_list:
            txt += str(o) + "\n"
        self.widget.setText(txt)
        
        
def test1():
    """Dummy-testing the movement analyzer
    """
    analyzer = YoloV3Analyzer(verbose=True, debug=True)

    img = numpy.zeros((1080 // 4, 1920 // 4, 3), dtype=numpy.uint8)
    result = analyzer(img)
    print("\nresult =", result, "\n")

    img = numpy.zeros((1080 // 4, 1920 // 4, 3), dtype=numpy.uint8)
    result = analyzer(img)
    print("\nresult =", result, "\n")

    img = numpy.ones((1080 // 4, 1920 // 4, 3), dtype=numpy.uint8) * 100
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
