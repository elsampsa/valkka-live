"""
multiprocess.py : multiprocess / Qt intercommunication through pipes and signals

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the machine vision plugin for the Valkka Live program

This plugin is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    multiprocess.py
@author  Sampsa Riikonen
@date    2018
@version 0.13.0 
@brief   multiprocess / Qt intercommunication through pipes and signals
"""

# from PyQt5 import QtWidgets, QtCore, QtGui # Qt5
from PySide2 import QtWidgets, QtCore, QtGui
import sys
import time
import logging

from valkka.api2 import ValkkaProcess, Namespace, ShmemRGBClient, ShmemRGBServer
from valkka.api2.tools import *
from valkka.live.multiprocess import MessageObject, safe_select, QMultiProcess
from valkka.live import singleton as live_singleton
from valkka.mvision import singleton as mvision_singleton


logger = getLogger(__name__)


"""

::

    QShmemProcess.activate => QShmemProcess.c__activate  [activates shmem ringbuffer client]

    QShmem.setMasterProcess => QShmem.c__setMasterProcess [activates shmem ringbuffer server]


::

    QShmemProcess
        QShmemMasterProcess
        QShmemClientProcess
            MVisionClientBaseProcess
        MVisionBaseProcess




A signal --> slot walkthrough:

::

    
    valkka/live/container/video.py:

    VideoContainer
        
        - Organizes / encapsulates QWidgets & QSignals
        - Encapsulates a VideoWidget that handles drag'n'drop
          and showing of video using X11 window mappings to OpenGL
         
    valkka/live/container/mvision.py:

    MVisionClientContainer(VideoContainer)

        Drag'n'dropping video into this container's VideoWidget,
        launches method setDevice
        => shmem server at the cpp side, by calling valkka/live/chain/multifork.py: getShmem
        (which creates the server)
        => then calls self.activate
        => calls self.mvision_process.activate, which is a QShmemClientProcess
        frontend method
        => calls c__activate in the backend
        => establishes an shmem client that listens to the shmem channel
        
        => calls QShmemClientProcesses' setMasterProcess
        => goes to backend c__setMasterProcess, which establishes an shmem
        server at the python side

        Once that is done, call master processes "registerClient" method
        => master process establishes ShmemRGBClient to listen for client's
        RGBShmem server

        Other things:

        - Creates a floating AnalyzerWidget that appears only
        when analyzer is defined
        - ..when that happens, call self.analyzer_widget.activate




"""

class QShmemProcess(QMultiProcess):
    """A multiprocess with Qt signals and reading RGB images from shared memory.  Shared memory client is instantiated on demand (by calling activate)
    """
    timeout = 1.0

    class Signals(QtCore.QObject):
        pong = QtCore.Signal(object) # demo outgoing signal

    # **** define here backend methods that correspond to incoming slots
    # **** 

    def c__ping(self, message = ""):
        print("c__ping:", message)
        self.send_out__(MessageObject("pong", lis = [1,2,3]))


    def c__activate(self, 
        n_buffer:int = None, 
        image_dimensions:tuple = None, 
        shmem_name:str = None):
    
        # if not defined, use default values
        # if n_buffer is None: n_buffer = self.n_buffer
        # if image_dimensions is None: image_dimensions = self.image_dimensions
        # if shmem_name is None: shmem_name = self.shmem_name

        self.logger.debug("c__activate")
        self.listening = True
        # self.image_dimensions = image_dimensions
        self.client = ShmemRGBClient(
            name            =shmem_name,
            n_ringbuffer    =n_buffer,   # size of ring buffer
            width           =image_dimensions[0],
            height          =image_dimensions[1],
            # client timeouts if nothing has been received in 1000 milliseconds
            mstimeout   =int(self.timeout*1000),
            verbose     =self.shmem_verbose
            )

        self.shmem_name = shmem_name
        self.n_buffer = n_buffer
        self.image_dimensions = image_dimensions
        
        self.postActivate_()
        

    def c__deactivate(self):
        """Init shmem variables to None
        """
        self.logger.debug("c__deactivate")
        # print("c__deactivate")
        self.preDeactivate_()
        self.listening = False
        # self.image_dimensions = None
        self.client = None # shared memory client was created when activate was called
    # ****

    parameter_defs = {
        # "n_buffer"          : (int, 10),
        # "image_dimensions"  : (tuple, (1920//4, 1080//4)),
        # "image_dimensions"  : tuple,
        "shmem_verbose"     : (bool, False),
        # "shmem_name"        : None
        }

    def __init__(self, name = "QShmemProcess", **kwargs):
        super().__init__(name)
        parameterInitCheck(QShmemProcess.parameter_defs, kwargs, self)
        """
        if self.shmem_name is None:
            self.shmem_name = "valkkashmemclient"+str(id(self))
        else:
            assert(isinstance(self.shmem_name, str))
        self.shmem_name_default = self.shmem_name
        """


    def preRun_(self):
        self.logger.debug("preRun_")
        self.c__deactivate() # init variables
        

    def postRun_(self):
        """Clear shmem variables
        """
        self.c__deactivate()

        
    def resetState_(self):
        pass


    def run(self):
        self.preRun_()

        while self.loop:
            if self.listening:
                self.cycle_()
                self.readPipes__(timeout = 0) # timeout = 0 == just poll
            else:
                self.readPipes__(timeout = self.timeout) # timeout of 1 sec

        self.postRun_()
        # indicate front end qt thread to exit
        self.back_pipe.send(None)
        self.logger.debug("bye!")


    def cycle_(self):
        """Receives frames from the shmem client and does something with them

        Typically launch qt signals
        """
        index, meta = self.client.pullFrame()
        if (index is None):
            self.logger.debug("Client timed out..")
            return
        
        self.logger.debug("Client index = %s", index)
        if meta.size < 1:
            return

        data = self.client.shmem_list[index][0:meta.size]
        img = data.reshape(
            (meta.height, meta.width, 3))
        """ # WARNING: the x-server doesn't like this, i.e., we're creating a window from a separate python multiprocess, so the program will crash
        print(self.pre,"Visualizing with OpenCV")
        cv2.imshow("openCV_window",img)
        cv2.waitKey(1)
        """
        self.logger.debug("got frame %s", img.shape)
        # res=self.analyzer(img) # does something .. returns something ..


    def postActivate_(self):
        """Whatever you need to do after creating the shmem client.  Overwrite in child classes
        """
        pass


    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client.  Overwrite in child classes
        """
        pass
    

    # *** frontend ***

    def activate(self, **kwargs):
        # save values to front-end also:
        self.shmem_name = kwargs["shmem_name"]
        self.n_buffer = kwargs["n_buffer"]
        self.image_dimensions = kwargs["image_dimensions"]
        # this sets the values at back-end:
        self.sendMessageToBack(MessageObject(
            "activate", **kwargs))


    def deactivate(self):
        self.sendMessageToBack(MessageObject(
            "deactivate"))


    def ping(self, message = ""):
        """Test call
        """
        self.sendMessageToBack(MessageObject("ping", message = message))



class QShmemMasterProcess(QShmemProcess):

    max_clients = 999 # how many clients can register to this master process
    
    class Client:
        def __init__(self, fd = None, pipe = None, shmem_client = None):
            self.fd = fd
            self.pipe = pipe
            self.shmem_client = shmem_client


    def c__registerClient(self,
        n_buffer:int = None, 
        image_dimensions:tuple = None, 
        shmem_name:str = None,
        ipc_index:int = None):
        """Shared mem info is given.  Now we can create the shmem client

        There can be several shmem clients
        """
        self.logger.debug("c__registerClient")

        event_fd, pipe = mvision_singleton.ipc.get2(ipc_index)
        mvision_singleton.ipc.wait(ipc_index) # wait till the shmem server has been created
        # this flag is controlled by QShmemClientProcess.c__setMasterProcess
        mvision_singleton.ipc.clear(ipc_index)
        shmem_client = ShmemRGBClient(
                name            =shmem_name,
                n_ringbuffer    =n_buffer,   # size of ring buffer
                width           =image_dimensions[0],
                height          =image_dimensions[1],
                # client timeouts if nothing has been received in 1000 milliseconds
                mstimeout   =1000,
                verbose     =False
                )
        shmem_client.useEventFd(event_fd)

        fd = event_fd.getFd()

        client = self.Client(
            fd = fd,
            pipe = pipe,
            shmem_client = shmem_client
            )

        self.clients[ipc_index] = client
        self.clients_by_fd[fd] = client
        self.logger.debug("c__registerClient: fd=%s", fd)
        self.rlis.append(fd)

        if len(self.clients) == 1:
            self.logger.debug("c__registerClient: first client registered")
            self.firstClientRegistered_()

        self.logger.debug("c__registerClient: number of clients is %s", len(self.clients))


    def c__unregisterClient(self, ipc_index = None):
        client = self.clients.pop(ipc_index)
        self.clients_by_fd.pop(client.fd)
        self.rlis.remove(client.fd)
        client.pipe.send(None)
        if len(self.clients) == 0:
            self.logger.debug("c__unregisterClient: last client unregistered")
            self.lastClientUnregistered_()


    parameter_defs = {
        }


    def __init__(self, name = "QShmemMasterProcess", **kwargs):
        super().__init__(name)
        parameterInitCheck(QShmemMasterProcess.parameter_defs, kwargs, self)
        self.n_clients = 0 # a front-end variable


    def preRun_(self):
        self.logger.debug("preRun_")
        self.clients = {}
        self.clients_by_fd = {}
        self.rlis = [self.back_pipe]


    def postRun_(self):
        """Clear shmem variables
        """
        self.clients = {}
        self.lastClientUnregistered_()


    def firstClientRegistered_(self):
        pass

    def lastClientUnregistered_(self):
        pass
    

    def run(self):
        self.preRun_()

        while self.loop:
            self.logger.debug("run: select %s", self.rlis)
            rlis, wlis, elis = safe_select(self.rlis, [], [], timeout = self.timeout)
            self.logger.debug("run: select done %s", rlis)

            if self.back_pipe in rlis:
                rlis.remove(self.back_pipe)
                obj = self.back_pipe.recv()
                self.routeMainPipe__(obj)

            for fd in rlis:
                self.logger.debug("run: handling %s", fd)
                # an fd removed from clients_by_fd might still be in rlis... routeMainPipe__ => c__unregisterClient => clients_by_fd modified
                try:
                    client = self.clients_by_fd[fd]
                except KeyError:
                    pass
                else:
                    reply = self.handleFrame_(client.shmem_client)
                    client.pipe.send(reply)

        self.postRun_()
        # indicate front end qt thread to exit
        self.back_pipe.send(None)
        self.logger.debug("run: bye!")


    def handleFrame_(self, shmem_client):
        """Receives frames from the shmem client.  Reply with results
        """
        index, meta = shmem_client.pullFrame()
        if meta.size < 1:
            return None
        return "kokkelis"
        

    def postActivate_(self):
        """Whatever you need to do after creating the shmem client.  Overwrite in child classes
        """
        pass


    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client.  Overwrite in child classes
        """
        pass
    


    # *** frontend ***

    def registerClient(self, **kwargs):
        # keep the books on number of clients at frontend as well
        self.n_clients += 1
        if self.n_clients > self.max_clients:
            self.logger.warning("no more clients available: max is %s", self.max_clients)
            self.n_clients = self.max_clients
            return
        self.sendMessageToBack(MessageObject(
            "registerClient", **kwargs))
        self.logger.debug("registerClient: frontend: number of clients is %s", self.n_clients)


    def unregisterClient(self, **kwargs):
        self.n_clients -= 1
        if self.n_clients < 1:
            self.n_clients = 0
        self.sendMessageToBack(MessageObject(
            "unregisterClient", **kwargs))
        self.logger.debug("unregisterClient: frontend: number of clients is %s", self.n_clients)



    def available(self):
        """Has available space for clients or not
        """
        return self.n_clients < self.max_clients



class QShmemClientProcess(QShmemProcess):
    """Like QShmemProcess, but uses a common master process
    """

    """
    def c__setMasterProcess(self, 
            ipc_index = None,
            n_buffer = None,
            image_dimensions = None,
            shmem_name = None):
    """
    def c__setMasterProcess(self, ipc_index = None):
        # get shmem parameters from master process frontend
        self.ipc_index = ipc_index
        self.eventfd, self.master_pipe = mvision_singleton.ipc.get1(self.ipc_index)
        # self.n_buffer etc. have been set by a call to c__activate
        self.server = ShmemRGBServer(
            name            =self.shmem_name_server,
            n_ringbuffer    =self.n_buffer,   # size of ring buffer
            width           =self.image_dimensions[0],
            height          =self.image_dimensions[1],
            verbose         =self.shmem_verbose
            )        
        self.server.useEventFd(self.eventfd) # activate eventfd API
        mvision_singleton.ipc.set(ipc_index)


    def c__unsetMasterProcess(self):
        # mvision_singleton.ipc.release(self.ipc_index) # not here
        self.server = None
        self.master_pipe = None
        self.eventfd = None

    # ****

    def __init__(self, name = "QShmemClientProcess", **kwargs):
        super().__init__(name = name, **kwargs)
        self.shmem_name_server = live_singleton.sema_uuid + "_shmemserver_" + str(id(self))
        # parameterInitCheck(QShmemClientProcess.parameter_defs, kwargs, self)
        self.ipc_index = None # used at the frontend
        self.master_process = None
        
        
    def preRun_(self):
        self.logger.debug("preRun_")
        self.c__deactivate() # init variables
        self.c__unsetMasterProcess()

    def postRun_(self):
        """Clear shmem variables
        """
        self.c__deactivate()
        self.c__unsetMasterProcess()

        
    def run(self):
        self.preRun_()
        while self.loop:
            if self.listening:
                self.cycle_()
                self.readPipes__(timeout = 0) # timeout = 0 == just poll
            else:
                self.readPipes__(timeout = self.timeout) # timeout of 1 sec

            # print("QShmemClientProcess: alive")

        self.postRun_()
        # indicate front end qt thread to exit
        self.back_pipe.send(None)
        self.logger.debug("bye!")


    def cycle_(self):
        """Receives frame from the shmem client and sends them for further
        processing to a master process
        """
        # get rgb frame from the filterchain
        index, meta = self.client.pullFrame()
        if (index is None):
            self.logger.debug("Client timed out..")
            return
        
        self.logger.debug("Client index, size = %s", index)
        data = self.client.shmem_list[index][0:meta.size]
        img = data.reshape(
            (meta.height, meta.width, 3))
        # forward rgb frame to master process (yolo etc.)
        self.logger.debug("cycle_: got frame %s", img.shape)

        if self.server is not None:
            self.logger.debug("cycle_ : pushing to server")
            self.server.pushFrame(
                img,
                meta.slot,
                meta.mstimestamp
            )
            # receive results from master process
            message = self.master_pipe.recv()
            print("reply from master process:", message)


    # *** frontend ***

    def setMasterProcess(self, master_process = None):
        # ipc_index, n_buffer, image_dimensions, shmem_name # TODO
        self.master_process = master_process
        self.ipc_index = mvision_singleton.ipc.reserve()

        # first, create the server
        self.sendMessageToBack(MessageObject(
            "setMasterProcess", 
            ipc_index = self.ipc_index))

        # this will create the client:
        # self.n_buffer etc. have been set by call to self.activate
        master_process.registerClient(
            ipc_index = self.ipc_index,
            n_buffer = self.n_buffer,
            image_dimensions = self.image_dimensions,
            shmem_name = self.shmem_name_server)
        

    def unsetMasterProcess(self): # , master_process):
        if self.master_process is None:
            self.logger.warning("unsetMasterProcess: none set")
            return

        self.sendMessageToBack(MessageObject(
            "unsetMasterProcess"
        ))
        self.master_process.unregisterClient(
            ipc_index = self.ipc_index
        )
        mvision_singleton.ipc.release(self.ipc_index)
        self.ipc_index = None
        self.master_process = None


    def requestStop(self):
        self.unsetMasterProcess()
        super().requestStop()
    

    def deactivate(self):
        self.unsetMasterProcess()
        super().deactivate()



    """
    def activate(self, **kwargs):
        self.sendMessageToBack(MessageObject(
            "activate", **kwargs))
                
    def deactivate(self):
        self.sendMessageToBack(MessageObject(
            "deactivate"))
        
    def ping(self, message = ""):
        #Test call
        self.sendMessageToBack(MessageObject("ping", message = message))
    """


class MVisionBaseProcess(QShmemProcess):
    """Mvision process without a common master process
    """

    class Signals(QtCore.QObject):
        pong = QtCore.Signal(object) # demo outgoing signal
        shmem_server = QtCore.Signal(object) # launched when the mvision process has established a shared mem server


    def __init__(self, **kwargs):
        self.parameters = None
        self.parameters_changed = False
        self.qt_server = None
        super().__init__(**kwargs)


    # *** common back-end methods for machine vision processes ***

    def c__updateAnalyzerParameters(self, **kwargs):
        self.logger.debug("backend: got analyzer parameters %s", kwargs)
        self.parameters = kwargs # update parameters at the backend
        self.parameters_changed = True

    def c__resetAnalyzerState(self, **kwargs):
        self.logger.info("backend: reset analyzer state")
        self.resetState_()
        self.parameters_changed = True

    def c__requestQtShmemServer(self, **kwargs):
        self.logger.debug("shmem server requested")
        # should be called only after the shmem client has been instantiated
        self.shmem_name_qt_server = self.shmem_name + "_qt_server"
        self.qt_server = ShmemRGBServer(
            name            =self.shmem_name_qt_server,
            n_ringbuffer    =self.n_buffer,   # size of ring buffer
            width           =self.image_dimensions[0],
            height          =self.image_dimensions[1],
            verbose         =self.shmem_verbose
            )
        # inform frontend & widgets that the shmem server is available:
        self.send_out__(MessageObject("shmem_server",  # this is routed to the qt signal with the same name
            shmem_name      =self.shmem_name_qt_server, 
            shmem_n_buffer  =self.n_buffer, 
            width           =self.image_dimensions[0],
            height          =self.image_dimensions[1],
            verbose         =self.shmem_verbose
        ))


    def c__releaseQtShmemServer(self, **kwargs):
        self.logger.debug("shmem server released")
        self.qt_server = None


    def postActivate_(self):
        """Whatever you need to do after creating the shmem client:

        - Create a shmem server for visualizing the machine vision process
        """
        pass

    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client
        """
        self.qt_server = None
        pass

    
    # *** common frontend methods for machine vision processes ***

    def connectAnalyzerWidget(self, analyzer_widget):
        analyzer_widget.video.signals.update_analyzer_parameters.connect(
            self.updateAnalyzerParameters)
        print("connectAnalyzerWidget: signals:", self.signals)
        self.signals.shmem_server.connect(
            analyzer_widget.setShmem_slot
        )
        analyzer_widget.signals.show.connect(
            self.requestQtShmemServer
        )
        analyzer_widget.signals.close.connect(
            self.releaseQtShmemServer
        )
        
    def resetAnalyzerState(self):
        print(">resetAnalyzerState")
        self.sendMessageToBack(MessageObject(
            "resetAnalyzerState", **{}))

    def disconnectAnalyzerWidget(self, analyzer_widget):
        analyzer_widget.video.signals.update_analyzer_parameters.disconnect(
            self.updateAnalyzerParameters)
        self.signals.shmem_server.disconnect(
            analyzer_widget.setShmem_slot
        )
        analyzer_widget.signals.show.disconnect(
            self.requestQtShmemServer
        )
        analyzer_widget.signals.close.disconnect(
            self.releaseQtShmemServer
        )



    # *** create a widget for this machine vision module ***
    def getWidget(self):
        """Some ideas for your widget:
        - Textual information (alert, license place number)
        - Check boxes : if checked, send e-mail to your mom when the analyzer spots something
        - .. or send an sms to yourself
        - You can include the cv2.imshow window to the widget to see how the analyzer proceeds
        """
        widget = QtWidgets.QLabel("nada de nada")
        # widget.setStyleSheet(style.detector_test)
        #self.signals.start_move.connect(lambda : widget.setText("MOVEMENT START"))
        #self.signals.stop_move. connect(lambda : widget.setText("MOVEMENT STOP"))
        return widget

    def getAnalyzerParameters(self):
        return self.parameters

    def updateAnalyzerParameters(self, kwargs):
        self.parameters = kwargs
        self.logger.debug("updateAnalyzerParameters %s", kwargs)
        self.sendMessageToBack(MessageObject(
            "updateAnalyzerParameters", **kwargs))

    def requestQtShmemServer(self):
        kwargs = {}
        self.sendMessageToBack(MessageObject(
            "requestQtShmemServer", **kwargs))

    def releaseQtShmemServer(self):
        kwargs = {}
        self.sendMessageToBack(MessageObject(
            "releaseQtShmemServer", **kwargs))





class MVisionClientBaseProcess(QShmemClientProcess):
    """Client Analyzer processes that use a common master processs
    """

    class Signals(QtCore.QObject):
        pong = QtCore.Signal(object) # demo outgoing signal
        shmem_server = QtCore.Signal(object) # launched when the mvision process has established a shared mem server

    def __init__(self, **kwargs):
        self.parameters = None
        self.parameters_changed = False
        self.qt_server = None
        super().__init__(**kwargs)

    # *** common back-end methods for machine vision processes ***

    def c__updateAnalyzerParameters(self, **kwargs):
        self.logger.debug("Movement mvision: got analyzer parameters %s", kwargs)
        self.parameters = kwargs # update parameters at the backend
        self.parameters_changed = True


    def c__resetAnalyzerState(self, **kwargs):
        self.logger.info("backend: reset analyzer state")
        self.resetState_()


    def c__requestQtShmemServer(self, **kwargs):
        self.logger.debug("shmem server requested")
        # should be called only after the shmem client has been instantiated
        self.shmem_name_qt_server = self.shmem_name + "_qt_server"
        self.qt_server = ShmemRGBServer(
            name            =self.shmem_name_qt_server,
            n_ringbuffer    =self.n_buffer,   # size of ring buffer
            width           =self.image_dimensions[0],
            height          =self.image_dimensions[1],
            verbose         =self.shmem_verbose
            )
        # inform frontend & widgets that the shmem server is available:
        self.send_out__(MessageObject("shmem_server",  # this is routed to the qt signal with the same name
            shmem_name      =self.shmem_name_qt_server, 
            shmem_n_buffer  =self.n_buffer, 
            width           =self.image_dimensions[0],
            height          =self.image_dimensions[1],
            verbose         =self.shmem_verbose
        ))


    def c__releaseQtShmemServer(self, **kwargs):
        self.logger.debug("shmem server released")
        self.qt_server = None


    def postActivate_(self):
        """Whatever you need to do after creating the shmem client:

        - Create a shmem server for visualizing the machine vision process
        """
        pass

    def preDeactivate_(self):
        """Whatever you need to do prior to deactivating the shmem client
        """
        self.qt_server = None
        pass

    
    def connectAnalyzerWidget(self, analyzer_widget):
        analyzer_widget.video.signals.update_analyzer_parameters.connect(
            self.updateAnalyzerParameters)
        # print("connectAnalyzerWidget: signals:", self.signals)
        self.signals.shmem_server.connect(
            analyzer_widget.setShmem_slot
        )
        analyzer_widget.signals.show.connect(
            self.requestQtShmemServer
        )
        analyzer_widget.signals.close.connect(
            self.releaseQtShmemServer
        )

    def resetAnalyzerState(self):
        print(">resetAnalyzerState")
        self.sendMessageToBack(MessageObject(
            "resetAnalyzerState", **{}))
        
    def disconnectAnalyzerWidget(self, analyzer_widget):
        analyzer_widget.video.signals.update_analyzer_parameters.disconnect(
            self.updateAnalyzerParameters)
        self.signals.shmem_server.disconnect(
            analyzer_widget.setShmem_slot
        )
        analyzer_widget.signals.show.disconnect(
            self.requestQtShmemServer
        )
        analyzer_widget.signals.close.disconnect(
            self.releaseQtShmemServer
        )
        

    # *** common frontend methods for machine vision processes ***


    # *** create a widget for this machine vision module ***
    def getWidget(self):
        """Some ideas for your widget:
        - Textual information (alert, license place number)
        - Check boxes : if checked, send e-mail to your mom when the analyzer spots something
        - .. or send an sms to yourself
        - You can include the cv2.imshow window to the widget to see how the analyzer proceeds
        """
        widget = QtWidgets.QLabel("nada de nada")
        # widget.setStyleSheet(style.detector_test)
        #self.signals.start_move.connect(lambda : widget.setText("MOVEMENT START"))
        #self.signals.stop_move. connect(lambda : widget.setText("MOVEMENT STOP"))
        return widget


    def updateAnalyzerParameters(self, kwargs):
        self.parameters = kwargs
        self.logger.debug("updateAnalyzerParameters %s", kwargs)
        self.sendMessageToBack(MessageObject(
            "updateAnalyzerParameters", **kwargs))

    def getAnalyzerParameters(self):
        return self.parameters

    def requestQtShmemServer(self):
        kwargs = {}
        self.sendMessageToBack(MessageObject(
            "requestQtShmemServer", **kwargs))

    def releaseQtShmemServer(self):
        kwargs = {}
        self.sendMessageToBack(MessageObject(
            "releaseQtShmemServer", **kwargs))



def test_process(mvision_process_class):
    import time
    p = mvision_process_class()
    p.go()
    time.sleep(5)
    p.stop()
    

def test_with_file(
        mvision_process_class,
        mvision_class_names = ["valkka.mvision"],
        shmem_image_interval = 1000,
        shmem_image_dimensions  =(1920 // 2, 1080 // 2),
        init_filename = None
        ):
    """Test the analyzer process with files

    :param mvision_process_class: Which class to test
    :param mvision_class_names: Namespaces to search for required master process classes

    Files must be encoded and muxed correctly, i.e., with:
    
    ::
    
        ffmpeg -i your_video_file -c:v h264 -an outfile.mkv
    
    """
    import time
    from valkka.mvision.file import FileGUI
    from valkka.live import tools


    ps = mvision_process_class()
    mp = None

    if hasattr(ps,"master"):
        # find master process if required .. a bit cumbersome..
        mvision_classes, mvision_client_classes, mvision_master_classes =\
            tools.scanMVisionClasses(
                mvision_class_names
            ) # scans for submodules in namespace valkka.mvision.*
        master_classes_by_tag = {}
        for cl in mvision_master_classes:
            master_classes_by_tag[cl.tag] = cl
        mp = master_classes_by_tag[ps.master]()


    app = QtWidgets.QApplication(["mvision test"])
    fg = FileGUI(
        mvision_process         = ps,
        mvision_master_process  = mp,
        shmem_name              = "test_studio_file",
        shmem_image_dimensions  = shmem_image_dimensions,
        shmem_image_interval    = shmem_image_interval,
        shmem_ringbuffer_size   = 5,
        init_filename           = init_filename
        )
    fg.show()
    app.exec_()
    ps.stop()
    print("bye from app!")
    

class MyGui(QtWidgets.QMainWindow):
    """An example demo GUI
    """
    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.initVars()
        self.setupUi()


    def initVars(self):
        self.process1 = QShmemProcess("process1")
        self.process2 = QShmemProcess("process2")

        self.process1.setDebug()

        self.process1.go()
        self.process2.go()

        
    def setupUi(self):
        self.setGeometry(QtCore.QRect(100, 100, 500, 500))
        self.w = QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)

        self.lay = QtWidgets.QGridLayout(self.w)

        self.button1 = QtWidgets.QPushButton("Button 1", self.w)
        self.button2 = QtWidgets.QPushButton("Button 2", self.w)

        self.check1 = QtWidgets.QRadioButton(self.w)
        self.check2 = QtWidgets.QRadioButton(self.w)

        self.lay.addWidget(self.button1, 0, 0)
        self.lay.addWidget(self.check1, 0, 1)
        self.lay.addWidget(self.button2, 1, 0)
        self.lay.addWidget(self.check2, 1, 1)

        self.button1.clicked.connect(self.button1_slot)
        self.button2.clicked.connect(self.button2_slot)

        self.process1.signals.pong.connect(self.pong1_slot)
        self.process2.signals.pong.connect(self.pong2_slot)

    def button1_slot(self):
        self.process1.ping(message="<sent ping from button1>")
        self.check1.setChecked(True)

    def button2_slot(self):
        self.process2.ping(message="<sent ping from button2>")
        self.check2.setChecked(True)

    def pong1_slot(self, dic = {}):
        print("pong1_slot: dic=", dic)

    def pong2_slot(self, dic = {}):
        print("pong2_slot: dic=", dic)

    def closeEvent(self, e):
        print("closeEvent!")
        self.process1.stop()
        self.process2.stop()
        super().closeEvent(e)


def test1():
    p = QShmemProcess("test", n_buffer=10, image_dimensions=(1920//4, 1080//4))
    p.setDebug()
    p.start()
    time.sleep(5)
    p.activate()
    time.sleep(5)
    p.deactivate()
    time.sleep(5)
    p.activate()
    time.sleep(5)
    p.stop()


def test2():
    import numpy

    shmem_name = "kokkelis"
    n_buffer = 10
    image_dimensions = (400, 300)
    server = ShmemRGBServer(
        name            =shmem_name,
        n_ringbuffer    =n_buffer,   # size of ring buffer
        width           =image_dimensions[0],
        height          =image_dimensions[1],
        verbose         =True
        )

    p = QShmemProcess("test", 
        n_buffer=n_buffer, 
        image_dimensions=image_dimensions, 
        shmem_verbose = True, 
        shmem_name=shmem_name)
    
    p.setDebug()
    p.start()
    p.activate()

    img = numpy.zeros((300, 400, 3), dtype = numpy.uint8)

    for i in range(5):
        img[:,:,:] = i
        server.pushFrame(
            img,
            1,
            123
        )
        time.sleep(0.2)

    p.deactivate()

    for i in range(50):
        img[:,:,:] = i
        server.pushFrame(
            img,
            1,
            123
        )
        # time.sleep(0.2)

    p.activate()

    for i in range(15):
        img[:,:,:] = i
        server.pushFrame(
            img,
            1,
            123
        )
        time.sleep(0.1)

    p.stop()



def test3():
    """One client, one master process
    """
    import numpy

    shmem_name = "kokkelis"
    n_buffer = 10
    image_dimensions = (400, 300)
    server = ShmemRGBServer(
        name            =shmem_name,
        n_ringbuffer    =n_buffer,   # size of ring buffer
        width           =image_dimensions[0],
        height          =image_dimensions[1],
        verbose         =True
        )
    
    p = QShmemClientProcess("test", 
        n_buffer=n_buffer, 
        image_dimensions=image_dimensions, 
        shmem_verbose = True, 
        shmem_name=shmem_name)
    
    p.setDebug()
    p.start()

    pm = QShmemMasterProcess("master_test")
    pm.setDebug()
    pm.start()

    """
    p.activate(n_buffer=n_buffer, 
        image_dimensions=image_dimensions, 
        shmem_name=shmem_name)
    """
    p.activate()

    img = numpy.zeros((300, 400, 3), dtype = numpy.uint8)
    for i in range(10):
        img[:,:,:] = i
        server.pushFrame(
            img,
            1,
            123
        )
        time.sleep(0.1)

    print("\nConnecting master process\n")

    p.setMasterProcess(pm)

    for i in range(10):
        img[:,:,:] = i
        server.pushFrame(
            img,
            1,
            123
        )
        time.sleep(0.1)

    p.unsetMasterProcess(pm)

    p.stop()
    pm.stop()



def test4():
    """Two clients, one master process
    """
    import numpy

    shmem_name1 = "kokkelis1"
    n_buffer1 = 10
    image_dimensions1 = (400, 300)
    server1 = ShmemRGBServer(
        name            =shmem_name1,
        n_ringbuffer    =n_buffer1,   # size of ring buffer
        width           =image_dimensions1[0],
        height          =image_dimensions1[1],
        verbose         =True
        )
    p1 = QShmemClientProcess("test1", 
        n_buffer=n_buffer1, 
        image_dimensions=image_dimensions1, 
        shmem_verbose = True, 
        shmem_name=shmem_name1)
    
    shmem_name2 = "kokkelis2"
    n_buffer2 = 10
    image_dimensions2 = (400, 300)
    server2 = ShmemRGBServer(
        name            =shmem_name2,
        n_ringbuffer    =n_buffer2,   # size of ring buffer
        width           =image_dimensions2[0],
        height          =image_dimensions2[1],
        verbose         =True
        )
    p2 = QShmemClientProcess("test2", 
        n_buffer=n_buffer2, 
        image_dimensions=image_dimensions2, 
        shmem_verbose = True, 
        shmem_name=shmem_name2)
    
    p1.setDebug()
    p1.start()
    p2.setDebug()
    p2.start()
    
    pm = QShmemMasterProcess("master_test")
    pm.setDebug()
    pm.start()
    """
    p.activate(n_buffer=n_buffer, 
        image_dimensions=image_dimensions, 
        shmem_name=shmem_name)
    """
    p1.activate()
    p2.activate()
    
    img = numpy.zeros((300, 400, 3), dtype = numpy.uint8)
    for i in range(10):
        img[:,:,:] = i
        server1.pushFrame(img, 1, 123)
        server2.pushFrame(img, 2, 123)
        time.sleep(0.1)

    print("\nConnecting master process\n")
    p1.setMasterProcess(pm)
    p2.setMasterProcess(pm)
    
    for i in range(10):
        img[:,:,:] = i
        server1.pushFrame(img, 1, 123)
        server2.pushFrame(img, 2, 123)
        time.sleep(0.1)

    p1.unsetMasterProcess(pm)
    p2.unsetMasterProcess(pm)

    p1.stop()
    p2.stop()
    
    pm.stop()


def main():
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    # main()
    # test1()
    # test2()
    # test3()
    test4()
    
