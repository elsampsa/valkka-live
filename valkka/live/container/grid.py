"""
grid.py : Classes implementing a N x M grid, based on the RootVideoContainer (see root.py)

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    grid.py
@author  Sampsa Riikonen
@date    2018
@version 0.9.0 
@brief   Classes implementing a N x M grid, based on the RootVideoContainer (see root.py)
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
import copy
from valkka.api2.tools import parameterInitCheck

from valkka.live import style
from valkka.live.gpuhandler import GPUHandler
from valkka.live.quickmenu import QuickMenu, QuickMenuElement
from valkka.live.filterchain import FilterChainGroup
from valkka.live.container.root import RootVideoContainer
from valkka.live.container.video import VideoContainer


class VideoContainerNxM(RootVideoContainer):
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
        
        
    TODO: VideoContainerNxM.deSerialize (class method)
    VideoContainerNxM ctor should take a list of child objects .. that can be used to ctruct the children (in fact, RootVideoContainer should have this)
    VideoContainer ctor should take as an optional argument a device object
    
    
    
    """
    parameter_defs = {
        "n_dim"             : (int, 1),  # y  3
        "m_dim"             : (int, 1)   # x  2
        }
    parameter_defs.update(RootVideoContainer.parameter_defs)
    
    
    def __init__(self, **kwargs):
        parameterInitCheck(VideoContainerNxM.parameter_defs, kwargs, self)
        kwargs.pop("n_dim")
        kwargs.pop("m_dim")
        super().__init__(**kwargs)


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
 
