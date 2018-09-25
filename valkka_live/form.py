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
@version 0.1.1 
@brief   Custom cute_mongo_forms
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
from cute_mongo_forms.row import Row
from cute_mongo_forms.container import EditFormSet2

pre = "valkka_live.form : "
verbose = True


class SlotFormSet(EditFormSet2):
    """A special form class that uses the "slot" keys value.

    The form has an internal state of the slot, saved in self.current_slot_value

    Changing from one form type to another maintains the value of the slot key.
    """

    def initVars(self):
        super().initVars()
        self.current_slot = None
        
        
    def makeWidget(self):
        super().makeWidget()
        i = self.lay.count()
        self.info_label = QtWidgets.QLabel("Cameralists and services are reinitiated\n once you close this window", self.widget)
        self.lay.insertWidget(i,self.info_label)
        
        
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
        print(self.pre, "dropdown_changed_slot",
              i, self.row_instance_by_index[i])
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
