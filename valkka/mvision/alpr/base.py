"""
base.py : Plugin for the celebrated ALPR (Automatic License Plate Recognition) package, which is (not-that) OpenSource.

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 0.9.0 
@brief   Plugin for the celebrated ALPR (Automatic License Plate Recognition) package, which is (not-that) OpenSource.
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
import os
import numpy
import imutils
import importlib
from valkka.api2 import parameterInitCheck, typeCheck
from valkka.live import style

# local imports
from valkka.mvision.base import Analyzer
from valkka.mvision.multiprocess import QValkkaShmemProcess2
from valkka.mvision.movement.base import MovementDetector

# external libraries
# from openalpr import Alpr # lets load it in the multiprocess instead
assert(importlib.find_loader('openalpr')) # test if module exists, without loading it


def writePng(fname, img):
    import png # pip3 install --user pypng
    f = open(fname,"wb")
    writer = png.Writer(width = img.shape[1], height = img.shape[0])
    writer.write(f,numpy.reshape(img, (-1, img.shape[1]*3)))
    f.close()
    
pre = "valkka.mvision.movement.alpr : "

class LicensePlateDetector(Analyzer):
    """A demo movement detector, written using OpenCV
    """

    parameter_defs = {
        "verbose": (bool, False),       # :param verbose:  Verbose output or not?  Default: False.
        "debug": (bool, False),         # :param debug:    debugging or not
        "country": (str, "eu"),         # :param country: Country code, default european ("eu")
        "conf_file" : 
            (str, "/usr/share/openalpr/config/openalpr.defaults.conf"),
        "runtime_data" :
            (str, "/usr/share/openalpr/runtime_data"),
        "top_n" :                       # :param top_n:  How many top results are included in the list
            (int, 3),
        "at_movement" : 
            (bool, True)
    }

    def __init__(self, **kwargs):
        # checks that kwargs is consistent with parameter_defs.  Attaches
        # parameters as attributes to self
        parameterInitCheck(LicensePlateDetector.parameter_defs, kwargs, self)
        self.pre = self.__class__.__name__ + " : "
        self.init()
        # self.verbose = True

    def init(self):
        """Init alpr
        
        The LicensePlateDetector object gets instantiated in the multiprocess, so the library is imported in the multiprocess (i.e. "other side of the fork") as well
        """
        # some modules might need to be imported "on the other side of the fork"
        # .. but the, when importing this module, the import is not tested
        #
        # 
        # from openalpr import Alpr
        from valkka.mvision.alpr.openalpr_fix import Alpr
        self.movement = MovementDetector()
        self.alpr = Alpr(self.country, self.conf_file, self.runtime_data)
        if not self.alpr.is_loaded():
            self.alpr = None
            return
        self.alpr.set_top_n(self.top_n)
        self.reset()
        
        """
        # test in ipython:
        from valkka.mvision.alpr.openalpr_fix import Alpr
        country="eu"
        conf_file="/usr/share/openalpr/config/openalpr.defaults.conf"
        runtime_data="/usr/share/openalpr/runtime_data"
        a = Alpr(country, conf_file, runtime_data)
        a.is_loaded()        
        """
        
        
    def reset(self):
        """No state to reset
        """
        pass
    
    
    def close(self):
        """Release resources acquired by alpr
        """
        # self.alpr.unload() # necessary or not?
        pass
        
    
    def __call__(self, img):
        # traceback.print_tb(10)
        self.report("got frame :", img.shape)
        self.report("__call__ : got frame")
        if (self.alpr==None):
            print("OpenALPR was not loaded!  Is your license up-to-date?")
            return []
        # self.movement(img)
        lis = []
        # if (self.movement.isMoving() or not self.at_movement):
        if (True):
            self.report("__call__ : using alpr with frame", img.shape)
            # LicensePlateDetector :  __call__ : using alpr with frame (270, 480, 3)
            # writePng("alpr.png", img) # debugging # images are OK
            # results = self.alpr.recognize_ndarray(img)
            try:
                results = self.alpr.recognize_ndarray(img)
            except Exception as e:
                self.report("__call__ : alpr failed with",str(e))
                results = {"results" : []}
            
            for plate in results['results']:
                for candidate in plate['candidates']:
                    lis.append((candidate["plate"],candidate["confidence"]))                    
                    self.report("__call__ : %12s %12f" % (candidate['plate'], candidate['confidence']))
                    
        self.report("returning", lis)
        return lis # returns a list of (plate, confidence) pairs



class MVisionProcess(QValkkaShmemProcess2):
    """ALPR Process
    """
    
    name = "License Plate Recognition"
    
    instance_counter = 0
    max_instances = 2
    tag  = "alpr"
    
    incoming_signal_defs = {  # each key corresponds to a front- and backend method
        
        # don't touch these three..
        "activate_"     : {"n_buffer": int, "image_dimensions": tuple, "shmem_name": str},
        "deactivate_"   : [],
        "stop_"         : [],
    }

    outgoing_signal_defs = {
        "got_plates": {"plate_list": list} # returns a list of (plate, confidence) pairs
    }

    # For each outgoing signal, create a Qt signal with the same name.  The
    # frontend Qt thread will read processes communication pipe and emit these
    # signals.
    class Signals(QtCore.QObject):
        got_plates = QtCore.Signal(object)

    parameter_defs = {
        "verbose": (bool, False)
    }
    parameter_defs.update(LicensePlateDetector.parameter_defs)

    def __init__(self, **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(self.__class__.name, verbose=self.verbose)
        self.pre = self.__class__.__name__ + ":" + self.name+ " : "
        self.signals = self.Signals()
        
        # take just the LicensePlateDetector.parameter_defs
        self.analyzer_pars = { key: getattr(self,key) for key in LicensePlateDetector.parameter_defs.keys() }
        self.report("analyzer_pars =", self.analyzer_pars)
        # self.analyzer = LicensePlateDetector(**self.analyzer_pars)
        
        
    def preRun_(self):
        self.analyzer = None
        super().preRun_()
        
    def postRun_(self):
        if (self.analyzer): self.analyzer.close()
        super().postRun_()
        
    
    def postActivate_(self):
        """Whatever you need to do after creating the shmem client
        """
        self.analyzer = LicensePlateDetector(**self.analyzer_pars) # this is called after the fork (i.e. after the multiprocess has been spawned)
        self.report("analyzer object=", self.analyzer)
        
        
    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client
        """
        if (self.analyzer): self.analyzer.close()
        self.analyzer = None
    
    def cycle_(self):
        # print(self.pre,"cycle_ starts")
        result = []
        index, isize = self.client.pull()
        if (index is None):
            self.report("Client timed out..")
            # self.sendSignal_(name = "got_plates", plate_list = [("xgl921",0.9)]) # debugging
        else:
            self.report("Client index, size =",index, isize)
            data = self.client.shmem_list[index]
            img = data.reshape(
                (self.image_dimensions[1], self.image_dimensions[0], 3))
            # writePng("alpr.png", img) # debugging 
            result = self.analyzer(img)
            
            self.report(">>>",result)
            #"""
            if (len(result) > 0):
                self.report("sending signal got_plates")
                self.sendSignal_(name = "got_plates", plate_list = result)
            #"""
        # self.sendSignal_(name = "got_plates", plate_list = [("XGL921",1)]) # debugging
    

    # *** backend methods corresponding to incoming signals ***
    # *** i.e., how the signals are handled inside the running multiprocess
    
    # nada
    
    # ** frontend methods launching incoming signals
    # *** you can call these after the multiprocess is started

    # nada

    # ** frontend methods handling outgoing signals ***
    def got_plates(self, plate_list):
        print(self.pre, "At frontend: got_plates: ", plate_list)
        self.signals.got_plates.emit(plate_list)


    # *** This is used by the modules Qt Widget ***
    def got_plates_slot(self, plate_list): # receives a list of (plate, confidence) pairs
        for plate in plate_list:
            self.recent_plates.append(plate[0]) # just take the plate, scrap confidence
            if (len(self.recent_plates)>10): # show 10 latest recognized license plates
                self.recent_plates.pop(0)
        st=""
        for plate in self.recent_plates:
            st += plate + "\n"
        self.widget.setText(st)
    
    
    # *** create a Qt widget for this machine vision module **
    def getWidget(self):
        self.widget = QtWidgets.QTextEdit()
        self.widget.setStyleSheet(style.detector_test)
        self.widget.setReadOnly(True)
        self.recent_plates = []
        self.signals.got_plates.connect(self.got_plates_slot) 
        return self.widget
    
        
    
def test1():
    """Dummy-testing the license plate analyzer
    """
    analyzer = LicensePlateDetector(verbose = True, at_movement = False)

    img = numpy.zeros((1080 // 4, 1920 // 4, 3), dtype = numpy.uint8)
    result = analyzer(img)
    print("\nresult =", result, "\n")


def test2():
    """Test license plate analyzer with an image
    """
    analyzer = LicensePlateDetector(at_movement = False)
    
    filename="IMG_20170308_093511.jpg"
    dirname="/home/sampsa/python3/tests/lprtest/RealImages/"
    img = imutils.url_to_image("file:"+dirname+filename)
    print("img=",img.shape)
    # img= (1232, 2048, 3)
    
    # writePng("kokkelis.png", img) 
    
    result = analyzer(img)
    print("\nresult =", result, "\n")

    result = analyzer(img)
    print("\nresult =", result, "\n")


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
