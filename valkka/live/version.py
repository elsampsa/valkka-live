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
@version 0.5.0 
@brief   Handle program version numbers
"""

from valkka.core import VERSION_MAJOR as VALKKA_VERSION_MAJOR
from valkka.core import VERSION_MINOR as VALKKA_VERSION_MINOR
from valkka.core import VERSION_PATCH as VALKKA_VERSION_PATCH
from valkka.live import constant


# the following three lines are modded by setver.bash:
VERSION_MAJOR=0
VERSION_MINOR=5
VERSION_PATCH=0

# required valkka version
MIN_VALKKA_VERSION_MAJOR = 0
MIN_VALKKA_VERSION_MINOR = 8
MIN_VALKKA_VERSION_PATCH = 0


def check():
    # check that the imported valkka is fresh enough
    if ( (MIN_VALKKA_VERSION_MAJOR > VALKKA_VERSION_MAJOR) 
        or (MIN_VALKKA_VERSION_MINOR > VALKKA_VERSION_MINOR) 
        or (MIN_VALKKA_VERSION_PATCH > VALKKA_VERSION_PATCH) ):
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
    
    
