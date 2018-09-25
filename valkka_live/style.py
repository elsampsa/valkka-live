"""
style.py : Qt stylesheets for Valkka Live

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    style.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   Qt stylesheets for Valkka Live
"""

from PySide2 import QtWidgets, QtCore, QtGui # Qt5

main_gui="""
"""

root_container="""
"""


video_widget="""
border: 1px solid gray; 
border-radius: 10px; 
margin: 0px; 
padding: 0px; 
background: white;
"""

default="""
QPushButton {
color: white;
background-color: rgba(0, 54, 178, 255);
}

QPushButton::pressed{
color: white;
background-color: rgba(0, 54, 178, 255);
}


QTabWidget::pane {
border-top: 2px solid #C2C7CB;
background: white;
 }

QTabWidget::tab-bar {
 }

QTabBar::tab {
background: lightgray;
color: black;
padding: 20px;
}

QTabBar::tab:selected {
background: rgba(0, 54, 178, 255);
color: white;
font-style: normal;
}

.QFrame{
border: 2px solid #36B2FE;
}
"""
