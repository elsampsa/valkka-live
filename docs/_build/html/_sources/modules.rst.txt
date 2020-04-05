   
Modules
*******

Machine Vision
==============

*Warning: version 0.12.0 has seen a major revision and reorganization in the multiprocessing architecture*

Once Valkka has decoded a frame from a certain camera, that decoded frame can be dumped to screen (to hundred windows if necessary) and passed to machine vision routines.  There is no overhead, as the stream from a certain camera is decoded only once.

Decoded frames can be pushed to machine vision routines that are programmed at the python level.  You can easily construct your own too.  At the moment, there are two schemes of plugging-in a python machine vision module.

**1. Using a python multiprocess.**  Communication with the python multiprocess is done by passing frames through shared memory from the Valkka main process.

    - Use this always when you can embed your routine as a python module
    - Typical use-case: OpenCV

**2. Using an external python program.**  Frames are passed to the external program through the filesystem.  Other communication is done through stdin and stdout.

    - Use when your program is impossible to embed as a python module
    - Your program must conform to a certain base class, see:
    
      ::
      
        valkka_live/valkka/mvision/example_process1.py

Each machine vision module appears as its own directory (the plugin scheme is indicated as well):

::

    valkka-live/valkka/mvision/
    
        movement/           simple movement detector
        nix/                demo detector, using an external python program
        yolo3/              Yolo v3 object detection
        yolo3tiny/          Yolo v3 Tiny object detection
        yolo2/              Yolo v2 object detection

        yolo3client/        Yolo client process, using a common master process
        yolo3master/        Yolo v3 Tiny object detection, for multiple client using a common master process


        
You can create your own by copying any of the directories to a different name.  Then, study and edit the file *base.py* in that directory.  After that, you still have to register the module into:

::

    valkka-live/valkka/mvision/__init__.py


Before deploying your machine vision routine, you can test within the module file like this:

::

    cd valkka-live/valkka/mvision/movement
    python3 base.py N
    
where *N* is the test number.  Test number 4 in particular, lets you to test the machine vision module with video files (see each *base.py* for more information).
    
Machine Vision Examples
=======================

Movement Detector
-----------------

This is an extremely simple demo, using OpenCV.  It reports when there is movement.  A good basis for using your own, OpenCV based module.  

This module needs OpenCV installed.  See `here <https://elsampsa.github.io/valkka-examples/_build/html/requirements.html#opencv>`_.

This one also demonstrates how to communicate machine vision parameters to your machine vision multiprocess: click on the "Define Analyzer" button, and you'll see what is going on with the analysis

By clicking on the appearing window, you can define a line and a normal direction for line-crossing.  The parameters are communicated to the multiprocess.  This is just to demo the process of sending parameters to your machine vision module / multiprocess (does nothing else).



Nix
---

Demonstrates how to send frames to an external process.  

Files are sent to a file in the "/tmp" directory, reading and writing frames is synchronized using communication through stdin and stdout.
    
Yolo Object Detection
---------------------

Once you have installed and tested `our Darknet python bindings <https://github.com/elsampsa/darknet-python>`_, the Yolo 3 object detector will appear in the Machine Vision plug-in menu.

Several Yolo versions are provided:

- Yolo v3 is the best, but a bit heavy.  You'll need a hefty GPU with 2.4 GB of GPU memory
- Yolo v2 is almost as good as Yolo v3, but needs less memory on the GPU
- Yolo v3 Tiny works on the CPU as well and on a regular i7 laptop (if you don't abuse the framerate)

You also have the option to use a single yolo instance (neural net) for several machine vision clients:

- Say, you have 3 yolo clients, each running zone intrusion analytics with object labels and boxes from yolo together with some heuristics, processing 10 fps
- Each one of those clients is feeding images to a common yolo master process that is capable of handling 30 fps
- Each client receives textual information (labels and boxes) from the common master process

All of this is orchestrated under-the-hood using libValkka multiprocessing servers and clients

Creating Packages
=================

You can create your own packages with machine vision modules using namespaces starting with *valkka.mvision*.  

If you create, a namespace package to, say, namespace *valkka.mvision_myown*, and use the same conventions (directories, classnames, etc.) explained above for *valkka.mvision*, they will appear automagically in Valkka Live's *Machine Vision* menus.

For creating namespace modules under *valkka.*, refer `here <https://github.com/elsampsa/valkka-skeleton>`_

.. Commercial Modules
.. ==================
.. - Simultaneous synchronized recording of several ip cameras
.. - Audio
