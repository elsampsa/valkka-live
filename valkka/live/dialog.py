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
@version 0.10.0 
@brief   Dialog, help and warning windows
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
from valkka.live import constant


# TODO: text dialog

"""
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
    self.field_layout=QtGui.QVBoxLayout(self)
    
    self.buttons=QtGui.QWidget(self)
    self.ok=QtGui.QPushButton(Data.translator.get(u'Accept'),self.buttons)
    self.cancel=QtGui.QPushButton(Data.translator.get(u'Decline'),self.buttons)
    self.buttonlayout=QtGui.QHBoxLayout(self.buttons)
    
    self.field_layout.addWidget(self.license)
    self.field_layout.addWidget(self.txt)
    self.field_layout.addWidget(self.buttons)
    
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
"""

class CopyToDialog(QtWidgets.QDialog):
    """
    Copy camera parameters
    
    ip range          192.168.1.41 - 192.168.1.[45]
    slot range        [5] - 9
    
    Overwrite Slots   Cancel
    """
  
  
    def __init__(self, ip, slot=1, max_slot=32, parent=None):
        """
        ip corresponds to slot
        
        max ip = ip + (max_slot - slot)
        
        """
        super().__init__(parent)
        self.setWindowTitle("Configuration Copy")
        
        self.max_dn = max_slot - slot
        
        assert(isinstance(slot, int))
        ip_nums=[]
        for part in ip.split("."):
            ip_nums.append(int(part))
            
        self.start_ip_text = ip
    
        self.min_num = ip_nums.pop(-1) # take the last number
        self.max_num = self.min_num + self.max_dn
        self.min_slot = slot
    
        self.stop_ip_text =""
        for part in ip_nums:
            self.stop_ip_text += str(part)+"."
    
        self.lay = QtWidgets.QVBoxLayout(self)
    
        self.field = QtWidgets.QWidget(self)
        self.buttons = QtWidgets.QWidget(self)
        
        self.lay.addWidget(self.field)
        self.lay.addWidget(self.buttons)
    
        self.field_lay = QtWidgets.QGridLayout(self.field)
        self.buttons_lay = QtWidgets.QHBoxLayout(self.buttons)
        
        self.ip_label = QtWidgets.QLabel("IP range", self.field)
        self.slot_label = QtWidgets.QLabel("Slot range", self.field)
        self.field_lay.addWidget(self.ip_label, 0, 0)
        self.field_lay.addWidget(self.slot_label, 1, 0)
        
        self.ip_field = QtWidgets.QWidget(self.field)
        self.slot_field = QtWidgets.QWidget(self.field)
        self.field_lay.addWidget(self.ip_field, 0, 1)
        self.field_lay.addWidget(self.slot_field, 1, 1)
        
        self.write_button = QtWidgets.QPushButton("Overwrite slots", self.buttons)
        self.cancel_button = QtWidgets.QPushButton("Cancel", self.buttons)
        # self.buttons_lay.addWidget(self.write_button, 2, 0)
        # self.buttons_lay.addWidget(self.cancel_button, 3, 0)
        self.buttons_lay.addWidget(self.write_button)
        self.buttons_lay.addWidget(self.cancel_button)

        self.ip_field_lay = QtWidgets.QHBoxLayout(self.ip_field)
        self.slot_field_lay = QtWidgets.QHBoxLayout(self.slot_field)

        self.ip_field_label = QtWidgets.QLabel(
            self.start_ip_text + 
            " - " + 
            self.stop_ip_text)
        
        
        self.ip_field_input = QtWidgets.QSpinBox(self.ip_field)
        self.ip_field_lay.addWidget(self.ip_field_label)
        self.ip_field_lay.addWidget(self.ip_field_input)
        self.ip_field_input.setMinimum(self.min_num)
        self.ip_field_input.setMaximum(self.max_num)
        
        self.slot_field_label = QtWidgets.QLabel(self.slot_field) 
        self.slot_field_lay.addWidget(self.slot_field_label)
        
        self.ip_field_input.valueChanged.connect(self.update_ip_slot)
        self.write_button.clicked.connect(lambda: self.done(1))
        self.cancel_button.clicked.connect(lambda: self.done(0))

        self.update_ip_slot(self.min_num)
        
        
    def update_ip_slot(self, i):
        slot = self.min_slot + (i - self.min_num)
        self.slot_field_label.setText(
            str(self.min_slot) + " - " + str(slot)
            )

    def exec_(self):
        i=super().exec_()
        if (i==0):
            return []
        else:
            lis=[]
            for num in range(self.min_num, self.ip_field_input.value()+1):
                dn = (num - self.min_num)
                lis.append((self.stop_ip_text+str(num), self.min_slot+dn))
            return lis
            
            
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
  # mg=MyGui()
  # mg.show()
  mg=CopyToDialog("192.168.1.24", slot=4, max_slot=10)
  lis=mg.exec_()
  for l in lis:
      print(l)
  # app.exec_()



if (__name__=="__main__"):
  main()
 
