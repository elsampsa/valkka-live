"""
container.py : cute-mongo-forms containers

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    container.py
@author  Sampsa Riikonen
@date    2018
@version 0.12.2 
@brief   
"""

import sys
from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
#from cute_mongo_forms.column import LineEditColumn, IntegerColumn, ConstantIntegerColumn, IPv4AddressColumn, LabelColumn, CheckBoxColumn
from cute_mongo_forms.row import RowWatcher
from cute_mongo_forms.container import List, SimpleForm
# from valkka.live import default, tools
from valkka.live.datamodel.row import MemoryConfigRow, ValkkaFSConfigRow


# *** Simple lists ***

class DeviceList(List):

    class SortableWidgetItem(QtWidgets.QListWidgetItem):
        """A sortable listwidget item class
        """

        def __init__(self):
            super().__init__()
            # self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        def __lt__(self, other):
            try:
                return int(self.slot) < int(other.slot)
            except Exception:
                return QtWidgets.QListWidgetItem.__lt__(self, other)

    def makeWidget(self):
        super().makeWidget()
        # self.widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)


    def update(self):
        # Fills the root and subwidgets with data.
        self.widget.clear()
        self.items_by_id={}
        for entry in self.collection.get():
            item  =self.createItem()
            label =self.makeLabel(entry)
            item.setText(label)
            item._id         =entry["_id"]
            item.slot        =int(entry["slot"]) # add an extra attribute
            try:
                item.classname =entry["classname"]
            except KeyError:
                raise(KeyError("Your database contains crap.  Do a purge"))
            self.items_by_id[item._id]=item
            self.widget.addItem(item)
        self.widget.sortItems()
        self.widget.setMinimumWidth(self.widget.sizeHintForColumn(0))


    def createItem(self):
        """Overwrite in child classes to create custom items (say, sortable items, etc.)
        """
        return self.SortableWidgetItem()

    def makeLabel(self, entry):
        # print("DataModel : makeLabel :", entry["classname"])
        st = str(entry["slot"])
        if (entry["classname"] == "RTSPCameraRow"):
            st += " RTSP ("+entry["address"]+")"
        elif (entry["classname"] == "USBCameraRow"):
            st += " USB ("+str(entry["address"])+")" # could be NoneType
        elif (entry["classname"] == "SDPFileRow"):
            fname = str(entry["address"]).split("/")[-1]
            st += " FILE ("+fname+")"
        return st

    def close(self):
        pass # the ListAndForm has been closed

# *** A stand-alone form for MemoryConfigRow ***

class MemoryConfigForm(SimpleForm):

    class Signals(QtCore.QObject):
        save = QtCore.Signal()

    parameter_defs = {
        "row_class": RowWatcher,
        "collection": None
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.signals = self.Signals()
        self.load()

    def makeWidget(self):
        super().makeWidget()

        self.button_row = QtWidgets.QWidget(self.widget)
        self.button_lay = QtWidgets.QHBoxLayout(self.button_row)
        self.lay.addWidget(self.button_row)

        self.reset_button = QtWidgets.QPushButton("Reset", self.button_row)
        self.save_button = QtWidgets.QPushButton("Save", self.button_row)
        self.button_lay.addWidget(self.reset_button)
        self.button_lay.addWidget(self.save_button)

        self.info_label = QtWidgets.QLabel("Saving restarts all Valkka services", self.widget)
        self.lay.addWidget(self.info_label)
        
        self.reset_button.clicked.connect(self.row_instance.clear)
        self.save_button.clicked.connect(self.save_slot)

    def load(self):
        try:
            el = next(self.collection.get(
                {"classname": MemoryConfigRow.__name__}))
        except StopIteration:
            print(self.pre, "no row!")
        else:
            print(self.pre, "reading saved")
            self.row_instance.get(self.collection, el["_id"])

    def save_slot(self):
        try:
            el = next(self.collection.get(
                {"classname": MemoryConfigRow.__name__}))
        except StopIteration:
            print(self.pre, "new row")
            _id = self.row_instance.new(
                self.collection)  # create a new instance
        else:
            print(self.pre, "update row")
            _id = el["_id"]
            self.row_instance.update(self.collection, _id)

        self.signals.save.emit()



class ValkkaFSForm(SimpleForm):

    class Signals(QtCore.QObject):
        save = QtCore.Signal()

    parameter_defs = {
        "row_class": RowWatcher,
        "collection": None
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.signals = self.Signals()
        self.load()

    def makeWidget(self):
        super().makeWidget()

        self.button_row = QtWidgets.QWidget(self.widget)
        self.button_lay = QtWidgets.QHBoxLayout(self.button_row)
        self.lay.addWidget(self.button_row)

        self.reset_button = QtWidgets.QPushButton("Reset", self.button_row)
        self.save_button = QtWidgets.QPushButton("Save", self.button_row)
        self.button_lay.addWidget(self.reset_button)
        self.button_lay.addWidget(self.save_button)

        self.info_label = QtWidgets.QLabel("(not yet functional)", self.widget)
        self.lay.addWidget(self.info_label)
        
        self.reset_button.clicked.connect(self.row_instance.clear)
        self.save_button.clicked.connect(self.save_slot)

    def load(self):
        try:
            el = next(self.collection.get(
                {"classname": ValkkaFSConfigRow.__name__}))
        except StopIteration:
            print(self.pre, "no row!")
        else:
            print(self.pre, "reading saved")
            self.row_instance.get(self.collection, el["_id"])

    def save_slot(self):
        try:
            el = next(self.collection.get(
                {"classname": ValkkaFSConfigRow.__name__}))
        except StopIteration:
            print(self.pre, "new row")
            _id = self.row_instance.new(
                self.collection)  # create a new instance
        else:
            print(self.pre, "update row")
            _id = el["_id"]
            self.row_instance.update(self.collection, _id)

        self.signals.save.emit()







class ListAndForm:
    """Creates a composite widget using a List and a FormSet
    """

    def __init__(self, lis, form, title="", parent=None):
        self.title = title
        self.lis = lis
        self.form = form

        self.widget = QtWidgets.QWidget(parent)  # create a new widget
        self.lay = QtWidgets.QVBoxLayout(
            self.widget)  # attach layout to that widget
        self.label = QtWidgets.QLabel(self.title, self.widget)

        self.subwidget = QtWidgets.QWidget(self.widget)
        self.sublay = QtWidgets.QHBoxLayout(self.subwidget)

        self.lay.addWidget(self.label)
        self.lay.addWidget(self.subwidget)

        self.subwidget.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
        self.lis.widget.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum)
        self.lis.widget.setMaximumWidth(100)

        # get widget from List and set its parent to widget
        self.lis. widget.setParent(self.subwidget)
        self.form.widget.setParent(self.subwidget)
        # add List's internal widget to widget's layout
        self.sublay. addWidget(self.lis.widget)
        self.sublay. addWidget(self.form.widget)
        self.lis.widget.currentItemChanged. connect(
            self.form.chooseForm_slot)  # connections between list and the form
        self.form.signals.modified.connect(self.lis.update_slot)
        self.modified = self.form.signals.modified  # shorthand

    def update(self):
        """Widgets might have drop-down menus and sublists that depend on other document collections
        """
        self.form.updateWidget()

    def getForm(self):
        return self.form

    def choose_first_slot(self):
        self.lis.widget.setCurrentItem(self.lis.widget.item(0))
        
    def close_slot(self):
        """Inform list and form that they have been closed
        """
        self.lis.close()
        self.form.close()




def main():
    app=QtWidgets.QApplication(["test_app"])
    mg=MyGui()
    mg.show()
    app.exec_()


if (__name__=="__main__"):
    main()
 
