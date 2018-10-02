
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

We'll be installing directly from github, so git is required:

::

    sudo apt-get install git

After that, install (or update) with:

::

    pip3 install --user --upgrade git+git://github.com/elsampsa/valkka-live.git    
    install-valkka-core
    valkka-tune

(the first script installs valkka-core modules, the second one tunes the maxmimum socket buffer sizes)
    
In the case that *install-valkka-core* etc. scripts refuse to work, you must fix your path with

::
    
    export PATH=$PATH:$HOME/.local/bin

Finally, run with
    
::

    valkka-live
    
Before running, you might also want to move as many processes to core 0 as possible with

::

    valkka-move-ps
    
    
    
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

