"""
quickmenu.py : Menu creation helpers

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    NAME.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   Menu creation helpers
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys


class QuickMenuElement(object):
    """Generic menu element object.  Can add lots of things here, say, tooltips, translations, etc.
    """

    def __init__(self, title="none", method_name=None):
        self.title = title
        self.method_name = method_name

    def getTitle(self):
        return self.title


class QuickMenuSection(object):

    def __init__(self, title="none"):
        self.title = title

    def getTitle(self):
        return self.title


class QuickMenu(object):
    title = "none"

    elements = []  # a list of QuickMenuElement(s)

    def __init__(self, parent=None):
        """
        :param parent:  Where this menu will be placed
        """
        if (issubclass(parent.__class__, QtWidgets.QMainWindow)
            ):  # i.e. the current menu will be placed in the main menu bar
            self.menu = parent.menuBar().addMenu(self.title)
        elif (parent is None):  # this is a popup menu
            self.menu = QtWidgets.QMenu()
        else:  # a submenu
            # print("QuickMenu: submenu")
            assert(issubclass(parent.__class__, QtWidgets.QMenu))
            self.menu = parent.addMenu(self.title)

        for element in self.elements:
            # print("QuickMenu :",element)
            if (isinstance(element, QuickMenuElement)):
                # create menu entry / action, and find the callback / slot if defined
                # If name in EasyMenuElement was "Open File", create a
                # method_name that is "open_file"
                if (element.method_name is None):
                    method_name = element.getTitle().lower().replace(
                        " ", "_").strip()  # title is converted into an attribute name
                else:
                    method_name = element.method_name
                # self.open_file =QMenu.addAction("Open File")
                setattr(
                    self,
                    method_name,
                    self.menu.addAction(
                        element.getTitle()))
                # print("QuickMenu: method_name", method_name)
                # now we have "self.method_name" .. lets refer to it as
                # "method"
                method = getattr(self, method_name)
                """ # connect automatically to instances methods .. not really useful
        # callback functions name: self.open_file_called
        cbname = method_name + "_called"
        if (hasattr(self, cbname)):
          # if self.open_file_called exists, make connection: self.open_file.triggered.connect(self.open_file_called)
          method.triggered.connect(getattr(self, cbname))
        """
            elif (isinstance(element, QuickMenuSection)):
                self.menu.addSection(element.title)
            # recursion: this is a subclass of MyMenu.  We instantiate it here
            elif (issubclass(element, QuickMenu)):
                # this constructor called for another subclass of QuickMenu
                submenu = element(parent=self.menu)
                submenu_title = element.title.lower().replace(
                    " ", "_").strip()  # title is converted into an attribute name
                # now we can access menus hierarchically:
                # menu.submenu.subsubmenu.etc
                setattr(self, submenu_title, submenu)
            else:  # must be an EasyMenuElement instance
                raise(
                    AssertionError("Use QuickMenu subclasses or QuickMenuElement instances"))

    def connect(self, name, cb):
        method = getattr(self, name)
        method.triggered.connect(cb)

    def popup(self, qp):
        self.menu.popup(qp)


class MyGui(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.initVars()
        self.setupUi()
        self.openValkka()

    def initVars(self):
        pass

    def setupUi(self):
        self.setGeometry(QtCore.QRect(100, 100, 500, 500))

        self.w = QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)

        # here's the demo ..
        class FileMenu(QuickMenu):
            title = "File"
            elements = [
                QuickMenuElement(title="Exit")
            ]

        class GridMenu(QuickMenu):
            title = "Video Grid"
            elements = [
                QuickMenuElement(title="Grid 1x1"),
                QuickMenuElement(title="Grid 2x2"),
                QuickMenuElement(title="Grid 3x3"),
                QuickMenuElement(title="Grid 4x4")
            ]

        class ViewMenu(QuickMenu):
            title = "View"
            elements = [
                QuickMenuElement(title="Camera List"),
                GridMenu
            ]

        self.filemenu = FileMenu(parent=self)
        self.viewmenu = ViewMenu(parent=self)

        # the attributes were autogenerated:
        self.filemenu.exit.triggered.connect(self.exit_slot)
        self.viewmenu.video_grid.grid_1x1.triggered.connect(self.grid1x1_slot)

    def openValkka(self):
        pass

    def closeValkka(self):
        pass

    def closeEvent(self, e):
        print("closeEvent!")
        e.accept()

    def exit_slot(self):
        print("exit slot")

    def grid1x1_slot(self):
        print("grid1x1 slot")


def main():
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()
