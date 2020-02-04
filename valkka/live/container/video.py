"""
video.py : a container that manages widgets for video

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    video.py
@author  Sampsa Riikonen
@date    2018
@version 0.12.1 
@brief   a container that manages widgets for video
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
import pickle
from valkka.api2.tools import parameterInitCheck
from valkka.api2.chains import ViewPort

from valkka.live import singleton
from valkka.live import style
from valkka.live.quickmenu import QuickMenu, QuickMenuElement, QuickMenuSection
from valkka.live.filterchain import FilterChainGroup
from valkka.live.mouse import MouseClickContext


class VideoContainer:
    """
    This class is not a QWidget itself.  It's used to organize / encapsulate QWidgets and QSignals.
    
    This is a Container handling a master QWidget that encloses a video QWidget, and if required, other widgets as well (buttons, alerts, etc.)

    Does not handle X-screen hop / change (this should be done by the parent widget)
    
    Internal QWidgets:
    
    ::    
         
        ContainerWidget
             |
             +-- VideoWidget (handles drag'n'drop)
                    - Drag'n'drop receives objects of the type device.RTSPCameraDevice (has member _id to define uniquely a stream)
                      into VideoContainer.setDevice (i.e. into the main container object method)
                

    Important parameter members:
    
    - self.filterchain_group : an instance of FilterChainGroup: filterchains can be instantiated / get'ted by a unique _id
    - self.viewport : an instance of ViewPort: several ViewPort instances can be added to a filterchain; they represent endpoints of the video on the screen (OpenGL windows)

    Important QWidget members:
    
    - self.main_widget: instance of self.ContainerWidget

    QWidgets are instantiated like this:
    
    ::
    
        makeWidget()
            # this is called by the parent container object in its placeChildren method (see for example root.RootVideoContainer)
            self.main_widget = self.ContainerWidget
            self.video = self.VideoWidget(parent = self.main_widget)

    """

    class Signals(QtCore.QObject):
        close = QtCore.Signal(object)
        drop  = QtCore.Signal(object)
        left_double_click  = QtCore.Signal()
        right_double_click = QtCore.Signal()
        
    # Right-click pop-up menu
    # Adding installed cameras here could be done as follows: create this
    # class and the callbacks dynamically

    class RightClickMenu(QuickMenu):
        title = "popup"
        elements = [
            QuickMenuSection(title="Choose Action"),
            QuickMenuElement(
                title="Maximize / Normalize Size",
                method_name="maximize"),
            QuickMenuElement(title="Remove Camera")
        ]

    class ContainerWidget(QtWidgets.QWidget):
        """Main level widget: this contains the VideoWidget and additionally, alert widgets, button for changing x screen, etc.
        """
        # TODO: connect close signal

        def __init__(self, parent):
            super().__init__(parent)
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding)

    class VideoWidget(QtWidgets.QFrame):
        """The video appears here.  Must handle drag'n'drop of camera info.  Or choosing camera from a pop-up menu.
        """

        def __init__(self, parent=None, mouse_gesture_handler=lambda e: None):
            super().__init__(parent)
            # self.setStyleSheet("background-color: dark-blue")
            # self.setStyleSheet("background-color: rgba(0,0,0,0)");
            # self.setStyleSheet("border: 1px solid gray; border-radius: 10px; margin: 0px; padding: 0px; background: white;")
            self.setStyleSheet(style.video_widget)
            self.setAutoFillBackground(True)
            self.setAcceptDrops(True)
            
            self.signals = VideoContainer.Signals()
            
            self.device = None
            
            """
            pal = QtGui.QPalette()
            pal.setColor(QtGui.QPalette.Background, QtCore.Qt.black);
            self.setPalette(pal);
            """
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding)
            self.mouse_click_ctx = MouseClickContext(mouse_gesture_handler)

        # TODO: how we communicate, say, a double-click, to the higher-level widget
        # VideoContainer .. give it a callback that hides/shows all other
        # widgets .. (stream decoding should be paused as well if needed)

        def setDevice(self, device):
            self.device = device

        def dragEnterEvent(self, e):
            print("VideoWidget: dragEnterEvent")
            e.accept()

        def dropEvent(self, e):
            print("VideoWidget: dropEvent")
            # print("VideoWidget: drop event to i,j=",self.row_index,self.column_index)
            formlist = e.mimeData().formats()
            if ("application/octet-stream" in formlist):
                device = pickle.loads(
                    e.mimeData().data("application/octet-stream").data())
                print("VideoWidget: got: ", device) # device.RTSPCameraDevice
                self.signals.drop.emit(device)
                e.accept()
            else:
                e.ignore()

        def mousePressEvent(self, e):
            print("VideoWidget: mousePress")
            self.mouse_click_ctx.atPressEvent(e)
            super().mousePressEvent(e)
            
        def mouseMoveEvent(self, e):
            if not (e.buttons() & QtCore.Qt.LeftButton):
                return
            
            leni = ( e.pos() - self.mouse_click_ctx.info.pos ).manhattanLength()
            
            if (leni < QtWidgets.QApplication.startDragDistance()):
                return

            drag = QtGui.QDrag(self)
            mimeData = QtCore.QMimeData()

            mimeData.setData("application/octet-stream", 
                             pickle.dumps(self.device)
                             # pickle.dumps(None)
                             )
            drag.setMimeData(mimeData)

            dropAction = drag.exec_(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction)
            
            
        def mouseReleaseEvent(self, e):
            self.mouse_click_ctx.atReleaseEvent(e)
            super().mouseReleaseEvent(e)

    parameter_defs = {
        "parent_container"  : None,                 # RootVideoContainer or child class
        "filterchain_group" : None,                 # Instance of FilterChainGroup.  Filterchain manager class.  # None for debugging
        "n_xscreen"         : (int, 0),             # x-screen index
        "verbose"           : (bool, False),
        "device_id"         : (int, -1)             # optional: the unique id of this video stream
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        print(self.pre, kwargs)
        parameterInitCheck(VideoContainer.parameter_defs, kwargs, self)
        self.signals = self.Signals()
        
        # reset callback functions
        self.set_cb_focus()
        self.set_cb_unfocus()

        # container state variables
        self.double_click_focus = False  # has this container been double-click focused

        # right-click menu
        self.right_click_menu = self.RightClickMenu()
        self.right_click_menu.maximize.triggered.connect(lambda x: self.handle_left_double_click(
            None))  # use lambda as we must connect to a function
        self.right_click_menu.remove_camera.triggered.connect(self.clearDevice)

        # no stream yet
        self.device = None
        self.filterchain = None
        self.viewport = ViewPort() # viewport instance is used by ManagedFilterChain(s)


    def serialize(self):
        """Return a dict of parameters that the parent object needs to de-serialize & instantiate this object
        """
        return {
            "device_id" : self.getDeviceId()
            }
        
    def report(self, *args):
        if (self.verbose):
            print(self.pre, *args)

    def __del__(self):
        # self.close()
        pass

    # callback setters

    def set_cb_focus(self, cb=lambda x: None):
        self.cb_focus = cb

    def set_cb_unfocus(self, cb=lambda x: None):
        self.cb_unfocus = cb

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
            

    def hide(self):
        """Hide the widget.  Stream is not required while hidden.
        """
        self.main_widget.hide()

    def show(self):
        """Show the widget.  Stream is required again (if it was on)
        """
        self.main_widget.show()

    def close(self):
        """Called by the RootContainer when it's being closed
        """
        self.clearDevice()
        self.main_widget.close()

    def setDevice(self, device): 
        """Sets the video stream
        
        :param device:      A rather generic device class.  In this case device.RTSPCameraDevice.
        """
        print(self.pre, "setDevice :", device)
        
        if (not device and not self.device): # None can be passed as an argument when the device has not been set yet
            return
            
        if (self.device):
            if self.device == device:
                print(self.pre, "setDevice : same device")
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


    def setDeviceById(self, _id):
        """Set the video to this VideoContainer by stream id only
        """
        print(self.pre, "setDeviceById:", _id)
        try:
            device = singleton.devices_by_id[_id]
        except KeyError:
            print(self.pre, "setDeviceById: no device with id", _id)
            return
        else:
            self.setDevice(device)
        
        
    def clearDevice(self):
        """Remove the current stream
        """
        print(self.pre, "clearDevice")
        if not self.device:
            return
        
        self.filterchain.delViewPort(self.viewport)
        
        self.filterchain = None
        self.device = None
        
        self.video.update()
        

    def getDevice(self): # e.g. device.RTSPCameraDevice
        return self.device
    
    
    def getDeviceId(self):
        if self.device is None:
            return -1
        else:
            return self.device._id # e.g. device.RTSPCameraDevice
    

    def mouseGestureHandler(self, info):
        """This is the callback for MouseClickContext.  Passed to VideoWidget as a parameter
        """
        print(self.pre, ": mouseGestureHandler: ")
        # *** single click events ***
        if (info.fsingle):
            print(self.pre, ": mouseGestureHandler: single click")
            if (info.button == QtCore.Qt.LeftButton):
                print(self.pre, ": mouseGestureHandler: Left button clicked")
            elif (info.button == QtCore.Qt.RightButton):
                print(self.pre, ": mouseGestureHandler: Right button clicked")
                self.handle_right_single_click(info)
        # *** double click events ***
        elif (info.fdouble):
            if (info.button == QtCore.Qt.LeftButton):
                print(
                    self.pre,
                    ": mouseGestureHandler: Left button double-clicked")
                self.handle_left_double_click(info)
            elif (info.button == QtCore.Qt.RightButton):
                print(
                    self.pre,
                    ": mouseGestureHandler: Right button double-clicked")
                self.handle_right_double_click(info)

    # mouse gesture handlers

    def handle_left_double_click(self, info):
        """Whatever we want to do, when the VideoWidget has been double-clicked with the left button
        """
        if (self.double_click_focus == False):  # turn focus on
            print(self.pre, "handle_left_double_click: focus on")
            self.cb_focus()
        else:  # turn focus off
            print(self.pre, "handle_left_double_click: focus off")
            self.cb_unfocus()
        self.double_click_focus = not(
            self.double_click_focus)  # boolean switch
        self.signals.left_double_click.emit()

    def handle_right_single_click(self, info):
        # get the QMenu object from the QuickMenu helper class and show it
        self.right_click_menu.menu.popup(QtGui.QCursor.pos())

    def handle_right_double_click(self, info):
        self.signals.right_double_click.emit()



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
 
