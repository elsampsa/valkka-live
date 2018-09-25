"""
constant.py : Constant strings, etc.

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    constant.py
@author  Sampsa Riikonen
@date    2018
@version 0.1.1 
@brief   Constant strings, etc.
"""

valkka_core_not_found="""
Valkka core module is not installed

On Ubuntu you can install it with:

sudo apt-add-repository ppa:sampsa-riikonen/valkka
sudo apt-get update
sudo apt-get install valkka

Or alternatively, just use the following command:

install-valkka-core

For more information, see https://elsampsa.github.io/valkka-examples
"""


valkka_core_old="""

Valkka core module is not up to date

(required version %i.%i.%i, valkka-core version %i.%i.%i)

Please update with

sudo apt-get update
sudo apt-get upgrade valkka

Or alternatively, just use the following command:

update-valkka-core
"""

program_info="""

Valkka Live version %s

(Valkka core version %s)

Copyright Sampsa Riikonen 2018

"""

max_devices = 10

config_skeleton={ # TODO: do we need this, really?
  "containers" : [],
  }

