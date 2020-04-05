"""
multifork.py : General Valkka filterchain for Valkka Live

Copyright 2019 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    multifork.py
@author  Sampsa Riikonen
@date    2019
@version 0.12.1 
@brief   
"""

import sys
import time
import copy
from enum import Enum

# so, everything that has .core, refers to the api1 level (i.e. swig
# wrapped cpp code)
from valkka import core
# api2 versions of the thread classes
from valkka.api2.threads import LiveThread, USBDeviceThread, OpenGLThread
from valkka.api2.valkkafs import ValkkaFSManager, ValkkaFS
from valkka.api2.tools import parameterInitCheck, typeCheck, generateGetters
from valkka.api2.chains.port import ViewPort

from valkka.live.chain.base import BaseFilterchain


class ContextType(Enum):
    none = 0
    live = 1
    usb = 2
    

class RecordType(Enum):
    never = 0
    movement = 1
    always = 2

    

class MultiForkFilterchain(BaseFilterchain):
    """This class implements the following filterchain:
    
    ::
    
        *** main branch ***
        
        ANYSOURCE --> {ForkFrameFilterN:fork_filter_main} --+
                                                            |
                                       filesystem branch <--+ 
                                                            |
                                         decoding branch <--+ 
                                                            |
                                                 [other] <--+   [for tcp server, rtsp server, etc.]
                                                     
        *** filesystem branch ***
        
        --> {GateFrameFilter:fs_gate} --> {ForkFrameFilterN:fork_filter_file} -->> ValkkaFSWriterThread
                     |
          [controlled by callback (**)]               [can be recorded to 0-N filesystems on-demand]
                                                                             
                                                                             
        *** decode branch ***
                                                (OpenGLThread: glthread) <<--+ 
                                                                             |
        -->> (AVThread:avthread) --> {ForkFrameFilterN:fork_filter_decode} --+--> analysis branch
                           [feeds AVBitmapFrames]                            |
                                                                             +--> [other]
        
        *** analysis branch ***
    
        --> {MovementFrameFilter: movement_filter}
             |             |
             |             +~~ callback (**)
             |
             +-- {GateFrameFilter: sws_gate} --> {SwScaleFrameFilter: sws_filter} --> {ForkFrameFilterN: sws_fork_M}
                                                                                           |                                                                 
                   +------------+------------+---------------------------------------------+             
                   |            |            |
                 on-demand terminals for RGB images, for example
                   
                 - RGBShmemFrameFilter(s)                                               
                 - A common framefilter for all threads: 
                 
                 --> {ThreadSafeFrameFilter: common_sws_filter} --> {RGBShmemFrameFilter: common_rgb_shmem_filter}
                 [this could feed a common yolo detector for N streams]
                 
        *** qt bitmap branch *** (in the case you need to pass bitmaps to the qt subsystem)

        --> {GateFrameFilter: qt_gate} --> {TimeIntervalFrameFilter: qt_interval} -->
        --> {SwScaleFrameFilter: qt_sws_filter} --> {ForkFrameFilterN: qt_fork_N}
                                                              |                                                                 
                   +------------+------------+----------------+             
                   |            |            |
                 on-demand terminals for RGB images, for example
        





    """
    
    parameter_defs = {
        "context_type"      : ContextType,
        "openglthreads"     : list,
        "livethread"        : LiveThread,
        "usbdevicethread"   : USBDeviceThread,
        
        #"valkkafsmanager"   : None, # ValkkaFSManager .. this is connected on-demand & can be detached & changed
        #"record_type"       : RecordType,
        
        # common to LiveThread & USBDeviceThread
        "address"      : str,  # string identifying the stream
        "slot"         : int,
        # Timestamp correction type: TimeCorrectionType_none,
        # TimeCorrectionType_dummy, or TimeCorrectionType_smart (default)
        "time_correction"
                       : (int, core.TimeCorrectionType_smart),
                       
        # identify this device / stream
        "_id"          : int,
        
        # LiveThread specific
        "recv_buffer_size"  : (int, 0),     # Operating system socket ringbuffer size in bytes # 0 means default
        "reordering_mstime" : (int, 0),     # Reordering buffer time for Live555 packets in MILLIseconds # 0 means default
        "request_tcp" : (bool, False),

        # these are for the AVThread instance:
        "n_basic"      : (int, 20),  # number of payload frames in the stack
        "n_setup"      : (int, 20),  # number of setup frames in the stack
        "n_signal"     : (int, 20),  # number of signal frames in the stack
        "flush_when_full"
                       : (bool, False),  # clear fifo at overflow
        "affinity"     : (int, -1),
        "number_of_threads" : (int, 2),  # let's set this to > 1.  Otherwise people start whining when their 4K 60 fps cameras don't work..
        "verbose"      : (bool, False),
        "msreconnect"  : (int, 0),

        "shmem_image_dimensions" : (tuple, (1920//4, 1080//4)),
        "shmem_n_buffer"         : (int, 10),
        "shmem_image_interval"   : (int, 1000),
        
        # "movement_interval" : (int, 100), # pass frames at 10 fps # USE shmem_image_interval
        # "movement_treshold" : (float, 0.01),
        "movement_treshold" : (float, 0.0), # pass always
        "movement_duration" : (int, 30000) # when movement starts, pass through frames during 30 secs
    }

    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(MultiForkFilterchain.parameter_defs, kwargs, self)
        generateGetters(self.parameter_defs, self)
        
        # check some types
        for openglthread in self.openglthreads:
            assert(issubclass(openglthread.__class__, OpenGLThread))
        #if self.valkkafsmanager is not None:
        #    assert(isinstance(self.valkkafsmanager, ValkkaFSManager))
        #if record_type != RecordType.never:
        #    assert(self.id_rec > -1)
        
        self.idst = str(id(self))
        
        self.initVars() # must be called before any clients are requested
        
        self.make_main_branch()
        self.make_filesystem_branch() # calls by default self.fs_gate.unSet()
        self.make_decode_branch()
        self.make_analysis_branch()
        self.make_qt_branch()
        
        self.createContext() # creates & registers contexes to LiveThread & USBDeviceThread
        
        self.start() # starts threads corresponding to this filterchain
    
    
    def __del__(self):
        self.requestClose()
        
        
    def initVars(self):
        # client counters
        self.decoding_client_count = 0
        self.movement_client_count = 0
        
        self.sws_client_count = 0
        self.x_screen_count = {}

        self.sws_client_count_qt = 0
        self.x_screen_count_qt = {}

        for i in range(len(self.openglthreads)):
            self.x_screen_count[i] = 0

        # view port related
        self.ports = []
        self.tokens_by_port = {}

        # shmem related
        self.shmem_terminals = {}
        self.width      = self.shmem_image_dimensions[0]
        self.height     = self.shmem_image_dimensions[1]
            
        self.shmem_terminals_qt = {}

        self.record_type = None
        self.id_rec = None
        self.valkkafsmanager = None
        
        self.closed = False
        
    
    def start(self):
        """Starts threads required by the filter chain
        """
        self.avthread.startCall()


    def requestClose(self):
        if not self.closed:
            self.avthread.requestStopCall()
            self.clearRecording()
            self.releaseAllShmem()
            self.clearAllViewPorts()
        self.closed = True
        
        
    def waitClose(self):
        self.avthread.waitStopCall()


    # *** Filesystem branch related ***

    def movement_cb(self, tup: tuple):
        """callback from the cpp side
        
        tup = (bool, SlotNumber, mstimestamp)
        
        bool = True means new movement even, bool = False means movement event ended stopped
        
        Controls the passthrough on self.fs_gate
        """
        try:
            if tup[0]:
                self.fs_gate.set()
            else:
                self.fs_gate.unSet()
        except Exception as e:
            print("MultiFork: movement_cb failed with", e)
            
            
    # (De)activate ValkkaFSWriterThread for this slot
    
    def setRecording(self, record_type: RecordType, manager: ValkkaFSManager, id_rec: int = None, ):
        # for the moment, only one ValkkaFSManager can be set
        if self.record_type == RecordType.never:
            print("setRecording: never")
            return

        if id_rec is None:
            self.id_rec = self._id
        else:
            self.id_rec = id_rec
        
        if self.valkkafsmanager is not None:
            self.clearRecording()
            
        self.record_type = record_type
        self.valkkafsmanager = manager
        
        self.fork_filter_file.connect("recorder_" + str(self.slot) , self.valkkafsmanager.getFrameFilter())
        if self.record_type== RecordType.always:
            self.fs_gate.set()
        elif self.record_type == RecordType.movement:
            print("setRecording: movement")
            self.movement_client(inc = 1)
            self.movement_filter.setCallback(self.movement_cb)
        self.valkkafsmanager.setInput(self.id_rec, self.slot) 
       
       
    def clearRecording(self):
        if self.record_type == RecordType.never:
            return
        if self.valkkafsmanager is None:
            return
        
        if self.record_type == RecordType.always:
            self.fs_gate.unSet()
        elif self.record_type == RecordType.movement:
            self.movement_client(inc = -1)
        self.valkkafsmanager.clearInput(self.slot)
        self.fork_filter_file.disconnect("recorder_" + str(self.slot))
        
        self.record_type = None
        self.id_rec = None
        self.valkkafsmanager = None
        

    # *** Context creation for the relevant thread (LiveThread or USBDeviceThread) ***
    
    def createContext(self):
        if self.context_type == ContextType.live:
            self.createLiveContext()
        elif self.context_type == ContextType.usb:
            self.createUSBContext()
    
    
    def closeContext(self):
        if self.context_type == ContextType.live:
            self.livethread.stopStream(self.ctx)
            self.livethread.deRegisterStream(self.ctx)
        elif self.context_type == ContextType.usb:
            self.usbdevicethread.stopStream(self.ctx)
    
    
    def createLiveContext(self):
        """Context for LiveThread
        
        Creates & registers a context to LiveThread and connects it to the main filterchain
        
        Parameters required:
        
        ::
        
            self.slot
            self.address
            self.msreconnect
            
            self.time_correction
            self.recv_buffer_size
            self.reordering_mstime
        """
        
        self.ctx = core.LiveConnectionContext()
        self.ctx.slot = self.slot

        if (self.address.find("rtsp://") == 0):
            self.ctx.connection_type = core.LiveConnectionType_rtsp # rtsp connection
        else:
            self.ctx.connection_type = core.LiveConnectionType_sdp  # an sdp file

        if (self.request_tcp):
            self.ctx.request_tcp = self.request_tcp

        self.ctx.address = self.address
        # stream address, i.e. "rtsp://.."
        self.ctx.msreconnect = self.msreconnect
        
        self.ctx.recv_buffer_size = self.recv_buffer_size
        self.ctx.reordering_time = self.reordering_mstime * 1000  # from millisecs to microsecs

        self.ctx.time_correction = self.time_correction
        if self.ctx.time_correction == core.TimeCorrectionType_smart:
            print("createLiveContext: smart timestamps")
        else:
            print("createLiveContext: dummy timestamps")
            

        # connect to the main filterchain
        self.ctx.framefilter = self.fork_filter_main

        # send the information about the stream to LiveThread
        self.livethread.registerStream(self.ctx)
        self.livethread.playStream(self.ctx)

    
    def createTCPContext(self): # TODO
        pass
    
    
    def createUSBContext(self):
        """Context for USBDeviceThread
        
        Creates & registers a context to USBDeviceThread and connects it to the main filterchain
        
        Required parameters:
        
        ::
        
            self.slot
            self.address
            self.msreconnect
            
            self.time_correction
            
        """
        self.ctx = core.USBCameraConnectionContext()
        self.ctx.slot        = self.slot
        self.ctx.device      = self.address
        self.ctx.width       = 1280
        self.ctx.height      = 720
        if (self.time_correction is not None):
            self.ctx.time_correction = self.time_correction
        
        # connect to the main filterchain
        self.ctx.framefilter = self.fork_filter_main

        # start playing
        print("createUSBContext: play")
        self.usbdevicethread.playStream(self.ctx)
    
    
    # *** Create filtergraph branches ***
    
    def make_main_branch(self):
        self.fork_filter_main = core.ForkFrameFilterN("fork_filter_main_" + str(self.slot))

        
    def make_filesystem_branch(self):
        self.fork_filter_file = core.ForkFrameFilterN("fork_filter_file_" + str(self.slot))
        self.fs_gate = core.GateFrameFilter("fs_gate_" + str(self.slot), self.fork_filter_file)
        # connect to main:
        self.fork_filter_main.connect("fs_gate_" + str(self.slot), self.fs_gate)
        self.fs_gate.unSet()
    
        
    def make_decode_branch(self):
        self.fork_filter_decode = core.ForkFrameFilterN("fork_filter_decode_" + str(self.slot))
        
        self.framefifo_ctx = core.FrameFifoContext()
        self.framefifo_ctx.n_basic = self.n_basic
        self.framefifo_ctx.n_setup = self.n_setup
        self.framefifo_ctx.n_signal = self.n_signal
        self.framefifo_ctx.flush_when_full = self.flush_when_full
        
        self.avthread = core.AVThread(
            "avthread_" + str(self.slot),
            self.fork_filter_decode,
            self.framefifo_ctx)

        if self.affinity > -1: # affinity overwrites number of threads
            self.avthread.setAffinity(self.affinity)
        elif self.number_of_threads > 1:
            self.avthread.setNumberOfThreads(self.number_of_threads) # two by default
        
        # get input FrameFilter from AVThread
        self.av_in_filter = self.avthread.getFrameFilter()
        
        # connect to main:
        self.fork_filter_main.connect("decoding_" + str(self.slot), self.av_in_filter)
    
        
    def make_analysis_branch(self):
        """Connect only if movement detector is required:
        
        - Recording on movement
        - Analysis on movement
        """
        self.sws_fork_filter = core.ForkFrameFilterN("sws_fork_" + str(self.slot))
        self.sws_filter = core.SwScaleFrameFilter("sws_scale_" + str(self.slot), self.width, self.height, self.sws_fork_filter)
        self.sws_gate = core.GateFrameFilter("sws_gate_" + str(self.slot), self.sws_filter)
        self.movement_filter = core.MovementFrameFilter("movement_" + str(self.slot), 
                # self.movement_interval,
                self.shmem_image_interval,
                self.movement_treshold,
                self.movement_duration,
                self.sws_gate
                )
        # MovementFrameFilter(const char* name, long int interval, float treshold, long int duration, FrameFilter* next=NULL);
        

    def make_qt_branch(self):
        """Connect only if bitmaps needed at the Qt side
        """
        self.qt_fork_filter = core.ForkFrameFilterN("qt_fork_" + str(self.slot))
        
        self.qt_sws_filter =\
        core.SwScaleFrameFilter("qt_sws_scale_" + str(self.slot), self.width, 
            self.height, self.qt_fork_filter)

        self.qt_interval = core.TimeIntervalFrameFilter(
            "qt_interval_" + str(self.slot),
            # self.shmem_image_interval,
            500,
            self.qt_sws_filter
            )
        self.qt_gate = core.GateFrameFilter("qt_gate_" + str(self.slot), self.qt_interval)

        # connect to main:
        self.fork_filter_decode.connect("qt_branch_" + str(self.slot), self.qt_gate)



    # *** Client calculators ***
    
    def decoding_client(self, inc = 0):
        """Count instances that need decoding
        
        Start decoding if the number goes from 0 => 1
        Stop decoding if the number goes from 1 => 0
        """
        if self.decoding_client_count < 1 and inc > 0:
            # connect the analysis branch
            print("start decoding for slot", self.slot)
            self.avthread.decodingOnCall()
        elif self.decoding_client_count == 1 and inc < 0:
            print("stop decoding for slot", self.slot)
            self.avthread.decodingOffCall()
        self.decoding_client_count += inc
        
    
    def movement_client(self, inc = 0):
        """Count instances that need the movement detector
        
        Connect if the number goes from 0 => 1
        Disconnect if the number goes from 1 => 0
        """
        print("movement_client: count, inc:", self.movement_client_count, inc)
        if self.movement_client_count < 1 and inc > 0:
            # connect the analysis branch
            print("connecting analysis branch for slot", self.slot)
            self.fork_filter_decode.connect("analysis_" + str(self.slot), self.movement_filter)
        elif self.movement_client_count == 1 and inc < 0:
            print("disconnecting analysis branch for slot", self.slot)
            self.fork_filter_decode.disconnect("analysis_" + str(self.slot))
        self.movement_client_count += inc
        self.decoding_client(inc = inc)
        
        
    def sws_client(self, inc = 0):
        """Count instances that need the sw scaled images
        
        Enable sws_gate if number goes from 0 => 1
        Disable sws_gate if number goes from 1 => 0
        """
        if self.sws_client_count < 1 and inc > 0:
            # connect the analysis branch
            print("connecting sws_gate for slot", self.slot)
            self.sws_gate.set()
        elif self.sws_client_count == 1 and inc < 0:
            print("disconnecting sws_gate for slot", self.slot)
            self.sws_gate.unSet()
        self.sws_client_count += inc
        self.movement_client(inc = inc)
    

    def sws_client_qt(self, inc = 0):
        """Count instances that need the sw scaled images for Qt
        
        Enable qt_gate if number goes from 0 => 1
        Disable qt_gate if number goes from 1 => 0
        """
        if self.sws_client_count_qt < 1 and inc > 0:
            # connect the analysis branch
            print("connecting qt_gate for slot", self.slot)
            self.qt_gate.set()
        elif self.sws_client_count_qt == 1 and inc < 0:
            print("disconnecting qt_gate for slot", self.slot)
            self.qt_gate.unSet()
        self.sws_client_count_qt += inc
        

    def x_screen_client(self, index, inc = 0):
        if self.x_screen_count[index] < 1 and inc > 0:
            openglthread = self.openglthreads[index]
            self.fork_filter_decode.connect("openglthread_" + str(index), openglthread.getInput())
        elif self.x_screen_count[index] == 1 and inc < 0:
            self.fork_filter_decode.disconnect("openglthread_" + str(index))
        self.x_screen_count[index] += inc
        self.decoding_client(inc = inc)
        
            

    # *** Shmem hooks ***
            
    def getShmem(self):
        """Returns the unique name identifying the shared mem and semaphores.  The name can be passed to the machine vision routines.
        """
        shmem_name = self.idst + "_" + str(len(self.shmem_terminals))
        print("getShmem : reserving", shmem_name)
        shmem_filter = core.RGBShmemFrameFilter(shmem_name, self.shmem_n_buffer, self.width, self.height)
        # shmem_filter = core.BriefInfoFrameFilter(shmem_name) # DEBUG: see if you are actually getting any frames here ..
        self.shmem_terminals[shmem_name] = shmem_filter
        self.sws_fork_filter.connect(shmem_name, shmem_filter)
        # if first time, connect main branch to swscale_branch
        self.sws_client(inc = 1)
        return shmem_name 
    
        
    def releaseShmem(self, shmem_name):
        try:
            self.shmem_terminals.pop(shmem_name)
        except KeyError:
            return False
        print("releaseShmem : releasing", shmem_name)
        self.sws_fork_filter.disconnect(shmem_name)
        self.sws_client(inc = -1)
        return True
        
        
    def releaseAllShmem(self):
        for key in list(self.shmem_terminals.keys()):
            self.releaseShmem(key)
            

    # *** Shmem hooks for qt bitmaps ***

    def getShmemQt(self):
        """For passing bitmaps to the Qt side
        """
        shmem_name = self.idst + "_qt_" + str(len(self.shmem_terminals_qt))
        print("getShmemQt : reserving", shmem_name)
        shmem_filter = core.RGBShmemFrameFilter(shmem_name, self.shmem_n_buffer, self.width, self.height)
        # shmem_filter = core.BriefInfoFrameFilter(shmem_name) # DEBUG: see if you are actually getting any frames here ..
        self.shmem_terminals_qt[shmem_name] = shmem_filter
        self.qt_fork_filter.connect(shmem_name, shmem_filter)
        # if first time, connect main branch to swscale_branch
        self.sws_client_qt(inc = 1)
        return shmem_name, self.shmem_n_buffer, self.width, self.height
    
        
    def releaseShmemQt(self, shmem_name):
        try:
            self.shmem_terminals_qt.pop(shmem_name)
        except KeyError:
            return False
        print("releaseShmemQt : releasing", shmem_name)
        self.qt_fork_filter.disconnect(shmem_name)
        self.sws_client_qt(inc = -1)
        return True
        

    def releaseAllShmemQt(self):
        for key in list(self.shmem_terminals_qt.keys()):
            self.releaseShmemQt(key)
    




            
    # *** Sending video to OpenGLThreads ***
    # now in the mother class        
    


def createTestThreads():
    
    """
    valkkafsmanager = ValkkaFSManager(
        valkkafs,
        # read = False,   # debugging
        # cache = False,  # debugging
        # write = False   # debugging
        )
    """

    livethread = LiveThread(         # starts live stream services (using live555)
        name="live_thread",
        # verbose=True,
        verbose=False
        )
    
    usbdevicethread = USBDeviceThread(
        name="usb_thread",
        #verbose=True,
        verbose=False
        )
    

    openglthread = OpenGLThread(     # starts frame presenting services
        name="opengl_thread",
        # reserve stacks of YUV video frames for various resolutions
        n_720p  = 20,
        n_1080p = 20,
        n_1440p = 20,
        n_4K    = 0,
        verbose = True,
        # verbose=False,
        msbuftime = 300
        )

    return livethread, usbdevicethread, openglthread


def test1():
    """Test basic functionality of the MultiForkFilterchain
    """
    valkkafs = ValkkaFS.newFromDirectory(
        dirname = "/home/sampsa/tmp/testvalkkafs",
        blocksize = 512*1024,
        n_blocks = 10,
        verbose = True
        )
        
    valkkafsmanager = ValkkaFSManager(valkkafs)
        
    livethread, usbdevicethread, openglthread = createTestThreads()
    
    address = "rtsp://admin:12345@192.168.0.124"
    context_type = ContextType.live
    
    #address = "/dev/video0"
    #context_type = ContextType.usb

    # record_type = RecordType.never
    #record_type = RecordType.always
    #record_type = RecordType.movement
    
    fc = MultiForkFilterchain(
        context_type     = context_type,
        openglthreads    = [openglthread],
        livethread       = livethread,
        usbdevicethread  = usbdevicethread,
        address          = address,
        slot             = 2,
        _id              = 123
        )
    
    window_id = openglthread.createWindow()
    view_port = ViewPort(window_id = window_id, x_screen_num = 0)
    
    n = 2
    
    print("\nadd view port\n")
    fc.addViewPort(view_port)
    print("\nsleep\n")
    time.sleep(n)
    
    print("\ndel view port\n")
    fc.delViewPort(view_port)
    print("\nsleep\n")
    time.sleep(n)
    
    print("\nsetRecording (always)\n")
    fc.setRecording(12345, RecordType.always, valkkafsmanager)
    print("\nsleep\n")
    time.sleep(n)
    
    print("\nclearRecording\n")
    fc.clearRecording()
    print("\nsleep\n")
    time.sleep(n)
    
    print("\nsetRecording (movement)\n")
    fc.setRecording(12345, RecordType.movement, valkkafsmanager)
    print("\nsleep\n")
    time.sleep(n)
    
    print("\nsetRecording getShmem\n")
    name = fc.getShmem()
    print("\nsleep\n")
    time.sleep(n)
    
    print("\nsetRecording releaseShmem\n")
    fc.releaseShmem(name)
    print("\nsleep\n")
    time.sleep(n)
    
    print("\nclearRecording\n")
    fc.clearRecording()
    print("\nsleep\n")
    time.sleep(n)
    
    fc.             requestClose()
    valkkafsmanager.requestClose()
    livethread.     requestClose()
    usbdevicethread.requestClose()
    openglthread.   requestClose()
    
    fc.             waitClose()
    valkkafsmanager.waitClose()
    livethread.     waitClose()
    usbdevicethread.waitClose()
    openglthread.   waitClose()


def main():
    pre = __name__ + "main :"
    print(pre, "main: arguments: ", sys.argv)
    if (len(sys.argv) < 2):
        print(pre, "main: needs test number")
    else:
        st = "test" + str(sys.argv[1]) + "()"
        exec(st)


if (__name__ == "__main__"):
    main()


