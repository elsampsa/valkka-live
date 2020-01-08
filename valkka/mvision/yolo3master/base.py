"""
base.py : Yolo v3 object detector for Valkka Live

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 0.11.0 
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
from valkka.mvision.base import Analyzer
from valkka.live.multiprocess import MessageObject
from valkka.mvision.multiprocess import QShmemMasterProcess
from valkka.live import style
from valkka.live.tools import getLogger, setLogger, getFreeGPU_MB

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
        self.init()
            
            
    def init(self):
        # from darknet.api2.error import WeightMissingError
        from darknet.api2.predictor import get_YOLOv3_Predictor, get_YOLOv3_Tiny_Predictor, get_YOLOv2_Predictor
        # self.predictor = get_YOLOv3_Predictor()
        self.predictor = get_YOLOv3_Tiny_Predictor()
        # self.predictor = get_YOLOv2_Predictor()
        self.reset()
        
    def reset(self):
        pass
        
    def __call__(self, img):
        self.logger.debug("analyzing frame : %s",img.shape)    
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
        self.logger.debug("finished analyzing frame")
        return lis



class MVisionMasterProcess(QShmemMasterProcess):
    """
    YOLO v3 object detector master process
    
    See:
    
    https://github.com/elsampsa/darknet-python
    
    """
    
    name = "YOLO v3 object detector master"
    tag = "yolo3master"
    max_instances = 1       # just one instance allowed .. this is kinda heavy detector
    max_clients = 4
    
    required_mb = 2700      # required GPU memory in MB
    
    
    parameter_defs = {
        "verbose": (bool, False)
    }

    def __init__(self, **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(self.__class__.name)
        self.analyzer = None
        # self.setDebug()

    def preRun_(self):
        super().preRun_()
        self.analyzer = None
        
    def postRun_(self):
        if (self.analyzer is not None): self.analyzer.close() # release any resources acquired by the analyzer
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
        

    def firstClientRegistered_(self):
        if (self.requiredGPU_MB(self.required_mb)):
            self.analyzer = YoloV3Analyzer(verbose = self.verbose)
            # self.analyzer = None # debug
        else:
            self.warning_message = "WARNING: not enough GPU memory!"
            self.analyzer = None
        

    def lastClientUnregistered_(self):
        if (self.analyzer): self.analyzer.close()
        self.analyzer = None
            

    def handleFrame_(self, shmem_client):
        """Receives frames from the shmem client and does something with them

        This routine returns:
        - None
        - A list
            - a tuple
                (nametag, x, y, w, h)
            - string
        """
        index, meta = shmem_client.pullFrame()
        self.logger.debug("index %s, meta.size %s, meta.height %s, meta.width %s, prod %s", index, meta.size, meta.height, meta.width, meta.height*meta.width*3)
        # return [] # debugging

        if (meta.size < 1) or (self.analyzer is None):
            return None

        data = shmem_client.shmem_list[index][0:meta.size]
        img = data.reshape(
            (meta.height, meta.width, 3))
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
        bbox_list=[]
        for l in lis:
            # """
            bbox_list.append((
                l[0], # name tag
                l[2]/img.shape[1],  # from pixels to fractional coordinates
                l[3]/img.shape[1],
                l[4]/img.shape[0],
                l[5]/img.shape[0]
            ))
            # """
            
        if (hasattr(self, "warning_message")):
            bbox_list.append(self.warning_message)
  
        return bbox_list # will be forwarded through pipes to the correct client process

        
def test1():
    """Dummy-testing the analyzer
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
    # test_process(MVisionProcess)
    pass

    
def test4():
    # test_with_file(MVisionProcess)
    pass


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
