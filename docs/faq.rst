
FAQ 
===

Discarding late frame
---------------------

One of the typical error messages you might find in the terminal, 
please read about them from `here <file:///home/sampsa/python3_packages/valkka_examples/docs/_build/html/pitfalls.html>`_

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
