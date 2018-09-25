"""
cameralist.py : QTree abstraction for a drag'n'drop camera list

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    cameralist.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   QTree abstraction for a drag'n'drop camera list
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
import pickle
from valkka_live.listitem import HeaderListItem, ServerListItem, RTSPCameraListItem
from valkka.api2.tools import parameterInitCheck


class TreeModel(QtCore.QAbstractItemModel):
    """ see also: http://stackoverflow.com/questions/1985936/creating-qt-models-for-tree-views
    """

    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.root = root

    # ************ Re-implemented virtual functions **************

    def data(self, index, role):
        """ Returns the data stored under the given role for the item referred to by the index.
        index == QModelIndex
        """
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole:
            return None

        item = index.internalPointer()
        return item.data(index.column())

    def index(self, row, column, parent):
        """ Returns the index of the item in the model specified by the given row, column and parent index.
        row, column == int, parent == QModelIndex
        """

        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parentItem = self.root
        else:
            # So, here we go from QModelIndex to the actual object .. ?
            parentItem = parent.internalPointer()

        # the only place where a child item is queried
        childItem = parentItem.getChild(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        """ Returns the parent of the model item with the given index. If the item has no parent, an invalid QModelIndex is returned.
        """
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        # the only place where the parent item is queried
        parentItem = childItem.getParent()

        if parentItem == self.root:
            return QtCore.QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def columnCount(self, parent):
        """ Returns the number of columns for the children of the given parent.
        """
        # print("columnCount:",self)
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.root.columnCount()

    def rowCount(self, parent):
        """ Returns the number of rows under the given parent. When the parent is valid it means that rowCount is returning the number of children of parent.
        """

        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.root
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def headerData(self, section, orientation, role):
        """ Returns the data for the given role and section in the header with the specified orientation.
        """

        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.root.data(section)

        return None

    def flags(self, index):
        """ Returns the item flags for the given index.
        """

        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        item = index.internalPointer()

        # return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable |
        # QtCore.Qt.ItemIsDragEnabled
        return item.getFlags()
    
    def removeRows(self, row: int, count: int, parent: QtCore.QModelIndex):
        if (not parent.isValid()):
            parentItem = self.root
        else:
            parentItem = parent.internalPointer()

        if (row < 0 or row >= parentItem.childCount()):
            return False

        self.beginRemoveRows(parent, row, row + count - 1)
        for i in range(0, count):
            if (not parentItem.removeChild(row)):
                break
        self.endRemoveRows()
    

    
    
    """
    def removeSubRows(self, parent: QtCore.QModelIndex):
        if not parent.isValid():
            parentItem = self.root
        else:
            parentItem = parent.internalPointer()

        parentItem.removeChildren()
        return True
    """
    
    # ***************************************************'

    # **** drag'n'drop ****

    def mimeTypes(self):
        # print("data model: mime types")
        # return ["application/vnd.text.list"]
        return ["application/octet-stream"]

    def mimeData(self, par):
        # print("data model: mime data",par) # [QModelIndex, QModelIndex]
        mimeData = QtCore.QMimeData()
        index = par[0]
        item = index.internalPointer()
        # print("data model: mime data: item=",item,item.getSlot())
        # mimeData.setText("kokkelis")
        # mimeData.setText(pickle.dumps(item.getMimeData()))
        # mimeData.setData("application/octet-stream",pickle.dumps(item.getMimeData()))
        mimeData.setData(
            "application/octet-stream",
            pickle.dumps(
                item.getMimeData()))
        return mimeData


class GuiView(QtWidgets.QWidget):
    """ Views that accept GuiDevices
    """

    def __init__(self, parent):
        super().__init__(parent)


class BasicView(QtWidgets.QTreeView):
    """ Tree view
    """

    def __init__(self, parent=None, root=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.root = root
        self.setMinimumWidth(600)
        self.initTree()

    def initTree(self):
        self.model = TreeModel(self.root)
        self.setModel(self.model)
    
    
    def reset_(self):
        # self.root.removeChildren()
        # self.model.removeSubRows(self.rootIndex())
        self.model.removeRows(0, self.root.childCount(), self.rootIndex())
        

    """
    index = self.rootIndex()
    n_row = self.model.rowCount(index)
    print("BasicTreeView: index, rowcount =", index, n_row)
    self.model.beginRemoveRows(index, 0, n_row-1)
    self.model.endRemoveRows()
    """


class MyGui(QtWidgets.QMainWindow):

    class VideoWidget(QtWidgets.QFrame):
        """The video appears here.  Must handle drag'n'drop of camera info.  Or choosing camera from a pop-up menu.
        """

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setAutoFillBackground(True)
            self.setStyleSheet("background-color: black")
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding)
            self.setAcceptDrops(True)

        def dragEnterEvent(self, e):
            print("VideoWidget: dragEnterEvent")
            e.accept()

        def dropEvent(self, e):
            print("VideoWidget: dropEvent")
            # print("VideoWidget: drop event to i,j=",self.row_index,self.column_index)
            formlist = e.mimeData().formats()
            if ("application/octet-stream" in formlist):
                # bytes # example:
                # pickle.loads(QtCore.QByteArray(pickle.dumps("hello")).data())
                bs = e.mimeData().data("application/octet-stream").data()
                device = pickle.loads(bs)
                print("drop got :", device)
                e.accept()
            else:
                e.ignore()

    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.initVars()
        self.setupUi()
        self.openValkka()

    def initVars(self):
        pass

    def setupUi(self):
        self.setGeometry(QtCore.QRect(100, 100, 500, 500))
        self.w = self.VideoWidget(self)
        self.setCentralWidget(self.w)

        self.root = HeaderListItem()

        self.server1 = ServerListItem(
            name="First Server",
            ip="192.168.1.20",
            parent=self.root)
        self.server2 = ServerListItem(
            name="First Server",
            ip="192.168.1.21",
            parent=self.root)
        self.server3 = ServerListItem(
            name="First Server",
            ip="192.168.1.22",
            parent=self.root)
        self.server4 = ServerListItem(
            name="First Server",
            ip="192.168.1.23",
            parent=self.root)

        self.camera1 = RTSPCameraListItem(
            camera=RTSPCameraDevice(
                ip="192.168.1.4",
                username="admin",
                password="1234"),
            parent=self.server1)
        self.camera2 = RTSPCameraListItem(
            camera=RTSPCameraDevice(
                ip="192.168.1.4",
                username="admin",
                password="1234"),
            parent=self.server1)
        self.camera3 = RTSPCameraListItem(
            camera=RTSPCameraDevice(
                ip="192.168.1.4",
                username="admin",
                password="1234"),
            parent=self.server2)
        self.camera4 = RTSPCameraListItem(
            camera=RTSPCameraDevice(
                ip="192.168.1.4",
                username="admin",
                password="1234"),
            parent=self.server2)
        self.camera5 = RTSPCameraListItem(
            camera=RTSPCameraDevice(
                ip="192.168.1.4",
                username="admin",
                password="1234"),
            parent=self.server3)
        self.camera6 = RTSPCameraListItem(
            camera=RTSPCameraDevice(
                ip="192.168.1.4",
                username="admin",
                password="1234"),
            parent=self.server4)

        self.treelist = BasicView(parent=None, root=self.root)
        self.treelist.show()

    def openValkka(self):
        pass

    def closeValkka(self):
        pass

    def closeEvent(self, e):
        print("closeEvent!")
        self.closeValkka()
        e.accept()


def main():
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()
