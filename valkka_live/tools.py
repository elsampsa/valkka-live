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
@version 0.1.1 
@brief   Helper routines
"""

import sys
import os
import types

home = os.path.expanduser("~")
config_dir = os.path.join(home, ".valkka", "live")


def getConfigDir():
    return config_dir


def makeConfigDir():
    os.makedirs(config_dir)


def clearConfigDir():
    os.rmdir(config_dir)


def hasConfigDir():
    return os.path.exists(config_dir)


def getConfigFile(fname):
    return os.path.join(config_dir, fname)


""" # TODO
def scanMvision():
    import valkka_mvision
    dic = valkka_mvision.__dict__
    submodules = []
    for key in dic:
        obj = dic[key]
        if isinstance(obj, types.ModuleType):
            print key
"""


