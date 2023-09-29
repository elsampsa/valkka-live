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
@version 1.2.1 
@brief   Datatypes that can be saved and visualized using cute_mongo_forms
"""

from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot  # Qt5
import sys
import os
# from valkka.core import *
from valkka.api2.tools import parameterInitCheck
from cute_mongo_forms.db import SimpleCollection

from valkka.live import default
from valkka.live.form import SlotFormSet
from valkka.live import constant, tools, singleton

from valkka.live.datamodel.row import RTSPCameraRow, EmptyRow, USBCameraRow, SDPFileRow, MemoryConfigRow, ValkkaFSConfigRow
# from valkka.live.datamodel.layout_row import VideoContainerNxMRow, PlayVideoContainerNxMRow, CameraListWindowRow, MainWindowRow
from valkka.live.datamodel.layout_row import LayoutContainerRow
from valkka.live.datamodel.column import USBCameraColumn
from valkka.live.datamodel.container import DeviceList, MemoryConfigForm, ValkkaFSForm, ListAndForm

from valkka.live.device import RTSPCameraDevice, USBCameraDevice, SDPFileDevice

        
class DataModel:

    def __init__(self, directory="."):
        """DataModel ctor
        """
        self.directory = directory
        self.define()

    def __del__(self):
        # self.close()
        pass

    def close(self):
        # print("close: ",self.area_rights_collection)
        for collection in self.collections:
            collection.close()

    def clearAll(self):
        # print("DataModel", "clearAll")
        self.clearCameraCollection()
        self.config_collection.clear()
        self.valkkafs_collection.clear()
        self.layout_collection.clear()

    def saveAll(self):
        for collection in self.collections:
            collection.save()
        
    def clearCameraCollection(self):
        self.camera_collection.clear()
        for i in range(1, constant.max_devices + 1):
            self.camera_collection.new(EmptyRow, {"slot": i})

    def checkCameraCollection(self):
        c=0
        for c, device in enumerate(self.camera_collection.get()):
            pass
        if (c != constant.max_devices - 1):
            return False
        return True

    def autoGenerateCameraCollection(self, base_address, nstart, n, port, tail, username, password):
        """
        :param:  base_address    str, e.g. "192.168.1"
        :param:  nstart          int, e.g. 24
        :param:  n               int, how many ips generated 
        """
        self.camera_collection.clear()
        self.camera_collection.save()
        cc = nstart
        for i in range(1, min((n + 1, constant.max_devices + 1))):
            print(i)
            # TODO: this sucks:
            # the only place where the data structure is defined
            # should be row.py:RTSPCameraRow
            # ..it should also have some default values defined therein
            # => no need to readjust the columns all over the place
            self.camera_collection.new(
                RTSPCameraRow, 
                {
                    "slot":         i, 
                    "address":      base_address+"."+str(cc),
                    "username":     username,
                    "password":     password,
                    "port":         port,
                    "tail":         tail,
                    "force_tcp":    False,
                    "record":       False,
                    
                    "subaddress_main" : "",
                    "live_main"       : True,
                    "rec_main"        : False,
                    
                    "subaddress_sub"  : "",
                    "live_sub"        : False,
                    "rec_sub"         : False
                })
            cc +=1
        
        print("Camera addesses now:")
        for c, device in enumerate(self.camera_collection.get()):
            print(c+1, RTSPCameraRow.getMainAddressFromDict(device))
        
        for i in range(n+1, constant.max_devices + 1):
            self.camera_collection.new(EmptyRow, {"slot": i})

        self.camera_collection.save()
        
        print("Camera collection now:")
        for c, device in enumerate(self.camera_collection.get()):
            print(c+1, device)
        

            
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
                    EmptyRow,
                    RTSPCameraRow,
                    USBCameraRow,
                    SDPFileRow
                ]
            )
        self.collections.append(self.camera_collection)

        self.config_collection = \
            SimpleCollection(filename=os.path.join(self.directory, "config.dat"),
                row_classes=[  # we could dump here all kinds of info related to different kind of configuration forms
                    MemoryConfigRow
                ]
            )
        self.collections.append(self.config_collection)

        self.valkkafs_collection = \
            SimpleCollection(filename=os.path.join(self.directory, "valkkafs.dat"),
                row_classes=[
                    ValkkaFSConfigRow
                ]
            )
        self.collections.append(self.valkkafs_collection)

        """
        self.layout_collection = \
            SimpleCollection(filename=os.path.join(self.directory, "layout.dat"),
                row_classes=[
                    VideoContainerNxMRow,
                    PlayVideoContainerNxMRow,
                    CameraListWindowRow,
                    MainWindowRow
                ]
            )
        """
        self.layout_collection = \
            SimpleCollection(filename=os.path.join(self.directory, "layout.dat"),
                row_classes=[
                    LayoutContainerRow
                ]
            )

        self.collections.append(self.layout_collection)


    def getDeviceList(self):
        return DeviceList(collection=self.camera_collection)

    def getDeviceListAndForm(self, parent):
        device_list = DeviceList(collection=self.camera_collection)
        device_form = SlotFormSet(collection=self.camera_collection)
        return ListAndForm(device_list, device_form,
                           title="Camera configuration", parent=parent)

    def getConfigForm(self):
        return MemoryConfigForm(
            row_class=MemoryConfigRow, collection=self.config_collection)


    def getValkkaFSForm(self):
        return ValkkaFSForm(
            row_class=ValkkaFSConfigRow, collection = self.valkkafs_collection)


    def getRowsById(self, query):
        rows = self.camera_collection.get(query)
        rows_by_id = {}
        for row in rows:
            rows_by_id[row["_id"]] = row
        
        return rows_by_id
    
    
    def getDevicesById(self): # , query):
        """
        rows = self.camera_collection.get(query)
        devices_by_id = {}
        for row in rows:
            row.pop("classname")
            device = RTSPCameraDevice(**row)
            devices_by_id[device._id] = device
        return devices_by_id
        """
        rows = self.camera_collection.get()
        devices_by_id = {}
        for row in rows:
            classname=row.pop("classname")
            if (classname == "RTSPCameraRow"):
                device = RTSPCameraDevice(**row)
            elif (classname == "USBCameraRow"):
                device = USBCameraDevice(**row)
            elif (classname == "SDPFileRow"):
                device = SDPFileDevice(**row)
            else:
                device = None
            if (device):
                devices_by_id[device._id] = device
        return devices_by_id
        

    def writeDefaultValkkaFSConfig(self):
        # TODO: when ValkkaFSConfigRow is changed
        # there should be no need to change the column names everywhere
        # => ValkkaFSConfigRow should define some default..
        # (it should be the only place for "ground truth")
        self.valkkafs_collection.new(
            ValkkaFSConfigRow,
            {
                # "dirname"    : default.valkkafs_config["dirname"], # not written to db for the moment
                "n_blocks"   : default.get_valkkafs_config()["n_blocks"],
                "blocksize"  : default.get_valkkafs_config()["blocksize"],
                #"fs_flavor"  : default.get_valkkafs_config()["fs_flavor"],
                #"record"     : default.get_valkkafs_config()["record"],
                #"partition_uuid" : default.get_valkkafs_config()["partition_uuid"]
            })


    def writeDefaultMemoryConfig(self):
        self.config_collection.new(MemoryConfigRow, default.get_memory_config())


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
    col.new(RTSPCameraRow,
            {"slot"    : 1,
             "address" : "192.168.1.41",
             "username": "admin",
             "password": "1234",
             "port"    : "",
             "tail"    : "",
             "subaddress_main" : "",
             "live_main" : True,
             "rec_main"  : False,
             "subaddress_sub"  : "",
             "live_sub" : False,
             "rec_sub"  : False
                 })
            
    """
    "_id"       : int,
    "slot"      : int,
    "address"   : str,
    "username"  : str,
    "password"  : str,
    "port"      : (str, ""),
    "tail"      : (str, ""),
    "subaddress_main" : (str, ""),
    "live_main" : bool,
    "rec_main"  : bool,
    "subaddress_sub"  : (str, ""),
    "live_sub" : bool,
    "rec_sub"  : bool
    """
       
    for element in col.get():
        print(element)


def test2():
    dm = DataModel()
    for entry in dm.camera_collection.get():
        print(entry)
    
    devices_by_id = dm.getDevicesById({"classname" : RTSPCameraRow.__name__})
    print(devices_by_id)
    
    
def test3():
    dm = DataModel(directory = singleton.config_dir())
    dm.autoGenerateCameraCollection("192.168.1", 24, 100, "", "kokkelis/", "admin", "12345")
    dm.saveAll()
    dm.close()
    

if (__name__ == "__main__"):
    test1()
    # test3()
    
    
    
