   
Modules
*******

Machine Vision Examples
=======================

Once Valkka has decoded a frame from a certain camera, that decoded frame can be dumped to screen (to hundred windows if necessary) and passed to machine vision routines.  There is no overhead, as the stream from a certain camera is decoded only once.

Decoded frames can be pushed to machine vision routines that are programmed at the python level.  You can easily construct your own too.  At the moment, there are two schemes of plugging-in a python machine vision module.

**1. Using a python multiprocess.**  Communication with the python multiprocess is done by passing frames through shared memory from the Valkka main process.

    - Use this always when you can embed your routine as a python module
    - Typical use-case: OpenCV

**2. Using an external python program.**  Frames are passed to the external program through the filesystem.  Other communication is done through stdin and stdout.

    - Use when your program is impossible to embed as a python module
    - Say, when using keras machine vision running in a docker
    - Your program must conform to a certain base class, see:
    
      ::
      
        valkka_live/valkka/mvision/example_process1.py
    

Each machine vision module appears as its own directory (the plugin scheme is indicated as well):

::

    valkka-live/valkka/mvision/
    
        movement/           simple movement detector [1]
        nix/                demo detector [2]
        alpr/               OpenALPR [1]

You can create your own by copying any of the directories to a different name.  Then, study and edit the file *base.py* in that directory.  After that, you still have to register the module into:

::

    valkka-live/valkka/mvision/__init__.py


Before deploying your machine vision routine, you can test within the module file like this:

::

    cd valkka-live/valkka/mvision/movement
    python3 base.py N
    
where *N* is the test number.  Test number 5 lets you to test the machine vision module with video files (see each *base.py* for more information).
    
Before taking a detailed look into the provided modules, keep in mind that the scheme used here for passing frames among processes with POSIX shared memory and semaphores is ok if you need around 1 frame per second. 

This is sufficient for many applications.  However, if you want more serious a thing, say, 25 fps video analysis at higher resolution, you should implement your stuff at the cpp level.  And only after that interface to Valkka (`this  <https://github.com/elsampsa/valkka-cpp-examples>`_ could help).

Movement Detector
-----------------

This is an extremely simple demo, using OpenCV.  It reports when there is movement.  A good basis for using your own, OpenCV based module.  

This module needs OpenCV installed.  See `here <https://elsampsa.github.io/valkka-examples/_build/html/requirements.html#opencv>`_.


Nix
---

Demonstrates how to send frames to an external process.  

Files are sent to a file in the "/tmp" directory, reading and writing frames is synchronized using communication through stdin and stdout.


OpenALPR
--------

`OpenALPR <https://www.openalpr.com>`_ is a popular OpenSource library for automatic license plate recognition.  We provide a bridge to it.

First of all **DO NOT** install the freemium OpenSource version available at the `github repository <https://github.com/openalpr/openalpr>`_, as its outdated and buggy.  Instead, install the commercial version as instructed `here <http://doc.openalpr.com/sdk.html>`_, i.e. like this:

::

    bash <(curl -s https://deb.openalpr.com/install)
    
You will also need a license key which you can get from here `here <https://www.openalpr.com/on-premises.html>`_.  Place the key you obtain from the OpenALPR folks into

::

    /etc/openalpr/license.conf

Confirm that OpenALPR works with:

::

    alpr -c eu photo_of_your_car.jpg

In order to make this work with python, you still have to do this:

::

    echo 'deb https://deb.openalpr.com/bionic/ bionic main' | sudo tee /etc/apt/sources.list.d/openalpr.list
    sudo apt-get update
    sudo apt-get install python3-openalpr

(as for some reason that script provided by openalpr unsubscribes your from their repository)

Confirm that the python bindings work with

::
    
    ipython3
    from openalpr import Alpr

That's it!  Now "License Plate Recognition" should appear under "Machine Vision" in Valkka Live
    

.. Matlab
.. ------
.. As you might know, Matlab can be bridged to python, and from there into Valkka Live machine vision  
.. This way you will get instantly lots of goodies, say a state-of-the-art neural-network facial recognition.  Now, how cool is that..!?


More
----

*coming soon*


.. Commercial Modules
.. ==================
.. - Simultaneous synchronized recording of several ip cameras
.. - Audio
