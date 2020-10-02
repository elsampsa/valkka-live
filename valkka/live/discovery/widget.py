"""
NAME.py :

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    NAME.py
@author  Sampsa Riikonen
@date    2018
@version 1.0.0 
@brief   
"""

from valkka.live.qimport2 import *
import sys
from valkka.discovery import runWSDiscovery, runARPScan

"""# enable for stand-alone testing
from valkka.live.local import ValkkaLocalDir
from valkka.live import singleton
singleton.config_dir = ValkkaLocalDir("live")
singleton.valkkafs_dir = ValkkaLocalDir("live","fs")
# from valkka.live.datamodel.base import DataModel
"""
from valkka.live.datamodel.row import RTSPCameraRow

from valkka.live.listitem import HeaderListItem, ServerListItem,\
    RTSPCameraListItem, USBCameraListItem, ListItem
from valkka.live.cameralist import TreeModel
from valkka.live.device import RTSPCameraDevice
from valkka.live import singleton, constant


class DiscoveryHeaderListItem(ListItem):
    """A root item that's in the tree lists header
    """
    def makeItemData(self):
        self.itemData = ["RTSP Device", ""]

    def getMimeData(self):
        return None


class DiscoveryThread(QThread):

    class Signals(QObject):
        ip_list = Signal(object) # incoming signal that carries and object (++)


    def __init__(self, arp = False):
        super().__init__()
        self.arp = arp
        self.signals = self.Signals()


    def run(self):
        print(">wsdiscovery")
        ips = runWSDiscovery()
        print(">wsdiscovery done")
        # print(ips)
        ips2 = []
        if self.arp:
            print(">arp-scan")
            ips2 = runARPScan(exclude_list = ips)
        ips = ips + ips2
        self.signals.ip_list.emit(ips)
        print(">discovery thread bye")


class DiscoveryTree(QTreeView):

    def __init__(self, parent=None, root=None):
        super().__init__(parent)
        # self.setDragEnabled(True)
        self.setDragEnabled(False)
        self.root = root
        self.setMinimumWidth(600)
        self.initTree()

    def initTree(self):
        self.model = TreeModel(self.root)
        self.setModel(self.model)
        self.setColumnWidth(0, 300)
    
    def reset_(self):
        self.model.removeRows(0, self.root.childCount(), self.rootIndex())
        
    def showEvent(self, e):
        super().showEvent(e)
        self.expandAll()
    

class ImportDialog(QDialog):

    def __init__(self, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Import")

        self.lay = QVBoxLayout(self)
        
        # the form
        self.form = QWidget(self)
        self.formlay = QGridLayout(self.form)
        self.lay.addWidget(self.form)

        self.start_slot_label = QLabel("Start slot", self.form)
        self.start_slot = QSpinBox(self.form)
        self.start_slot.setRange(1, constant.max_devices)
        self.formlay.addWidget(self.start_slot_label, 0, 0)
        self.formlay.addWidget(self.start_slot, 0, 1)
        
        self.end_slot_label = QLabel("End slot", self.form)
        self.end_slot = QSpinBox(self.form)
        self.end_slot.setRange(1, constant.max_devices)
        self.formlay.addWidget(self.end_slot_label, 1, 0)
        self.formlay.addWidget(self.end_slot, 1, 1)
        
        self.overwrite_label = QLabel("Overwrite", self.form)
        self.overwrite = QCheckBox(self.form)
        self.formlay.addWidget(self.overwrite_label, 2, 0)
        self.formlay.addWidget(self.overwrite, 2, 1)
        
        self.new_label = QLabel("Only new", self.form)
        self.new = QCheckBox(self.form)
        self.formlay.addWidget(self.new_label, 3, 0)
        self.formlay.addWidget(self.new, 3, 1)

        self.user_label = QLabel("User")
        self.user = QLineEdit(self.form)
        self.formlay.addWidget(self.user_label, 4, 0)
        self.formlay.addWidget(self.user, 4, 1)

        self.passwd_label = QLabel("Password")
        self.passwd = QLineEdit(self.form)
        self.formlay.addWidget(self.passwd_label, 5, 0)
        self.formlay.addWidget(self.passwd, 5, 1)

        # the buttons
        self.buttons = QWidget(self)
        self.lay.addWidget(self.buttons)
        self.buttonlay = QHBoxLayout(self.buttons)

        self.ok_button = QPushButton("Ok", self.buttons)
        self.cancel_button = QPushButton("Cancel", self.buttons)
        self.buttonlay.addWidget(self.ok_button)
        self.buttonlay.addWidget(self.cancel_button)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)


    def getState(self):
        return (self.start_slot.value(),
            self.end_slot.value(),
            self.overwrite.isChecked(),
            self.new.isChecked(),
            self.user.text(),
            self.passwd.text())

            
class DiscoveryWidget(QWidget):


    def __init__(self, parent = None, sig = None):
        super().__init__(parent)
        self.sig = sig
        self.import_dialog = ImportDialog(self)

        self.lay = QVBoxLayout(self)

        self.root = DiscoveryHeaderListItem()
        self.listitems = []
        self.tree = DiscoveryTree(self, root = self.root)
        self.lay.addWidget(self.tree)

        self.use_arp = QCheckBox("Use arp scan", self)
        self.lay.addWidget(self.use_arp)

        self.buttons = QWidget(self)
        self.button_lay = QHBoxLayout(self.buttons)
        self.lay.addWidget(self.buttons)
        
        self.scan_button = QPushButton("(Re)Scan", self.buttons)
        self.import_button = QPushButton("Import", self.buttons)
        self.button_lay.addWidget(self.scan_button)
        self.button_lay.addWidget(self.import_button)
        self.import_button.setEnabled(False)

        self.scan_button.clicked.connect(self.scan_slot)
        self.import_button.clicked.connect(self.import_slot)


    def scan_slot(self):
        print(">scan")
        self.scan_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.thread = DiscoveryThread(arp = self.use_arp.isChecked())
        self.thread.signals.ip_list.connect(self.ip_list_slot)
        self.thread.start()
        print(">thread started")
        """# DEBUG
        self.ip_list_slot([
            "192.168.1.24",
            "192.168.1.32"
        ])
        """

    def import_slot(self):
        verbose = False
        # verbose = True
        if self.import_dialog.exec_() == self.import_dialog.Accepted:
            # print("dialog result", res == self.import_dialog.Accepted)
            start_slot, end_slot, overwrite, new, user, password = self.import_dialog.getState()
            if verbose: print("dialog:", start_slot, end_slot, overwrite, new, user, password)
            """
            for i in range(start_slot, end_slot+1):
                print("slot>", i)
            """
            dics = []
            existing_ips = []
            for dic in singleton.data_model.camera_collection.get():
                dics.append(dic)
                if dic["classname"] == "RTSPCameraRow":
                    existing_ips.append(dic["address"])
            dics.sort(key=lambda x: x["slot"])
            # singleton.data_model.clearCameraCollection() # nopes

            # filter out only new ips if necessary
            device_list = []
            for item in self.listitems:
                device = item.getMimeData()
                if (new == False) or (device.address not in existing_ips):
                    device_list.append(device)
                    if verbose: print("new device>", device)

            count = 0            
            for cc, dic in enumerate(dics): # iterate over existing dics
                n_slot = cc +1
                if verbose: print("old", dic["classname"], "at slot", n_slot)
                written = False
                """
                try:
                    new_ip = self.listitems[cc]
                except IndexError:
                    pass
                else:
                """
                if n_slot >= start_slot:
                    if n_slot <= end_slot:
                        if dic["classname"] == "EmptyRow" or overwrite:
                            try:
                                device = device_list[count]
                            except IndexError:
                                if verbose: print("no more new devices")
                            else:
                                # delete old entry
                                if verbose: print("deleting", dic["classname"], "at slot", n_slot)
                                singleton.data_model.camera_collection.delete(dic["_id"])
                                # write new entry
                                if verbose: print("writing new", device, "at slot", n_slot)
                                # print(">", RTSPCameraRow.getDefaults())
                                singleton.data_model.camera_collection.new(
                                    RTSPCameraRow, {
                                        "slot"    : n_slot,
                                        "address" : device.address,
                                        "username": device.username,
                                        "password": device.password,
                                        "port"    : "",
                                        "tail"    : "",

                                        "subaddress_main" : "",
                                        "live_main"       : True,
                                        "rec_main"        : False,

                                        "subaddress_sub"  : "",
                                        "live_sub" : False,
                                        "rec_sub"  : False,

                                        "force_tcp": False
                                    } # TODO: use RTSPCameraRow.getDefaults() 
                                    # remember to update cute_mongo_forms distro though
                                )
                                written = True
                                count += 1
                if not written:
                    if verbose: print("retaining old", dic["classname"], "at slot", n_slot)
                    pass

            if count > 0:
                # so, a new camera was written
                # datamodel.container.ListAndForm
                # DeviceList inherits cute_mongo_forms.container.List
                # it has update_slot
                # used by ListAndForm
                # which uses:
                # valkka.live.form.SlotFormSet
                # & connects valkka.live.form.SlotFormSet.signals.modified
                # to DeviceList.update_slot
                # so we need to fire valkka.live.form.SlotFormSet.signals.modified
                if self.sig is not None:
                    self.sig.emit(None)



    def ip_list_slot(self, ip_lis):
        self.listitems = []
        self.tree.reset_()

        for ip in ip_lis:
            listitem = RTSPCameraListItem(
                camera = RTSPCameraDevice(
                    _id     =0,
                    slot    =0,
                    address =ip,
                    username="admin",
                    password="1234"
                ),
                parent = self.root
            )
            self.listitems.append(listitem)

        self.tree.update()
        self.tree.expandAll()
        self.scan_button.setEnabled(True)
        if len(ip_lis) > 0:
            self.import_button.setEnabled(True)

"""Scheme

DiscoveryWidget 
    => ImportDialog
       returns parameters
    => manipulates db

"""




class MyGui(QMainWindow):

  
  def __init__(self,parent=None):
    super(MyGui, self).__init__()
    self.initVars()
    self.setupUi()
    self.openValkka()
    

  def initVars(self):
    from valkka.live.datamodel.base import DataModel
    singleton.data_model = DataModel(directory = singleton.config_dir.get())


  def setupUi(self):
    self.setGeometry(QRect(100,100,500,500))
    # self.w = ImportDialog()
    self.w = DiscoveryWidget()
    self.setCentralWidget(self.w)
    
      
  def openValkka(self):
    pass
    
  
  def closeValkka(self):
    pass
  
  
  def closeEvent(self,e):
    print("closeEvent!")
    self.closeValkka()
    e.accept()



def main():
  app=QApplication(["test_app"])
  mg=MyGui()
  mg.show()
  app.exec_()



if (__name__=="__main__"):
  main()
 
