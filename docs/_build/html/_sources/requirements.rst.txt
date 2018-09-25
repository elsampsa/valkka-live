
.. _started:

Getting started
===============


System requirements
-------------------

- A modern Linux distro
- Nvidia or Intel graphics card (ATI has not been tested)
- A graphics card driver supporting OpenGL 3+
- An up-to-date valkka-core library
    
    - For Ubuntu-based distros, an automatic installation is provided
    - If you need to compile from source, refer to `valkka-examples <https://elsampsa.github.io/valkka-examples/_build/html/index.html>`_


Installing
----------

Install with

::

    sudo pip3 install valkka-live
    install-valkka-core
    
*install-valkka-core* is a script that subscribes you to a PPA repository and installs valkka-core binary packages.
    
Run with
    
::

    valkka-live

    
Development version
-------------------

Install development version like this:

::

    git clone https://github.com/elsampsa/valkka-live.git
    cd valkka-live
    git checkout dev
    pip3 install --user -e .


.. If the scripts don't run, remember that pip3 installs scripts (*install-valkka-core* and *valkka-live*) under *$HOME/local/bin*.  See that this directory is on your $PATH.


.. TODO
.. System tuning
.. -------------

.. To understand bottlenecks in high-throughput video streaming, please read the *Common problems* chapter in `valkka-examples page <https://elsampsa.github.io/valkka-examples/_build/html/index.html>`_

.. To augment the socket buffers, run
.. valkka-live-system-tune
.. This will modify your */etc/sysctl.conf* file automatically.

