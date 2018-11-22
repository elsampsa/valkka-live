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
@version 0.6.0 
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

home = os.path.expanduser("~")
config_dir = os.path.join(home, ".valkka", "live")


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


def scanMVisionClasses():
    mvision_modules = []

    valkka = importlib.import_module("valkka")
    for p in pkgutil.iter_modules(valkka.__path__, valkka.__name__ + "."):
        if (p.name.find(".mvision")>-1):
            # print("mvision scan: >",p)
            try:
                m = importlib.import_module(p.name)
            except ModuleNotFoundError:
                print("mvision scan: could not import", p.name)
            else:
                # print(m)
                mvision_modules.append(m)
            
    mvision_classes = []

    for m in mvision_modules:
        # print(m)
        dic = m.__dict__
        for key in dic:
            # print("  ", key, dic[key])
            obj = dic[key]
            if isinstance(obj, types.ModuleType): # modules only
                # print("mvision scan:", obj)
                name = obj.__name__
                # modules that have the following name pattern: "valkka.mvision*."
                p = re.compile("valkka\.mvision\S*\.")
                if p.match(name):
                    # print("mvision scan: ", name)
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
                            print("mvision scan: found machine vision class with name, tag and max_instances")
                            mvision_classes.append(mvisionclass)
                        else:
                            print("mvision scan: submodule",name,"missing members (name, tag or max_instances)")
                    else:
                        print("mvision scan: submodule",name,"missing MVisionProcess")
                        
    return mvision_classes


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
    

if (__name__ == "__main__"):
    """
    mvision_classes = scanMVisionClasses()
    for cl in mvision_classes:
        print(cl)
    """
    print(getFreeGPU_MB())
    
    
    

    

