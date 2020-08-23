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
@version 0.14.1 
@brief   
"""
import sys
import os
import shutil

home = os.path.expanduser("~")

class LocalDir:
    basedir = ".some_hidden_dir"

    def __init__(self, *args):
        self.dirname = os.path.join(home, self.basedir, *args)
        self.make()

    def get(self):
        return self.dirname

    def reMake(self):
        self.clear()
        self.make()

    def make(self):
        if not self.has():
            os.makedirs(self.dirname)

    def clear(self):
        if self.dirname == home:
            raise BaseException("sanity exception - are you nuts!")
            return
        try:
            shutil.rmtree(self.dirname)
        except Exception as e:
            pass

    def has(self):
        return os.path.exists(self.dirname)

    def getFile(self, fname):
        return os.path.join(self.dirname, fname)


class ValkkaLocalDir(LocalDir):
    basedir = ".valkka"



if __name__ == "__main__":
    config_dir = ValkkaLocalDir("kokkelis")
    valkkafs_dir = ValkkaLocalDir("kokkelis","fs")
    print(config_dir.getFile("diibadaaba"))
    valkkafs_dir.clear()
    config_dir.clear()

