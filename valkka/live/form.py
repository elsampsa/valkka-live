"""
form.py : Custom cute_mongo_forms

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    form.py
@author  Sampsa Riikonen
@date    2018
@version 0.14.1 
@brief   Custom cute_mongo_forms
"""

from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot  # Qt5
import sys
from cute_mongo_forms.row import Row, Column
from cute_mongo_forms.container import EditFormSet2
from valkka.live.tools import getH264V4l2
from valkka.api2.tools import parameterInitCheck
from valkka.live import dialog, constant
from valkka.live.discovery.widget import DiscoveryWidget
from valkka.live.qt.tools import QCapsulate

pre = "valkka.live.form : "
verbose = True


class SlotFormSet(EditFormSet2):
    """A special form class that uses the "slot" keys value.

    The form has an internal state of the slot, saved in self.current_slot_value

    Changing from one form type to another maintains the value of the slot key.
    """
    
    class Signals(QtCore.QObject):
        """Signals emitted by this class:
        
        - new_record(object) : emitted when a new record has been added.  Carries the record _id.
        - save_record(object): emitted when a record has been saved.  Carries the record _id.
        """
        save_record  =Signal(object) # emitted when a record has been saved
        modified     =Signal(object) # emitted when one of the above has been triggered
        copy_request =Signal(object) # emitted when user wants to copy a certain entry to other slots
    

    def initVars(self):
        super().initVars()
        self.current_slot = None
        
        
    def makeWidget(self):
        super().makeWidget()
        i = self.lay.count()
        self.info_label = QtWidgets.QLabel("Cameralists and services are reinitiated\n once you close this window", self.widget)
        self.lay.insertWidget(i,self.info_label)
        
        # give a signal thats emitted once discovery has modified the camera list
        self.discovery_win = QCapsulate(DiscoveryWidget(sig = self.signals.modified), "Camera Discovery")
        self.discovery_win.hide()
        self.discovery_button = QtWidgets.QPushButton("Camera Search", self.widget)
        self.discovery_button.clicked.connect(self.discovery_slot)
        self.lay.insertWidget(i+1,self.discovery_button)


    def makeButtons(self):
        super().makeButtons()
        self.copyto_button =QtWidgets.QPushButton("COPY", self.buttons)
        self.buttons_lay.addWidget(self.copyto_button)
        # self.copyto_button.clicked.connect(self.signals.copy_request)
        self.copyto_button.clicked.connect(self.copy_slot)
        
        
    def discovery_slot(self):
        print("discovery_slot")
        self.discovery_win.show()


    def chooseForm_slot(self, element, element_old):
        """Calling this slot chooses the form to be shown

        :param element:      an object that has *_id* and *classname* attributes
        :param element_old:  an object that has *_id* and *classname* attributes

        This slot is typically connected to List classes, widget attribute's, currentItemChanged method (List.widget is QListWidget that has currentItemChanged slot), so the element and element_old parameters are QListWidgetItem instances with extra attributes "_id" and "_classname" attached.

        Queries the database for element._id
        """

        self.current_slot = None

        if (verbose):
            # enable this if you're unsure what's coming here..
            print(self.pre, "chooseForm_slot :", element)
        if (isinstance(element, type(None))):
            self.current_row = None
            self.element = None
        else:
            # print(self.pre,"chooseForm_slot :",element)
            assert(hasattr(element, "_id"))
            assert(hasattr(element, "classname"))
            try:
                self.current_row = self.row_instance_by_name[element.classname]
            except KeyError:
                print(
                    self.pre,
                    "chooseForm_slot : no such classname for this FormSet : ",
                    element.classname)
                self.current_row = None
                self.element = None
            else:
                self.resetForm()
                self.current_row.get(self.collection, element._id)
                self.element = element
                self.current_slot = self.current_row.get_column_value("slot")

        self.showCurrent()

    def dropdown_changed_slot(self, i):
        if (i<0): # nothing chosen by the user
            return
        if (self.current_slot==None): # if no list entry has been chosen yet ..
            return
        
        print(self.pre, "dropdown_changed_slot",i, self.row_instance_by_index[i])
        for key in self.row_instance_by_name:
            self.row_instance_by_name[key].widget.hide()

        self.current_row = self.row_instance_by_index[i]
        if (isinstance(self.current_row, type(None))):
            pass
        else:
            # user changed the object/form class type.  Copy the the slot index
            # to the new object.
            print(
                self.pre,
                "dropdown_changed_slot : current_slot=",
                self.current_slot)
            self.current_row.set_column_value("slot", self.current_slot)
            self.current_row.widget.show()

    def save_slot(self):
        if (isinstance(self.element, type(None))):
            if (verbose):
                print(self.pre, "save_slot : no document chosen yet")
            return
        self.current_row.update(self.collection, self.element._id)
        self.collection.save()
        if (verbose):
            print(self.pre, "save_slot: emitting", self.element._id)
        self.signals.save_record.emit(self.element._id)

    def clear_slot(self):
        if (isinstance(self.current_row, type(None))):
            if (verbose):
                print(self.pre, "clear_slot : can't clear None")
        else:
            self.current_row.clear()
            
    def copy_slot(self):
        if (isinstance(self.element, type(None))):
            if (verbose):
                print(self.pre, "copy_slot : no document chosen yet")
            return
        print(self.element)
        dic = next(self.collection.get({"_id" : self.element._id}))
        if (dic["classname"] == "RTSPCameraRow"): # only for RTSP cameras for the moment ..        
            # remove _id and classname (as collection adds these automatically)
            dic.pop("_id")
            dic.pop("classname")
            print(self.pre, "copy_slot : dic now =", dic)
            d = dialog.CopyToDialog(dic["address"], dic["slot"], constant.max_devices)
            res = d.exec_()
            for address, slot in res: # list of tuples: (address, slot)
                # remove the old entry for this slot
                old_dic = next(self.collection.get({"slot": slot}))
                self.collection.delete(old_dic["_id"])
            
                # overwrite address, everything else stays the same as in the original
                dic["address"] = address
                dic["slot"] = slot
                
                # add new entry to the same slot
                _id = self.collection.newByClassname(
                    "RTSPCameraRow", 
                    dic
                    )
            
            self.collection.save()
            self.signals.save_record.emit(_id)
        else:
            print(self.pre, "copy_slot : can only do that for RTSPCameraRow")
        
            
    def update_dropdown_list_slot(self):
        """Keep updating the dropdown list.  Say, don't let the user choose USB devices if none is available
        """
        self.dropdown_widget.clear() # this will trigger dropdown_changed_slot
        self.row_instance_by_index = []
        for i, key in enumerate(self.row_instance_by_name.keys()):
            row_instance = self.row_instance_by_name[key]
            if (row_instance.isActive()):
                self.row_instance_by_index.append(row_instance)
                display_name = row_instance.getName()
                self.dropdown_widget.insertItem(i, display_name)
            row_instance.updateWidget() # updates columns internal drop-down list

            
    def show_slot(self):
        """Inform here when the visibility of the main containing widget (window, tab, etc.) changes.  Can update available devices etc.
        """
        print(self.pre, "show_slot")
        self.update_dropdown_list_slot()
            
    
    def close(self):
        # the parent ListAndForm has been closed
        self.discovery_win.close()
