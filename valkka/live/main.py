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
@version 1.1.1 
@brief   
"""
import sys
# import PyQt5 # this would trigger PyQt5 instead of PySide2
from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot
import logging
import argparse
from setproctitle import setproctitle

from valkka.live.tools import getLogger
from valkka.live.local import ValkkaLocalDir
from valkka.live import singleton
try:
    from valkka import web
except Exception as e:
    print("WARNING: web backend not loaded")

singleton.test = "hello"
singleton.sema_uuid = "valkka-live"
# shared memory ring-buffer and image sizes
singleton.shmem_n_buffer = 10
singleton.shmem_image_dimensions = (1920//4, 1080//4)
singleton.shmem_image_interval = 100 # 10 fps

# set variables in the singleton module before loading gui
singleton.config_dir = ValkkaLocalDir("live")
singleton.valkkafs_dir = ValkkaLocalDir("live","fs")
singleton.logs_dir = ValkkaLocalDir("live","logs")
singleton.ipc_dir = ValkkaLocalDir("live","ipc")


"""
from valkka.live.gui import get_valkka_live_universe

class MyGui(get_valkka_live_universe("xxx")):
    
    def __init__(self, parent = None):
        print("\n*** Welcome to xxx ***\n")
        super().__init__(parent)
"""

    
def process_cl_args():

    def str2bool(v):
        # print("vittu")
        return v.lower() in ("yes", "true", "t", "1")

    parser = argparse.ArgumentParser("valkka-live")
    parser.register('type','bool',str2bool)    
    """
    parser.add_argument("command", action="store", type=str,                 
        help="mandatory command)")
    """
    parser.add_argument("--quiet", action="store", type=str2bool, default=False, 
        help="less verbosity")

    parser.add_argument("--reset", action="store", type=str2bool, default=False, 
        help="reset views, cameras lists etc.")

    parser.add_argument("--playback", action="store", type=str2bool, default=True, 
        help="enable / disable experimental playback")

    parser.add_argument("--load", action="store", type=str2bool, default=False, 
        help="load layout saved previously")

    parser.add_argument("--www", action="store", type=str2bool, default=False, 
        help="starts the web- and websocket servers.  Before this, you need to install the www extras with 'pip3 install --user -e .[www]'")

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

    if parsed_args.playback:
        singleton.use_playback = True
    else:
        singleton.use_playback = False


    if parsed_args.load:
        singleton.load_layout = True
    else:
        singleton.load_layout = False


    if parsed_args.www:
        singleton.start_www = True
        singleton.www_module = web
    else:
        singleton.start_www = False
        
    #print(singleton.start_www)
    #return

    from valkka.live.gui import MyGui as MyGuiBase

    class MyGui(MyGuiBase):
    
        def __init__(self, parent = None):
            print("\n*** Welcome to Valkka Live ***\n")
            super().__init__(parent)

    setproctitle("valkka-live")
    app = QtWidgets.QApplication(["Valkka Live"])
    mg = MyGui()
    mg.show()
    app.exec_()



if (__name__ == "__main__"):
    main()
