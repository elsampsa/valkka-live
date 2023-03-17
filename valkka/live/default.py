"""
default.py : Default configuration values

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    default.py
@author  Sampsa Riikonen
@date    2018
@version 1.1.1 
@brief   Default configuration values
"""

from valkka.live import singleton

def get_memory_config():
    memory_config = {
        "msbuftime" : 100,
        "n_720p"    : 20,
        "n_1080p"   : 20,
        "n_1440p"   : 10,
        "n_4K"      : 5,
        "bind"      : False,
        "overwrite_timestamps" : False
        }
    return memory_config

def get_valkkafs_config():
    valkkafs_config = {
        "dirname"    : singleton.valkkafs_dir.get(),
        "n_blocks"   : 50,
        "blocksize"  : 2, # 50*2MB = 100 MB
        "fs_flavor"  : "file",
        "record"     : False,
        "partition_uuid" : None
    }
    return valkkafs_config

fps = 25
