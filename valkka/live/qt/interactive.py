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
@version 0.14.0 
@brief   Custom Qt Widgets
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys
import time
from pprint import pprint
# import math
import numpy
from valkka.live.qt.tools import numpy2QPixmap
from valkka.live.qt.widget import SimpleVideoWidget, CanvasWidget
from valkka.live.mouse import MouseClickContext


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



class LineCrossingCanvasWidget(CanvasWidget):

    def __init__(self, signals, def_pixmap=None, parent=None, strict = True):
        super().__init__(signals, def_pixmap=def_pixmap, parent=parent)
        # self.lines = []
        self.strict = strict
        self.line = None  # tuple of two 2D numpy vectors
        self.unitnormal = None  # a 2D numpy vector

    def drawWidget(self, qp):
        super().drawWidget(qp)  # draws the bitmap on the background

    def initVars(self):
        self.state = 0
        self.p0 = None
        self.p1 = None
        self.p2 = None
        self.unSetTracking()

    def parametersToMvision(self) -> dict:
        """Internal parameters of this analyzer widget to something that\
        is understood by the associated machine vision process

        Must use json-seriazable objects
        """
        return {
            # "line"         : [invertY(self.line[0], shift = 1).tolist(), invertY(self.line[1], shift = 1).tolist()],
            # cv2 / numpy has the same coordinates
            "line": [self.line[0].tolist(), self.line[1].tolist()],
            "unitnormal": self.unitnormal.tolist(),
            # "line_"        : [self.line[0].tolist(), self.line[1].tolist()],
            # "unitnormal_"  : self.unitnormal.tolist()
        }

    def mvisionToParameters(self, dic: dict):
        """Inverse of parametersToMVision
        """
        self.line = (numpy.array(dic["line"][0]),
                        numpy.array(dic["line"][1]))
        self.unitnormal = numpy.array(dic["unitnormal"])

    def handle_move(self, info):
        print("handle_move")

    def handle_left_single_click(self, info):
        """info is a custom object with member "pos" having the MouseEvent.pos()

        member "event" has the MouseEvent
        """
        # print("handle_left_single_click, state=", self.state)
        if self.state == 0:  # nothing clicked yet.  start line definition
            # self.lines = []
            self.line = None
            self.unitnormal = None
            self.setTracking()
            self.state = 1
            self.p0 = info.pos
        elif self.state == 1:  # finish line definition. start normal definition
            self.state = 2
        elif self.state == 2:  # finish normal definition
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
            return  # this should not happen..
        elif self.state == 1:  # line definition going on
            # print("line def")
            self.p1 = e.pos()  # https://doc.qt.io/qt-5/qmouseevent.html#globalPos
            self.repaint()
        elif self.state == 2:  # normal definition going on
            # print("normal def")
            self.p2 = e.pos()
            self.repaint()

    def drawWidget(self, qp):
        """Draw lines on top of the bitmal
        """
        qp.setPen(QtGui.QPen(QtCore.Qt.cyan, 5))
        # qp.setPen(QtGui.QPen(QtCore.Qt.cyan, 1))

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
            self.line = (point2vecRel(self.p0, self),
                            point2vecRel(self.p1, self))

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
            le = numpy.sqrt(numpy.dot(v, v))
            if le == 0:
                v = numpy.array([0, 0])
            else:
                v0 = v / le
            # print(p0, p1, n0, v, le, v0) # [165  56] [310  91] [ 237.5   73.5] [145  35] 149.164338902 [ 0.97208221  0.23464053]
            # qp.drawLine(self.p2, self.p2 + vec2point(v0*100)) # debug
            w = p2 - p1
            if self.strict:
                w = w - numpy.dot(w, v0) * v0
            # qp.drawLine(vec2point(n0), vec2point(n0 + w))
            # self.lines = [QtCore.QLineF(self.p0, self.p1), QtCore.QLineF(vec2point(n0), vec2point(n0 + w))]

            # self.line = (vec2Rel(p0, self), vec2Rel(p1, self))
            w_rel = vec2Rel(w, self)
            le = numpy.dot(w_rel, w_rel)
            if le == 0:
                self.unitnormal = numpy.array([0, 0])
            else:
                self.unitnormal = w_rel / \
                    numpy.sqrt(numpy.dot(w_rel, w_rel))
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
            qp.drawLine(vec2pointAbs(
                self.line[0], self), vec2pointAbs(self.line[1], self))
            if self.unitnormal is not None:
                # print("unit normal:", self.unitnormal)
                qp.drawLine(
                    vec2pointAbs(midpoint, self),
                    vec2pointAbs(midpoint + self.unitnormal/10, self)
                )



class LineCrossingVideoWidget(SimpleVideoWidget):
    """An example how to implement a video widget to control parameters for a line crossing detector

    1. Left click initiates the process: now a line is being drawn
    2. Next left click finishes the line
    3. Third left click defines the line normal
    """
    def __init__(self, def_pixmap=None, parent=None, strict = True):
        QtWidgets.QWidget.__init__(self, parent)
        self.signals = self.Signals()
        self.pre = "LineCrossingVideoWidget : "
        self.lay = QtWidgets.QVBoxLayout(self)
        self.canvas = LineCrossingCanvasWidget(self.signals, def_pixmap, parent=self, strict = strict)
        self.lay.addWidget(self.canvas)



class NLineCrossingCanvasWidget(CanvasWidget):

    def __init__(self, signals, def_pixmap=None, parent=None, N = 2):
        # self.strict = strict
        self.N = N
        self.index = -1
        self.lines_normals = self.N * [(None, None)]
        self.line_widths = self.N * [1]
        # current line & normal under definition:
        self.line = None  # tuple of two 2D numpy vectors # current line being manipulated
        self.unitnormal = None  # a 2D numpy vector # current normal being manipulated
        super().__init__(signals, def_pixmap=def_pixmap, parent=parent)

    def define_line_slot(self, n = -1):
        self.index = n
        if n < 0: return
        self.lines_normals[n] = (None, None)
        print("index, lines_normals", self.index, self.lines_normals[self.index])
        self.state = 0

    def set_line_width_slot(self, n, width):
        if n < 0: return
        self.line_widths[n] = width
        if self.state == 0: # send new line widths immediately
            self.signals.update_analyzer_parameters.emit(
                    self.parametersToMvision()
                )
        else:
            # line definition is going on; when its finished, it'll send the parameters
            pass

    def drawWidget(self, qp):
        super().drawWidget(qp)  # draws the bitmap on the background

    def initVars(self):
        print("initvars!", self.index)
        self.state = 0
        self.index = -1
        self.p0 = None
        self.p1 = None
        self.p2 = None
        self.line = None
        self.unSetTracking()

    def cancel(self):
        print("cancel!", self.index)
        if self.index > -1:
            self.lines_normals[self.index] = (None, None)
        self.initVars()

    def parametersToMvision(self) -> dict:
        """Internal parameters of this analyzer widget to something that\
        is understood by the associated machine vision process

        Must use json-seriazable objects
        """
        lines = []
        unitnormals = []
        
        for line, normal in self.lines_normals:
            print("parametersToMvision: line", line)
            if line is None:
                lines.append(None)
                unitnormals.append(None)
            else:
                print("parametersToMvision", line)
                lines.append([line[0].tolist(), line[1].tolist()])
                unitnormals.append(normal.tolist())   
        res = {
            "lines"         : lines,
            "unitnormals"   : unitnormals,
            "linewidths"    : self.line_widths
        }
        #print("parametersToMvision")
        #pprint(res)
        return res

    def mvisionToParameters(self, dic: dict):
        """Inverse of parametersToMVision
        """
        for cc, line in enumerate(dic["lines"]):
            if line is None:
                self.lines_normals[cc] = (None, None)
                self.line_widths[cc] = 1
            else:
                unitnormal = dic["unitnormals"][cc]
                line_ = (numpy.array(line[0]), numpy.array(line[1]))
                unitnormal_ = numpy.array(unitnormal)
                self.lines_normals[cc] = (line_, unitnormal_)
                self.line_widths[cc] = dic["linewidths"][cc]

    def handle_move(self, info):
        print("handle_move")

    def handle_left_single_click(self, info):
        """info is a custom object with member "pos" having the MouseEvent.pos()

        member "event" has the MouseEvent
        """
        # print("handle_left_single_click, state=", self.state)

        if self.index < 0:
            return

        if self.state == 0:  # nothing clicked yet.  start line definition
            self.line = None
            self.unitnormal = None
            self.setTracking()
            self.state = 1
            self.p0 = info.pos
        elif self.state == 1:  # finish line definition. start normal definition
            self.state = 2
        elif self.state == 2:  # finish normal definition
            self.lines_normals[self.index] = (
                self.line,
                self.unitnormal
            )
            self.initVars()
            self.signals.update_analyzer_parameters.emit(
                self.parametersToMvision()
            )

    def handle_right_single_click(self, info):
        # cancel definition
        print("cancel", self.index)
        if self.index < 0:
            return
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
        if self.index < 0:
            return
        if self.state == 0:
            return  # this should not happen..
        elif self.state == 1:  # line definition going on
            # print("line def")
            self.p1 = e.pos()  # https://doc.qt.io/qt-5/qmouseevent.html#globalPos
            self.repaint()
        elif self.state == 2:  # normal definition going on
            # print("normal def")
            self.p2 = e.pos()
            self.repaint()

    def drawWidget(self, qp):
        """Draw lines on top of the bitmal
        """
        qp.setPen(QtGui.QPen(QtCore.Qt.cyan, 5))
        # qp.setPen(QtGui.QPen(QtCore.Qt.cyan, 1))

        if self.pixmap is not None:
            qp.drawPixmap(0, 0, self.width(), self.height(), self.pixmap)

        if self.index >= 0:
            # print(">p0, p1", self.p0, self.p1)

            if self.state >= 1 and self.p1 is not None:
                self.line = (point2vecRel(self.p0, self),
                                point2vecRel(self.p1, self))

            if self.state >= 2 and self.p1 is not None and self.p2 is not None:
                p0 = point2vec(self.p0)
                p1 = point2vec(self.p1)
                p2 = point2vec(self.p2)
                n0 = p0 + (p1 - p0) / 2

                v = p1 - p0
                le = numpy.sqrt(numpy.dot(v, v))
                if le == 0:
                    v = numpy.array([0, 0])
                else:
                    v0 = v / le
                w = p2 - p1
                #if self.strict:
                #    w = w - numpy.dot(w, v0) * v0
                w_rel = vec2Rel(w, self)
                le = numpy.dot(w_rel, w_rel)
                if le == 0:
                    self.unitnormal = numpy.array([0, 0])
                else:
                    self.unitnormal = w_rel / numpy.sqrt(le)
                # print(">>", numpy.linalg.norm(self.unitnormal))

        if self.line is not None:
            midpoint = self.line[0] + 0.5 * (self.line[1] - self.line[0])
            qp.drawLine(vec2pointAbs(self.line[0], self), vec2pointAbs(self.line[1], self))
            if self.unitnormal is not None:
                # print("unit normal:", self.unitnormal)
                qp.drawLine(
                    vec2pointAbs(midpoint, self),
                    vec2pointAbs(midpoint + self.unitnormal/10, self)
                )

        for line, unitnormal in self.lines_normals:
            if line is not None:
                midpoint = line[0] + 0.5 * (line[1] - line[0])
                qp.drawLine(vec2pointAbs(line[0], self), vec2pointAbs(line[1], self))
                #if unitnormal is not None:
                qp.drawLine(
                    vec2pointAbs(midpoint, self),
                    vec2pointAbs(midpoint + unitnormal/10, self)
                )



class NLineCrossingVideoWidget(SimpleVideoWidget):
    """An example how to implement a video widget to control parameters for a line crossing detector with various lines

    ::

        [
           - canvas
           - buttons
             --button1--button2
        ]


    """
    def __init__(self, def_pixmap=None, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.signals = self.Signals()
        self.pre = "NLineCrossingVideoWidget : "
        self.lay = QtWidgets.QVBoxLayout(self)
        self.canvas = NLineCrossingCanvasWidget(self.signals, def_pixmap, parent=self)
        self.lay.addWidget(self.canvas)
        # WARNING: the numerical constants are reversed between min/max...!
        self.canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
            )
        self.buttons = QtWidgets.QWidget(self)
        self.lay.addWidget(self.buttons)
        self.button1 = QtWidgets.QPushButton("Set Line 1", self.buttons)
        self.linedef1 = QtWidgets.QSpinBox(self.buttons)
        self.button2 = QtWidgets.QPushButton("Set Line 2", self.buttons)
        self.linedef2 = QtWidgets.QSpinBox(self.buttons)

        self.linedef1.setRange(4,60)
        self.linedef2.setRange(4,60)

        for b in [self.buttons, self.button1, self.linedef1, self.button2, self.linedef2]:
            b.setSizePolicy(
                QtWidgets.QSizePolicy.Maximum,
                QtWidgets.QSizePolicy.Maximum
                )

        self.button_lay = QtWidgets.QHBoxLayout(self.buttons)
        self.button_lay.addWidget(self.button1)
        self.button_lay.addWidget(self.linedef1)
        self.button_lay.addWidget(self.button2)
        self.button_lay.addWidget(self.linedef2)

        self.button1.clicked.connect(lambda: self.canvas.define_line_slot(0))
        self.button2.clicked.connect(lambda: self.canvas.define_line_slot(1))
        self.linedef1.valueChanged.connect(lambda i: self.canvas.set_line_width_slot(0, i))
        self.linedef2.valueChanged.connect(lambda i: self.canvas.set_line_width_slot(1, i))



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
    # self.video = LineCrossingVideoWidget(parent=self.w, strict = False)
    self.video = NLineCrossingVideoWidget(parent=self.w)
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
 
