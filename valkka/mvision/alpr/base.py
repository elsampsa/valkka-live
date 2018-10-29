"""
base.py : Plugin for the celebrated ALPR (Automatic License Plate Recognition) package, which is (not-that) OpenSource.

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 0.5.0 
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

# local imports
from valkka.mvision.base import Analyzer
from valkka.mvision.multiprocess import QValkkaOpenCVProcess
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
        self.verbose = True

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
        self.alpr.set_top_n(self.top_n)
        self.reset()
        
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


class MVisionProcess(QValkkaOpenCVProcess):
    """ALPR Process
    """
    
    name = "License Plate Recognition"
    
    incoming_signal_defs = {  # each key corresponds to a front- and backend method
        "stop_": []
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
        "n_buffer": (int, 10),
        "image_dimensions": (tuple, (1920 // 4, 1080 // 4)),
        "shmem_name": str,
        "verbose": (bool, False)
        # "deadtime": (int, 1)
    }
    parameter_defs.update(LicensePlateDetector.parameter_defs)

    def __init__(self, **kwargs):
        parameterInitCheck(self.parameter_defs, kwargs, self)
        super().__init__(self.__class__.name, n_buffer = self.n_buffer, image_dimensions = self.image_dimensions, shmem_name = self.shmem_name)
        self.pre = self.__class__.__name__ + ":" + self.name+ " : "
        self.signals = self.Signals()
        typeCheck(self.image_dimensions[0], int)
        typeCheck(self.image_dimensions[1], int)
        
        self.verbose = True
        
        # take just the LicensePlateDetector.parameter_defs
        self.analyzer_pars = { key: getattr(self,key) for key in LicensePlateDetector.parameter_defs.keys() }
        self.report("analyzer_pars =", self.analyzer_pars)
        # self.analyzer = LicensePlateDetector(**self.analyzer_pars)
        
        
    def preRun_(self):
        super().preRun_()
        self.analyzer = LicensePlateDetector(**self.analyzer_pars) # this is called after the fork (i.e. after the multiprocess has been spawned)
        self.report("analyzer object=", self.analyzer)
        
        
    def postRun_(self):
        self.analyzer.close() # release any resources acquired by the analyzer
        super().postRun_()


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
    
    def stop_(self):
        self.running = False

    # ** frontend methods launching incoming signals
    # *** you can call these after the multiprocess is started
    
    def stop(self):
        self.sendSignal(name="stop_")

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
    
    p = MVisionProcess(shmem_name="test3")
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

    # from valkka.mvision import QValkkaThread
    
    #t = QValkkaThread()
    #t.start()
    
    shmem_name="test_studio_file"
    # shmem_image_dimensions=(1920 // 1, 1080 // 1)
    # shmem_image_dimensions=(1920 // 4, 1080 // 4)
    shmem_image_dimensions = (2048, 1232, 3)
    shmem_image_interval=1000
    shmem_ringbuffer_size=5
    
    # """
    ps = MVisionProcess(
            shmem_name = shmem_name, 
            image_dimensions = shmem_image_dimensions,
            n_buffer = shmem_ringbuffer_size,
            verbose = True,
            at_movement = False
        )
    # """
       
    #t.addProcess(ps)
    #time.sleep(5)
    #t.stop()
    #return

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
    
    
"""
Traceback (most recent call last):
  File "/usr/lib/python3.6/multiprocessing/process.py", line 258, in _bootstrap
    self.run()
  File "/home/sampsa/C/valkka/python/valkka/api2/multiprocess.py", line 160, in run
    self.cycle_()
  File "base.py", line 180, in cycle_
    result = self.analyzer(img)
  File "base.py", line 86, in __call__
    results = self.alpr.recognize_ndarray(img)
  File "/usr/lib/python3/dist-packages/openalpr/openalpr.py", line 195, in recognize_ndarray
    response_obj = json.loads(json_data)
  File "/usr/lib/python3.6/json/__init__.py", line 354, in loads
    return _default_decoder.decode(s)
  File "/usr/lib/python3.6/json/decoder.py", line 339, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
  File "/usr/lib/python3.6/json/decoder.py", line 355, in raw_decode
    obj, end = self.scan_once(s, idx)
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 128 (char 127)
"""

"""
i = 0
for plate in results['results']:
    i += 1
    print("Plate #%d" % i)
    print("   %12s %12s" % ("Plate", "Confidence"))
    for candidate in plate['candidates']:
        prefix = "-"
        if candidate['matches_template']:
            prefix = "*"

        print("  %s %12s%12f" % (prefix, candidate['plate'], candidate['confidence']))
"""
# [”results"][0..N]["candidates"][0..N]["matches_template"]
