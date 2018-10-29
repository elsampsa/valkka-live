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
@version 0.5.0 
@brief   a container class that manages Qt widgets for stream visualization and frame streaming to machine vision modules
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
from valkka.api2.tools import parameterInitCheck
from valkka.live.container.video import VideoContainer
from valkka.live.filterchain import FilterChainGroup
from valkka.live import constant
from valkka.mvision import multiprocess



class MVisionContainer(VideoContainer):
    """This class starts an analyzer process and passes it the correct shmem identifier
    """
    
    parameter_defs = {
        "parent_container"  : None,                 # RootVideoContainer or child class
        "filterchain_group" : FilterChainGroup,     # Filterchain manager class
        "n_xscreen"         : (int,0),              # x-screen index
        "mvision_class"     : type,                 # for example : valkka_mvision.movement.base.MVisionProcess
        "thread"            : None,                 # thread that watches the multiprocesses communication pipes
        "verbose"           : (bool, False)
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(MVisionContainer.parameter_defs, kwargs, self)
        assert(issubclass(self.mvision_class,multiprocess.QValkkaOpenCVProcess))
        super().__init__(parent_container = self.parent_container, filterchain_group = self.filterchain_group, n_xscreen = self.n_xscreen)
        
        
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
    
    
    def setDevice(self, device): 
        """Sets the video stream
        
        :param device:      A rather generic device class.  In this case DataModel.RTSPCameraDevice.
        """
        self.report("setDevice :", device)
        
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
            """
            TODO:
            - Instantiate an analyzer class.  Give it the correct shmem name
            - Get the custom widget from the analyzer.  Embed into the view.
            - Start the analyzer multiprocess
            """
            """
            # a simulation ..
            self.mvision_widget = QtWidgets.QFrame()
            self.mvision_widget.setAutoFillBackground(True)
            self.mvision_widget.setMinimumSize(0, 200)
            
            self.mvision_widget.setParent(self.main_widget)
            self.main_layout.addWidget(self.mvision_widget)
            """
            # initiate mvision process
            self.mvision_process = self.mvision_class(
                n_buffer         = constant.shmem_n_buffer,
                image_dimensions = constant.shmem_image_dimensions,
                shmem_name       = self.shmem_name
                )
            
            self.mvision_widget = self.mvision_process.getWidget()
            self.mvision_widget.setParent(self.main_widget)
            self.main_layout.addWidget(self.mvision_widget)
            
            self.mvision_process.start() # process must be started before calling addProcess
            self.thread.addProcess(self.mvision_process)
            
            
    def clearDevice(self):
        """Remove the current stream
        """
        self.report("clearDevice")
        if not self.device:
            return
        
        self.filterchain.delViewPort(self.viewport)
        self.filterchain.releaseShmem(self.shmem_name)

        self.main_layout.removeWidget(self.mvision_widget)
        self.mvision_widget = None
        self.thread.delProcess(self.mvision_process) # stops the multiprocess as well
        
        self.mvision_process = None
        self.filterchain = None
        self.device = None
        
        self.video.update()





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
 
