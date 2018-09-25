"""
menu.py : Menu definitions

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    menu.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   Menu definitions
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
from valkka_live.quickmenu import QuickMenu, QuickMenuElement

"""
File  View    Configuration   Plugins   About
"""


class FileMenu(QuickMenu):
    title = "File"
    elements = [
        QuickMenuElement(title="Save Window Layout"),
        QuickMenuElement(title="Load Window Layout"),
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


class ConfigMenu(QuickMenu):
    title = "Configuration"
    elements = [
        QuickMenuElement(title="Manage Cameras"),
        QuickMenuElement(title="Memory Usage")
    ]

    
class PluginsMenu(QuickMenu):
    title = "Plugins"
    elements = [
        QuickMenuElement(title="Machine Vision")
    ]


class AboutMenu(QuickMenu):
    title = "About"
    elements = [
        QuickMenuElement(title="About Valkka Live")
    ]


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

        self.filemenu = FileMenu(parent=self)
        self.viewmenu = ViewMenu(parent=self)
        self.configmenu = ConfigMenu(parent=self)
        self.aboutmenu = AboutMenu(parent=self)

        self.filemenu.exit.triggered.connect(self.exit_slot)

        self.viewmenu.video_grid.grid_1x1.triggered.connect(self.grid1x1_slot)

    def openValkka(self):
        pass

    def closeValkka(self):
        pass

    def closeEvent(self, e):
        print("closeEvent!")
        self.closeValkka()
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
