   
Modules
*******

Machine Vision
==============

This is a standalone plugin that you can use to create your own python-based machine vision modules.  The provided example uses OpenCV, so install it as instructed `here <https://elsampsa.github.io/valkka-examples/_build/html/requirements.html#opencv>`_

Install the machine vision plugin like this:

::
    
    git clone git://github.com/elsampsa/valkka-mvision.git
    cd valkka-mvision
    pip3 install --user -e .
    
Now you have an editable version of the machine vision plugin available.
    
If you restart Valkka Live, there will be a new entry "Machine Vision" in the menu bar (Valkka Live scans the "valkka_mvision" namespace for submodules)

A simple movement detector is provided as an example.

Creating your own module
------------------------

Proceed like this:

::

    cd valkka-mvision/valkka/mvision
    cp -r movement my_module
    
Edit the file *valkka-mvision/valkka/mvision/__init__.py* and add the following line:

::

    from valkka.mvision.my_module import *
    
Edit file *valkka-mvision/valkka/mvision/my_module/base.py* and change line
    
::
    
    name = "Simple Movement Detector"
    
To

::

    name = "My Movement Detector"
    

Restart Valkka Live and confirm that "My Movement Detector" is available at the "Machine Vision" submenu
    
This is a namespace module, so if you want the packaging to work, modify *setup.py* like this:

::

    packages = [
    ...

    'valkka.mvision.my_module'
    ]
    
    
Using Your Module
-----------------
    
Drag'n' drop cameras into the machine vision widget and your module starts doing its magic

Remarks
-------

Your machine vision module runs as an independent python multiprocess that receives frames from the main Valkka Live program once in a second at a relatively low resolution, using POSIX shared memory and semaphores.

This is sufficient for many applications.  However, if you want more serious a thing, say, 25 fps video analysis at higher resolution, you should implement your stuff at the cpp level.  And only after that interface to Valkka (see the upcoming **valkka-cpp-examples** module for an example).

Commercial Modules
==================

*coming soon*

- Simultaneous synchronized recording of several ip cameras
- Audio

