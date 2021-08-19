.. valkka_live documentation master file, created by
   sphinx-quickstart on Mon Mar 20 16:31:00 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Valkka Live
===========

   
.. meta::
   :description: A python video surveillance program
   :keywords: opensource, python, video surveillance, video management, video analysis, machine vision, qt

.. raw:: html

    <style> .myright {font-size: 10pt; text-align: right;} </style>

.. rst-class:: myright

    *Screenshot : Valkka Live running on Ubuntu 18 with Yolo object detection*
   
.. image:: images/screenshot_1.png
    :width: 100 %

.. https://www.labnol.org/internet/embed-google-photos-in-website/29194/
.. raw: html
.. <img src="demo1.png" lowsrc="demo1_lowres.png", width="200">
.. <a href='https://photos.google.com/share/AF1QipMcrbBZ8R8isnglrqBUMWj7mtVQeU0ZA-kgfDO9WmAMu0BSArdPcej9ddgQ6IcYcA?key=R2tRRVA5ZTZ1THJWZFhBWE9MQ1d2SElJR0h0Z1hn&source=ctrlq.org'><img src='https://lh3.googleusercontent.com/fd9hK8vFgSnfkz1ZbBaMp5EJD2hdsd6-7j-Q8f1CyxAY3gidyPDTvnTasUNx3e9xOsJzVRx6MKyX2kyqhYhEVeU39XKCLbtTbuIKF_TwfRGGBW8sUtPNFG-U6QHhWIhiDqWDyGq3Lw=w2400' /></a>
    
Valkka Live is an OpenSource video surveillance and management program for Linux 

Some highlights of Valkka Live
------------------------------

- Written in Python3 -  hack the code, add your own machine vision modules as plug-ins
- Create custom graphical interfaces with Python3 and Qt
- Works with stock OnVif compliant IP cameras
- Designed for massive video streaming - view and analyze simultaneously a large number of IP cameras
- Streams are decoded once and only once: same stream can be passed to several machine vision routines without extra overhead

Valkka Live is based on the `valkka library <https://elsampsa.github.io/valkka-examples/>`_.

For hardware and driver requirements, see `here <https://elsampsa.github.io/valkka-examples/_build/html/hardware.html>`_.

What can you do with Valkka Live?
---------------------------------

Consider the following:

- You have tons of ip cameras
- You have all kinds of cool machine vision routines, which you have written in OpenCV and Tensorflow
- Now you want to create a production-grade software with a slick Qt interface, superb image quality and possibility for the user to interact and define parameters for your machine vision routines (say, define line crossing, zone intrusion, etc.)
- You also want to record events and evoke alerts in the user interface

For a typical user-case, imagine a control room with a large amount of ip cameras, running machine vision for a facility of any kind (manufacturing, airport, etc.)

Hacking Valkka Live, you can create such deployments even on a single GPU-equipped laptop

.. _quickstart:

Quickstart
----------

.. TODO: install through pypi is a must .. people are not going to bother in writing long command lines
.. move git installs into requirements.rst
.. Install with
.. pypi sucks
.. pip3 install --user --upgrade valkka-live

We'll be installing directly from github, so git is required:

::

    sudo apt-get install git python3-pip python3-opencv v4l-utils

After that, install (and in the future, update) with:

::

    pip3 install --user --upgrade git+git://github.com/elsampsa/valkka-live.git    
    install-valkka-core
    valkka-tune

(the first script installs valkka-core modules, the second one tunes the maximum socket buffer sizes).
    
In the case that *install-valkka-core* etc. scripts refuse to work, you must fix your path with

::
    
    export PATH=$PATH:$HOME/.local/bin

Finally, run with
    
::

    valkka-live

To run with the experimental (and non-stable) playback & recording features, run with:

::

    valkka-live --playback=true 


Contents:

.. toctree::
   :maxdepth: 3

   requirements
   manual
   faq
   modules
   license
   authors
   

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

