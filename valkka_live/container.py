"""
container.py : Classes for handling video streams in Qt Widgets

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    container.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   Classes for handling video streams in Qt Widgets
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
import time
import pickle
# from valkka.valkka_core import *
from valkka.api2.tools import parameterInitCheck
from valkka.api2.chains import ViewPort
from valkka_live import style
from valkka_live.gpuhandler import GPUHandler
from valkka_live.quickmenu import QuickMenu, QuickMenuElement, QuickMenuSection
from valkka_live.filterchain import FilterChainGroup


class MouseClickContext:
    """A class that helps you distinguish between different kind of mouse clicks and gestures

    The scheme here is:

    - user clicks .. atPressEvent
    - user releases .. a timer is started
    - user clicks again .. atPressEvent
      if timer active, this is a double click
    - timer goes off before a new click
      this is a single click
    """

    class MouseClickInfo:

        def __init__(self):
            self.fsingle = False
            self.fdouble = False
            self.flong = False

            self.button = None
            self.event = None
            self.pos = None

        def __str__(self):
            st = "\n"
            st += "single: " + str(self.fsingle) + "\n"
            st += "double: " + str(self.fdouble) + "\n"
            st += "long  : " + str(self.flong) + "\n"
            return st

    def_t_long_click = 2    # definition of "long" click in seconds
    def_t_double_click = 500  # definition of double click in _milli_seconds

    def __init__(self, callback=None, t_double_click=def_t_double_click,
                 t_long_click=def_t_long_click):
        self.callback = callback

        self.t_double_click = t_double_click
        self.t_long_click = t_long_click

        self.timer = QtCore.QTimer()
        self.timer   .setSingleShot(True)
        self.timer   .timeout.connect(self.timer_slot)
        self.info = self.MouseClickInfo()

    def atPressEvent(self, e):
        if (self.timer.isActive()):
            self.info.fdouble = True
            self.info.fsingle = False
        else:
            self.info.fsingle = True
        self.t = time.time()
        # print("MouseClickContext:",e.button())
        self.info.button = e.button()
        # self.info.events.append(e)
        self.info.event = e  # save the event..
        self.info.pos = e.globalPos()

    def atReleaseEvent(self, e):
        dt = time.time() - self.t
        if (dt > self.t_long_click):  # a "long" click
            self.info.flong = True
        self.timer.start(self.t_double_click)

    def getPos(self):
        """
        button=e.button()
        p=e.globalPos()
        """
        return self.info.pos

    def timer_slot(self):
        # print("MouseClickContext: info="+str(self.info))
        if (self.callback is None):
            return
        self.callback(self.info)
        # single click: one event, double click: two events
        self.info = self.MouseClickInfo()



class VideoContainer:
    """A Container handling a master QWidget that encloses a video QWidget, and if required other widgets as well (buttons, alerts, etc.)

    Does not handle x-screen change (this should be done by the parent widget)
    """

    class Signals(QtCore.QObject):
        close = QtCore.Signal(object)
        drop  = QtCore.Signal(object)

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
                print("VideoWidget: got: ", device) # DataModel.RTSPCameraDevice
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
        "filterchain_group" : FilterChainGroup,     # Filterchain manager class
        "n_xscreen"         : (int,0)               # x-screen index
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(self.parameter_defs, kwargs, self)
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
        
        :param device:      A rather generic device class.  In this case DataModel.RTSPCameraDevice.
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
        

    def getDevice(self): # e.g. DataModel.RTSPCameraDevice
        return self.device
    

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

    def handle_right_single_click(self, info):
        # get the QMenu object from the QuickMenu helper class and show it
        self.right_click_menu.menu.popup(QtGui.QCursor.pos())


class RootVideoContainer:
    """A container handling hierarchical QWidgets.  QWidgets can be send to a desired x screen.
    """

    class Signals(QtCore.QObject):
        close = QtCore.Signal()

    class ContainerWindow(QtWidgets.QMainWindow):
        # TODO: connect close signal

        def __init__(self, signals, title, parent=None):
            super().__init__(parent)
            assert(isinstance(signals, RootVideoContainer.Signals))
            self.signals = signals
            # self.setGeometry(QtCore.QRect(100,100,500,500))
            # self.setStyleSheet("QMainWindow {}")
            self.setMinimumSize(500, 500)
            self.setStyleSheet(style.root_container)
            self.setWindowTitle(title)

        def closeEvent(self, e):
            self.signals.close.emit()
            super().closeEvent(e)

    class ContainerWidget(QtWidgets.QWidget):
        """Main level widget: this contains the GridWidget and anything else needed
        """
        pass

    class GridWidget(QtWidgets.QWidget):
        """The VideoContainerWidget(s) appear here in a grid
        """
        pass

    parameter_defs = {
        "parent"                : None,
        "gpu_handler"           : GPUHandler,
        "filterchain_group"     : FilterChainGroup, # this will be passed upstream to VideoContainer
        "title"                 : (str, "Video Grid")
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(self.parameter_defs, kwargs, self)
        self.signals = self.Signals()
        self.closed = False
        self.children = []
        self.n_xscreen = 0  # x-screen number
        self.openglthread = self.gpu_handler.openglthreads[self.n_xscreen]

        self.signals.close.connect(self.close_slot)

        # this creates the container objects .. their widgets are created in
        # makeWidget
        self.createChildren()
        # create widget into a certain xscreen
        self.makeWidget(self.gpu_handler.true_screens[self.n_xscreen])

    def makeWidget(self, qscreen: QtGui.QScreen):
        # (re)create the widget, do the same for children
        # how children are placed on the parent widget, depends on the subclass
        self.window = self.ContainerWindow(
            self.signals, self.title, self.parent)

        # send to correct x-screen
        self.window.show()
        self.window.windowHandle().setScreen(qscreen)
        self.n_xscreen = self.gpu_handler.getXScreenNum(qscreen) # the correct x-screen number must be passed upstream, to the VideoContainer

        # continue window / widget construction in the correct x screen
        self.main_widget = self.ContainerWidget(self.window)
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.window.setCentralWidget(self.main_widget)

        # add here any extra turf to the widget you want in addition to the
        # grid

        # create the grid
        self.grid_widget = self.GridWidget(self.main_widget)
        self.main_layout.addWidget(self.grid_widget)

        self.grid_layout = QtWidgets.QGridLayout(self.grid_widget)
        self.grid_layout.setHorizontalSpacing(2)
        self.grid_layout.setVerticalSpacing(2)
        # ( int left, int top, int right, int bottom )
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        class ScreenMenu(QuickMenu):
            title = "Change Screen"
            elements = [
                QuickMenuElement(title="Screen 1"),
                QuickMenuElement(title="Screen 2")
            ]
            
        """ TODO: activate after gpu-hopping has been debugged
        self.screenmenu = ScreenMenu(self.window)
        self.screenmenu.screen_1.triggered.connect(self.test_slot)
        self.screenmenu.screen_2.triggered.connect(self.test_slot)
        """

        if (len(self.gpu_handler.true_screens) > 1):
            # so, there's more than a single x screen: create a button for
            # changing x-screens
            self.button = QtWidgets.QPushButton(
                "Change Screen", self.main_widget)
            self.main_layout.addWidget(self.button)
            self.button.setSizePolicy(
                QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Minimum)
            self.button.clicked.connect(self.change_xscreen_slot)

        self.placeChildren()

    def createChildren(self):
        """Create child objects, say VideoContainer(s)
        """
        raise(AttributeError("virtual method"))

    def placeChildren(self):
        """Create child object(s) main_widget instances.  Place them to the layout.

        Along these lines:

        ::

            for child in self.children:
              child.makeWidget(self.grid_widget) # re-create widgets in the child objects .. their parent is the grid
              child.main_widget.setParent(self.grid_widget) # set widget parent/child relation
        """
        raise(AttributeError("virtual method"))

    def close(self):
        """Called by the main gui to close the containers.  Called also when the container widget is closed
        """
        if (self.closed):
            return
        print(self.pre, "close")
        for child in self.children:
            child.close()
        self.openglthread = None
        self.gpu_handler = None
        self.closed = True
        self.window.close() 

    def serialize(self):
        """Serialize information about the widget: coordinates, size, which cameras are selected.
        """
        ids = []
        for child in self.children:
            device = child.getDevice()
            if device:
                ids.append(device._id) # e.g. DataModel.RTSPCameraDevice._id
            else:
                ids.append(None)

        # gather all information to re-construct this RootVideoContainer
        dic = {  # these are used when re-instantiating the view
            "classname": self.__class__.__name__,
            "kwargs": {},  # parameters that we're used to instantiate this class
            # these parameters are used by deserialize
            "x": self.window.x(),
            "y": self.window.y(),
            "width": self.window.width(),
            "height": self.window.height(),
            "ids": ids
        }

        return dic

    def deSerialize(self, dic, devices_by_id):
        print(self.pre, "deSerialize : dic", dic)
        print(self.pre, "deSerialize : devices_by_id", devices_by_id)
        self.window.setGeometry(
            dic["x"],
            dic["y"],
            dic["width"],
            dic["height"])
        childiter = iter(self.children)
        
        for _id in dic["ids"]:
            child = next(childiter) # follow the grid layout
            if _id in devices_by_id:
                device = devices_by_id[_id]
            else:
                device = None
                
            child.setDevice(device)

    # *** slots ***

    def test_slot(self):
        print(self.pre, "test_slot")

    def close_slot(self):
        print(self.pre, "close_slot")
        self.close()


class VideoContainerNxM(RootVideoContainer):
    """A RootVideoContainer with n x m (y x x) video grid
    """

    parameter_defs = {
        "parent"            : None,
        "gpu_handler"       : GPUHandler,
        "filterchain_group" : FilterChainGroup, # this will be passed upstream to VideoContainer
        "title"             : (str, "Video Grid"),
        "n_dim"             : (int, 1),  # y  3
        "m_dim"             : (int, 1)  # x  2
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def serialize(self):
        dic = super().serialize()
        dic["kwargs"] = {"title": self.title,
                         "n_dim": self.n_dim,
                         "m_dim": self.m_dim
                         }
        return dic

    def createChildren(self):
        for i in range(self.n_dim * self.m_dim):
            vc = VideoContainer(filterchain_group = self.filterchain_group, n_xscreen = self.n_xscreen)
            self.children.append(vc)

    def placeChildren(self):
        # print(self.pre, "placeChildren :", self.n_dim, self.m_dim)
        for i, child in enumerate(self.children):
            child.makeWidget(parent=self.grid_widget)
            """
            print(
                self.pre,
                "placeChildren : ",
                i //
                self.m_dim,
                i %
                self.m_dim)
            print(
                self.pre,
                "placeChildren : placing",
                child.main_widget,
                "into",
                self.grid_layout)
            """
            self.grid_layout.addWidget(
                child.main_widget, i // self.m_dim, i %
                self.m_dim)

        # define how to get some callback functions
        def get_hide_others_func(this_child):
            def hide_others():  # hide all other children than "this_child"
                for child_ in self.children:
                    if (child_ != this_child):
                        child_.hide()
            return hide_others

        def get_show_others_func(this_child):
            def show_others():  # apply show to all other children than "this_child"
                for child_ in self.children:
                    if (child_ != this_child):
                        child_.show()
            return show_others

        for child in self.children:
            # pass those callbacks to each child
            child.set_cb_focus(get_hide_others_func(child))
            child.set_cb_unfocus(get_show_others_func(child))


class MyGui(QtWidgets.QMainWindow):

    debug = False
    # debug=True

    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.initVars()
        self.setupUi()
        if (self.debug):
            return
        self.openValkka()

    def initVars(self):
        pass

    def setupUi(self):
        self.setGeometry(QtCore.QRect(150, 150, 150, 150))

        """
        self.w=QtWidgets.QFrame(self)
        self.w.setStyleSheet("QWidget {background-color:green;}")
        self.w.setAutoFillBackground(True)
        self.w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.b =QtWidgets.QPushButton("kokkelis",self.w)

        self.setCentralWidget(self.w)
        """

        self.container = VideoContainerNxM(
            gpu_handler=GPUHandler(),
            n_dim=3,
            m_dim=2)  # TODO: pass parent widget?
        # self.container =VideoContainer(); self.container.makeWidget()
        # self.setCentralWidget(self.container.main_widget)
        dic = self.container.serialize()
        print("gui",dic)
        self.container.close()

        cls = globals()[dic["classname"]]
        kw = dic["kwargs"]
        self.container2 = cls(
            gpu_handler=GPUHandler(),
            n_dim=kw["n_dim"],
            m_dim=kw["m_dim"])
        self.container.deSerialize(dic)

    def openValkka(self):
        pass

    def closeValkka(self):
        pass

    def closeEvent(self, e):
        print("closeEvent!")
        self.closeValkka()
        e.accept()


def main():
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()
