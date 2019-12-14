"""
multiprocess.py : multiprocess / Qt intercommunication through pipes and signals

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    multiprocess.py
@author  Sampsa Riikonen
@date    2018
@version 0.11.0 
@brief   multiprocess / Qt intercommunication through pipes and signals
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
import logging

from valkka.api2 import ValkkaProcess, Namespace, safe_select, ShmemRGBClient
from valkka.api2.tools import *
from valkka.live.multiprocess import MessageObject, safe_select, QMultiProcess

logger = getLogger(__name__)



class QShmemProcess(QMultiProcess):
    """A multiprocess with Qt signals and reading RGB images from shared memory.  Shared memory client is instantiated on demand (by calling activate)
    """

    timeout = 1.0

    class Signals(QtCore.QObject):
        pong = QtCore.Signal(object) # demo outgoing signal

    # **** define here backend methods that correspond to incoming slots
    # **** 

    def c__ping(self, message = ""):
        print("c__ping:", message)
        self.send_out__(MessageObject("pong", lis = [1,2,3]))


    def c__activate(self, n_buffer:int = None, image_dimensions:tuple = None, shmem_name:str = None):
        """Shared mem info is given.  Now we can create the shmem client
        """
        self.logger.debug("c__activate")
        self.listening = True
        self.image_dimensions = image_dimensions
        self.client = ShmemRGBClient(
            name            =shmem_name,
            n_ringbuffer    =n_buffer,   # size of ring buffer
            width           =image_dimensions[0],
            height          =image_dimensions[1],
            # client timeouts if nothing has been received in 1000 milliseconds
            mstimeout   =1000,
            verbose     =False
        )
        self.postActivate_()
        
    def c__deactivate(self):
        """Init shmem variables to None
        """
        self.logger.debug("c__deactivate")
        self.preDeactivate_()
        self.listening = False
        self.image_dimensions = None
        self.client = None # shared memory client created when activate is called

    # ****

    parameter_defs = {
        }

    def __init__(self, name = "QShmemProcess", **kwargs):
        super().__init__(name)
        parameterInitCheck(QShmemProcess.parameter_defs, kwargs, self)
        
        
    def preRun_(self):
        self.logger.debug("preRun_")
        self.c__deactivate() # init variables
        
    def postRun_(self):
        """Clear shmem variables
        """
        self.c__deactivate()
        
    def run(self):
        self.preRun_()

        while self.loop:
            if self.listening:
                self.cycle_()
                self.readPipes__(timeout = 0) # timeout = 0 == just poll
            else:
                self.readPipes__(timeout = self.timeout) # timeout of 1 sec

        self.postRun_()
        # indicate front end qt thread to exit
        self.back_pipe.send(None)
        self.logger.debug("bye!")

    def cycle_(self):
        index, isize = self.client.pull()
        if (index is None):
            print(self.pre, "Client timed out..")
        else:
            print(self.pre, "Client index, size =", index, isize)
            data = self.client.shmem_list[index]
            img = data.reshape(
                (self.image_dimensions[1], self.image_dimensions[0], 3))
            """ # WARNING: the x-server doesn't like this, i.e., we're creating a window from a separate python multiprocess, so the program will crash
            print(self.pre,"Visualizing with OpenCV")
            cv2.imshow("openCV_window",img)
            cv2.waitKey(1)
            """
            print(self.pre, ">>>", data[0:10])
            # res=self.analyzer(img) # does something .. returns something ..

        
    def postActivate_(self):
        """Whatever you need to do after creating the shmem client.  Overwrite in child classes
        """
        pass
        
    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client.  Overwrite in child classes
        """
        pass
    

    # *** frontend ***

    def activate(self, **kwargs):
        self.sendMessageToBack(MessageObject(
            "activate", **kwargs))
                
    def deactivate(self):
        self.sendMessageToBack(MessageObject(
            "deactivate"))
        
    def ping(self, message = ""):
        self.sendMessageToBack(MessageObject("ping", message = message))



def test_process(mvision_process_class):
    import time
    p = mvision_process_class()
    p.go()
    time.sleep(5)
    p.stop()
    

def test_with_file(mvision_class):
    """Test the analyzer process with files
    
    They must be encoded and muxed correctly, i.e., with:
    
    ::
    
        ffmpeg -i your_video_file -c:v h264 -an outfile.mkv
    
    """
    import time
    from valkka.mvision.file import FileGUI
    ps = mvision_process_class()
    
    app = QtWidgets.QApplication(["mvision test"])
    fg = FileGUI(
        mvision_process         = ps, 
        shmem_name              ="test_studio_file",
        shmem_image_dimensions  =(1920 // 2, 1080 // 2),
        shmem_image_interval    =1000,
        shmem_ringbuffer_size   =5
        )
    fg.show()
    app.exec_()
    ps.stop()
    print("bye from app!")
    

class MyGui(QtWidgets.QMainWindow):
    """An example demo GUI
    """
    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.initVars()
        self.setupUi()


    def initVars(self):
        self.process1 = QShmemProcess("process1")
        self.process2 = QShmemProcess("process2")

        self.process1.setDebug()

        self.process1.go()
        self.process2.go()

        
    def setupUi(self):
        self.setGeometry(QtCore.QRect(100, 100, 500, 500))
        self.w = QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)

        self.lay = QtWidgets.QGridLayout(self.w)

        self.button1 = QtWidgets.QPushButton("Button 1", self.w)
        self.button2 = QtWidgets.QPushButton("Button 2", self.w)

        self.check1 = QtWidgets.QRadioButton(self.w)
        self.check2 = QtWidgets.QRadioButton(self.w)

        self.lay.addWidget(self.button1, 0, 0)
        self.lay.addWidget(self.check1, 0, 1)
        self.lay.addWidget(self.button2, 1, 0)
        self.lay.addWidget(self.check2, 1, 1)

        self.button1.clicked.connect(self.button1_slot)
        self.button2.clicked.connect(self.button2_slot)

        self.process1.signals.pong.connect(self.pong1_slot)
        self.process2.signals.pong.connect(self.pong2_slot)

    def button1_slot(self):
        self.process1.ping(message="<sent ping from button1>")
        self.check1.setChecked(True)

    def button2_slot(self):
        self.process2.ping(message="<sent ping from button2>")
        self.check2.setChecked(True)

    def pong1_slot(self, dic = {}):
        print("pong1_slot: dic=", dic)

    def pong2_slot(self, dic = {}):
        print("pong2_slot: dic=", dic)

    def closeEvent(self, e):
        print("closeEvent!")
        self.process1.stop()
        self.process2.stop()
        super().closeEvent(e)


def test1():
    p = QShmemProcess("test")
    p.setDebug()
    p.start()
    time.sleep(5)
    p.activate(n_buffer=10, image_dimensions=(1920//4, 1080//4), shmem_name="test123")
    time.sleep(5)
    p.deactivate()
    time.sleep(5)
    p.activate(n_buffer=10, image_dimensions=(1920//4, 1080//4), shmem_name="test123")
    time.sleep(5)
    p.stop()


def main():
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    # main()
    test1()
