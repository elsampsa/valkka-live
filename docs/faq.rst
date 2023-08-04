
FAQ 
===

Could not load the Qt platform plugin "xcb"
-------------------------------------------

If you get this error:

::

    qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.

Then you are *not* running valkka-live directly in a desktop, but from remote etc. connection (or in docker, etc. "headless" environment).

It has really nothing to do with libValkka or valkka-live.  In fact, *none* of your Qt and KDE-based desktop programs would work at all.  Check with this command:

::

    echo $XDG_SESSION_TYPE

and make sure that it reports the value `x11`.

If the error persists, you're desktop environment might have missing or broken Qt/KDE dependencies.  Install the whole KDE and Qt stack with:

::

    sudo apt-get install kate

(this pulls a minimal KDE + Qt installation as dependencies of the Kate editor)


If this error *still* persists and is reported by python's cv2 module, you have a broken cv2 version, so uninstall cv2 with:

::

    pip3 uninstall opencv-python
    sudo pip3 uninstall opencv-python # just in case!

And install your linux distro's default opencv instead with:

::

    sudo apt-get install python3-opencv


Discarding late frame
---------------------

One of the typical error messages you might find in the terminal, 
please read about them from `here <https://elsampsa.github.io/valkka-examples/_build/html/pitfalls.html>`_

2K and 4K cameras
-----------------

*I have benchmarked Valkka against an expensive commercial program.  The other program is capable of showing 20 live 2K cameras on the screen using a cheap laptop.*

That commercial program is not streaming at 2K resolution.  Instead, it requests the so-called "substream" from those cameras which is typically 720p or less.

If you want to benchmark against Valkka, you must use the substream address instead.

The substream address depends on the manufacturer.  For HIK, mainstream and substream addresses are typically (might vary, depending on the camera model):

::

    main stream : rtsp://user:password@ip_address
    sub stream  : rtsp://user:password@ip_address/Streaming/Channels/102

    
in Valkka Live camera config menu, you should then use *Streaming/Channels/102* at the *Tail* field
