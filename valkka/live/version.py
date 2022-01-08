"""
version.py : Handle program version numbers

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    version.py
@author  Sampsa Riikonen
@date    2018
@version 1.1.0 
@brief   Handle program version numbers
"""

from valkka.core import VERSION_MAJOR as VALKKA_VERSION_MAJOR
from valkka.core import VERSION_MINOR as VALKKA_VERSION_MINOR
from valkka.core import VERSION_PATCH as VALKKA_VERSION_PATCH
from valkka.live import constant


# the following three lines are modded by setver.bash:
VERSION_MAJOR=1
VERSION_MINOR=1
VERSION_PATCH=0

version_tag = "%i.%i.%i" % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

# required libValkka version
MIN_VALKKA_VERSION_MAJOR = 1
MIN_VALKKA_VERSION_MINOR = 3
MIN_VALKKA_VERSION_PATCH = 0

# required darknet_py version # https://github.com/elsampsa/darknet-python
MIN_DARKNET_VERSION_MAJOR = 0
MIN_DARKNET_VERSION_MINOR = 2
MIN_DARKNET_VERSION_PATCH = 0

def check():
    version_min = int("%4.4i%4.4i%4.4i" % (MIN_VALKKA_VERSION_MAJOR, MIN_VALKKA_VERSION_MINOR, MIN_VALKKA_VERSION_PATCH))
    version = int("%4.4i%4.4i%4.4i" % (VALKKA_VERSION_MAJOR, VALKKA_VERSION_MINOR, VALKKA_VERSION_PATCH))
    if version < version_min:
            print(constant.valkka_core_old % (MIN_VALKKA_VERSION_MAJOR, 
                                              MIN_VALKKA_VERSION_MINOR, 
                                              MIN_VALKKA_VERSION_PATCH,
                                              VALKKA_VERSION_MAJOR, 
                                              VALKKA_VERSION_MINOR,
                                              VALKKA_VERSION_PATCH,))
            raise SystemExit()


def get():
    return "%i.%i.%i" % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)


def getValkka():
    return "%i.%i.%i" % (VALKKA_VERSION_MAJOR, VALKKA_VERSION_MINOR, VALKKA_VERSION_PATCH)
    
    
