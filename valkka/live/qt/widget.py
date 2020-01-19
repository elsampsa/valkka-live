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
# import math
import numpy
from valkka.live.qt.tools import numpy2QPixmap
from valkka.live.mouse import MouseClickContext
from valkka.api2 import ShmemRGBClient


def point2vec(point):
    return numpy.array([point.x(), point.y()])

def vec2point(vec):
    return QtCore.QPoint(int(vec[0]), int(vec[1]))


def point2vecRel(point, widget):
    scale = numpy.array([widget.width(), widget.height()])
    return point2vec(point) / scale


def vec2pointAbs(vec, widget):
    scale = numpy.array([widget.width(), widget.height()])
    return vec2point(vec * scale)


def vec2Abs(vec, widget):
    scale = numpy.array([widget.width(), widget.height()])
    return vec * scale

def vec2Rel(vec, widget):
    scale = numpy.array([widget.width(), widget.height()])
    return vec / scale

def invertY(vec, shift = 0):
    return numpy.array([vec[0], shift - vec[1]])






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
    class Signals(QtCore.QObject):
        update_analyzer_parameters = QtCore.Signal(object)
    

    def __init__(self, def_pixmap = None, parent = None):
        super().__init__(parent)
        self.signals = self.Signals()
        self.pre = "SimpleVideoWidget : "
        self.painter = QtGui.QPainter()
        self.pixmap = def_pixmap
        self.mouse_click_ctx = MouseClickContext(
            self.mouseGestureHandler,
            t_double_click = 0
        )

        self.initVars()

    def initVars(self):
        pass


    def parametersToMvision(self) -> dict:
        """Internal parameters of this analyzer widget to something that\
        is understood by the associated machine vision process

        Must use json-seriazable objects
        """
        return {
            "some" : "parameters"
            }


    def mvisionToParameters(self, dic: dict):
        """Inverse of parametersToMVision
        """
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
    """An example how to implement a video widget to control parameters for a line crossing detector

    1. Left click initiates the process: now a line is being drawn
    2. Next left click finishes the line
    3. Third left click defines the line normal
    """
    def __init__(self, def_pixmap = None, parent = None):
        super().__init__(def_pixmap = def_pixmap, parent = parent)
        # self.lines = []
        self.line = None # tuple of two 2D numpy vectors
        self.unitnormal = None # a 2D numpy vector

    def drawWidget(self, qp):
        super().drawWidget(qp) # draws the bitmap on the background
        # TODO: draw something more

    def initVars(self):
        self.state = 0
        self.p0 = None
        self.p1 = None
        self.p2 = None
        self.unSetTracking()



    def parametersToMvision(self) -> dict:
        """Internal parameters of this analyzer widget to something that\
        is understood by the associated machine vision process

        WARNING: y-direction is inverted

        Must use json-seriazable objects
        """
        return {
            # "line"         : [invertY(self.line[0], shift = 1).tolist(), invertY(self.line[1], shift = 1).tolist()],
            "line"         : [self.line[0].tolist(), self.line[1].tolist()], # cv2 / numpy has the same coordinates
            "unitnormal"   : self.unitnormal.tolist(),
            # "line_"        : [self.line[0].tolist(), self.line[1].tolist()],
            # "unitnormal_"  : self.unitnormal.tolist()
            }


    def mvisionToParameters(self, dic: dict):
        """Inverse of parametersToMVision
        """
        self.line = (numpy.array(dic["line"][0]), numpy.array(dic["line"][1]))
        self.unitnormal = numpy.array(dic["unitnormal"])


    def handle_move(self, info):
        print("handle_move")


    def handle_left_single_click(self, info):
        """info is a custom object with member "pos" having the MouseEvent.pos()

        member "event" has the MouseEvent
        """
        print("handle_left_single_click, state=", self.state)
        if self.state == 0: # nothing clicked yet.  start line definition
            # self.lines = []
            self.line = None
            self.unitnormal = None
            self.setTracking()
            self.state = 1
            self.p0 = info.pos
        elif self.state == 1: # finish line definition. start normal definition
            self.state = 2
        elif self.state == 2: # finish normal definition
            self.initVars()
            self.signals.update_analyzer_parameters.emit(
                self.parametersToMvision()
                )


    def handle_right_single_click(self, info):
        # cancel definition
        self.initVars()
        """ # nopes
        self.signals.update_analyzer_parameters.emit({
            })
        """

    def handle_left_double_click(self, info):
        pass


    def handle_right_double_click(self, info):
        pass


    def handle_move(self, e):
        """handle_move receives the complete MouseEvent
        """
        if self.state == 0:
            return # this should not happen..
        elif self.state == 1: # line definition going on
            # print("line def")
            self.p1 = e.pos() # https://doc.qt.io/qt-5/qmouseevent.html#globalPos
            self.repaint()
        elif self.state == 2: # normal definition going on
            # print("normal def")
            self.p2 = e.pos()
            self.repaint()


    def drawWidget(self, qp):
        """Draw lines on top of the bitmal
        """
        qp.setPen(QtGui.QPen(QtCore.Qt.cyan, 5))

        if self.pixmap is not None:
            qp.drawPixmap(0, 0, self.width(), self.height(), self.pixmap)

        if self.state >= 1 and self.p1 is not None:
            # https://doc.qt.io/qt-5/qpainter.html#drawLine-2
            # print("drawWidget: p0 = ", self.p0)
            # print("drawWidget: p1 = ", self.p1)
            # qp.drawLine(self.p0, self.p1)
            # self.lines = [QtCore.QLineF(self.p0, self.p1)]
            """
            self.lines = [
                ( point2vecRel(self.p0, self), point2vecRel(self.p1, self) ) 
            ]
            """
            self.line = ( point2vecRel(self.p0, self), point2vecRel(self.p1, self) )
            
        if self.state >= 2 and self.p1 is not None and self.p2 is not None:
            # qp.drawLine(self.p1, self.p2) # debug

            p0 = point2vec(self.p0)
            p1 = point2vec(self.p1)
            p2 = point2vec(self.p2)
            n0 = p0 + (p1 - p0) / 2
            # n0 = self.p0 + (self.p1 - self.p0) / 2 # starting point of the normal
            """
            v = p0 -> p1
            w = p1 -> p2

            subtract from w its projection to v

            w := w - (w * v0)v0
            """
            v = p1 - p0
            le = numpy.sqrt(numpy.dot(v,v))
            if le == 0:
                v = numpy.array([0,0])
            else:
                v0 = v / le
            # print(p0, p1, n0, v, le, v0) # [165  56] [310  91] [ 237.5   73.5] [145  35] 149.164338902 [ 0.97208221  0.23464053]
            # qp.drawLine(self.p2, self.p2 + vec2point(v0*100)) # debug
            w = p2 - p1
            w = w - numpy.dot(w, v0) * v0
            # qp.drawLine(vec2point(n0), vec2point(n0 + w))
            # self.lines = [QtCore.QLineF(self.p0, self.p1), QtCore.QLineF(vec2point(n0), vec2point(n0 + w))]

            # self.line = (vec2Rel(p0, self), vec2Rel(p1, self))
            w_rel = vec2Rel(w, self)
            le = numpy.dot(w_rel,w_rel)
            if le == 0:
                self.unitnormal = numpy.array([0,0])
            else:
                self.unitnormal = w_rel / numpy.sqrt(numpy.dot(w_rel,w_rel))
            """
            self.lines = [
                ( vec2Rel(p0, self), vec2Rel(p1, self) ),
                ( vec2Rel(n0, self), vec2Rel(n0 + w, self) )
            ]
            """

        """
        for line in self.lines:
            qp.drawLine(vec2pointAbs(line[0], self), vec2pointAbs(line[1], self))
        """
        if self.line is not None:
            midpoint = self.line[0] + 0.5 * (self.line[1] - self.line[0])
            qp.drawLine(vec2pointAbs(self.line[0], self), vec2pointAbs(self.line[1], self))
            if self.unitnormal is not None:
                # print("unit normal:", self.unitnormal)
                qp.drawLine(
                    vec2pointAbs(midpoint, self),
                    vec2pointAbs(midpoint + self.unitnormal/10, self)
                )

                
            

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
    

# class AnalyzerWindow(QtWidgets.QMainWindow):
class AnalyzerWidget(QtWidgets.QWidget):
    """
    - Runs a VideoShmemThread that reads frames from shmem
    - ..frames from shmem => self.video.set_pixmap_slot
    - self.video is a custom analyzer video widget class (i.e. for defining lines, areas, etc.) that is encapsulated into this QMainWindow
    """

    class Signals(QtCore.QObject):
        show = QtCore.Signal()
        close = QtCore.Signal()

    def __init__(self, parent = None, analyzer_video_widget_class = SimpleVideoWidget):
        super().__init__(parent)

        self.w = QtWidgets.QWidget(self)
        self.main_lay = QtWidgets.QVBoxLayout(self)
        self.main_lay.addWidget(self.w)
        #self.setCentralWidget(self.w)
        
        self.lay = QtWidgets.QVBoxLayout(self.w)
        # self.video = SimpleVideoWidget(parent = self.w)
        # self.video = LineCrossingVideoWidget(parent = self.w)
        self.video = analyzer_video_widget_class(parent = self.w)
        # self.signals = self.video.signals # alias
        self.signals = self.Signals()
        self.lay.addWidget(self.video)
        self.thread_ = None # woops.. thread seems to be a member of QWidget..!


    def parametersToMvision(self) -> dict:
        return self.video.parametersToMvision()


    def mvisionToParameters(self, dic: dict):
        self.video.mvisionToParameters(dic)


    def activate(self, geom = None):
        self.setVisible(True)
        if geom:
            self.setGeometry(geom)


    def showEvent(self, e):
        print("AnalyzerWindow: showEvent")
        # request shmem server from mvision process
        self.signals.show.emit()
        e.accept()


    def closeEvent(self, e):
        # TODO: why this is not fired?
        print("AnalyzerWindow: closeEvent: thread_", self.thread_)
        if self.thread_ is not None:
            self.thread_.stop()
            self.thread_.signals.pixmap.disconnect(self.video.set_pixmap_slot)
            self.thread_ = None
        # release shmem server from mvision
        self.signals.close.emit()
        e.accept()


    # def setShmem_slot(self, shmem_name, shmem_n_buffer, width, height):
    def setShmem_slot(self, kwargs):
        """ Called after the mvision process has established a shmem server
        drag'n'drop => setDevice => MVisionProcess.activate => MVisionProcess.c__activate => should establish shmem server
        => MVisionProcess.send_out_(MessageObject) => get's converted into a Qt signal that is connected to this method
        """
        shmem_name = kwargs["shmem_name"]
        shmem_n_buffer = kwargs["shmem_n_buffer"]
        width = kwargs["width"]
        height = kwargs["height"]
        self.thread_ = VideoShmemThread(
                shmem_name,
                shmem_n_buffer,
                width,
                height
            )
        self.thread_.signals.pixmap.connect(self.video.set_pixmap_slot)
        self.thread_.start()
        print("AnalyzerWindow: setShmem_slot: thread_", self.thread_)



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

    # self.video = SimpleVideoWidget(parent=self.w)
    self.video = LineCrossingVideoWidget(parent=self.w)
    self.lay.addWidget(self.video)
    
    
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
 
