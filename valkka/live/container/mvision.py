"""
mvision.py : a container class that manages Qt widgets for stream visualization and frame streaming to machine vision modules

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    mvision.py
@author  Sampsa Riikonen
@date    2018
@version 0.11.0 
@brief   a container class that manages Qt widgets for stream visualization and frame streaming to machine vision modules
"""
from pprint import pprint, pformat

from PySide2 import QtWidgets, QtCore, QtGui # Qt5

from valkka.live import singleton
from valkka.api2.tools import parameterInitCheck
from valkka.live.tools import filter_keys
from valkka.live.container.video import VideoContainer
from valkka.live.filterchain import FilterChainGroup
from valkka.live import constant
from valkka.live.tools import classToName, nameToClass
from valkka.mvision import multiprocess
from valkka.live.qt.widget import SimpleVideoWidget, LineCrossingVideoWidget, VideoShmemThread



class MVisionContainer(VideoContainer):
    """This class starts an analyzer process and passes it the correct shmem identifier
    """
    class AnalyzerWindow(QtWidgets.QMainWindow):

        def __init__(self, parent = None):
            super().__init__()
            self.w = QtWidgets.QWidget(self)
            self.setCentralWidget(self.w)
            self.lay = QtWidgets.QVBoxLayout(self.w)
            # self.video = SimpleVideoWidget(parent = self.w)
            self.video = LineCrossingVideoWidget(parent = self.w)
            self.lay.addWidget(self.video)
            self.filterchain = None


        def activate(self, filterchain):
            self.filterchain = filterchain
            self.shmem_name, self.shmem_n_buffer, self.width, self.height = filterchain.getShmemQt()
            self.thread = VideoShmemThread(
                    self.shmem_name,
                    self.shmem_n_buffer,
                    self.width,
                    self.height
                )
            self.thread.signals.pixmap.connect(self.video.set_pixmap_slot)
            self.thread.start()
            self.setVisible(True)

        def showEvent(self, e):
            print("AnalyzerWindow: showEvent")
            
        def closeEvent(self, e):
            print("AnalyzerWindow: closeEvent")
            if self.filterchain:
                self.thread.signals.pixmap.disconnect(self.video.set_pixmap_slot)
                self.filterchain.releaseShmemQt(self.shmem_name)
                self.thread.stop()
                

    parameter_defs = {
        #"parent_container"  : None,                 # RootVideoContainer or child class
        #"filterchain_group" : FilterChainGroup,     # Filterchain manager class
        #"n_xscreen"         : (int,0),              # x-screen index
        #"device_id"         : (int, -1),            # optional: the unique id of this video stream
        "mvision_class"     : None,                  # Either a class instance, or a complete string of the module.class, for example : valkka_mvision.movement.base.MVisionProcess
        # non-seriazable parameters:
        # "thread"            : None,                 # thread that watches the multiprocesses communication pipes # NEW: now at singleton
        # "process_map"       : (dict,{}),            # NEW: now at singleton
        "verbose"           : (bool, False)
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        print("MVisionContainer: __init__: kwargs:", pformat(kwargs))
        super().__init__(**filter_keys(super().parameter_defs.keys(), kwargs))
        parameterInitCheck(MVisionContainer.parameter_defs, filter_keys(MVisionContainer.parameter_defs.keys(), kwargs), self)
        
        if isinstance(self.mvision_class, str):
            self.mvision_class = nameToClass(self.mvision_class)
        
        assert(issubclass(self.mvision_class, multiprocess.QShmemProcess))
        
        tag = self.mvision_class.tag # identifies a list of multiprocesses in singleton.process_map
        
        self.verbose = True
        
        try:
            queue = singleton.process_map[tag]
        except KeyError:
            self.mvision_process = None
            return
        
        try:
            self.mvision_process = queue.pop()
        except IndexError:
            self.mvision_process = None
            return
    
        self.analyzer_window = self.AnalyzerWindow()
        self.analyzer_window.setVisible(False)
        self.signals.right_double_click.connect(self.right_double_click_slot)

    
    def serialize(self):
        """Return a dict of parameters that the parent object needs to de-serialize & instantiate this object
        """
        return {
            "mvision_class" : classToName(self.mvision_class),
            "device_id" : self.getDeviceId()
            }
    
    def makeWidget(self, parent=None):
        self.main_widget = self.ContainerWidget(parent)
        # self.signals.close.connect(self.close_slot) # not closed by clicking
        # the close symbol
        # this layout includes VideoWidget, buttons, alerts, etc.
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.video = self.VideoWidget(
            parent=self.main_widget,
            mouse_gesture_handler=self.mouseGestureHandler)

        self.main_layout.addWidget(self.video)
        self.video.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        
        self.video.signals.drop.connect(self.setDevice)
        
        # this VideoContainer was initialized with a device id, so we stream the video now
        if self.device_id > -1:
            self.setDeviceById(self.device_id)
        
    
    def setDevice(self, device): 
        """Sets the video stream
        
        :param device:      A rather generic device class.  In this case device.RTSPCameraDevice.
        """
        self.report("setDevice :", device)
        
        if (self.mvision_process == None):
            return
        
        if (not device and not self.device): # None can be passed as an argument when the device has not been set yet
            return
            
        if (self.device):
            if self.device == device:
                self.report("setDevice : same device")
                return
            
        if self.filterchain: # there's video already
            self.clearDevice()
        
        self.device = device
        self.video.setDevice(self.device) # inform the video widget so it can start drags
        
        # ManagedFilterChain.addViewPort accepts ViewPort instance
        self.filterchain = self.filterchain_group.get(_id = self.device._id)
        
        if self.filterchain:
            self.viewport.setXScreenNum(self.n_xscreen)
            self.viewport.setWindowId  (int(self.video.winId()))
            self.filterchain.addViewPort(self.viewport)
            
            # now the shared mem / semaphore part :
            self.shmem_name = self.filterchain.getShmem()
            print(self.pre, "setDevice : got shmem name", self.shmem_name)
            
            self.mvision_widget = self.mvision_process.getWidget()
            self.mvision_widget.setParent(self.main_widget)
            self.main_layout.addWidget(self.mvision_widget)
            
            self.mvision_process.activate(
                n_buffer         = constant.shmem_n_buffer,
                image_dimensions = constant.shmem_image_dimensions,
                shmem_name       = self.shmem_name
                )
                
            # singleton.thread.addProcess(self.mvision_process)
            
            # is there a signal giving the bounding boxes..?  let's connect it
            if hasattr(self.mvision_process.signals,"bboxes"):
                print(self.pre, "setDevice : connecting bboxes signal")
                self.mvision_process.signals.bboxes.connect(self.set_bounding_boxes_slot)
            
            
    def set_bounding_boxes_slot(self, message_object):
        if (self.device):
            bbox_list = message_object["bbox_list"]
            # device might have been cleared while the yolo object detector takes it time ..
            # .. and then it still calls this
            self.filterchain.setBoundingBoxes(self.viewport, bbox_list)
            

    def right_double_click_slot(self):
        if self.filterchain:
            self.analyzer_window.activate(self.filterchain)


            
    def clearDevice(self):
        """Remove the current stream
        """
        print(self.pre, "clearDevice: ")
        self.report("clearDevice")
        if not self.device:
            return
        if (self.mvision_process==None):
            return
        
        self.analyzer_window.close()

        self.filterchain.delViewPort(self.viewport)
        self.filterchain.releaseShmem(self.shmem_name)

        self.mvision_process.deactivate() # put process back to sleep ..
        
        self.main_layout.removeWidget(self.mvision_widget)
        
        self.filterchain = None
        self.device = None
        
        self.video.update()
        
        
    def close(self):
        super().close() # calls clearDevice
        tag = self.mvision_class.tag
        singleton.process_map[tag].append(self.mvision_process) # .. and recycle it
        print(self.pre, "close: process_map=", singleton.process_map)
        self.mvision_process = None
        

class MyGui(QtWidgets.QMainWindow):

  
  def __init__(self,parent=None):
    super(MyGui, self).__init__()
    self.initVars()
    self.setupUi()
    self.openValkka()
    

  def initVars(self):
    pass


  def setupUi(self):
    self.setGeometry(QtCore.QRect(100,100,500,500))
    
    self.w=QtWidgets.QWidget(self)
    self.setCentralWidget(self.w)
    
    
  def openValkka(self):
    pass
    
  
  def closeValkka(self):
    pass
  
  
  def closeEvent(self,e):
    print("closeEvent!")
    self.closeValkka()
    e.accept()



def main():
  app=QtWidgets.QApplication(["test_app"])
  mg=MyGui()
  mg.show()
  app.exec_()



if (__name__=="__main__"):
  main()
 
