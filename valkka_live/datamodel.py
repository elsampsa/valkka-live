"""
datamodel.py : Datatypes that can be saved and visualized using cute_mongo_forms

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    datamodel.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   Datatypes that can be saved and visualized using cute_mongo_forms
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
import os
# from valkka.valkka_core import *
from valkka.api2.tools import parameterInitCheck

from cute_mongo_forms.db import SimpleCollection
from cute_mongo_forms.column import LineEditColumn, IntegerColumn, ConstantIntegerColumn, IPv4AddressColumn, LabelColumn
from cute_mongo_forms.row import ColumnSpec, Row, RowWatcher
from cute_mongo_forms.container import List, SimpleForm

from valkka_live import default
from valkka_live.form import SlotFormSet
from valkka_live import constant


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

class DataModel:

    # Device collection: RTSP Cameras, SDP files, etc.

    class EmptyRow(Row):
        name = "<Empty>"
        columns = [
            ColumnSpec(
                ConstantIntegerColumn,
                key_name="slot",
                label_name="Slot"),
        ]

    class RTSPCameraRow(Row):
        name = "RTSP Camera"
        columns = [
            ColumnSpec(
                ConstantIntegerColumn,
                key_name="slot",
                label_name="Slot"),
            ColumnSpec(
                IPv4AddressColumn,
                key_name="address",
                label_name="IP Address"),
            ColumnSpec(
                LineEditColumn,
                key_name="username",
                label_name="Username"),
            ColumnSpec(
                LineEditColumn,
                key_name="password",
                label_name="Password"),
            ColumnSpec(LineEditColumn, key_name="tail", label_name="Tail")
        ]

        @classmethod
        def getAddressFromDict(cls, dic):
            st = "rtsp://"       \
                + dic["username"] + ":" \
                + dic["password"] + "@" \
                + dic["address"] + "/"       \
                + dic["tail"]
            st = st.strip()
            return st

        def makeWidget(self):
            """Add a summary RTSP address in the end of the form
            """
            super().makeWidget()

            i = self.lay.rowCount()
            self.label = QtWidgets.QLabel("RTSP address ", self.widget)
            self.rtsp_address_label = QtWidgets.QLabel("", self.widget)
            
            self.lay.addWidget(self.label, i, 0)
            self.lay.addWidget(self.rtsp_address_label, i, 1)

        def getAddress(self):
            # e.g. : rtsp://admin:12345@192.168.1.4/tail
            dic = self.__collect__()  # returns a dictionary of column values
            return DataModel.RTSPCameraRow.getAddressFromDict(dic)

        def update_notify_slot(self):
            """This slot gets pinged always when the form fields have been updated
            """
            self.rtsp_address_label.setText(self.getAddress())

    class RTSPCameraDevice:
        """Device class used in drag'n'drop.  Copies the members of RTSPCameraRow
        """

        parameter_defs = {
            "_id"       : int,
            "slot"      : int,
            "address"   : str,
            "username"  : str,
            "password"  : str,
            "tail"      : (str, "")
        }

        def __init__(self, **kwargs):
            # auxiliary string for debugging output
            self.pre = self.__class__.__name__ + " : "
            # check for input parameters, attach them to this instance as
            # attributes
            parameterInitCheck(self.parameter_defs, kwargs, self)

        def __eq__(self, other):
            return self._id == other._id
                        
        def getAddress(self):
            return "rtsp://" + self.username + ":" + \
                self.password + "@" + self.address + "/" + self.tail

        def getLabel(self):
            return "rtsp://" + self.address + "/" + self.tail

    # A general collection for misc. stuff: configuration, etc.

    class MemoryConfigRow(Row):

        columns = [
            ColumnSpec(
                IntegerColumn,
                key_name="msbuftime",
                label_name="Buffering time (ms)",
                min_value=50,
                max_value=1000,
                def_value=default.memory_config["msbuftime"]),
            ColumnSpec(
                IntegerColumn,
                key_name="n_720p",
                label_name="Number of 720p cameras",
                min_value=0,
                max_value=1024,
                def_value=default.memory_config["n_720p"]),
            ColumnSpec(
                IntegerColumn,
                key_name="n_1080p",
                label_name="Number of 1080p cameras",
                min_value=0,
                max_value=1024,
                def_value=default.memory_config["n_1080p"]),
            ColumnSpec(
                IntegerColumn,
                key_name="n_1440p",
                label_name="Number of 1440p cameras",
                min_value=0,
                max_value=1024,
                def_value=default.memory_config["n_1440p"]),
            ColumnSpec(
                IntegerColumn,
                key_name="n_4K",
                label_name="Number of 4K cameras",
                min_value=0,
                max_value=1024,
                def_value=default.memory_config["n_4K"])
        ]

        def getNFrames(self, key):
            """Get number of necessary frames for certain camera resolution

            :param key:   n720p, n1080p, etc.
            """

            buftime = self["buftime"]
            ncam = self[key]

            # assume 25 fps cameras
            return int((buftime / 1000) * 25 * ncam)

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
                    return int(self.text()) < int(other.text())
                except Exception:
                    return QListWidgetItem.__lt__(self, other)

        def makeWidget(self):
            super().makeWidget()
            # self.widget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        def createItem(self):
            """Overwrite in child classes to create custom items (say, sortable items, etc.)
            """
            return self.SortableWidgetItem()

        def makeLabel(self, entry):
            # print("DataModel : makeLabel :", entry["classname"])
            st = str(entry["slot"])
            return st

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
                    {"classname": DataModel.MemoryConfigRow.__name__}))
            except StopIteration:
                print(self.pre, "no row!")
            else:
                print(self.pre, "reading saved")
                self.row_instance.get(self.collection, el["_id"])

        def save_slot(self):
            try:
                el = next(self.collection.get(
                    {"classname": DataModel.MemoryConfigRow.__name__}))
            except StopIteration:
                print(self.pre, "new row")
                _id = self.row_instance.new(
                    self.collection)  # create a new instance
            else:
                print(self.pre, "update row")
                _id = el["_id"]
                self.row_instance.update(self.collection, _id)

            self.signals.save.emit()
            
            

    def __init__(self, directory="."):
        self.directory = directory
        self.define()

    def __del__(self):
        self.close()

    def close(self):
        # print("close: ",self.area_rights_collection)
        for collection in self.collections:
            collection.close()

    def clearAll(self):
        # print("DataModel", "clearAll")
        self.clearCameraCollection()
        self.config_collection.clear()

    def saveAll(self):
        self.camera_collection.save()
        self.config_collection.save()

    def clearCameraCollection(self):
        self.camera_collection.clear()
        for i in range(1, constant.max_devices + 1):
            self.camera_collection.new(self.EmptyRow, {"slot": i})

    def checkCameraCollection(self):
        for c, device in enumerate(self.camera_collection.get()):
            pass
        if (c != constant.max_devices - 1):
            return False
        return True

    def purge(self):
        """For migrations / cleanup.  Collections should be in correct order.
        """
        for collection in self.collections:
            # print("purging",collection)
            collection.purge()

    def define(self):
        """Define column patterns and collections
        """
        self.collections = []

        self.camera_collection = \
            SimpleCollection(filename=os.path.join(self.directory, "devices.dat"),
                             row_classes=[
                DataModel.EmptyRow,
                DataModel.RTSPCameraRow
            ]
            )
        self.collections.append(self.camera_collection)

        self.config_collection = \
            SimpleCollection(filename=os.path.join(self.directory, "config.dat"),
                             row_classes=[  # we could dump here all kinds of info related to different kind of configuration forms
                DataModel.MemoryConfigRow
            ]
            )
        self.collections.append(self.config_collection)

    def getDeviceList(self):
        return DataModel.DeviceList(collection=self.camera_collection)

    def getDeviceListAndForm(self, parent):
        device_list = DataModel.DeviceList(collection=self.camera_collection)
        device_form = SlotFormSet(collection=self.camera_collection)
        return ListAndForm(device_list, device_form,
                           title="Camera configuration", parent=parent)

    def getConfigForm(self):
        return DataModel.MemoryConfigForm(
            row_class=DataModel.MemoryConfigRow, collection=self.config_collection)


    def getRowsById(self, query):
        rows = self.camera_collection.get(query)
        rows_by_id = {}
        for row in rows:
            rows_by_id[row["_id"]] = row
        
        return rows_by_id
    
    
    def getDevicesById(self, query):
        rows = self.camera_collection.get(query)
        devices_by_id = {}
        for row in rows:
            row.pop("classname")
            device = DataModel.RTSPCameraDevice(**row)
            devices_by_id[device._id] = device
        
        return devices_by_id
    
        


class MyGui(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.initVars()
        self.setupUi()
        self.openValkka()

    def initVars(self):
        self.dm = DataModel()
        self.dm.clearAll()  # run this when using db for the first time
        # self.dm.saveAll() # use this when leaving the menu
        # self.dm.close() # use this at exit

    def setupUi(self):
        self.setGeometry(QtCore.QRect(100, 100, 500, 500))

        self.w = QtWidgets.QWidget(self)
        self.lay = QtWidgets.QVBoxLayout(self.w)

        self.setCentralWidget(self.w)

        # self.device_list_form = self.dm.getDeviceListAndForm(self.w)
        # self.lay.addWidget(self.device_list_form.widget)

        self.device_list_form = self.dm.getDeviceListAndForm(None)
        self.device_list_form.widget.show()

        # self.config_form = self.dm.getConfigForm()
        # self.config_form.widget.setParent(self.w)

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


def test1():
    dm = DataModel()
    col = dm.camera_collection
    col.new(dm.RTSPCameraRow,
            {"slot": 1,
             "address": "192.168.1.41",
             "username": "admin",
             "password": "1234",
             "tail": ""})
    for element in col.get():
        print(element)


def test2():
    dm = DataModel()
    for entry in dm.camera_collection.get():
        print(entry)
    
    devices_by_id = dm.getDevicesById({"classname" : DataModel.RTSPCameraRow.__name__})
    print(devices_by_id)
    


if (__name__ == "__main__"):
    # main()
    # test1()
    test2()
