"""
toos.py : Some tools for QWidgets

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    tools.py
@author  Sampsa Riikonen
@date    2018
@version 0.9.0 
@brief   
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5
from valkka.live import style, constant, singleton
import sys



def getCorrectedGeom(window):
    """Returns x, y, width, height that can be used with setGeometry (that uses coordinates without frames)
    """
    # with window frames:
    q = window.frameGeometry() 
    p = window.pos()
    return (
        p.x() + singleton.dx, # window frame + margin .. will be used to set the window size without margin
        p.y() + singleton.dy,
        q.width() - singleton.dw,
        q.height() - singleton.dh
        )
    """# works only after window has been shown I guess... what a f mess
    dy = self.window.frameGeometry().height() - self.window.geometry().height()
    print("dy", dy)
    """
    # self.window.move(x + singleton.dx, y + singleton.dy)
    # self.window.setFramePosition(x, y) # this one neither?
    # https://doc.qt.io/qt-5/stylesheet-customizing.html#box-model
    # geometry() : "Returns the geometry of the window, excluding its window frame"
    # https://doc.qt.io/qt-5/application-windows.html#window-geometry
    #
    # fm = self.window.frameMargins() # not in the python API !?
    """
    # https://forum.qt.io/topic/99528/window-titlebar-height-example/3
    qapp = QtCore.QCoreApplication.instance()
    bh = qapp.style().pixelMetric(QtWidgets.QStyle.PM_TitleBarHeight)
    """




def QCapsulate(widget, name, blocking = False, nude = False):
    """Helper function that encapsulates QWidget into a QMainWindow
    """

    class QuickWindow(QtWidgets.QMainWindow):

        class Signals(QtCore.QObject):
            close = QtCore.Signal()
            show  = QtCore.Signal()

        def __init__(self, blocking = False, parent = None, nude = False):
            super().__init__(parent)
            self.propagate = True # send signals or not
            self.setStyleSheet(style.main_gui)
            if (blocking):
                self.setWindowModality(QtCore.Qt.ApplicationModal)
            if (nude):
                # http://doc.qt.io/qt-5/qt.html#WindowType-enum
                # TODO: create a widget for a proper splashscreen (omitting X11 and centering manually)
                # self.setWindowFlags(QtCore.Qt.Popup) # Qt 5.9+ : setFlags()
                # self.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.WindowStaysOnTopHint)
                self.setWindowFlags(QtCore.Qt.Dialog)
            self.signals = self.Signals()
            

        def closeEvent(self, e):
            if (self.propagate):
                self.signals.close.emit()
            e.accept()
            
        def showEvent(self, e):
            if (self.propagate):
                self.signals.show.emit()
            e.accept()
            
        def setPropagate(self):
            self.propagate = True
            
        def unSetPropagate(self):
            self.propagate = False
            

    win = QuickWindow(blocking = blocking, nude = nude)
    win.setCentralWidget(widget)
    win.setLayout(QtWidgets.QHBoxLayout())
    win.setWindowTitle(name)
    return win


def QTabCapsulate(name, widget_list, blocking = False):
    """Helper function that encapsulates QWidget into a QMainWindow
    
    :param widget_list:     List of tuples : [(widget,"name"), (widget,"name"), ..]
    
    """

    class QuickWindow(QtWidgets.QMainWindow):

        class Signals(QtCore.QObject):
            close = QtCore.Signal()
            show  = QtCore.Signal()

        def __init__(self, blocking = False, parent = None):
            super().__init__(parent)
            self.propagate = True # send signals or not
            self.setStyleSheet(style.main_gui)
            if (blocking):
                self.setWindowModality(QtCore.Qt.ApplicationModal)
            self.signals = self.Signals()
            self.tab = QtWidgets.QTabWidget()
            self.setCentralWidget(self.tab)
            self.setLayout(QtWidgets.QHBoxLayout())

        def closeEvent(self, e):
            if (self.propagate):
                self.signals.close.emit()
            e.accept()
            
        def showEvent(self, e):
            if (self.propagate):
                self.signals.show.emit()
            e.accept()
            
        def setPropagate(self):
            self.propagate = True
            
        def unSetPropagate(self):
            self.propagate = False
            

    win = QuickWindow(blocking = blocking)
    win.setWindowTitle(name)
    for w in widget_list:
        win.tab.addTab(w[0], w[1])
    
    return win

 
def numpy2QPixmap(img):
    """Stupid, time-leaking conversion from numpy array => QImage => QPixmap
    
    .. but there seems to be no other way
    
    A memleak & a fix: https://bugreports.qt.io/browse/PYSIDE-140?focusedCommentId=403528&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-403528
    """
    ch = ctypes.c_char.from_buffer(img, 0)
    rcount = ctypes.c_long.from_address(id(ch)).value
    qimage = QImage(ch, img.shape[1], img.shape[0], QImage.Format_RGB888)
    ctypes.c_long.from_address(id(ch)).value = rcount
    return QPixmap.fromImage(qimage)
