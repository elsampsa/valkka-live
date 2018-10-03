"""
tools.py : Helper routines

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    tools.py
@author  Sampsa Riikonen
@date    2018
@version 0.3.0 
@brief   Helper routines
"""

import sys
import os
import types
import shutil

home = os.path.expanduser("~")
config_dir = os.path.join(home, ".valkka", "live")


def getConfigDir():
    return config_dir


def makeConfigDir():
    if (hasConfigDir()):
        clearConfigDir()
    os.makedirs(config_dir)


def clearConfigDir():
    # os.rmdir(config_dir)
    shutil.rmtree(config_dir)

def hasConfigDir():
    return os.path.exists(config_dir)


def getConfigFile(fname):
    return os.path.join(config_dir, fname)


def scanMVisionClasses():
    mvision_classes = []
    
    try:
        import valkka.mvision
    except ModuleNotFoundError:
        return mvision_classes
        
    dic = valkka.mvision.__dict__
    
    # search for namespaces:
    # valkka.mvision.*.base.MVisionProcess : should have class member "name"
    for key in dic: # valkka_mvision.*
        obj = dic[key]
        if isinstance(obj, types.ModuleType):
            # print(key)
            # print(dir(obj), obj.__loader__)
            # loader = obj.__loader__
            # print(dir(loader))
            if (hasattr(obj, "base")):
                base = getattr(obj, "base")
                if hasattr(base, "MVisionProcess"):
                    mvisionclass = getattr(base, "MVisionProcess")
                    if hasattr(mvisionclass, "name"):
                        name = getattr(mvisionclass, "name")
                        print("found machine vision class with name", name)
                        mvision_classes.append(mvisionclass)
    return mvision_classes                
    

