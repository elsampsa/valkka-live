"""
main.py : Main Valkka Live entry point

Copyright 2020 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    main.py
@author  Sampsa Riikonen
@date    2020
@version 0.12.0 
@brief   
"""

import sys


import sys
from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import logging
import argparse

from valkka.counter.tools import typeCheck, dictionaryCheck, objectCheck, parameterInitCheck, noCheck, getLogger
from valkka.live.local import ValkkaLocalDir
from valkka.live import singleton

singleton.test = "hello"
# set variables in the singleton module before loading gui
singleton.config_dir = ValkkaLocalDir("live")
singleton.valkkafs_dir = ValkkaLocalDir("live","fs")

"""
from valkka.live.gui import get_valkka_live_universe

class MyGui(get_valkka_live_universe("counter")):
    
    def __init__(self, parent = None):
        print("\n*** Welcome to Valkka Counter ***\n")
        super().__init__(parent)
"""

from valkka.live.gui import MyGui as MyGuiBase

class MyGui(MyGuiBase):
    
    def __init__(self, parent = None):
        print("\n*** Welcome to Valkka Live ***\n")
        super().__init__(parent)


    
def process_cl_args():

    def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")

    parser = argparse.ArgumentParser("valkka-counter")
    parser.register('type','bool',str2bool)    
    """
    parser.add_argument("command", action="store", type=str,                 
        help="mandatory command)")
    """
    parser.add_argument("--quiet", action="store", type=bool, default=False, 
        help="less verbosity")

    parser.add_argument("--reset", action="store", type=bool, default=False, 
        help="less verbosity")

    parsed_args, unparsed_args = parser.parse_known_args()
    return parsed_args, unparsed_args


def main():
    parsed_args, unparsed_args = process_cl_args()
    
    #print(parsed_args, unparsed_args)
    #return

    #"""
    if len(unparsed_args) > 0:
        print("Unknown command-line argument", unparsed_args[0])
        return
    #"""

    if parsed_args.quiet:
        # core.setLogLevel_valkkafslogger(loglevel_debug)
        print("libValkka verbosity set to fatal messages only")
        core.fatal_log_all()

    if parsed_args.reset:
        singleton.config_dir.reMake()

    app = QtWidgets.QApplication(["Valkka Live"])
    mg = MyGui()
    mg.show()
    app.exec_()



if (__name__ == "__main__"):
    main()
