"""
playgrid.py : Classes implementing a N x M grid, based on the RootVideoContainer (see root.py).  For playback, with time & calendar widgets

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    grid.py
@author  Sampsa Riikonen
@date    2018
@version 0.12.0 
@brief   Classes implementing a N x M grid, based on the RootVideoContainer (see root.py)
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
import copy
import datetime

from valkka.api2.tools import parameterInitCheck
from valkka.api2 import ValkkaFSManager, ValkkaFS

from valkka.live import style
from valkka.live.gpuhandler import GPUHandler
from valkka.live.quickmenu import QuickMenu, QuickMenuElement
from valkka.live.filterchain import FilterChainGroup
from valkka.live.container.root import RootVideoContainer
from valkka.live.container.video import VideoContainer
from valkka.live.qt.playwidget import TimeLineWidget, CalendarWidget
from valkka.live.qt.playback import PlaybackController, WidgetSet


class PlayVideoContainerNxM(RootVideoContainer):
    """A RootVideoContainer with n x m (y x x) video grid for live video
    
    
    ::
    
    
        VideoContainerNxM
            |
            +- VideoContainer
            |
            +- VideoContainer
            |
            +- VideoContainer
        
        Each VideoContainer initialized with:
        
            "parent_container"  : None,                 # RootVideoContainer or child class
            "filterchain_group" : FilterChainGroup,     # Filterchain manager class
            "n_xscreen"         : (int, 0),             # x-screen index
            "verbose"           : (bool, False)
            
        
    
    Deserialization process:
    
    - Read class name VideoContainerNxM
    - Read kwargs
    - Instantiate VideoContainerNxM(**kwargs)
        => empty VideoContainerNxM, with VideoContainers, with correct parent, FilterChainGroup, xscreen, etc.
        
    """

    class ContainerWidget(QtWidgets.QTabWidget):
        """Main level widget: this contains the GridWidget and anything else needed
        """
        pass


    parameter_defs = {
        "n_dim"             : (int, 1),  # y  3
        "m_dim"             : (int, 1),  # x  2
        "valkkafsmanager"   : ValkkaFSManager,
        "playback_controller" : PlaybackController
        }
    parameter_defs.update(RootVideoContainer.parameter_defs)
    
    
    def __init__(self, **kwargs):
        parameterInitCheck(PlayVideoContainerNxM.parameter_defs, kwargs, self)
        kwargs.pop("n_dim")
        kwargs.pop("m_dim")
        kwargs.pop("valkkafsmanager")
        kwargs.pop("playback_controller")
        super().__init__(**kwargs)


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
        self.main_widget = self.ContainerWidget(self.window) # a QTabWidget
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.window.setCentralWidget(self.main_widget)

        if len(geom) >= 4:
            self.window.setGeometry(
                geom[0],
                geom[1],
                geom[2],
                geom[3]
                )
        
        # create tabs
        self.play_video_tab = QtWidgets.QWidget(None)
        self.play_video_lay = QtWidgets.QVBoxLayout(self.play_video_tab)
        
        self.calendar_tab = QtWidgets.QWidget(None)
        self.calendar_lay = QtWidgets.QVBoxLayout(self.calendar_tab)
        
        self.main_widget.addTab(self.play_video_tab, "Recordings")
        self.main_widget.addTab(self.calendar_tab, "Calendar")
        
        # **** Recordings tab *****
        # create the grid into "the Recordings" tab (self.play_video_tab)
        self.grid_widget = self.GridWidget(self.play_video_tab)
        self.play_video_lay.addWidget(self.grid_widget)

        self.grid_layout = QtWidgets.QGridLayout(self.grid_widget)
        self.grid_layout.setHorizontalSpacing(2)
        self.grid_layout.setVerticalSpacing(2)
        # ( int left, int top, int right, int bottom )
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        # put timeline widget under the grid
        self.timelinewidget = TimeLineWidget(datetime.date.today(), parent = self.play_video_tab)
        # self.timelinewidget.setLogLevel(logging.DEBUG)
        self.play_video_lay.addWidget(self.timelinewidget)
        
        # put buttons under the timeline
        self.buttons = QtWidgets.QWidget(self.play_video_tab)
        self.buttons_lay = QtWidgets.QHBoxLayout(self.buttons)

        self.play_video_lay.addWidget(self.buttons)
        
        self.play_button = QtWidgets.QPushButton("play", self.buttons)
        self.stop_button = QtWidgets.QPushButton("stop", self.buttons)
        self.zoom_to_fs_button = QtWidgets.QPushButton("limits", self.buttons)
        
        self.buttons_lay.addWidget(self.play_button)
        self.buttons_lay.addWidget(self.stop_button)
        self.buttons_lay.addWidget(self.zoom_to_fs_button)
        
        # **** Calendar tab *****
        # put the calendar into the "Calendar" tab (self.calendar_tab)
        # calendar
        self.calendarwidget = CalendarWidget(datetime.date.today(), parent = self.calendar_tab)
        self.calendar_lay.addWidget(self.calendarwidget)

        """
        self.playback_controller = PlaybackController(
            calendar_widget     = self.calendarwidget,
            timeline_widget     = self.timelinewidget,
            valkkafs_manager    = self.valkkafsmanager,
            play_button         = self.play_button,
            stop_button         = self.stop_button
            )
        """
        self.widget_set = WidgetSet(
            calendar_widget     = self.calendarwidget,
            timeline_widget     = self.timelinewidget,
            play_button         = self.play_button,
            stop_button         = self.stop_button,
            zoom_to_fs_button   = self.zoom_to_fs_button
        )
        self.playback_controller.register(self.widget_set)

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


    def serialize(self):
        dic = super().serialize()
        dic.update({ # add constructor parameters of this class
            "n_dim": self.n_dim,
            "m_dim": self.m_dim
            })
        return dic


    def createChildren(self, child_class_pars = {}, child_pars = []):
        """
        :param child_class_pars:    common parameters needed for instantiating this kind of child object
        :param child_pars:          individual parameters for instantiating each child object (typically from de-serialization)
        """
        for i in range(self.n_dim * self.m_dim):
            pars = {
                "filterchain_group" : self.filterchain_group,
                "n_xscreen"         : self.n_xscreen
                }
            
            # set per-child object parameters
            if len(child_pars) > i:
                print("createChildren: child_pars", child_pars)
                pars_ = child_pars[i] # typically from the de-serialization
                pars.update(pars_)
                
            # set common parameters for this kind of class:
            pars.update(child_class_pars)
            # instantiate the object:
            vc = self.child_class(**pars)
            self.children.append(vc)


    def placeChildren(self):
        # print(self.pre, "placeChildren :", self.n_dim, self.m_dim)
        for i, child in enumerate(self.children):
            child.makeWidget(parent=self.grid_widget)
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


    def close(self):
        self.playback_controller.deregister(self.widget_set)
        super().close()





class MyGui(QtWidgets.QMainWindow):


    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.setupUi()
    

    def setupUi(self):
        self.setGeometry(QtCore.QRect(100,100,800,800))

        self.valkkafs = ValkkaFS.loadFromDirectory(dirname="/home/sampsa/tmp/testvalkkafs")
        self.manager = ValkkaFSManager(self.valkkafs)
        self.manager.setOutput_(925412, 1) # id => slot

        gpu_handler = GPUHandler()

        pvc = PlayVideoContainerNxM(
            n_dim = 3, 
            m_dim =3, 
            valkkafsmanager = self.manager, 
            gpu_handler = gpu_handler,
            filterchain_group = None
            )

        # dummy window
        self.w = QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)
        self.lay = QtWidgets.QVBoxLayout(self.w)
        
    
def main():
    app=QtWidgets.QApplication(["test_app"])
    mg=MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()

"""
TODO:
- A different filterchain group for playback
- Finish valkkafs config
- Connect live filterchain to valkkafs
- Enable creating playgrid views in the main gui
"""


