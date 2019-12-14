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
import time
from valkka.live.qt.tools import numpy2QPixmap
from valkka.live.mouse import MouseClickContext
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
    def __init__(self, def_pixmap = None, parent = None):
        super().__init__(parent)
        self.pre = "SimpleVideoWidget : "
        self.painter = QtGui.QPainter()
        self.pixmap = def_pixmap
        self.mouse_click_ctx = MouseClickContext(self.mouseGestureHandler)
        self.initVars()

    def initVars(self):
        pass

    def paintEvent(self, e):
        # http://zetcode.com/gui/pyqt5/painting/
        self.painter.begin(self)
        self.drawWidget(self.painter)
        self.painter.end()

    def drawWidget(self, qp):
        if self.pixmap is None:
            # print("no pixmap")
            return
        qp.drawPixmap(0, 0, self.width(), self.height(), self.pixmap)

    def mousePressEvent(self, e):
        print("VideoWidget: mousePress")
        self.mouse_click_ctx.atPressEvent(e)
        super().mousePressEvent(e)
        
    def mouseMoveEvent(self, e):
        self.handle_move(e)
        return
        """
        if not (e.buttons() & QtCore.Qt.LeftButton):
            return
        
        leni = ( e.pos() - self.mouse_click_ctx.info.pos ).manhattanLength()
        
        if (leni < QtWidgets.QApplication.startDragDistance()):
            return
        """
        """
        drag = QtGui.QDrag(self)
        mimeData = QtCore.QMimeData()

        mimeData.setData("application/octet-stream", 
                            pickle.dumps(self.device)
                            # pickle.dumps(None)
                            )
        drag.setMimeData(mimeData)

        dropAction = drag.exec_(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction)
        """

    def mouseReleaseEvent(self, e):
        self.mouse_click_ctx.atReleaseEvent(e)
        super().mouseReleaseEvent(e)

    def mouseGestureHandler(self, info):
        """This is the callback for MouseClickContext.  Passed to VideoWidget as a parameter
        """
        print(self.pre, ": mouseGestureHandler: ")
        # *** single click events ***
        if (info.fsingle):
            print(self.pre, ": mouseGestureHandler: single click")
            if (info.button == QtCore.Qt.LeftButton):
                print(self.pre, ": mouseGestureHandler: Left button clicked")
                self.handle_left_single_click(info)
            elif (info.button == QtCore.Qt.RightButton):
                print(self.pre, ": mouseGestureHandler: Right button clicked")
                self.handle_right_single_click(info)
        # *** double click events ***
        elif (info.fdouble):
            if (info.button == QtCore.Qt.LeftButton):
                print(
                    self.pre,
                    ": mouseGestureHandler: Left button double-clicked")
                self.handle_left_double_click(info)
            elif (info.button == QtCore.Qt.RightButton):
                print(
                    self.pre,
                    ": mouseGestureHandler: Right button double-clicked")
                self.handle_right_double_click(info)

    def setTracking(self):
        self.setMouseTracking(True)

    def unSetTracking(self):
        self.setMouseTracking(False)

    def handle_move(self, info):
        print("handle_move")

    def handle_left_single_click(self, info):
        pass

    def handle_right_single_click(self, info):
        pass

    def handle_left_double_click(self, info):
        pass

    def handle_right_double_click(self, info):
        pass


    # *** slots ***
    def set_pixmap_slot(self, pixmap):
        self.pixmap = pixmap
        self.repaint()



class LineCrossingVideoWidget(SimpleVideoWidget):
    """Receives QPixMaps to a slot & draws them

    TODO: mouse gestures, draw lines, boxes, etc.
    """
    def __init__(self, def_pixmap = None, parent = None):
        super().__init__(def_pixmap = def_pixmap, parent = parent)

    def drawWidget(self, qp):
        super().drawWidget(qp) # draws the bitmap on the background
        # TODO: draw something more

    def initVars(self):
        self.on = False

    def handle_move(self, info):
        print("handle_move")

    def handle_left_single_click(self, info):
        self.on = not self.on
        if self.on:
            self.setTracking()
        else:
            self.unSetTracking()

    def handle_right_single_click(self, info):
        pass

    def handle_left_double_click(self, info):
        pass

    def handle_right_double_click(self, info):
        pass



class VideoShmemThread(QtCore.QThread):
    """A Thread that creates a Valkka shmem client, reads frames from it & fires them as qt signals

    Connect VideoShmemThread to SimpleVideoWidget.set_pixmap_slot
    """
    class Signals(QtCore.QObject):  
        pixmap = QtCore.Signal(object)
        exit = QtCore.Signal()

    def __init__(self, shmem_name: str, shmem_n_buffer: int, width: int, height: int, verbose = False):
        super().__init__()
        self.pre = "VideoShmemThread: "
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
            n_ringbuffer    = self.shmem_n_buffer,   
            width           = self.width,
            height          = self.height,
            # client timeouts if nothing has been received in 1000 milliseconds
            mstimeout   =1000,
            verbose     =False
        )
        while self.loop:
            """
            print("Idling")
            time.sleep(1)
            """
            #"""
            index, meta = self.client.pullFrameThread() # releases Python GIL while waiting for a frame
            if (index is None):
                # print(self.pre, "VideoShmemThread: client timed out..")
                pass
            else:
                # print(self.pre, "VideoShmemThread: client index, w, h =", index, meta.width, meta.height)
                data = self.client.shmem_list[index]
                img = data.reshape(
                    (meta.height, meta.width, 3))
                pixmap = numpy2QPixmap(img)
                self.signals.pixmap.emit(pixmap)
            # """

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
    self.lay = QtWidgets.QVBoxLayout(self.w)

    self.video = SimpleVideoWidget(parent=self.w)
    self.lay.addWidget(self.video)
    
    
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
 
