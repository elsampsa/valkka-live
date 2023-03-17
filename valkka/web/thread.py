"""
thread.py : A QThread for handling onvif connection to an RTSP camera

Copyright 2020 Sampsa Riikonen

Authors: Sampsa Riikonen, ???

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/> 

@file    thread.py
@author  Sampsa Riikonen
@date    2020
@version 1.1.1 
@brief   
"""

import sys
import time
import os, pickle, inspect, subprocess, shlex
from valkka.live.qt.thread import IPCQThread
from valkka.live import singleton
from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot


class WWWQThread(IPCQThread):
    """Starts a pyramid webserver & handles intercom to Qt main thread with it

    ::

        Qt main thread <-- Qt signals --> IPCQThread <-- unix domains socket --> Pyramid webserver


    TODO: instantiate the client-side unix socket in the http requests
    """
    inifile = "valkka.ini"
    
    def __init__(self, server_address, web_module_name):
        super().__init__(server_address)
        self.web_module_name = web_module_name
        # this module's directory structure is inspected for
        # config/nginx.conf
        # config/valkka.ini
        self.pre = self.__class__.__name__


    def afterSocketCreated__(self):
        self.start_nginx()
        self.start_pyramid()


    def start_nginx(self):
        self.inipath = os.path.join(
            # "/".join(inspect.getabsfile(inspect.currentframe()).split("/")[0:-1]),
            "/".join(inspect.getabsfile(self.web_module_name).split("/")[0:-1]),
            "config",
            "nginx.conf"
        )
        # nginx -p $PWD -c config/nginx.conf -g 'error_log error.log;'
        comm = "nginx -p %s -c %s -g 'error_log error.log;'" % (
            singleton.logs_dir.get(),
            self.inipath
        )
        #print(">", comm)
        #print(">>",shlex.split(comm))
        """
        # print(">>", comm.split())
        sp = comm.split()
        sp += ["-g","'error_log error.log;'"]
        print(">>", sp)
        """
        self.nginx_process = subprocess.Popen(
            # comm, shell = True
            shlex.split(comm)
        )


    def start_pyramid(self):
        self.inipath = os.path.join(
            # "/".join(inspect.getabsfile(inspect.currentframe()).split("/")[0:-1]),
            "/".join(inspect.getabsfile(self.web_module_name).split("/")[0:-1]),
            "config",
            self.inifile
        )
        """
        comm = "VALKKA_PYRAMID_IPC=%s pserve --reload %s" % (
            self.server_address,
            self.inipath
        )
        self.pyramid_process = subprocess.Popen(comm, shell = True)
        """
        comm = "pserve --reload %s" % (
            self.inipath
        )
        env = os.environ
        env["VALKKA_PYRAMID_IPC"] = self.server_address

        fname = singleton.logs_dir.getFile("pyramid.out")
        with open(fname,"w") as pyramid_output:
            self.pyramid_process = subprocess.Popen(
                comm.split(), 
                env = env,
                #stdout = pyramid_output, # these don't get flushed like .. ever
                #stderr = pyramid_output
            )
        # self.pyramid_process = subprocess.Popen(comm.split())

    """test manually with:

    VALKKA_PYRAMID_IPC=/tmp/test.ipc pserve --reload config/development.ini

    TODO: finish the webserver part
    """


    def close(self):
        print("closing webserver")
        self.pyramid_process.terminate()
        self.nginx_process.terminate()
        print("closing nginx")
        self.pyramid_process.wait()
        self.nginx_process.wait()
        super().close()



class WebSocketThread(IPCQThread):
    """Starts a websocket daemon that communicates with this QThread using ipc


    ::

        Qt main thread <-- Qt signals --> IPCQThread [THIS ONE] <-- unix domains socket --> Websocket server


    - websocket requested => ws server creates the socket, sends a message to this thread through IPC
    - .. clients should be registered, based on the fd
    - valkka-counter case: increment signals are sent from here .. just connect that signal to rest of the system
    - incoming signals: should be forwarded to ws server .. per client & fd
    - ..special signals can be sent to all clients through ipc
    - ..websocket server gets that signal & sends it to client
    """
    cli = "valkka-live-ws-server"

    def __init__(self, server_address):
        super().__init__(server_address)
        self.pre = self.__class__.__name__
        self.ws_process = None    
    

    def afterSocketCreated__(self):
        self.start_ws_server()


    def start_ws_server(self):
        comm = "%s %s" % (
            self.cli,
            self.server_address
        )
        #print("WebSocketThread: sleeping")
        #time.sleep(20)
        print("WebSocketThread: running", comm)
        self.ws_process = subprocess.Popen(
            # comm, shell = True
            shlex.split(comm)
        )


    def close(self):
        if self.ws_process is not None:
            self.ws_process.terminate()
            self.ws_process.wait()
        super().close()



class MyGui(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.setupUi()

    def setupUi(self):
        self.setGeometry(QtCore.QRect(100, 100, 500, 500))

        # create widget inside this window
        self.w = QtWidgets.QFrame(self)
        self.w.setAutoFillBackground(True)
        self.w.setStyleSheet("QFrame {background-color: blue;}")
        self.setCentralWidget(self.w)

        self.lay = QtWidgets.QVBoxLayout(self.w)

        self.thread = WWWQThread(
            singleton.ipc_dir.getFile("pyramid.ipc"),
            inspect.currentframe()
        )
        self.ws_thread = WebSocketThread(
            singleton.ipc_dir.getFile("ws.ipc")
        )

        self.b = QtWidgets.QPushButton(self, "Push Me")
        self.b.clicked.connect(self.b_slot)
        self.lay.addWidget(self.b)

        self.ws_thread.signals.base.connect(self.ws_message)

        self.thread.start()
        time.sleep(1)
        self.ws_thread.start()

        # TODO: connect signal from ws_thread to a slot (i.e. message from the websocket)
        # TODO: implement ingoing messagee slot to IPCQThread => we can send message to the web-page using ws_thread

    def b_slot(self):
        pass


    def ws_message(self, obj):
        print("Main thread got ws message", obj)
        id_ = obj["id"]
        # let's do ping-pong game with the web frontend
        self.ws_thread.command.emit({
            "id" : id_,
            "class" : "base",
            "name"  : "pong",
            "parameters" : None
        })


    def closeEvent(self, e):
        print("closeEvent!")
        self.ws_thread.close()
        self.thread.close()
        e.accept()


def main():
    from valkka.live.local import ValkkaLocalDir
    singleton.logs_dir = ValkkaLocalDir("live","logs")
    singleton.ipc_dir = ValkkaLocalDir("live","ipc")
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if __name__ == "__main__":
    main()
    """
    thread = QOnvifThread(None, None, None, None)
    thread.start()
    print("thread started")
    time.sleep(2)
    print("sending hello")
    thread.signals.command.emit("hello")
    time.sleep(2)
    print("closing")
    thread.close()
    """

# ONVIF: TODO: codesave
"""
referenceTokenFactory = self.ptz_service.factory.ReferenceToken
vector2DFactory = self.ptz_service.factory.Vector2D
ptzSpeedFactory = self.ptz_service.factory.PTZSpeed
token = referenceTokenFactory(value='ptz0')
if (e.key() == QtCore.Qt.Key_Left):
    # print("VideoWidget: left arrow released")
    self.ptz_service.ws_client.Stop(ProfileToken=token)
if (e.key() == QtCore.Qt.Key_Right):
    # print("VideoWidget: right arrow released")
    self.ptz_service.ws_client.Stop(ProfileToken=token)
if (e.key() == QtCore.Qt.Key_Down):
    # print("VideoWidget: down arrow released")
    self.ptz_service.ws_client.Stop(ProfileToken=token)
if (e.key() == QtCore.Qt.Key_Up):
    # print("VideoWidget: up arrow released")
    self.ptz_service.ws_client.Stop(ProfileToken=token)

if (e.key() == QtCore.Qt.Key_Left):
    #print("VideoWidget: left arrow pressed")
    panTilt = vector2DFactory(x=-1.0, y=0.0)
    ptzSpeed = ptzSpeedFactory(PanTilt=panTilt)
    self.ptz_service.ws_client.ContinuousMove(ProfileToken=token, Velocity=ptzSpeed)
if (e.key() == QtCore.Qt.Key_Right):
    # print("VideoWidget: right arrow pressed")
    panTilt = vector2DFactory(x=1.0, y=0.0)
    ptzSpeed = ptzSpeedFactory(PanTilt=panTilt)
    self.ptz_service.ws_client.ContinuousMove(ProfileToken=token, Velocity=ptzSpeed)
if (e.key() == QtCore.Qt.Key_Down):
    #print("VideoWidget: down arrow pressed")
    panTilt = vector2DFactory(x=10.0, y=-1.0)
    ptzSpeed = ptzSpeedFactory(PanTilt=panTilt)
    self.ptz_service.ws_client.ContinuousMove(ProfileToken=token, Velocity=ptzSpeed)
if (e.key() == QtCore.Qt.Key_Up):
    print("VideoWidget: up arrow pressed")
    panTilt = vector2DFactory(x=0.0, y=1.0)
    ptzSpeed = ptzSpeedFactory(PanTilt=panTilt)
    self.ptz_service.ws_client.ContinuousMove(ProfileToken=token, Velocity=ptzSpeed)


"""
