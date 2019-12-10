"""
widget.py : Custom Qt Widgets

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    widget.py
@author  Sampsa Riikonen
@date    2018
@version 0.11.0 
@brief   Custom Qt Widgets
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
from valkka.live.qt.tools import numpy2QPixmap
from valkka.api2 import ShmemRGBClient


class FormWidget(QtWidgets.QWidget):
    """Just a QWidget that sends a signal when its shown
    """

    class Signals(QtCore.QObject):
        show = QtCore.Signal()

    def __init__(self, parent = None):
        super().__init__(parent)
        self.signals = self.Signals()

    def showEvent(self, e):
        self.signals.show.emit()
        e.accept()


class SimpleVideoWidget(QtWidgets.QWidget):
    """Receives QPixMaps to a slot & draws them

    TODO: mouse gestures, draw lines, boxes, etc.
    """
    def __init__(self, def_pixmap, parent = None):
        super().__init__(parent)
        self.painter = QPainter()
        self.pixmap = def_pixmap

    def paintEvent(self, e):
        # http://zetcode.com/gui/pyqt5/painting/
        self.painter.begin(self)
        self.drawWidget(self.painter)
        self.painter.end()

    def drawWidget(self, qp):
        qp.drawPixmap(0, 0, self.width(), self.height(), self.pixmap)

    # *** slots ***
    def set_pixmap_slot(self, pixmap):
        self.pixmap = pixmap
        self.repaint()
    

class QValkkaShmemThread(QtCore.QThread):
    """A Thread that creates a Valkka shmem client, reads frames from it & fires them as qt signals

    Connect QValkkaShmemThread to SimpleVideoWidget.set_pixmap_slot
    """
    class Signals(QtCore.QObject):  
        pixmap = QtCore.Signal(object)
        exit = QtCore.Signal()

    def __init__(self, shmem_name: str, shmem_n_buffer: int, width: int, height: int, verbose = False):
        super().__init__()
        self.pre = "QValkkaShmemThread: "
        self.shmem_name = shmem_name
        self.shmem_n_buffer = shmem_n_buffer
        self.width = width
        self.height = height
        self.verbose = verbose

        self.loop = True
        self.signals = self.Signals()
        self.signals.exit.connect(self.exit_slot_)
        
    def run(self):
        self.client = ShmemRGBClient(
            name            = self.shmem_name,
            n_ringbuffer    = self.n_buffer,   
            width           = self.width,
            height          = self.height,
            # client timeouts if nothing has been received in 1000 milliseconds
            mstimeout   =1000,
            verbose     =False
        )
        while self.loop:
            index, isize = self.client.pull()
            if (index is None):
                print(self.pre, "Client timed out..")
            else:
                print(self.pre, "Client index, size =", index, isize)
                data = self.client.shmem_list[index]
                img = data.reshape(
                    (self.image_dimensions[1], self.image_dimensions[0], 3))
                pixmap = numpy2QPixmap(img)
                self.signals.pixmap.emit(pixmap)

        print(self.pre, "exit")
    
    def exit_slot_(self):
        self.loop = False
        
    def stop(self):
        self.requestStop()
        self.waitStop()
        
    def requestStop(self):
        self.signals.exit.emit()
    
    def waitStop(self):
        self.wait()
    


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
    """TODO:

    - A simple filterchain for testing SimpleVideoWidget
    """
    
  
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
 
