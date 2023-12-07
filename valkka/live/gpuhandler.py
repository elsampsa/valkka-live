"""
gpuhandler.py : GPU Handler class

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    gpuhandler.py
@author  Sampsa Riikonen
@date    2018
@version 1.2.2 
@brief   GPU Handler class
"""

from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot  # Qt5
import sys, os
import copy
# from valkka.core import *
from valkka.api2.tools import parameterInitCheck
from valkka.api2 import OpenGLThread
# from singleton import display
# print(">>>>", display)

pre = "gpuhandler :"

class GPUHandler:
    """Handles an OpenGLThread for each separate GPU
    """
    parameter_defs = {
        "cpu_scheme" : None
        }
    # copy parameter definitions from OpenGLThread, apply same parameters to each OpenGLThread
    parameter_defs.update(OpenGLThread.parameter_defs)
    
    
    def __init__(self, **kwargs):
        self.pre = self.__class__.__name__+" : " # auxiliary string for debugging output
        parameterInitCheck(GPUHandler.parameter_defs, kwargs, self) # check kwargs agains parameter_defs, attach ok'd parameters to this object as attributes
        self.kwargs = kwargs
        self.true_screens = []  # list of QtCore.QScreen
        self.openglthreads = [] # list of OpenGLThread instances
        self.findXScreens()
        # self.true_screens=[self.true_screens[0]]

        #if display:
        #    print("GPUHandler: WARNING: using custom-defined X11 DISPLAY:", display)
        #else:
        if "DISPLAY" in os.environ:
            dispvar = os.environ["DISPLAY"] # [host]:<display>[.screen]
        else:
            print("GPUHandler: WARNING: no DISPLAY env variable set! will try 0.0, but no guaranteed to work")
            dispvar = ":0"

        """DISPLAY env variable, see: https://www.x.org/archive/X11R6.8.1/doc/X.7.html

        if [] are optional, then, THIS IS WRONG:

        [host]:[display.]screen

        THIS IS CORRECT:

        [host]:display[.screen]

        :D.S -> display =D, screen=S
        :.S -> display=0, screen=S
        :D -> display=0, screen=0

        "display" is basically the same as an X server and gives the increment to the default X server port number
        where the server is found
        each X server administers screens (that can span multiple monitors)
        """
        host=""
        disp="0"
        screen="0"
        try:
            host, serv_screen = dispvar.split(":")
            # print(">", host, serv_screen)
            if "." in serv_screen:
                disp, screen = serv_screen.split(".")
                if disp == "":
                    disp="0"
            else:
                disp = serv_screen
        except Exception as e:
            print("GPUHandler: could not extract display/screen number from", dispvar,":", e)
            host = ""
            disp = "0"
            screen = "0"

        #for n_gpu, screen in enumerate(self.true_screens):
        #    x_connection = f":{disp}.{str(n_gpu)}" 
        for dummy in range(0,1):
            """Should create (and debug) code (in multi-screen system) that gets the correct x-screen numbers: I've found
            an exotic x-screen configuration, where $DISPLAY is ":2" and there was no display ":0" at all (!)
            """
            x_connection = f"{host}:{disp}.{screen}"
            
            print(pre, "GPUHandler: starting OpenGLThread with", x_connection)

            affinity = -1
            if self.cpu_scheme:
                affinity = self.cpu_scheme.getOpenGL()

            openglthread = OpenGLThread(
                # name="gpu_" + str(n_gpu),
                name="gpu_" + str(dummy),
                # reserve stacks of YUV video frames for various resolutions
                n_720p  = self.n_720p,
                n_1080p = self.n_1080p,
                n_1440p = self.n_1440p,
                n_4K    = self.n_4K,
                verbose = False,
                msbuftime    = self.msbuftime,
                affinity     = affinity,
                x_connection = x_connection
            )

            print(pre, "GPUHandler: OpenGLThread started")

            self.openglthreads.append(openglthread)

        
    def findXScreens(self):
        """NOTE: finding correct X-screen numbers with Qt doesn't really work?

        Anyways would need multi-screen hardware setup to try/debug that.

        Something along these lines: https://stackoverflow.com/questions/11367354/obtaining-list-of-all-xorg-displays

        Read also this: https://unix.stackexchange.com/questions/367732/what-are-display-and-screen-with-regard-to-0-0
        """
        qapp = QtCore.QCoreApplication.instance()
        if not qapp: # QApplication has not been started
            return
        
        screens = qapp.screens()
        """
        let's find out which screens are virtual

        screen, siblings:

        One big virtual desktop:

        A [A, B, C]
        B [A, B, C]
        C [A, B, C]

        A & B in one xscreen, C in another:

        A [A, B]
        B [A, B]
        C [C]

        """
        virtual_screens = set()
        for screen in screens:
            # if screen has been deemed as "virtual", don't check its siblings
            if (screen not in virtual_screens):
                siblings = screen.virtualSiblings()
                # remove the current screen under scrutiny from the siblings
                # list
                virtual_screens.update(set(siblings).difference(set([screen])))
                # .. the ones left over are virtual

        # print("GPUHandler: findXScreens: virtual screens",virtual_screens)
        true_screens = list(set(screens) - virtual_screens)

        # sort'em
        for screen in true_screens:
            self.true_screens.insert(screens.index(screen), screen)

        print("GPUHandler: findXScreens: true screens:", self.true_screens)


    def getXScreenNum(self, qscreen: QtGui.QScreen):
        try:
            i = self.true_screens.index(qscreen)
        except IndexError:
            print("GPUHandler: getXScreenNum failed")
            i = 0
            
        return i


    def close(self):
        # initiate closing of all openglthreads
        for openglthread in self.openglthreads:
            openglthread.requestClose()
        # wait them to be closed
        for openglthread in self.openglthreads:
            openglthread.waitClose()
            


class FakeGPUHandler:
    #A dummy imitator class.  For debugging only

    def __init__(self):
        self.openglthreads=[None]

        qapp    =QtCore.QCoreApplication.instance()
        screens =qapp.screens()
        self.true_screens =[screens[0]]



