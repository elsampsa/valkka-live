"""
file.py : A GUI for testing your machine vision with plain video files

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    file.py
@author  Sampsa Riikonen
@date    2018
@version 0.14.0 
@brief   A GUI for testing your machine vision with plain video files
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # If you use PyQt5, be aware
# of the licensing consequences
from PySide2 import QtWidgets, QtCore, QtGui
import cv2
import sys
import json
import time
import os
from valkka.api2 import LiveThread, FileThread, OpenGLThread, ValkkaProcess, ShmemClient
from valkka.api2 import ShmemFilterchain1
from valkka.api2 import parameterInitCheck
from valkka.mvision.multiprocess import QShmemProcess
from valkka.live.qt.widget import AnalyzerWidget
from valkka.live import tools, singleton

pre = "mvision.file : "


class FileGUI(QtWidgets.QMainWindow):
    """Test your machine vision mvision_process and its widget with video files
    
    :param mvision_process:          QValkkaMultimvision_process-derived class
    :param shmem_image_interval:     How often the image is interpolated into rgb and passed to the mvision_process (milliseconds)
    """

    def __init__(self, 
                 mvision_process,
                 mvision_master_process,
                 shmem_image_interval = 1000, 
                 shmem_ringbuffer_size = 10, 
                 shmem_image_dimensions = (1920 // 2, 1080 // 2),
                 shmem_name="test",
                 init_filename = None
                 ):
        
        super().__init__()
        assert(issubclass(mvision_process.__class__, QShmemProcess))
        
        self.mvision_process        = mvision_process
        self.mvision_master_process = mvision_master_process

        # self.mvision_class          = mvision_class,
        self.shmem_image_interval   = shmem_image_interval
        self.shmem_ringbuffer_size  = shmem_ringbuffer_size
        self.shmem_image_dimensions = shmem_image_dimensions
        self.shmem_name             = shmem_name
        
        self.init_filename = init_filename

        self.initVars()
        self.setupUi()
        
        self.mvision_widget = self.mvision_process.getWidget()
        # self.mvision_widget = QtWidgets.QWidget()
        self.mvision_widget.setParent(self.widget)
        self.widget_lay.addWidget(self.mvision_widget)

        self.mvision_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum)
        
        self.openValkka()

        if len(sys.argv) > 2:
            self.open_file_button_slot(fname_ = sys.argv[2])


    def initVars(self):
        self.mode = "file"
        self.slot_reserved = False

    def setupUi(self):

        rec = QtWidgets.QApplication.desktop().screenGeometry()
        height = rec.height()
        width = rec.width()

        self.setGeometry(QtCore.QRect(0, 0, width, height//2))
        self.w = QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)
        self.lay = QtWidgets.QVBoxLayout(self.w)

        # return

        # divide window into three parts
        self.upper = QtWidgets.QWidget(self.w)
        self.middle = QtWidgets.QWidget(self.w)
        self.lower = QtWidgets.QWidget(self.w)
        self.lowest = QtWidgets.QWidget(self.w)
        self.lay.addWidget(self.upper)
        self.lay.addWidget(self.middle)
        self.lay.addWidget(self.lower)
        self.lay.addWidget(self.lowest)

        # upper part: detectors widget and the video itself
        self.upperlay = QtWidgets.QHBoxLayout(self.upper)

        # self.widget  =QtWidgets.QTextEdit(self.upper)
        self.widget  =QtWidgets.QWidget(self.upper)
        self.widget_lay = QtWidgets.QVBoxLayout(self.widget)

        # self.widget = self.mvision_process.getWidget()
        # self.widget.setParent(self.upper)

        self.video_area = QtWidgets.QWidget(self.upper)
        self.video_lay = QtWidgets.QGridLayout(self.video_area)

        self.upperlay.addWidget(self.widget)
        self.upperlay.addWidget(self.video_area)
        self.widget.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum)
        self.video_area.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)

        """
        [------|--------------------------------------]
        [Open File] [Close Live] [Play] [Stop] [Rewind]
        """

        self.middlelay = QtWidgets.QHBoxLayout(self.middle)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self.middle)
        self.middlelay.addWidget(self.slider)
        self.slider.setTracking(False)

        self.lowerlay = QtWidgets.QHBoxLayout(self.lower)
        self.open_file_button = QtWidgets.QPushButton("Open File", self.lower)
        self.close_file_button = QtWidgets.QPushButton(
            "Close File", self.lower)
        self.play_button = QtWidgets.QPushButton("Play", self.lower)
        self.stop_button = QtWidgets.QPushButton("Stop", self.lower)
        self.rewind_button = QtWidgets.QPushButton("<<", self.lower)
        self.seek_label = QtWidgets.QLabel("<<", self.lower)

        self.lowerlay.addWidget(self.open_file_button)
        self.lowerlay.addWidget(self.close_file_button)
        self.lowerlay.addWidget(self.play_button)
        self.lowerlay.addWidget(self.stop_button)
        self.lowerlay.addWidget(self.rewind_button)
        self.lowerlay.addWidget(self.seek_label)

        self.open_file_button.clicked. connect(self.open_file_button_slot)
        self.close_file_button.clicked.connect(self.close_file_button_slot)
        self.play_button.clicked.      connect(self.play_button_slot)
        self.stop_button.clicked.      connect(self.stop_button_slot)
        self.rewind_button.clicked.    connect(self.rewind_button_slot)
        self.slider.valueChanged.      connect(self.slider_slot)

        # lowest part: some text
        self.lowestlay = QtWidgets.QVBoxLayout(self.lowest)
        self.infotext = QtWidgets.QLabel("info text", self.lowest)
        self.lowestlay.addWidget(self.infotext)

        

    def openValkka(self):        
        self.mvision_process.go()

        if self.mvision_master_process is not None:
            assert(issubclass(self.mvision_master_process.__class__, QShmemProcess))
            self.mvision_master_process.go()

        self.livethread = LiveThread(         # starts live stream services (using live555)
            name="live_thread",
            verbose=False
        )

        self.filethread = FileThread(
            name="file_thread",
            verbose=False
        )

        self.openglthread = OpenGLThread(     # starts frame presenting services
            name="mythread",
            n_720p=10,
            n_1080p=10,
            n_1440p=10,
            n_4K=10,
            verbose=False,
            msbuftime=100,
            affinity=-1
        )

        # this filterchain creates a shared memory server
        self.chain = ShmemFilterchain1(       # decoding and branching the stream happens here
            openglthread = self.openglthread,
            slot = 1,
            shmem_name = self.shmem_name,
            shmem_image_dimensions = self.shmem_image_dimensions,
            shmem_image_interval = self.shmem_image_interval,
            shmem_ringbuffer_size = self.shmem_ringbuffer_size
        )

        shmem_name, n_buffer, shmem_image_dimensions = self.chain.getShmemPars()

        self.video = QtWidgets.QWidget(self.video_area)
        
        if hasattr(self.mvision_process, "analyzer_video_widget_class"):
            # the machine vision class may declare what video widget it wants to use to define the machine vision parameters (line crossing, zone intrusion, etc.)
            self.analyzer_widget = AnalyzerWidget(
                parent = self.video_area,
                analyzer_video_widget_class = self.mvision_process.analyzer_video_widget_class
                )
        else:
            self.analyzer_widget = AnalyzerWidget(parent = self.video_area)
        
        self.mvision_process.connectAnalyzerWidget(self.analyzer_widget)
        self.analyzer_widget.activate()

        self.win_id = int(self.video.winId())

        self.video_lay.addWidget(self.video, 0, 0)
        self.video_lay.addWidget(self.analyzer_widget, 0, 1)
        self.token = self.openglthread.connect(slot = 1, window_id = self.win_id)

        self.chain.decodingOn()  # tell the decoding thread to start its job

        self.mvision_process.activate(
            n_buffer                = self.shmem_ringbuffer_size, 
            image_dimensions        = self.shmem_image_dimensions, 
            shmem_name              = self.shmem_name  
        )

        if self.mvision_master_process:
            self.mvision_process.setMasterProcess(self.mvision_master_process)

        
        
    def closeValkka(self):
        if self.mvision_master_process:
            self.mvision_process.unsetMasterProcess()
        self.mvision_process.disconnectAnalyzerWidget(self.analyzer_widget)
        self.livethread.close()
        self.chain.close()
        self.chain = None
        self.openglthread.close()

        self.mvision_process.requestStop()
        self.mvision_process.waitStop()
        
        if self.mvision_master_process:
            self.mvision_master_process.requestStop()
            self.mvision_master_process.waitStop()
        


    def showEvent(self, e):
        if self.init_filename is not None:
            self.open_file_button_slot(fname_ = self.init_filename)
        e.accept()

    def closeEvent(self, e):
        print(pre, "closeEvent!")
        self.closeValkka()
        self.analyzer_widget.close() # wtf do we need this!
        # super().closeEvent(e)
        e.accept()

    # *** slot ****

    def open_file_button_slot(self, fname_ = None):
        if (self.slot_reserved):
            self.infotext.setText("Close the current file first")
            return
        if not fname_:
            fname = QtWidgets.QFileDialog.getOpenFileName(filter="*.mkv")[0]
        else:
            fname = fname_
        if (len(fname) > 0):
            print(pre, "open_file_button_slot: got filename", fname)
            self.chain.setFileContext(fname)
            self.filethread.openStream(self.chain.file_ctx)
            self.slot_reserved = True
            if (self.chain.fileStatusOk()):
                self.infotext.setText("Opened file " + fname)
                print("Duration:", self.chain.file_ctx.duration)
                self.slider.setMinimum(0)
                self.slider.setMaximum(self.chain.file_ctx.duration)
            else:
                self.infotext.setText("Can't play file " + fname)
        else:
            self.infotext.setText("No file opened")

    def close_file_button_slot(self):
        if (not self.slot_reserved):
            self.infotext.setText("Open a file first")
            return
        self.filethread.closeStream(self.chain.file_ctx)
        self.slot_reserved = False
        self.infotext.setText("Closed file")

    def open_live_button_slot(self):
        pass

    def play_button_slot(self):
        if (self.mode == "file"):
            if (not self.slot_reserved):
                self.infotext.setText("Open a file first")
                return
            self.filethread.playStream(self.chain.file_ctx)
        else:
            pass

    def rewind_button_slot(self):
        if (self.mode == "file"):
            if (not self.slot_reserved):
                self.infotext.setText("Open a file first")
                return
            self.chain.file_ctx.seektime_ = 0
            self.filethread.seekStream(self.chain.file_ctx)
        else:
            pass

    def stop_button_slot(self):
        if (self.mode == "file"):
            if (not self.slot_reserved):
                self.infotext.setText("Open a file first")
                return
            self.filethread.stopStream(self.chain.file_ctx)
        else:
            pass

    def slider_slot(self, v):
        print(">", v)
        self.chain.file_ctx.seektime_ = v
        # TODO: reset analyzer state
        self.seek_label.setText(str(v))
        self.mvision_process.resetAnalyzerState()
        self.filethread.seekStream(self.chain.file_ctx)

    def set_bounding_boxes_slot(self, bbox_list):
        self.openglthread.core.clearObjectsCall(self.token)
        for bbox in bbox_list:
            self.openglthread.core.addRectangleCall(self.token, bbox[0], bbox[1], bbox[2], bbox[3]) # left, right, top, bottom
        



