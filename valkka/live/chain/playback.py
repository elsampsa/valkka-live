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
@version 1.2.1 
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


class PlaybackFilterchain(BaseFilterchain):
    """This class implements the following filterchain:
    
    ::


        ** main branch **


                  [ValkkaFSManager]
        +----------------------------------------+
        |                                        |
        ValkkaFSReaderThread -->> FileCacherThread --->> {ForkFrameFilterN:fork_filter_main} ------+


        ** decode branch **
                                                                
        OpenGLThread (connected by user)---+{ForkFrameFilterN:fork_filter_decode} <<--- (AVThread:avthread) <<-------+
                                           |

    """
    
    parameter_defs = {
        "openglthreads"     : list,
        # "valkkafsmanager"   : ValkkaFSManager,
        #"record_type"       : RecordType,
        
        # common to LiveThread & USBDeviceThread
        "slot"         : int,
        # Timestamp correction type: TimeCorrectionType_none,
        # TimeCorrectionType_dummy, or TimeCorrectionType_smart (default)
        "time_correction"
                       : None,
                       
        # identify this device / stream
        "_id"          : int,
        
        # these are for the AVThread instance:
        "n_basic"      : (int, 20),  # number of payload frames in the stack
        "n_setup"      : (int, 20),  # number of setup frames in the stack
        "n_signal"     : (int, 20),  # number of signal frames in the stack
        "flush_when_full"
                       : (bool, False),  # clear fifo at overflow
        "affinity"     : (int, -1),
        "verbose"      : (bool, False)
    }


    def __init__(self, **kwargs):
        # auxiliary string for debugging output
        self.pre = self.__class__.__name__ + " : "
        # check for input parameters, attach them to this instance as
        # attributes
        parameterInitCheck(PlaybackFilterchain.parameter_defs, kwargs, self)
        generateGetters(self.parameter_defs, self)
        
        # check some types
        for openglthread in self.openglthreads:
            assert(issubclass(openglthread.__class__, OpenGLThread))
        
        self.idst = str(id(self))
        
        self.initVars() # must be called before any clients are requested
        
        self.make_main_branch()
        self.make_decode_branch()
        
        self.start() # starts threads corresponding to this filterchain
    
    
    def __del__(self):
        self.requestClose()
        
        
    def initVars(self):
        # client counters
        self.decoding_client_count = 0
        self.x_screen_count = {}
        for i in range(len(self.openglthreads)):
            self.x_screen_count[i] = 0

        # view port related
        self.ports = []
        self.tokens_by_port = {}

        self.closed = False
        
    
    def start(self):
        """Starts threads required by the filter chain
        """
        self.avthread.startCall()


    def requestClose(self):
        if not self.closed:
            self.avthread.requestStopCall()
            self.clearAllViewPorts()
        self.closed = True
        
        
    def waitClose(self):
        self.avthread.waitStopCall()

    def make_main_branch(self):
        self.fork_filter_main = core.ForkFrameFilterN("fork_filter_main_" + str(self.slot))
        # self.valkkafsmanager.setOutput(self._id, self.slot, self.fork_filter_main) # old
        
    def getInputFilter(self):
        return self.fork_filter_main

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
        
        self.avthread.setAffinity(self.affinity)
        # get input FrameFilter from AVThread
        self.av_in_filter = self.avthread.getFrameFilter()
        
        # connect to main:
        self.fork_filter_main.connect("decoding_" + str(self.slot), self.av_in_filter)
    

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
    

    def x_screen_client(self, index, inc = 0):
        if self.x_screen_count[index] < 1 and inc > 0:
            openglthread = self.openglthreads[index]
            self.fork_filter_decode.connect("openglthread_" + str(index), openglthread.getInput())
        elif self.x_screen_count[index] == 1 and inc < 0:
            self.fork_filter_decode.disconnect("openglthread_" + str(index))
        self.x_screen_count[index] += inc
        self.decoding_client(inc = inc)
    


def createTestThreads():
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

    return openglthread


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
    openglthread = createTestThreads()
    
    fc = PlaybackFilterchain(
        openglthreads    = [openglthread],
        valkkafsmanager  = valkkafsmanager,
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
    
    fc.             requestClose()
    valkkafsmanager.requestClose()
    openglthread.   requestClose()
    
    fc.             waitClose()
    valkkafsmanager.waitClose()
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

 
