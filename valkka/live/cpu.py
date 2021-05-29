"""
cpu.py : Scheme for binding Valkka threads (LiveThread, OpenGLThread, AVThread decoders) to certain cores

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    cpu.py
@author  Sampsa Riikonen
@date    2018
@version 1.0.1 
@brief   Scheme for binding Valkka threads (LiveThread, OpenGLThread, AVThread decoders) to certain cores
"""

import sys
import multiprocessing


class CPUScheme:
    
    
    class Ring:
        
        def __init__(self, start, stop):
            self.start = start
            self.stop = stop
            self.index = self.stop
            
        def get(self):
            self.index += 1
            if (self.index > self.stop):
                self.index = self.start
            return self.index
            
    
    
    def __init__(self, n_cores = None): #, n_live = 1, n_gpu = 1):
        if n_cores:
            self.n_cores = n_cores
        else:
            self.n_cores = multiprocessing.cpu_count()
        print("CPUScheme : cores", self.n_cores)
        self.max_index = self.n_cores - 1
        self.reset()


    def reset(self):
        if (self.n_cores < 4): # 1-4 : no binding here ..
            self.livecore       = self.Ring(-1, -1)
            self.usbcore        = self.Ring(-1, -1)
            self.openglcore     = self.Ring(-1, -1)
            self.avcore         = self.Ring(-1, -1)
        elif (self.n_cores <= 6): # 4-6
            self.livecore       = self.Ring(0, 2)
            self.usbcore        = self.Ring(0, 2)
            self.openglcore     = self.Ring(0, 2)
            self.avcore         = self.Ring(1, self.max_index) 
        else: # 6+
            self.livecore       = self.Ring(0, 2)
            self.usbcore        = self.Ring(0, 2)
            self.openglcore     = self.Ring(1, 3)
            self.avcore         = self.Ring(2, self.max_index)
            
        
    def getLive(self):
        """Where the LiveThread is bound
        """
        return self.livecore.get()
    
    
    def getUSB(self):
        """Where the USBDeviceThread is bound
        """
        return self.usbcore.get()
        
    
    def getOpenGL(self):
        """Where the OpenGLThread is bound
        """
        return self.openglcore.get()
    
    
    def getAV(self):
        """Were the next AVThread is bound
        """
        return self.avcore.get()
        
        
    
def test1():
    scheme = CPUScheme()
    # scheme = CPUScheme(n_cores = 3)
    # scheme = CPUScheme(n_cores = 4)
    
    for i in range(5):
        print("live  ",scheme.getLive())
    for i in range(5):
        print("opengl",scheme.getOpenGL())
    for i in range(10):
        print("av    ",scheme.getAV())
    
    
    
if (__name__=="__main__"):
    test1()
    
    
    
