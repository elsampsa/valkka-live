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
@version 0.14.0 
@brief   a container class that manages Qt widgets for stream visualization and frame streaming to machine vision modules
"""
from pprint import pprint, pformat

from PySide2 import QtWidgets, QtCore, QtGui # Qt5

from valkka.live import singleton
from valkka.api2.tools import parameterInitCheck
from valkka.live.tools import filter_keys, remove_keys
from valkka.live.container.video import VideoContainer
from valkka.live.filterchain import FilterChainGroup
from valkka.live import constant
from valkka.live.tools import classToName, nameToClass
from valkka.mvision import multiprocess
# from valkka.live.qt.widget import SimpleVideoWidget, LineCrossingVideoWidget, VideoShmemThread
from valkka.live.qt.widget import AnalyzerWidget

"""walk-through

valkka.live.container.mvision.MVisionContainer
    - encloses widgets
    - encloses a machine vision multiprocess
        --> self.mvision_process
    - encloses self.analyzer_widget{valkka.live.qt.widget.AnalyzerWidget}
        - AnalyzerWidget encloses self.video{valkka.live.qt.widget.SimpleVideoWidget}
    - encloses self.video_widget{self.VideoWidget}
        --> emits signal upon drag'n'drop
    - setDevice is called when drag'n'drop occurs

    in self.init():

    self.mvision_process.connectAnalyzerWidget(
        self.analyzer_widget
    )

    connects:

    - MVisionProcess.signals.shmem_server
      ==> self.analyzer_widget.setShmem_slot
      (signals that shmem server is ready)

    - self.analyzer_widget.signals.show
      ==> MVisionProcess.requestQtShmemServer
      (requests shmem server from MVisionProcess)

    - self.analyzer_widget.signals.close
      ==> MVisionProcess.releaseQtShmemServer
      (tells MVisionProcess that shmem server can be released)

"""




class MVisionContainer(VideoContainer):
    """This class starts an analyzer process and passes it the correct shmem identifier
    """
    
    parameter_defs = {
        "mvision_class"      : None,                  # Either a class instance, or a complete string of the module.class, for example : valkka_mvision.movement.base.MVisionProcess
        "mvision_parameters" : None,
        "verbose"           : (bool, False)
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        # print("MVisionContainer: __init__: kwargs:", pformat(kwargs))

        # remove key-values of this child class & pass the rest to the superclass
        super().__init__(**remove_keys(MVisionContainer.parameter_defs.keys(), 
            kwargs))

        # init internal variables for this child class
        parameterInitCheck(MVisionContainer.parameter_defs, 
            filter_keys(MVisionContainer.parameter_defs.keys(), kwargs), self)

        # print(">>>", self.filterchain_group)
        self.init()        


    def init(self):
        if isinstance(self.mvision_class, str):
            self.mvision_class = nameToClass(self.mvision_class)
        
        assert(issubclass(self.mvision_class, multiprocess.QShmemProcess))
        
        tag = self.mvision_class.tag # identifies a list of multiprocesses in singleton.process_map
        
        self.verbose = True
        
        self.mvision_process = self.getProcess(tag)
        if self.mvision_process is None: return

        self.analyzer_widget_connected = False
        if hasattr(self.mvision_process, "analyzer_video_widget_class"):
            # the machine vision class may declare what video widget it wants to use to define the machine vision parameters (line crossing, zone intrusion, etc.)
            self.analyzer_widget = AnalyzerWidget(
                analyzer_video_widget_class = self.mvision_process.analyzer_video_widget_class
                )

            print("MVisionContainer created AnalyzerWidget", id(self.analyzer_widget))
            # if hasattr(self.mvision_process, "connectAnalyzerWidget"):
            # self.mvision_process.connectAnalyzerWidget(self.analyzer_widget)
            # self.analyzer_widget_connected = True
            # TODO: init analyzer parameters by sending a signal & serialize analyzer parameters
        else:
            self.analyzer_widget = AnalyzerWidget()

        self.mvision_process.connectAnalyzerWidget(self.analyzer_widget)
        self.analyzer_widget_connected = True
        # self.mvision_process.connectShmem(self.analyzer_widget) # do in connectAnalyzerWidget

        self.analyzer_widget.setVisible(False)
        self.signals.right_double_click.connect(self.right_double_click_slot)

        if self.mvision_parameters:
            self.mvision_process.updateAnalyzerParameters(self.mvision_parameters)
            self.analyzer_widget.mvisionToParameters(self.mvision_parameters)


    
    def getProcess(self, tag):
        try:
            queue = singleton.process_map[tag]
        except KeyError:
            return None
        
        try:
            mvision_process = queue.pop()
        except IndexError:
            return None

        return mvision_process
    

    def serialize(self):
        """Return a dict of parameters that the parent object needs to de-serialize & instantiate this object
        """
        return {
            "mvision_class"             : classToName(self.mvision_class),
            "device_id"                 : self.getDeviceId(),
            "mvision_parameters"        : self.mvision_process.getAnalyzerParameters()
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

        self.define_analyzer_button = QtWidgets.QPushButton("Define Analyzer", self.main_widget)
        self.main_layout.addWidget(self.define_analyzer_button)

        self.main_layout.addWidget(self.video)
        self.video.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        
        self.video.signals.drop.connect(self.setDevice)
        self.define_analyzer_button.clicked.connect(self.right_double_click_slot) # show the analyzer widget windows
        
        # this VideoContainer was initialized with a device id, so we stream the video now
        if self.device_id > -1:
            self.setDeviceById(self.device_id)
        
    
    def setDevice(self, device): 
        """Sets the video stream
        
        :param device:      A rather generic device class.  In this case device.RTSPCameraDevice.
        """
        self.report("setDevice :", device)
        
        if (self.mvision_process == None):
            self.report("setDevice : no mvision process")
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
            
            self.activate()

            # singleton.thread.addProcess(self.mvision_process)
            
            self.connectSignals()


    def connectSignals(self):
        # print("\nSAAAAATANA",self.__class__,"\n")
        # is there a signal giving the bounding boxes..?  let's connect it
        if hasattr(self.mvision_process.signals,"bboxes"):
            print(self.pre, "connecting bboxes signal")
            self.mvision_process.signals.bboxes.connect(self.set_bounding_boxes_slot)
    

    def disconnectSignals(self):
        # is there a signal giving the bounding boxes..?  let's connect it
        if hasattr(self.mvision_process.signals,"bboxes"):
            print(self.pre, "disconnecting bboxes signal")
            self.mvision_process.signals.bboxes.disconnect(self.set_bounding_boxes_slot)


    def setFile(self, fname):
        # TODO: when testing mvision classes with a file
        pass


    def activate(self):
        self.mvision_process.activate(
                n_buffer         = singleton.shmem_n_buffer,
                image_dimensions = singleton.shmem_image_dimensions,
                shmem_name       = self.shmem_name
                )
        # creates the shmem client at the multiprocess
            

    def set_bounding_boxes_slot(self, message_object):
        if (self.device):
            bbox_list = message_object["bbox_list"]
            # device might have been cleared while the yolo object detector takes it time ..
            # .. and then it still calls this
            self.filterchain.setBoundingBoxes(self.viewport, bbox_list)
            

    def right_double_click_slot(self):
        if self.filterchain:
            self.analyzer_widget.activate(
                # self.filterchain,
                self.main_widget.geometry()
                )
            # self.mvision_process.requestQtShmemServer()


            
    def clearDevice(self):
        """Remove the current stream
        """
        print(self.pre, "clearDevice: ")
        # self.report("clearDevice")
        if not self.device:
            return
        if self.mvision_process is None:
            return
        
        # if self.analyzer_widget.visible:
        self.analyzer_widget.close()

        self.filterchain.delViewPort(self.viewport)
        self.filterchain.releaseShmem(self.shmem_name)

        self.mvision_process.deactivate() # deactivates the shmem client at the multiprocess & puts process back to sleep ..
        
        self.main_layout.removeWidget(self.mvision_widget)
        
        self.filterchain = None
        self.device = None
        
        self.disconnectSignals()

        self.video.update()
        
        
    def clearProcess(self):
        print("MVisionContainer: clearProcess")
        if self.mvision_process is None:
            return
        tag = self.mvision_class.tag
        singleton.process_map[tag].append(self.mvision_process) # .. and recycle it
        print(self.pre, "close: process_map=", singleton.process_map)
        if self.analyzer_widget_connected:
            self.mvision_process.disconnectAnalyzerWidget(self.analyzer_widget)
        self.mvision_process = None


    def close(self):
        super().close() # calls clearDevice
        self.clearProcess()



class MVisionClientContainer(MVisionContainer):
    """Like the mother class, but does client/master process handling
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.mvision_process is None:
            self.mvision_master_process = None
            return

        master_tag = self.mvision_process.master
        self.mvision_master_process = self.getMasterProcess(master_tag)
        if self.mvision_master_process is None: 
            self.clearProcess()
            return

        # self.mvision_process.setMasterProcess(self.mvision_master_process)


    def getProcess(self, tag):
        # print(self.pre, "getProcess: client_process_map0=", singleton.client_process_map)
        try:
            queue = singleton.client_process_map[tag]
        except KeyError:
            return None
        try:
            mvision_process = queue.pop()
        except IndexError:
            return None
        # print(self.pre, "getProcess: client_process_map=", singleton.client_process_map)
        return mvision_process


    def clearProcess(self):
        print("MVisionClientContainer: clearProcess")
        if self.mvision_process is None:
            return
        self.mvision_process.unsetMasterProcess()        
        tag = self.mvision_class.tag
        # print(self.pre, "clearProcess: client_process_map0=", singleton.client_process_map)
        singleton.client_process_map[tag].append(self.mvision_process) # .. and recycle it
        # print(self.pre, "clearProcess: client_process_map=", singleton.client_process_map)
        if self.analyzer_widget_connected:
            self.mvision_process.disconnectAnalyzerWidget(self.analyzer_widget)
        self.mvision_process = None

    
    def getMasterProcess(self, tag):
        return singleton.get_avail_master_process(tag)

    def clearMasterProcess(self):
        if self.mvision_master_process is None:
            return
        master_tag = self.mvision_master_process.tag
        singleton.master_process_map[master_tag].append(self.mvision_master_process)
        self.mvision_master_process = None


    def activate(self):
        self.mvision_process.activate(
            n_buffer         = singleton.shmem_n_buffer,
            image_dimensions = singleton.shmem_image_dimensions,
            shmem_name       = self.shmem_name
            )
        self.mvision_process.setMasterProcess(self.mvision_master_process)


    def close(self):
        super().close()
        self.clearMasterProcess()
        


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
 
