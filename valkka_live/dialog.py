"""
dialog.py : Dialog, help and warning windows

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    dialog.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   Dialog, help and warning windows
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
from valkka_live import constant


# TODO: text dialog



class EulaDialog(QtGui.QDialog):
  
  def __init__(self,fname,parent=None):
    super(EulaDialog,self).__init__(parent)
  
    self.setWindowTitle(Data.translator.get(u'End User License Agreement'))
    
    # self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint) #  | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.X11BypassWindowManagerHint)
    # self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowTitleHint)
    # self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
    
    self.license=QtGui.QTextEdit(self)
    self.license.setReadOnly(True)
    self.scrollbar=self.license.verticalScrollBar()
    
    self.txt=QtGui.QLabel(Data.translator.get(u'By pressing Accept, I accept the license terms'),self)
    self.layout=QtGui.QVBoxLayout(self)
    
    self.buttons=QtGui.QWidget(self)
    self.ok=QtGui.QPushButton(Data.translator.get(u'Accept'),self.buttons)
    self.cancel=QtGui.QPushButton(Data.translator.get(u'Decline'),self.buttons)
    self.buttonlayout=QtGui.QHBoxLayout(self.buttons)
    
    self.layout.addWidget(self.license)
    self.layout.addWidget(self.txt)
    self.layout.addWidget(self.buttons)
    
    self.buttonlayout.addWidget(self.cancel)
    self.buttonlayout.addWidget(self.ok)
  
    self.cancel.clicked.connect(self.cancelPressed)
    self.ok.clicked.connect(self.okPressed)
    self.scrollbar.valueChanged.connect(self.checkSlider)
    self.ok.setEnabled(False)
    
    f=open(fname,"r")
    txt=QtCore.QString(f.read())
    f.close()
    self.license.setDocument(QtGui.QTextDocument(txt))
    # self.license.scrollContentsBy(0,1000)


  def closeEvent(self, e):
    self.done(-1)
    
    
  """
  def hideEvent(self, e):
    # self.hide()
    self.show()
    # self.raise_()
    # print "hide!"
    # e.ignore()
  """
  

  def cancelPressed(self):
    # print "cancel eula!"
    self.done(-1)
    
    
  def okPressed(self):
    # print "eula ok'd!"
    # self.license.scroll(0,100)
    # self.scrollbar.setValue(100)
    self.done(0)
    
    
  def checkSlider(self, val):
    # print ">>",val,"/",self.scrollbar.maximum()
    if (val>=self.scrollbar.maximum()):
      self.ok.setEnabled(True)





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
    
    QtWidgets.QMessageBox.about(self.w, "About it", constant.valkka_core_not_found)
    
    
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
 
