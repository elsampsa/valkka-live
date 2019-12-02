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
@version 0.10.0 
@brief   Constant strings, etc.
"""

valkka_core_not_found="""
Valkka core module is not installed 

(or your version of Valkka Live is _very_ old)

On Ubuntu you can install valkka-core with:

sudo apt-add-repository ppa:sampsa-riikonen/valkka
sudo apt-get update
sudo apt-get install valkka

Or alternatively, just use the following command:

install-valkka-core

For more information, see https://elsampsa.github.io/valkka-examples
"""


valkka_core_old="""
Valkka core module is not up to date

(or your version of Valkka Live is _very_ old)

required valkka-core version %i.%i.%i
your valkka-core version is %i.%i.%i

Please update with

sudo apt-get update
sudo apt-get install --only-upgrade valkka

Or alternatively, just use the following command:

update-valkka-core
"""

program_info="""
Valkka Live version %s

(Valkka core version %s)

Valkka uses the following OpenSource software:

FFMpeg libraries (Lesser General Public License)
Live555 library  (Lesser General Public License)

Valkka Live, Copyright Sampsa Riikonen 2018
"""

max_devices = 32

config_skeleton={ # TODO: do we need this, really?
  "containers" : [],
  }


# shared memory ring-buffer and image sizes
shmem_n_buffer = 10
shmem_image_dimensions = (1920 // 2, 1080 // 2)
shmem_image_interval = 1000

# minimum size for video root widget
root_video_container_minsize = (300, 300)


