"""
formtest.py : Test Cute Mongo Forms forms

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    formtest.py
@author  Sampsa Riikonen
@date    2018
@version 0.14.1 
@brief   Test Cute Mongo Forms forms
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
import cute_mongo_forms

from valkka.live.local import ValkkaLocalDir
from valkka.live import singleton

singleton.config_dir = ValkkaLocalDir("live")
singleton.valkkafs_dir = ValkkaLocalDir("live","fs")

from valkka.live.datamodel.base import DataModel


class MyGui(QtWidgets.QMainWindow):

  
  def __init__(self,parent=None):
    super(MyGui, self).__init__()
    self.initVars()
    self.setupUi()
    

  def initVars(self):
    self.dm = DataModel(directory = singleton.config_dir.get())
    # self.dm.clearAll()
    print(cute_mongo_forms.__file__)


  def setupUi(self):
    # self.setGeometry(QtCore.QRect(100,100,500,500))
    
    self.w=QtWidgets.QWidget(self)
    self.setCentralWidget(self.w)
    self.lay = QtWidgets.QVBoxLayout(self.w)
    
    self.container = self.dm.getDeviceListAndForm(self.w)
    self.lay.addWidget(self.container.widget)
    
    
  def closeEvent(self,e):
    print("closeEvent!")
    e.accept()



def main():
    app=QtWidgets.QApplication(["test_app"])
    mg=MyGui()
    mg.show()
    app.exec_()



if (__name__=="__main__"):
  main()
 
