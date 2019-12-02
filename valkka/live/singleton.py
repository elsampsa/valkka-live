"""
singleton.py : Module-wide variables

Copyright 2019 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    singleton.py
@author  Sampsa Riikonen
@date    2019
@version 0.10.0 
@brief   
"""
from valkka.live.local import ValkkaLocalDir

# The datamodel.DataModel instance:
data_model = None

# cached devices by id.  Update every now & then
# key: id, value: device object
devices_by_id = {}

# process map for different analyzers
process_map = {}

# QThread for interprocess communication
thread = None

# For a hack to get the X11 window margins
dx = 0
dy = 0
dw = 0
dh = 0

config_dir = ValkkaLocalDir("live")
valkkafs_dir = ValkkaLocalDir("live","fs")

def reCacheDevicesById():
    global data_model, devices_by_id
    devices_by_id = data_model.getDevicesById()

