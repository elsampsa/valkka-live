"""
filterchain.py : Manage and group Valkka filterchains

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    filterchain.py
@author  Sampsa Riikonen
@date    2018
@version 1.1.1 
@brief   Manage and group Valkka filterchains
"""

from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot # Qt5
import sys
from valkka.live.gpuhandler import GPUHandler
from valkka.live import constant, singleton
# from valkka.api2.chains import ManagedFilterchain, LiveManagedFilterchain, USBManagedFilterchain
from valkka.live.chain.multifork import MultiForkFilterchain, ContextType, RecordType
from valkka.live.chain.playback import PlaybackFilterchain
from valkka.api2.threads import LiveThread, USBDeviceThread
from valkka.api2.tools import parameterInitCheck
from valkka.api2.valkkafs import ValkkaFSManager

from valkka.live.datamodel.base import DataModel
from valkka.live.datamodel.row import RTSPCameraRow, USBCameraRow, SDPFileRow
from valkka.live.device import RTSPCameraDevice, USBCameraDevice, SDPFileDevice

from valkka import core


class FilterChainGroup:

    parameter_defs = {
        }

    def __init__(self, **kwargs):
        parameterInitCheck(FilterChainGroup.parameter_defs, kwargs, self)
        self.pre = self.__class__.__name__ + " : "
        self.chains = []
        self.closed = False
        
    def __del__(self):
        if not self.closed:
            self.close()
        
    def __len__(self):
        return len(self.chains)

    def dump(self):
        for chain in self.chains:
            print(chain)
        
    def close(self):
        self.closed = True
        self.reset()
        
        
    def reset(self):
        # start closing all threads simultaneously
        for chain in self.chains:
            chain.requestClose()
        # wait until all threads closed
        for chain in self.chains:
            chain.waitClose()
        self.chains = []


    def get(self, **kwargs):
        """Find correct filterchain based on generic variables

        You can pass, say: get(address = "rtsp://some_address")

        That searches a filterchain with the member address == "rtsp://some_address"
        """
        if len(self.chains) < 1:
            print("FilterChainGroup: WARNING: empty")
            return None
        for chain in self.chains:
            for key in kwargs:
                getter_name = "get_"+key
                # scan all possible getters
                if (hasattr(chain, getter_name)):
                    getter = getattr(chain, getter_name) # e.g. "get_address"
                    if (getter() == kwargs[key]):
                        return chain
                else:
                    print("FilterChainGroup: no such getter", getter_name)
        return None
    

    def read(self):
        pass


    def update(self):
        pass


    def getDevice(self, **kwargs): 
        """Like get, but returns a Device instance (RTSPCameraDevice, etc.)
        """
        pass



class LiveFilterChainGroup(FilterChainGroup):
    """Create & manage filterchains for live video

    Creates MultiForkFilterchain instances
    """
    parameter_defs = {
        "datamodel"        : DataModel,
        "livethread"       : LiveThread,
        "usbthread"        : USBDeviceThread,
        "gpu_handler"      : GPUHandler,
        "verbose"          : (bool, False),
        "cpu_scheme"       : None,
        "vaapi"            : (bool, False)
        }
    

    def __init__(self, **kwargs):
        parameterInitCheck(LiveFilterChainGroup.parameter_defs, kwargs, self)
        self.pre = self.__class__.__name__ + " : "
        self.chains = []
        self.context_type = None
        self.closed = False
        if self.vaapi:
            print("LiveFilterChainGroup: enabling VAAPI")

    
    def read(self):
        """Reads all devices from the database and creates filterchains
        
        TODO: we can, of course, just modify the added / removed cameras
        """
        self.reset()

        # take some stuff from the general config
        config = next(self.datamodel.config_collection.get())
        if config["overwrite_timestamps"]:
            self.time_correction = core.TimeCorrectionType_dummy
        else:
            self.time_correction = core.TimeCorrectionType_smart

        for dic in self.datamodel.camera_collection.get(): # TODO: search directly for RTSPCameraRow
            if (self.verbose): print(self.pre, "read : dic", dic)
            affinity = -1
            if self.cpu_scheme is not None:
                affinity = self.cpu_scheme.getAV()
            classname = dic.pop("classname")

            if classname == RTSPCameraRow.__name__:            
                device = RTSPCameraDevice(**dic) # a neat object with useful methods
                self.context_type = ContextType.live

            elif classname == USBCameraRow.__name__:
                device = USBCameraDevice(**dic) # a neat object with useful methods
                self.context_type = ContextType.usb

            elif classname == SDPFileRow.__name__:            
                device = SDPFileDevice(**dic) # a neat object with useful methods
                self.context_type = ContextType.live

            else:
                print(self.pre, "no context for classname", classname)
                continue

            # chain = ManagedFilterchain( # decoding and branching the stream happens here
            # chain = ManagedFilterchain2( # decoding and branching the stream happens here
            # chain = LiveManagedFilterchain( # decoding and branching the stream happens here
            chain = MultiForkFilterchain( # decoding and branching the stream happens here
                context_type = self.context_type,
                livethread  = self.livethread,
                usbdevicethread  = self.usbthread,
                openglthreads
                            = self.gpu_handler.openglthreads,
                address     = device.getMainAddress(),
                slot        = device.getLiveMainSlot(),
                # request_tcp = device.getForceTCP(),
                ## ..that one not here
                ## MultiForkFilterChain is "universal" for all types
                ## of inputs (rtsp, usb & sdp files)
                ## however, requesting tcp streaming instead of udp
                ## is just for RTSP cameras
                _id         = device._id,
                affinity    = affinity,
                msreconnect = 10000,
                # verbose     = True,
                verbose      = False,
                vaapi        = self.vaapi,
                
                time_correction = self.time_correction, # overwrite timestamps or not?

                shmem_image_dimensions = singleton.shmem_image_dimensions,
                shmem_n_buffer = singleton.shmem_n_buffer,
                shmem_image_interval = singleton.shmem_image_interval
            )

            if classname == RTSPCameraRow.__name__:
                """RTSP cameras specific configurations here
                """
                if (device.getForceTCP()):
                    chain.setTCPStreaming(True)

            self.chains.append(chain) # important .. otherwise chain will go out of context and get garbage collected
    

    def update(self):
        """Reads all devices from the database.  Creates new filterchains and removes old ones
        
        TODO: currently this is broken: if user changes any other field than the ip address, the cameras don't get updated
        """
        raise(AssertionError("out of date"))
        
        new_ids = []
        old_ids = []
        
        # collect old ip addresses
        for chain in self.chains:
            if (self.verbose): print(self.pre, "old :", chain, chain.get__id(), chain.get_address(), chain._id)
            old_ids.append(chain.get__id())
            
        # collect devices
        devices = []
        for dic in self.datamodel.camera_collection.get():
            if (self.verbose): print(self.pre, "update : dic", dic)
            if (dic["classname"] == RTSPCameraRow.__name__):
                devices.append(dic)
            
        devices_by_id={}
        for dic in devices: # RTSPCameraRow instances
            _id = dic["_id"]
            new_ids.append(_id)
            devices_by_id[_id] = dic
        
        if (self.verbose):
            print(self.pre, "update : new_ids =", new_ids)
            print(self.pre, "update : old_ids =", old_ids)
        
        add_list = list(set(new_ids).difference(set(old_ids))) # cams to be added
        rem_list = list(set(old_ids).difference(set(new_ids))) # cams to be removed
        
        if (self.verbose):
            print(self.pre, "update : add_list =", add_list)
            print(self.pre, "update : rem_list =", rem_list)
        
        # purge removed chains
        for i, chain in enumerate(self.chains):
            if (chain.get__id() in rem_list):
                chain_ = self.chains.pop(i)
                if (self.verbose): print(self.pre, "closing chain", chain_)
                chain_.close()
        
        # add new chains
        for new_address in add_list:
            dic = devices_by_id[new_address]
            chain = ManagedFilterchain( # decoding and branching the stream happens here
                livethread  = self.livethread,
                openglthreads
                            = self.gpu_handler.openglthreads,
                address     = RTSPCameraRow.getMainAddressFromDict(dic),
                slot        = dic["slot"],
                _id         = dic["_id"],
                # affinity    = a,
                msreconnect = 10000,
                verbose = True
            )
            if (self.verbose): print(self.pre, "adding chain", chain)
            self.chains.append(chain) # important .. otherwise chain will go out of context and get garbage collected

        # TODO: purge the views from removed cameras    
            
                    
    def getDevice(self, **kwargs): 
        """Like get, but returns a Device instance (RTSPCameraDevice, etc.)

        You can pass, say: getDevice(address = "rtsp://some_address")

        - That searches a filterchain with the member address == "rtsp://some_address"
        - Converts the data to RTSPCameraDevice or USBCameraDevice
        """
        filterchain = self.get(**kwargs)
        
        if filterchain is None:
            return None
        
        # get filterchain init parameters that are compatible with RTSPCameraDevice input parameters
        if filterchain.context_type == ContextType.live:

            if "rtsp://" in filterchain.get_address(): # automatically generated getter for the address member (see multifork.py)
                pars = filterchain.getParDic(RTSPCameraDevice.parameter_defs) # filter out relevant parameters for the device class
                device = RTSPCameraDevice(**pars)
            else:
                pars = filterchain.getParDic(SDPFileDevice.parameter_defs)
                device = SDPFileDevice(**pars)

        elif filterchain.context_type == ContextType.usb:
            pars = filterchain.getParDic(USBCameraDevice.parameter_defs)
            device = USBCameraDevice(**pars)

        else:
            device = None

        print(self.pre, "getDevice :", pars, device)
        return device

    """removed: this worked only with ValkkaMultiFS
    def setRecording(self, record_type: RecordType, manager: ValkkaFSManager):
        # Set recording state for all filterchains in this group
        for chain in self.chains:
            chain.setRecording(
                record_type = record_type,
                manager = manager
                )
    """
    
class PlaybackFilterChainGroup(FilterChainGroup):
    """Create & manage filterchains for live video

    Creates PlaybackFilterchain instances
    """
    parameter_defs = {
        "datamodel"        : DataModel,
        "gpu_handler"      : GPUHandler,
        # "valkkafsmanager"  : ValkkaFSManager,
        "verbose"          : (bool, False),
        "cpu_scheme"       : None
        }
    

    def __init__(self, **kwargs):
        parameterInitCheck(PlaybackFilterChainGroup.parameter_defs, kwargs, self)
        self.pre = self.__class__.__name__ + " : "
        self.chains = []
        self.context_type = None
        self.closed = False
        # self.verbose = True

    
    def read(self):
        """Reads all devices from the database and creates filterchains
        
        TODO: we can, of course, just modify the added / removed cameras
        """
        self.reset()
        for dic in self.datamodel.camera_collection.get(): # TODO: search directly for RTSPCameraRow
            if (self.verbose): print(self.pre, "read : dic", dic)
            affinity = -1
            if self.cpu_scheme:
                affinity = self.cpu_scheme.getAV()
            classname = dic.pop("classname")

            if classname == RTSPCameraRow.__name__:            
                device = RTSPCameraDevice(**dic) # a neat object with useful methods
                self.context_type = ContextType.live

            elif classname == USBCameraRow.__name__:
                device = USBCameraDevice(**dic) # a neat object with useful methods
                self.context_type = ContextType.usb

            elif classname == SDPFileRow.__name__:            
                device = SDPFileDevice(**dic) # a neat object with useful methods
                self.context_type = ContextType.live

            else:
                print(self.pre, "no context for classname", classname)
                continue

            chain = PlaybackFilterchain( # decoding and branching the stream happens here
                openglthreads
                            = self.gpu_handler.openglthreads,
                # valkkafsmanager  = self.valkkafsmanager,
                slot        = device.getRecSlot(),
                _id         = device._id,
                affinity    = affinity,
                # verbose     = True,
                verbose     =False
            )
            self.chains.append(chain) # important .. otherwise chain will go out of context and get garbage collected
    

    def update(self):
        """Reads all devices from the database.  Creates new filterchains and removes old ones
        
        TODO: currently this is broken: if user changes any other field than the ip address, the cameras don't get updated
        """
        raise(AssertionError("out of date"))
        
        new_ids = []
        old_ids = []
        
        # collect old ip addresses
        for chain in self.chains:
            if (self.verbose): print(self.pre, "old :", chain, chain.get__id(), chain.get_address(), chain._id)
            old_ids.append(chain.get__id())
            
        # collect devices
        devices = []
        for dic in self.datamodel.camera_collection.get():
            if (self.verbose): print(self.pre, "update : dic", dic)
            if (dic["classname"] == RTSPCameraRow.__name__):
                devices.append(dic)
            
        devices_by_id={}
        for dic in devices: # RTSPCameraRow instances
            _id = dic["_id"]
            new_ids.append(_id)
            devices_by_id[_id] = dic
        
        if (self.verbose):
            print(self.pre, "update : new_ids =", new_ids)
            print(self.pre, "update : old_ids =", old_ids)
        
        add_list = list(set(new_ids).difference(set(old_ids))) # cams to be added
        rem_list = list(set(old_ids).difference(set(new_ids))) # cams to be removed
        
        if (self.verbose):
            print(self.pre, "update : add_list =", add_list)
            print(self.pre, "update : rem_list =", rem_list)
        
        # purge removed chains
        for i, chain in enumerate(self.chains):
            if (chain.get__id() in rem_list):
                chain_ = self.chains.pop(i)
                if (self.verbose): print(self.pre, "closing chain", chain_)
                chain_.close()
        
        # add new chains
        for new_address in add_list:
            dic = devices_by_id[new_address]
            chain = ManagedFilterchain( # decoding and branching the stream happens here
                livethread  = self.livethread,
                openglthreads
                            = self.gpu_handler.openglthreads,
                address     = RTSPCameraRow.getMainAddressFromDict(dic),
                slot        = dic["slot"],
                _id         = dic["_id"],
                # affinity    = a,
                msreconnect = 10000,
                verbose = True
            )
            if (self.verbose): print(self.pre, "adding chain", chain)
            self.chains.append(chain) # important .. otherwise chain will go out of context and get garbage collected

        # TODO: purge the views from removed cameras    
            
                    
    def getDevice(self, **kwargs): 
        """Like get, but returns a Device instance (RTSPCameraDevice, etc.)

        You can pass, say: getDevice(address = "rtsp://some_address")

        - That searches a filterchain with the member address == "rtsp://some_address"
        - Converts the data to RTSPCameraDevice or USBCameraDevice
        """
        filterchain = self.get(**kwargs)
        
        if filterchain is None:
            return None
        
        # get filterchain init parameters that are compatible with RTSPCameraDevice input parameters
        if filterchain.context_type == ContextType.live:

            if "rtsp://" in filterchain.get_address(): # automatically generated getter for the address member (see multifork.py)
                pars = filterchain.getParDic(RTSPCameraDevice.parameter_defs) # filter out relevant parameters for the device class
                device = RTSPCameraDevice(**pars)
            else:
                pars = filterchain.getParDic(SDPFileDevice.parameter_defs)
                device = SDPFileDevice(**pars)

        elif filterchain.context_type == ContextType.usb:
            pars = filterchain.getParDic(USBCameraDevice.parameter_defs)
            device = USBCameraDevice(**pars)

        else:
            device = None

        print(self.pre, "getDevice :", pars, device)
        return device


def test1():
    dm = DataModel()
    dm.clearAll()
    dm.saveAll()
    
    collection = dm.camera_collection
    
    collection.new(
        RTSPCameraRow,
            {"slot": 1,
             "address": "192.168.1.41",
             "username": "admin",
             "password": "1234",
             "tail": ""}
            )
    
    collection.new(RTSPCameraRow,
            {"slot": 2,
             "address": "192.168.1.42",
             "username": "admin",
             "password": "1234",
             "tail": ""}
            )
    
    for element in collection.get():
        print("test1 : 1", element)

    
    gpu_handler = GPUHandler(
            n_720p  = 5,
            n_1080p = 5,
            n_1440p = 0,
            n_4K    = 0,
            msbuftime = 300,
            verbose = False
        )
    
    livethread = LiveThread(
        name = "live_thread",
        # verbose = True,
        verbose = False,
        # affinity = self.pardic["live affinity"]
        )
    
    
    filterchain_group = FilterChainGroup(datamodel = dm, livethread = livethread, gpu_handler = gpu_handler, verbose = True)
    filterchain_group.update()
    
    print("\n ADDING ONE \n")
    
    collection.new(RTSPCameraRow,
            {"slot": 3,
             "address": "192.168.1.43",
             "username": "admin",
             "password": "1234",
             "tail": ""}
            )
    
    filterchain_group.update()
    
    print("\n REMOVING ONE \n")
    
    entry = next(collection.get({"address":"192.168.1.41"}))
    collection.delete(entry["_id"])
    
    filterchain_group.update()
    
    print("\n BYE \n")
    
    filterchain_group.close()
    
    
if (__name__=="__main__"):
    test1()
    
    
    
 
 
 
