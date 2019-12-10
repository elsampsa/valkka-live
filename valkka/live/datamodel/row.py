"""
row.py : cute-mongo-form row definitions

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    row.py
@author  Sampsa Riikonen
@date    2018
@version 0.11.0 
@brief
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
from cute_mongo_forms.column import LineEditColumn, IntegerColumn, SpinBoxIntegerColumn, ConstantIntegerColumn, IPv4AddressColumn, LabelColumn, CheckBoxColumn, ConstantComboBoxColumn, ConstantRadioButtonColumn
from cute_mongo_forms.row import ColumnSpec, Row, RowWatcher
from valkka.live import default, tools, style
from valkka.live.datamodel.column import USBCameraColumn
from valkka.live.qt.widget import FormWidget
from valkka.api2.valkkafs import findBlockDevices


class EmptyRow(Row):
    name = "<Empty>"
    columns = [
        ColumnSpec(
            ConstantIntegerColumn,
            key_name="slot",
            label_name="Slot"),
        ]

    def isActive(self):
        """Is this row class visible in the form drop-down menu
        """
        return True


class USBCameraRow(Row):
    name = "H264 USB Camera"
    columns = [
        ColumnSpec(ConstantIntegerColumn, key_name="slot", label_name="Slot"),
        ColumnSpec(USBCameraColumn, key_name ="address", label_name="Device")
        ]
    
    def isActive(self):
        """Show only if there are USB cams
        """
        return len(tools.getH264V4l2())>0
    
      
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
        ColumnSpec(
            LineEditColumn,
            key_name="port",
            label_name="Port"),
        ColumnSpec(
            LineEditColumn, 
            key_name="tail", 
            label_name="Tail"),
        
        ColumnSpec(
            LineEditColumn, 
            key_name="subaddress_main", 
            label_name="Subaddress",
            visible=False),
        ColumnSpec(
            CheckBoxColumn, 
            key_name="live_main", 
            label_name="Use stream",
            def_value=True),
        ColumnSpec(
            CheckBoxColumn, 
            key_name="rec_main", 
            label_name="Record stream",
            def_value=False),
        
        ColumnSpec(
            LineEditColumn, 
            key_name="subaddress_sub", 
            label_name="Subaddress"),
        ColumnSpec(
            CheckBoxColumn, 
            key_name="live_sub", 
            label_name="Use stream",
            def_value=False),
        ColumnSpec(
            CheckBoxColumn, 
            key_name="rec_sub", 
            label_name="Record stream",
            def_value=False)
        ]
    
    def isActive(self):
        return True

    @classmethod
    def getMainAddressFromDict(cls, dic):
        st = "rtsp://"
        st += dic["username"] + ":"
        st += dic["password"] + "@"
        st += dic["address"]
        if (dic["port"].strip() != ""):
            st += ":" + dic["port"].strip()
        if (len(dic["tail"]) > 0):
            st += "/" + dic["tail"]
        if (len(dic["subaddress_main"]) > 0):
            st += "/" + dic["subaddress_main"]
        return st

    @classmethod
    def getSubAddressFromDict(cls, dic):
        st = "rtsp://"
        st += dic["username"] + ":"
        st += dic["password"] + "@"
        st += dic["address"]
        if (dic["port"].strip() != ""):
            st += ":" + dic["port"].strip()
        if (len(dic["tail"]) > 0):
            st += "/" + dic["tail"]
        if (len(dic["subaddress_main"]) > 0):
            st += "/" + dic["subaddress_sub"]
        return st


    def makeWidget(self):
        """Subclassed from Row : custom form.  Add a summary RTSP address in the end of the form, etc.
        """
        # super().makeWidget() # do all by hand
        self.widget = FormWidget()
        self.lay = QtWidgets.QGridLayout(self.widget)
        
        cc=0;
        self.placeWidget(cc, "slot"); cc+=1
        self.placeWidget(cc, "address"); cc+=1
        self.placeWidget(cc, "username"); cc+=1
        self.placeWidget(cc, "password"); cc+=1
        self.placeWidget(cc, "port"); cc+=1
        self.placeWidget(cc, "tail"); cc+=1
        # self.setVisible("tail", False) # test
        
        # Mainstream
        self.label_mainstream = QtWidgets.QLabel("Mainstream", self.widget)
        self.label_mainstream.setStyleSheet(style.form_highlight)
        self.placeWidgetPair(cc, (self.label_mainstream, None)); cc+=1
        self.placeWidget(cc, "subaddress_main"); cc+=1
        # complete RTSP address
        self.label_mainstream_address = QtWidgets.QLabel("RTSP address", self.widget)
        self.mainstream_address = QtWidgets.QLabel("", self.widget)
        self.placeWidgetPair(cc, (self.label_mainstream_address, self.mainstream_address)); cc+=1
        # live and rec
        self.placeWidget(cc, "live_main"); cc+=1
        self.placeWidget(cc, "rec_main"); cc+=1
        
        # Substream
        self.label_substream = QtWidgets.QLabel("Substream", self.widget)
        self.label_substream.setStyleSheet(style.form_highlight)
        self.placeWidgetPair(cc, (self.label_substream, None)); cc+=1
        self.label_substream.setVisible(False) # hide for the moment
        self.placeWidget(cc, "subaddress_sub"); cc+=1
        # complete RTSP address
        self.label_substream_address = QtWidgets.QLabel("RTSP address", self.widget)
        self.substream_address = QtWidgets.QLabel("", self.widget)
        self.placeWidgetPair(cc, (self.label_substream_address, self.substream_address)); cc+=1
        self.label_substream_address.setVisible(False); self.substream_address.setVisible(False); 
        # .. hide for the moment

        # live and rec
        self.placeWidget(cc, "live_sub"); cc+=1
        self.placeWidget(cc, "rec_sub"); cc+=1
        
        """ # definitely NOT here!
        # self.copy_label = QtWidgets.QLabel("Copy this camera", self.widget)
        self.copy_button = QtWidgets.QPushButton("Copy", self.widget)
        self.placeWidgetPair(cc, (self.copy_button, None))
        self.copy_button.clicked.connect(self.copy_slot)
        """
        self.connectNotifications()
    
        def rec_main_clicked():
            if not self["live_main"].widget.isChecked(): # rec requires live
                print("live_main is NOT checked")
                self["rec_main"].widget.setChecked(False)
            if self["rec_main"].widget.isChecked(): # rec main excludes rec sub
                self["rec_sub"].widget.setChecked(False)
        
        def rec_sub_clicked():
            if not self["live_sub"].widget.isChecked(): # rec requires live
                print("live_sub is NOT checked")
                self["rec_sub"].widget.setChecked(False)
            if self["rec_sub"].widget.isChecked(): # rec sub excludes rec main
                self["rec_main"].widget.setChecked(False)
                
        self["rec_main"].widget.clicked.connect(rec_main_clicked)
        self["rec_sub"]. widget.clicked.connect(rec_sub_clicked)
        self.widget.signals.show.connect(self.show_slot)
        
        # TODO: remove these restrictions once functional:
        """
        self["subaddress_main"].widget.setEnabled(False)
        self["subaddress_sub"].widget.setEnabled(False)
        self["live_main"].widget.setEnabled(False)
        self["rec_main"].widget.setEnabled(False)
        self["live_sub"].widget.setEnabled(False)
        self["rec_sub"].widget.setEnabled(False)
        """
        self.setVisible("subaddress_main", False)
        self.setVisible("subaddress_sub", False)
        self.setVisible("live_main", False)
        self.setVisible("rec_main", False)
        self.setVisible("live_sub", False)
        self.setVisible("rec_sub", False)
        
                
    """
    def get(self, collection, _id):
        #Subclassed from Row : Load one entry from db to QtWidgets
        super().get(collection, _id)
        self.update_notify_slot()
    """
        
        
    def getMainAddress(self):
        # e.g. : rtsp://admin:12345@192.168.1.4/tail
        dic = self.__collect__()  # returns a dictionary of column values
        return RTSPCameraRow.getMainAddressFromDict(dic)

    def getSubAddress(self):
        # e.g. : rtsp://admin:12345@192.168.1.4/tail
        dic = self.__collect__()  # returns a dictionary of column values
        return RTSPCameraRow.getSubAddressFromDict(dic)

    def update_notify_slot(self):
        """This slot gets pinged always when the form fields have been updated
        """
        # pass
        # print("RTSPCameraRow: value changed")
        self.mainstream_address.setText(self.getMainAddress())
        self.substream_address.setText(self.getSubAddress())
        # self.copy_button.setEnabled(False) # must save before can copy # nopes ..
        
        # rec main and sub exclude each other
        # rec requires live
        
    def show_slot(self):
        self.mainstream_address.setText(self.getMainAddress())
        self.substream_address.setText(self.getSubAddress())
            
            

class MemoryConfigRow(Row):
    # A general collection for misc. stuff: configuration, etc.
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
            label_name="Number of 720p streams",
            min_value=0,
            max_value=1024,
            def_value=default.memory_config["n_720p"]),
        ColumnSpec(
            IntegerColumn,
            key_name="n_1080p",
            label_name="Number of 1080p streams",
            min_value=0,
            max_value=1024,
            def_value=default.memory_config["n_1080p"]),
        ColumnSpec(
            IntegerColumn,
            key_name="n_1440p",
            label_name="Number of 2K streams",
            min_value=0,
            max_value=1024,
            def_value=default.memory_config["n_1440p"]),
        ColumnSpec(
            IntegerColumn,
            key_name="n_4K",
            label_name="Number of 4K streams",
            min_value=0,
            max_value=1024,
            def_value=default.memory_config["n_4K"]),
        ColumnSpec(
            CheckBoxColumn,
            key_name="bind",
            label_name="Bind decoding thread to single core",
            def_value=default.memory_config["bind"]),
        ColumnSpec(
            CheckBoxColumn,
            key_name="overwrite_timestamps",
            label_name="Overwrite timestamps",
            def_value=default.memory_config["overwrite_timestamps"])
    ]


    def getNFrames(self, key):
        """Get number of necessary frames for certain camera resolution

        :param key:   n720p, n1080p, etc.
        """

        buftime = self["buftime"]
        ncam = self[key]

        # assume 25 fps cameras
        return int((buftime / 1000) * 25 * ncam)


class ValkkaFSConfigRow(Row):

    def getValkkaFSDevices():
        lis = [] # tuples of (name, key)
        for key, value in findBlockDevices().items():
            # they look like this: {'27f5e5d8-9e20-4bc1-84aa-6a3cbab498c8': ('/dev/sdc1', 500107862016)}
            lis.append((
                value[0]+" ("+str(int(value[1]/1024/1024))+" MB)", # shown in dropdown
                key # data to be saved
            ))
        return lis

    """
    "dirname"    : singleton.valkkafs_dir.get(),
    "n_blocks"   : 10,
    "blocksize"  : 10
    """

    columns = [
        # TODO: for valkkafs metadata directory: (1) add a non-editable column
        ColumnSpec(
            CheckBoxColumn, 
            key_name    = "record", 
            label_name  = "Activate Recording",
            def_value   = False),

        ColumnSpec(
            SpinBoxIntegerColumn,
            key_name    = "blocksize",
            label_name  = "Blocksize (MB)",
            min_value   = 1,
            max_value   = 1024*1024*1024, # 1 GB
            def_value   = default.valkkafs_config["blocksize"]), 

        ColumnSpec(
            SpinBoxIntegerColumn,
            key_name    = "n_blocks",
            label_name  = "Number of Blocks",
            min_value   = 5,
            max_value   = 999999999,
            def_value   = default.valkkafs_config["n_blocks"]), 
        # Calculate Total Size (MB)

        ColumnSpec(ConstantRadioButtonColumn, 
            key_name = "fs_flavor",    
            label_name = "ValkkaFS type", 
            list = [("Normal file", "file"),("Dedicated block device", "valkkafs")]),

        ColumnSpec(ConstantComboBoxColumn, 
            key_name = "partition_uuid",    
            label_name = "Available Devices", 
            callback = getValkkaFSDevices)
        ]
        # TODO:
        # Actions (buttons): format, save, cancel (exit without applying changes)
  

    def makeWidget(self):
        """Subclassed from Row : custom form.  Add a total disk space field.
        """
        self.widget = FormWidget()
        self.lay = QtWidgets.QGridLayout(self.widget)
        
        cc = 0
        self.placeWidget(cc, "record"); cc+=1
        self.placeWidget(cc, "blocksize"); cc+=1
        self.placeWidget(cc, "n_blocks"); cc+=1

        self.label_total_size = QtWidgets.QLabel("Total Size (MB)", self.widget)
        self.label_total_size_value = QtWidgets.QLabel("", self.widget)
        self.placeWidgetPair(cc, (self.label_total_size, self.label_total_size_value)); cc+=1

        self.placeWidget(cc, "fs_flavor"); cc+=1
        self.placeWidget(cc, "partition_uuid"); cc+=1
        
        self.connectNotifications()

        def fs_size_changed():
            total_size_mb = self["blocksize"].getValue()*self["n_blocks"].getValue()
            self.label_total_size_value.setText(str(total_size_mb))

        def block_device_slot():
            self["partition_uuid"].updateWidget()
            n_devs = self["partition_uuid"].widget.count() # QComboBox.count()
            if n_devs < 1:
                self["fs_flavor"]["file"].setChecked(True)
            
        self["blocksize"].widget.valueChanged.connect(fs_size_changed)
        self["n_blocks"].widget.valueChanged.connect(fs_size_changed)
        self["fs_flavor"]["valkkafs"].clicked.connect(block_device_slot)

        fs_size_changed()
        block_device_slot()

        """
        self.label3  = QtWidgets.QLabel("Actions", self.widget)
        self.label3_ = QtWidgets.QWidget(self.widget)
        self.placeWidgetPair(cc, (self.label3, self.label3_)); cc+=1
        
        self.format_button = QtWidgets.QPushButton("REFORMAT", self.widget)
        self.format_label = QtWidgets.QLabel("Applies filesystem changes and clears ValkkaFS")
        self.placeWidgetPair(cc, (self.format_button, self.format_label)); cc+=1
        
        self.save_button = QtWidgets.QPushButton("SAVE", self.widget)
        self.save_label = QtWidgets.QLabel("Applies other changes")
        self.placeWidgetPair(cc, (self.save_button, self.save_label)); cc+=1

        self.cancel_button = QtWidgets.QPushButton("CANCEL", self.widget)
        self.cancel_label = QtWidgets.QLabel("Exits without applying any changes")
        self.placeWidgetPair(cc, (self.cancel_button, self.cancel_label)); cc+=1
        """


def main():
  app=QtWidgets.QApplication(["test_app"])
  mg=MyGui()
  mg.show()
  app.exec_()



if (__name__=="__main__"):
  main()
 
