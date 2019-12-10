"""
NAME.py :

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    NAME.py
@author  Sampsa Riikonen
@date    2018
@version 0.11.0 
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


class YourFilterchain:
    """This class implements the following filterchain:
    
    ::
    
        *** main branch ***
        
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
                       : None,
                       
        # identify this device / stream
        "_id"          : int,
        
        # LiveThread specific
        "recv_buffer_size"  : (int, 0),     # Operating system socket ringbuffer size in bytes # 0 means default
        "reordering_mstime" : (int, 0),     # Reordering buffer time for Live555 packets in MILLIseconds # 0 means default
    
        # these are for the AVThread instance:
        "n_basic"      : (int, 20),  # number of payload frames in the stack
        "n_setup"      : (int, 20),  # number of setup frames in the stack
        "n_signal"     : (int, 20),  # number of signal frames in the stack
        "flush_when_full"
                       : (bool, False),  # clear fifo at overflow
        "affinity"     : (int, -1),
        "verbose"      : (bool, False),
        "msreconnect"  : (int, 0),

        "shmem_image_dimensions" : (tuple, (1920//4, 1080//4)),
        "shmem_n_buffer"         : (int, 10),
        "shmem_image_interval"   : (int, 1000),
        
        "movement_interval" : (int, 1000),
        "movement_treshold" : (float, 0.01),
        "movement_duration" : (int, 5000)
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
        for i in range(len(self.openglthreads)):
            self.x_screen_count[i] = 0

        # view port related
        self.ports = []
        self.tokens_by_port = {}

        # shmem related
        self.shmem_terminals = {}
        self.width      = self.shmem_image_dimensions[0]
        self.height     = self.shmem_image_dimensions[1]
            
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
