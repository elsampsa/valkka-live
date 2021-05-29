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
@version 1.0.1 
@brief   
"""


# **** Variables used to mod Valkka Live ****
# test = None

program_name = "Valkka Live"
sema_uuid = None

# shared memory ring-buffer and image sizes
shmem_n_buffer = None
shmem_image_dimensions = None
shmem_image_interval = None

# cli arguments
use_playback = True
load_layout = False

# local dirs
config_dir = None
valkkafs_dir = None
logs_dir = None
ipc_dir = None

# start extra servers
start_www = None
www_module = None

# search for machine vision packages
mvision_package_names = ["valkka.mvision"]

# custom widgets whose geometry you can save & (de)serialize them.  Should have methods serialize & deSerialize
serializable_widgets = ["camera_list_win"]

# setters
# *******************************************
def addMvisionPackageName(name):
    global mvision_package_names
    mvision_package_names.append(name)

def addSerializableWidget(name):
    global serializable_widgets
    serializable_widgets.append(name)
# *******************************************


# adjust mvision process verbosities
# mvision_verbose = True
mvision_verbose = False

# The datamodel.DataModel instance:
data_model = None

# cached devices by id.  Update every now & then
# key: id, value: device object
devices_by_id = {}

# process map for different analyzers
process_map = {}
client_process_map = {}
master_process_map = {}


def get_avail_master_process(tag):
    global master_process_map
    try:
        queue = master_process_map[tag]
    except KeyError:
        return None
    # return master process that still has space for clients
    for process in queue: 
        if process.available():
            return process
    return None


# QThread for interprocess communication
# thread = None

# For a hack to get the X11 window margins
dx = 0
dy = 0
dw = 0
dh = 0

def reCacheDevicesById():
    global data_model, devices_by_id
    devices_by_id = data_model.getDevicesById()

