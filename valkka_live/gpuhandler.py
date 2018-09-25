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
@version 0.1.1 
@brief   GPU Handler class
"""

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
import sys
# from valkka.valkka_core import *
from valkka.api2.tools import parameterInitCheck
from valkka.api2 import OpenGLThread

pre = "gpuhandler :"

class GPUHandler:
    """Handles an OpenGLThread for each separate GPU
    """

    # copy parameter definitions from OpenGLThread, apply same parameters to each OpenGLThread
    parameter_defs = OpenGLThread.parameter_defs 
    
    
    def __init__(self, **kwargs):
        self.pre = self.__class__.__name__+" : " # auxiliary string for debugging output
        parameterInitCheck(self.parameter_defs, kwargs, self) # check kwargs agains parameter_defs, attach ok'd parameters to this object as attributes
        self.kwargs = kwargs
        self.true_screens = []  # list of QtCore.QScreen
        self.openglthreads = [] # list of OpenGLThread instances
        self.findXScreens()

        # self.true_screens=[self.true_screens[0]]

        for n_gpu, screen in enumerate(self.true_screens):

            x_connection = ":0." + str(n_gpu)
            # x_connection=":0.1"
            # x_connection=":1.0" # nopes

            print(pre, "GPUHandler: starting OpenGLThread with", x_connection)

            openglthread = OpenGLThread(
                name="gpu_" + str(n_gpu),
                # reserve stacks of YUV video frames for various resolutions
                n_720p  = self.n_720p,
                n_1080p = self.n_1080p,
                n_1440p = self.n_1440p,
                n_4K    = self.n_4K,
                verbose = False,
                msbuftime    = self.msbuftime,
                # affinity     = self.affinity,
                x_connection = x_connection
            )

            print(pre, "GPUHandler: OpenGLThread started")

            self.openglthreads.append(openglthread)

        
    def findXScreens(self):
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
        for openglthread in self.openglthreads:
            openglthread.close()


class FakeGPUHandler:
    #A dummy imitator class.  For debugging only

    def __init__(self):
        self.openglthreads=[None]

        qapp    =QtCore.QCoreApplication.instance()
        screens =qapp.screens()
        self.true_screens =[screens[0]]



