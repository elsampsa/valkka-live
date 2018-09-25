"""
listitem.py : List item classes for the cameralist

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    listitem.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   List item classes for the cameralist
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
from valkka.api2.tools import parameterInitCheck
from valkka_live.datamodel import DataModel


"""
ListItem : a generic object that has some methods and members
Most importantly, "parent" .. that's returned by getParent and getMimeData, that returns the drag'n'drop data
The parent/child structure present in ListItem(s) is used by TreeModel(QtCore.QAbstractItemModel)

TreeModel digs up the ListItem(s) using the internalPointer method
"""


class ListItem(object):
    """A drag'n'droppable item in the Qt tree list
    """

    parameter_defs = {
        "parent": None
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(self.parameter_defs, kwargs, self)
        self.init()

    def init(self):
        if (self.parent is not None):  # must be another ListItem instance
            assert(issubclass(self.parent.__class__, ListItem))
            # so, we now about our parent
            self.parent.addChild(self)
            # .. now parent knows about us
        self.children = []
        self.makeFlags()
        self.makeItemData()  # what is shown in the table/tree view

    def makeItemData(self):
        """A list that is used by the tree view to create a label
        """
        raise(AssertionError("virtual method"))
        # self.itemData =

    def getMimeData(self):
        """The data structure that passed in drag'n'drop
        """
        raise(AssertionError("virtual method"))

    def getItemData(self):
        return self.itemData

    def makeFlags(self):
        self.flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled

    def addChild(self, child):
        self.children.append(child)
        
    """
    def removeChildren(self):
        for child in self.children:
            child.removeChildren()
        self.parent = None # detach
        self.children = []
        # self.itemData = None
    """
       

    # ****** An Item must re-implement these methods for nested tables ******

    def getFlags(self):
        return self.flags

    def getChild(self, row):   # return my children with index "Device classes for the cameralistrow"
        return self.children[row]

    def childCount(self):   # how many children I have
        return len(self.children)

    def removeChild(self, row):
        try:
            self.children.pop(row)
        except IndexError:
            return False
        else:
            return True
            
    def columnCount(self):  # how many data columns we have
        return len(self.itemData)

    def data(self, col):    # the actual data/text in the columns
        if (col >= len(self.itemData)):
            return None
        else:
            return self.itemData[col]

    def getParent(self):       # my parent
        return self.parent

    def row(self):          # my row index according to my parent
        if self.parent is not None:
            return self.parent.children.index(self)
        return 0
    # ***********************************************************************


class HeaderListItem(ListItem):
    """A root item that's in the tree lists header
    """

    def makeItemData(self):
        self.itemData = ["Device", "IP Address"]

    def getMimeData(self):
        return None


class ServerListItem(ListItem):
    """An example dummy server class for the tree list
    """

    parameter_defs = {
        "parent": None,
        "name": (str, "localhost"),
        "ip": (str, "0.0.0.0")
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(self.parameter_defs, kwargs, self)
        self.init()

    def makeItemData(self):
        self.itemData = [self.name, self.ip]

    def getMimeData(self):
        return None


class RTSPCameraListItem(ListItem):
    """An example camera class for the tree list
    """

    parameter_defs = {
        "parent": None,
        "camera": DataModel.RTSPCameraDevice
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(self.parameter_defs, kwargs, self)
        self.init()

    def makeItemData(self):
        self.itemData = [self.camera.getLabel()]

    def getMimeData(self):
        return self.camera
