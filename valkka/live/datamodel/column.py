"""
column.py : cute-mongo-form colums

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    column.py
@author  Sampsa Riikonen
@date    2018
@version 0.12.2 
@brief   
"""

import sys
from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
from cute_mongo_forms.column import Column
from valkka.live.tools import getH264V4l2
from valkka.api2.tools import parameterInitCheck



class USBCameraColumn(Column):
    """Drop-down list of usb cameras
    """

    parameter_defs = {
        "key_name": str,  # name of the database key in key(value)
        "label_name": str   # used to create the forms
    }
    parameter_defs.update(Column.parameter_defs)

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check kwargs agains parameter_defs, attach ok'd parameters to this
        # object as attributes
        parameterInitCheck(self.parameter_defs, kwargs, self)
        self.makeWidget()
        self.reset()

    def makeWidget(self):
        self.widget = QtWidgets.QComboBox()
        self.updateWidget()

    def makeDeviceList(self):
        self.device_list = getH264V4l2()
        self.device_dic  = {}
        for device in self.device_list:
            self.device_dic[device[0]]=device[1] # maps from "/dev/video2" => "HD Webcam Pro"

    def updateWidget(self):
        self.widget.clear()
        self.makeDeviceList()
        for i, item in enumerate(self.device_list):
            devicefile = item[0] # e.g. "/dev/video2"
            name = item[1] # e.g. "HD Webcam Pro"
            self.widget.insertItem(i, name, devicefile) # index, text, data
        self.widget.setCurrentIndex(0)


    def getValue(self):
        # Get the value from QtWidget
        # self.widget.currenText()
        # self.widget.currentData()
        # if evreything goes wrong, currentData could be None, so cast to string
        return str(self.widget.currentData())  # returns devicefile (e.g. "/dev/video2")

    def setValue(self, devicefile):
        # Set the value of the QtWidget
        # if foreign_key is not found (i.e. the row that's using this column has a database having incorrect foreign_key values),
        # findData returns -1
        # setCurrentIndex(-1) sets the selection to void
        if (devicefile in self.device_dic):
            i = self.widget.findData(devicefile)
            self.widget.setCurrentIndex(i)
        else:
            # self.widget.setCurrentIndex(-1)
            self.widget.setCurrentIndex(0)

    def reset(self):
        # self.widget.setCurrentIndex(-1)
        self.widget.setCurrentIndex(0)
            

def main():
  app=QtWidgets.QApplication(["test_app"])
  mg=MyGui()
  mg.show()
  app.exec_()



if (__name__=="__main__"):
  main()
 
