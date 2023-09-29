"""
base.py : A base class for analyzer and a multiprocess that is using an analyzer

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    base.py
@author  Sampsa Riikonen
@date    2018
@version 1.2.1 
@brief   A base class for analyzer and a multiprocess that is using an analyzer
"""

import sys
import logging
from valkka.api2 import parameterInitCheck
from valkka.live.tools import getLogger, setLogger

pre = "valkka.mvision.base : "


class Namespace(object):
    """Just a dummy namespace ..
    """

    def __init__(self):
        pass


class Analyzer(object):
    """A generic analyzer class
    """

    parameter_defs = {
        # :param verbose: verbose output or not?  Default: False.
        "verbose": (bool, False),
        # :param debug:   When this is True, will visualize on screen what the analyzer is doing (using OpenCV highgui)
        "debug": (bool, False)
    }

    def __init__(self, **kwargs):
        # checks that kwargs is consistent with parameter_defs.  Attaches
        # parameters as attributes to self.  This is a mother class: there
        # might be more parameters not defined here from child classes
        parameterInitCheck(
            Analyzer.parameter_defs,
            kwargs,
            self,
            undefined_ok=True)
        self.pre = self.__class__.__name__
        self.logger = getLogger(self.pre)
        if self.debug or self.verbose:
            self.setDebug()
        # self.init() # do this in child classes only ..


    def setDebug(self):
        setLogger(self.logger, logging.DEBUG)

    def init(self):
        """Acquire any resources required by the analyzer.  Must always call reset
        """
        raise(AssertionError("virtual method"))


    def reset(self):
        """If the analyzer has an internal state, reset it
        """
        raise(AssertionError("virtual method"))


    def __call__(self, img):
        """Do the magic for image img. Shape of the image array is (i,j,colors)
        """
        raise(AssertionError("virtual method"))


    def report(self, *args):
        if (self.verbose):
            print(self.pre, *args)
            # pass


    def close(self):
        """Release any resources acquired by the analyzer
        """
        pass
        
        
