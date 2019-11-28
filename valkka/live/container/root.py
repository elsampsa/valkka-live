"""
root.py : A root level container class.  VideoContainer (see video.py) can be placed in a grid into the root level container.

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    root.py
@author  Sampsa Riikonen
@date    2018
@version 0.9.0 
@brief   A root level container class.  VideoContainer (see video.py) can be placed in a grid into the root level container.
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
from valkka.api2.tools import parameterInitCheck
from valkka.live import style, constant
from valkka.live.gpuhandler import GPUHandler
from valkka.live.quickmenu import QuickMenu, QuickMenuElement
from valkka.live.filterchain import FilterChainGroup
from valkka.live.container.video import VideoContainer


class RootVideoContainer:
    """A container for handling hierarchical QWidgets.  QWidgets can be send to a desired x screen.
    
    This class is not a QWidget itself.  It's used to organize / encapsulate QWidgets and QSignals.
    
    QWidgets owned by this class are filled with qwidgets from container child classes.
    
    Internal QWidgets:
    
    ::
    
    ContainerWindow: the (floating) QWindow
         |
         +-- ContainerWidget: main level QWidget.  Place here the grid, or anything else needed
                      |  
                      +-- GridWidget: place child containers QWidget's here
                      
                      
    Important QWidget members:
    
    - self.window: instance of self.ContainerWindow
    - self.main_widget: instance of self.ContainerWidget
    - self.grid_widget: instance of self.GridWidget
    
    These are instantiated at self.makeWidget
                      
    All QWidgets are instantiated like this:
    
    ::
    
        __init__()
            createChildren() 
            # virtual method : instantiates child Container objects.  Does not instantiate the child container's internal QWidgets

            makeWidget()
                self.window = self.ContainerWindow
                self.main_widget = self.ContainerWidget
                self.grid_widget = self.GridWidget
                    
                placeChildren() 
                # virtual method : calls child Container's makeWidget() => instantiates child Container's QWidgets
                # places child Container's QWidgets to correct place (main QWidget & layout)
    """

    class Signals(QtCore.QObject):
        close = QtCore.Signal()
        closing = QtCore.Signal(object) # carries itself in the signal .. used to inform the main program that this instance can be removed from a list

    class ContainerWindow(QtWidgets.QMainWindow):
        # TODO: connect close signal

        def __init__(self, signals, title, parent=None):
            super().__init__(parent)
            assert(isinstance(signals, RootVideoContainer.Signals))
            self.signals = signals
            self.setPropagate()
            # self.setGeometry(QtCore.QRect(100,100,500,500))
            # self.setStyleSheet("QMainWindow {}")
            self.setMinimumSize(constant.root_video_container_minsize[0], constant.root_video_container_minsize[1])
            self.setStyleSheet(style.root_container)
            self.setWindowTitle(title)

        def setPropagate(self):
            self.propagate = True
                
        def unSetPropagate(self):
            self.propagate = False

        def closeEvent(self, e):
            if (self.propagate):
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

    """
    @classmethod
    def deSerialize(cls, parent = None, gpu_handler: GPUhandler, filterchain_group: filterchain_group, dic = {}):
        # Construct an instance of this class, according to serialized data in dic.  This is the counterparts of the self.serialize method
        # add unseriasizable parameters:
        dic.update({
            "parent" : parent,
            "gpu_handler" : gpu_handler,
            "filterchain_group" : filterchain_group
            })
        return cls(**dic)
    """
       
    parameter_defs = {
        "parent"                : None,
        "gpu_handler"           : GPUHandler,       # this will be passed upstream to child containers (for example VideoContainer)
        "filterchain_group"     : None,             # instance of FilterChainGroup this will be passed upstream to child containers (for example VideoContainer) # None for debugging 
        # seriazable parameters:
        "title"                 : (str, "Video Grid"),
        "n_xscreen"             : (int, 0),
        "child_class"           : (type, VideoContainer),
        "child_class_pars"      : (dict, {}), # common init parameters for child_class ctor
        "child_pars"            : (list, []), # list of kwarg dictionaries for each children
        "geom"                  : (tuple, ()) # a predefined geometry for the ContainerWindow
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(RootVideoContainer.parameter_defs, kwargs, self)
        self.signals = self.Signals()
        self.closed = False
        self.children = []
        self.openglthread = self.gpu_handler.openglthreads[self.n_xscreen]
        # TODO: check number of xscreens and correct self.n_xscreen if necessary

        self.signals.close.connect(self.close_slot)

        # this creates the container objects .. their widgets are created in
        # makeWidget
        self.createChildren(child_class_pars = self.child_class_pars, child_pars = self.child_pars)
        # create widget into a certain xscreen
        self.makeWidget(self.gpu_handler.true_screens[self.n_xscreen], geom = self.geom)


    def makeWidget(self, qscreen: QtGui.QScreen, geom: tuple = ()):
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

        if len(geom) >= 4:
            self.window.setGeometry(
                geom[0],
                geom[1],
                geom[2],
                geom[3]
                )
        
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


    def createChildren(self, child_class_pars = {}, child_pars = []):
        """
        Instantiates objects of the class self.child_class
        
        :param child_class_pars:    common parameters needed for instantiating this kind of child object
        :param child_pars:          individual parameters for instantiating each child object (typically from de-serialization)
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
        
        Closed by clicking the window: goes through self.close_slot
        Closed programmatically: use this method directly
        
        """
        if (self.closed):
            return
        print(self.pre, "close")
        for child in self.children:
            child.close()
        self.openglthread = None
        self.gpu_handler = None
        self.closed = True
        self.window.unSetPropagate() # we don't want the window to send the close signal .. which would call this *again* (through close_slot)
        self.window.close() 


    def serialize(self):
        """Serialize information about the widget: coordinates, size, which cameras are selected.
        """
        # gather all information to re-construct this RootVideoContainer
        dic = {  # parameters that will be used by self.deSerialize to instantiate this class
                "title"       : self.title,
                "n_xscreen"   : self.n_xscreen,
                "child_class" : self.child_class,
                "child_pars"  : [child.serialize() for child in self.children],
                "geom"        : self.getGeom()
                }
        
        return dic


    def getGeom(self):
        return (
            self.window.x(),
            self.window.y(),
            self.window.width(),
            self.window.height()
            )


    def deSerialize(self, dic, devices_by_id):
        print(self.pre, "deSerialize : dic", dic)
        print(self.pre, "deSerialize : devices_by_id", devices_by_id)
        
        self.window.setGeometry(
            dic["x"],
            dic["y"],
            dic["width"],
            dic["height"]
            )
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
        self.signals.closing.emit(self)
        self.close()




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
 
