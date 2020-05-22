"""
base.py : Yolo v2 object detector for Valkka Live

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 0.12.2 
@brief   Yolo v2 object detector for Valkka Live
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
# from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
import os
"""
import numpy
import imutils
import importlib
from valkka.live import style
from valkka.api2 import parameterInitCheck, typeCheck
from valkka.mvision.base import Analyzer
from valkka.mvision.multiprocess import QValkkaShmemProcess2
"""

pre = "valkka.mvision.yolo3tiny.base : "

from valkka.mvision.yolo3 import YoloV3Analyzer
from valkka.mvision.yolo3 import MVisionProcess as BaseProcess
from valkka.mvision.multiprocess import test_process, test_with_file

# if the following works, then darknet is available and the weights file has been downloaded ok
from darknet.api2.constant import get_yolov2_weights_file, get_yolov3_weights_file, get_yolov3_tiny_weights_file
fname = get_yolov3_tiny_weights_file()

from valkka.live.version import MIN_DARKNET_VERSION_MAJOR, MIN_DARKNET_VERSION_MINOR, MIN_DARKNET_VERSION_PATCH
from darknet.core import VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH
assert(VERSION_MAJOR >= MIN_DARKNET_VERSION_MAJOR)
assert(VERSION_MINOR >= MIN_DARKNET_VERSION_MINOR)
assert(VERSION_PATCH >= MIN_DARKNET_VERSION_PATCH)


class YoloV3TinyAnalyzer(YoloV3Analyzer):
    
    def init(self):
        # from darknet.api2.error import WeightMissingError
        from darknet.api2.predictor import get_YOLOv3_Predictor, get_YOLOv3_Tiny_Predictor, get_YOLOv2_Predictor
        # self.predictor = get_YOLOv3_Predictor()
        self.predictor = get_YOLOv3_Tiny_Predictor()
        # self.predictor = get_YOLOv2_Predictor()
        self.reset()
        

class MVisionProcess(BaseProcess):
    """YOLO v3 tiny object detector
    """
    
    name = "YOLO v3 Tiny object detector"
    tag = "yolov3tiny"
    max_instances = 2       # just one instance allowed .. this is kinda heavy detector
    auto_menu = True # append automatically to valkka live machine vision menu or not
    required_mb = 230      # required GPU memory in MB
    
    def postActivate_(self):
        """Whatever you need to do after creating the shmem client
        """
        # super().postActivate_() # nopes..! since we inherit from yolov3
        if (self.requiredGPU_MB(self.required_mb)):
            self.analyzer = YoloV3TinyAnalyzer(verbose = self.verbose)
        else:
            self.warning_message = "WARNING: not enough GPU memory!"
            self.analyzer = None
    
        
        
def test1():
    """Dummy-testing the movement analyzer
    """
    import numpy
    
    analyzer = YoloV3TinyAnalyzer(verbose=True, debug=True)

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
