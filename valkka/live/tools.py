"""
tools.py : Helper routines

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    tools.py
@author  Sampsa Riikonen
@date    2018
@version 1.0.1 
@brief   Helper routines
"""

import sys
import os
import types
import shutil
import pkgutil
import importlib
import types
import re
import logging
import copy
from pydoc import locate
from valkka.live.singleton import config_dir, valkkafs_dir

loggers = {}
"""
home = os.path.expanduser("~")
config_dir = os.path.join(home, ".valkka", "live")
valkkafs_dir = os.path.join(home, ".valkka", "live", "fs")
"""

assert(sys.version_info.major >= 3)

if sys.version_info.minor < 6:
    importerror = ImportError
else:
    importerror = ModuleNotFoundError


def classToName(cls):
    """Class to full module + class name
    """
    return cls.__module__+"."+cls.__name__


def nameToClass(name):
    """Full module + class name to class
    """
    return locate(name)
    

def getLogger(name):
    global loggers
    # print(">getLogger", name)
    logger = loggers.get(name)
    if logger: return logger
    # https://docs.python.org/2/howto/logging.html
    # log levels here : https://docs.python.org/2/howto/logging.html#when-to-use-logging
    # in the future, migrate this to a logger config file
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(name)
    loggers[name] = logger 
    return logger
    
    
def setLogger(name, level):
    """Give either logger name or the logger itself
    """
    if (isinstance(name,str)):
        logger = getLogger(name)
    else:
        logger = name 
    
    # print(">setLogger", name, "level",level)
    logger.setLevel(level)

    if not logger.hasHandlers():
        # print(">setLogger", name, "setting handler")
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)


def getConfigDir():
    return config_dir


def makeConfigDir():
    if (hasConfigDir()):
        clearConfigDir()
    os.makedirs(config_dir)


def clearConfigDir():
    # os.rmdir(config_dir)
    shutil.rmtree(config_dir)

def hasConfigDir():
    return os.path.exists(config_dir)


def getConfigFile(fname):
    return os.path.join(config_dir, fname)


def scanMVisionClasses(names = ["valkka.mvision"]):
    mvision_modules = []
    for name in names:
        module = importlib.import_module(name)
        # e.g. valkka.mvision.__init__.py is called
        mvision_modules.append(module)

    print(mvision_modules)

    mvision_classes = [] # stand-alone analyzers
    mvision_client_classes = [] # client analyzers that use a master process
    mvision_master_classes = [] # master processes (typically yolo)

    for m in mvision_modules:
        # print(m)
        dic = m.__dict__
        for key in dic:
            # print("  ", key, dic[key])
            obj = dic[key]
            if isinstance(obj, types.ModuleType): # modules only
                # # these are submodules, i.e. valkka.mvision = valkka.mvision.movement
                # # they have been imported to to valkka.mvision namespace at valkka.mvision.__init__.py
                # print("mvision scan:", obj)
                name = obj.__name__
                # modules that have the following name pattern: "valkka.mvision.*"
                p = re.compile(m.__name__ + ".\S*")
                if p.match(name):
                    print("mvision scan:", name)
                    try:
                        submodule = importlib.import_module(name)
                    except ModuleNotFoundError:
                        print("mvision scan: could not import", name)
                        continue

                    if (hasattr(submodule, "MVisionProcess")): # do we have a class valkka.mvision*.*.base.MVisionProcess ?
                        mvisionclass = getattr(submodule, "MVisionProcess")
                        if (hasattr(mvisionclass, "name")
                            and hasattr(mvisionclass, "tag")
                            and hasattr(mvisionclass, "max_instances")): # does that class has these members?
                            name = getattr(mvisionclass, "name")
                            print("mvision scan: found machine vision class with name, tag and max_instances", name)
                            mvision_classes.append(mvisionclass)
                        else:
                            print("mvision scan: submodule",submodule,"missing members (name, tag or max_instances)")

                    elif (hasattr(submodule, "MVisionClientProcess")):
                        mvisionclass = getattr(submodule, "MVisionClientProcess")
                        if (hasattr(mvisionclass, "name")
                            and hasattr(mvisionclass, "tag")
                            and hasattr(mvisionclass, "master")): # does that class has these members?
                            name = getattr(mvisionclass, "name")
                            print("mvision scan: found client machine vision class with name, tag and master instances", name)
                            mvision_client_classes.append(mvisionclass)
                        else:
                            print("mvision scan: submodule",submodule,"missing members (name, tag or master)")

                    elif (hasattr(submodule, "MVisionMasterProcess")):
                        mvisionclass = getattr(submodule, "MVisionMasterProcess")
                        if (hasattr(mvisionclass, "name")
                            and hasattr(mvisionclass, "tag")
                            and hasattr(mvisionclass, "max_instances")
                            and hasattr(mvisionclass, "max_clients")):
                            name = getattr(mvisionclass, "name")
                            print("mvision scan: found master machine vision class", name)
                            mvision_master_classes.append(mvisionclass)
                        else:
                            print("mvision scan: submodule",submodule,"missing members (name, tag or max_instances or max_clients)")

                    else:
                        print("mvision scan: submodule",submodule,"missing MVisionProcess")


    return mvision_classes, mvision_client_classes, mvision_master_classes



def getH264V4l2(verbose=False):
    """Find all V4l2 cameras with H264 encoding, and returns a list of tuples with ..

    (device file, device name), e.g. ("/dev/video2", "HD Pro Webcam C920 (/dev/video2)")
    """
    import glob
    from subprocess import Popen, PIPE

    cams=[]

    for device in glob.glob("/sys/class/video4linux/*"):
        devname=device.split("/")[-1]
        devfile=os.path.join("/dev",devname)

        lis=("v4l2-ctl --list-formats -d "+devfile).split()

        p = Popen(lis, stdout=PIPE, stderr=PIPE)
        # p.communicate()
        # print(dir(p))
        # print(p.returncode)
        # print(p.stderr.read().decode("utf-8"))
        st = p.stdout.read().decode("utf-8")
        # print(st)

        if (st.lower().find("h264")>-1):
            namefile=os.path.join(device, "name")
            # print(namefile)
            f=open(namefile, "r"); name=f.read(); f.close()
            fullname = name.strip() + " ("+devname+")"
            cams.append((devfile, fullname))

    if (verbose):
        for cam in cams:
            print(cam)

    return cams


def getFreeGPU_MB():
    import re
    from subprocess import Popen, PIPE
    s=re.compile("available .* memory: (\d+) MB")
    lis=("glxinfo").split()
    p = Popen(lis, stdout=PIPE, stderr=PIPE)
    st = p.stdout.read().decode("utf-8")

    try:
        val=int(s.findall(st)[0])
    except IndexError or ValueError:
        return -1

    return val


def parameterInitCheck(definitions, parameters, obj, undefined_ok=False):
    """ Checks that parameters are consistent with a definition

    :param definitions: Dictionary defining the parameters, their default values, etc.
    :param parameters:  Dictionary having the parameters to be checked
    :param obj:         Checked parameters are attached as attributes to this object

    An example definitions dictionary:

    |{
    |"age"     : (int,0),                 # parameter age defaults to 0 if not specified
    |"height"  : int,                     # parameter height **must** be defined by the user
    |"indexer" : some_module.Indexer,     # parameter indexer must of some user-defined class some_module.Indexer
    |"cleaner" : checkAttribute_cleaner,  # parameter cleaner is check by a custom function named "checkAttribute_cleaner" (that's been defined before)
    |"weird"   : None                     # parameter weird is passed without any checking - this means that your API is broken  :)
    | }

    """
    definitions = copy.copy(definitions)
    # parameters =getattr(obj,"kwargs")
    # parameters2=copy.copy(parameters)
    #print("parameterInitCheck: definitions=",definitions)
    for key in parameters:
        try:
            definition = definitions.pop(key)
        except KeyError:
            if (undefined_ok):
                continue
            else:
                raise AttributeError("Unknown parameter " + str(key))

        parameter = parameters[key]
        if (definition.__class__ ==
                tuple):   # a tuple defining (parameter_class, default value)
            #print("parameterInitCheck: tuple")
            required_type = definition[0]
            if (parameter.__class__ != required_type):
                raise(
                    AttributeError(
                        "Wrong type of parameter " +
                        key + " is " + str(parameter.__class__) +
                        " : should be " +
                        required_type.__name__))
            else:
                setattr(obj, key, parameter)  # parameters2.pop(key)
        elif isinstance(definition, types.FunctionType):
            # object is checked by a custom function
            #print("parameterInitCheck: callable")
            ok = definition(parameter)
            if (ok):
                setattr(obj, key, parameter)  # parameters2.pop(key)
            else:
                raise(
                    AttributeError(
                        "Checking of parameter " +
                        key +
                        " failed"))
        elif (definition is None):            # this is a generic object - no checking whatsoever
            #print("parameterInitCheck: None")
            setattr(obj, key, parameter)  # parameters2.pop(key)
        elif (definition.__class__ == type):  # Check the type
            #print("parameterInitCheck: type")
            required_type = definition
            if (parameter.__class__ != required_type):
                raise(
                    AttributeError(
                        "Wrong type of parameter " +
                        key + " is " + str(parameter.__class__) +
                        " : should be " +
                        required_type.__name__))
            else:
                setattr(obj, key, parameter)  # parameters2.pop(key)
        else:
            raise(AttributeError("Check your definitions syntax at "+key+" : "+str(parameter)))

    # in definitions, there might still some leftover parameters the user did
    # not bother to give
    for key in definitions.keys():
        definition = definitions[key]
        if (definition.__class__ ==
                tuple):   # a tuple defining (parameter_class, default value)
            setattr(obj, key, definition[1])  # parameters2.pop(key)
        elif (definition is None):            # parameter that can be void
            # parameters2.pop(key)
            # pass
            setattr(obj, key, None)
        else:
            raise(AttributeError("Missing a mandatory parameter " + key))

    # setattr(obj,"kwargs", parameters2)



def filter_keys(keys, dic):
    """
    :param keys: allowed keys
    :param dic : dictionary

    Only allowed keys are kept in the dictionary
    """
    out = {}
    for key in dic.keys():
        if (key in keys): # key is in allowed keys
            out[key] = dic[key]
    return out


def remove_keys(keys, dic):
    """
    :param keys: keys to be removed
    :param dic : dictionary

    """
    out = {}
    for key in dic.keys():
        if (key not in keys):
            out[key] = dic[key]
    return out




if (__name__ == "__main__"):
    """
    mvision_classes = scanMVisionClasses()
    for cl in mvision_classes:
        print(cl)
    """
    print(getFreeGPU_MB())







