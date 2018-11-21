"""
mouse.py : a class for separating and handling mouse events (click, double-click, etc.)

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    mouse.py
@author  Sampsa Riikonen
@date    2018
@version 0.6.0 
@brief   a class for separating and handling mouse events (click, double-click, etc.)
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
import time
from valkka.api2.tools import parameterInitCheck


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
 
