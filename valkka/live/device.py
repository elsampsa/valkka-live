"""
device.py : Device objects used in drag'n'drop

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    device.py
@author  Sampsa Riikonen
@date    2018
@version 0.12.1 
@brief   Device objects used in drag'n'drop
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
from valkka.api2.tools import parameterInitCheck



class RTSPCameraDevice:
    """Device class used in drag'n'drop.  Copies the members of RTSPCameraRow
    """

    parameter_defs = {
        "_id"       : int,
        "slot"      : int,
        "address"   : str,
        "username"  : str,
        "password"  : str,
        "port"      : (str, ""),
        "tail"      : (str, ""),
        "force_tcp" : (bool, False),

        "subaddress_main" : (str, ""),
        "live_main" : (bool, True),
        "rec_main"  : (bool, False),
        "subaddress_sub"  : (str, ""),
        "live_sub" : (bool, False),
        "rec_sub"  : (bool, False)
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(RTSPCameraDevice.parameter_defs, kwargs, self)

    def __eq__(self, other):
        return self._id == other._id
                    
    def getMainAddress(self):
        st = "rtsp://" + self.username + ":" + self.password + "@" + self.address 
        if (len(self.tail)>0):
            st += "/" + self.tail 
        if (len(self.subaddress_main)>0):
            st += "/" + self.subaddress_main
        return st

    def getSubAddress(self):
        st = "rtsp://" + self.username + ":" + self.password + "@" + self.address
        if (len(self.tail)>0):
            st += "/" + self.tail 
        if (len(self.subaddress_sub)>0):
            st += "/" + self.subaddress_main
        return st

    def getForceTCP(self):
        return self.force_tcp

    def getLabel(self):
        st = "rtsp://" + self.address
        if (len(self.tail)>0):
            st += "/" + self.tail
        return st
    
    # the following methods give the true slot numbers used by Valkka
    # one slot for main, sub and recorded stream per camera
    # 1..3, 4..6, 7..9, etc.
    def getLiveMainSlot(self):
        return (self.slot-1)*3+1
    
    def getLiveSubSlot(self):
        return (self.slot-1)*3+2
    
    def getRecSlot(self):
        return (self.slot-1)*3+3
        

class USBCameraDevice:
    """Device class used in drag'n'drop.  Copies the members of RTSPCameraRow
    """

    parameter_defs = {
        "_id"       : int,
        "slot"      : int,
        "address"   : str
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(USBCameraDevice.parameter_defs, kwargs, self)

    def __eq__(self, other):
        return self._id == other._id
                    
    def getMainAddress(self):
        return self.address

    def getSubAddress(self):
        return self.address
    
    def getLabel(self):
        return "usb:"+self.address
        

    # the following methods give the true slot numbers used by Valkka
    # one slot for main, sub and recorded stream per camera
    # 1..3, 4..6, 7..9, etc.
    def getLiveMainSlot(self):
        return (self.slot-1)*3+1
    
    def getLiveSubSlot(self):
        return (self.slot-1)*3+2
    
    def getRecSlot(self):
        return (self.slot-1)*3+3


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
 
