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
@version 0.14.1 
@brief   
"""

import sys
import time
from multiprocessing import Pipe, Lock
from valkka.live.multiprocess import safe_select
import socket, pickle, os
from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot


class IPCQThread(QtCore.QThread):
    """A thread that interacts with an external web, etc. server and the rest of the Qt system

    ::

        Qt main thread <-- Qt signals --> IPCQThread <-- unix domains socket --> Webserver
        Qt main thread <-- Qt signals --> IPCQThread <-- unix domains socket --> Websocket server
    
    TODO: 
    - implement slot for incoming messages
    - outgoing messages should carry a token (lets make it the fid) that identify the client
    - ..which can then be used to send incoming messages to this thread
    - ..and finally to the web request
    """
    class Signals(QtCore.QObject):
        """incoming (==from the rest of the Qt system) signals that carry an object

        - These signals are connectd to IPCQThread.handleCommand
        - ..which writes into internal pipe at the frontend
        - ..backend reads the object from the pipe and acts accordingly
        """
        command = Signal(object)
        
        """outgoing (== to the rest of the Qt system) signal classes

        - This thread emits these signals

        Messages that come through the unix ipc socket, have structures like this:

        ::

            {"class" : "base", "name" : "close"}
            {"class" : "valkka_live", "name" : "something", "parameters" : dict}

        When a message comes throught the ipc socket, class looks for correct signal object with the name
        defined by the key "class":
        """
        base = Signal(object)


    def __init__(self, server_address):
        super().__init__()
        self.pre = self.__class__.__name__
        self.lock = Lock()
        self.signals = self.Signals()
        self.signals.command.connect(self.handleCommand)
        self.command = self.signals.command # alias
        self.pipe_write, self.pipe_read = Pipe() # frontend pipe, backend pipe
        self.server_address = server_address
        try:
            os.unlink(self.server_address)
        except FileNotFoundError:
            pass # no pasa nada


    # *** frontend ****

    def handleCommand(self, com):
        """Should conform the scheme:
        {
            "class" : "base",
            "name"  : "somename",
            "id"    : "someid", # and id of the socket connection (there might be several websockets, etc)
            "parameters : {}
        }
        """
        with self.lock:
            self.pipe_write.send(com)

    def close(self):
        self.signals.command.emit(None)
        self.wait()
        os.unlink(self.server_address)

    # *** backend: on the other side of the fork ***

    def createSocket__(self):
        """client side
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        try:
            self.sock.connect(self.context.ipc_file)
        except Exception as e:
            print("createSocket failed with", e)
        """
        #"""server side
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.bind(self.server_address)
        self.sock.listen(1) # how many clients allowed
        #"""

    """client side interactive test snippet
import socket
ipc_file="/tmp/test-socket.ipc"
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(ipc_file)
msg = pickle.dumps({"message": "kikkelis"})
sock.send(msg)
    """

    def sendMessage__(self, cmd):
        """
        Organized in namespaces:

        ::

            {"class" : "base", "name" : "close"}
            {"class" : "valkka_live", "name" : "something", "parameters" : dict}
    
        """
        if not isinstance(cmd, dict):
            print("sendMessage__ : bad message", cmd, "must be dict")
            return

        if "class" not in cmd:
            print("sendMessage__ : bad message", cmd)
            return

        if hasattr(self.signals, cmd["class"]):
            # choose right signal class & emit name & parameters
            signal = getattr(self.signals, cmd["class"])
            cmd.pop("class")
            print("emitting signal", cmd)
            signal.emit(cmd)
        else:
            print("sendMessage__ : no class for signal", cmd)

    def afterSocketCreated__(self):
        pass


    def run(self):
        """Everything here happens in the multithread

        Multiplex reading from:

        - Internal commands (main QThread)
        - Unix domain server socket (that creates new active connections)
        - From active connections
        """
        self.createSocket__()
        self.afterSocketCreated__()
        ok = True
        active_conns = []
        conns_by_id = {}
        ids_by_conn = {}
        while ok:
            rlis = [self.pipe_read, self.sock]
            rlis += active_conns
            r, w, e = safe_select(rlis, [], [], timeout = 1.0)
            
            """
            if len(r) < 1:
                print(self.pre, ": timeout, ", len(rlis))
            """

            if self.pipe_read in r:
                """Commands from the frontend (i.e. from the rest of the Qt system)
                """
                msg = self.pipe_read.recv()
                """
                print(self.pre, ": got qt command", msg)
                print(self.pre, ": conns_by_id:", conns_by_id)
                """
                if msg is None:
                    break
                try:
                    key = msg["id"]
                except KeyError:
                    # send to all connections
                    print("sending to all")
                    for conn in active_conns:
                        print("sending", conn, msg)
                        conn.send(pickle.dumps(msg))
                else:
                    try:
                        conn = conns_by_id[key]
                    except KeyError:
                        print("no such registered unix ipc connection", key)
                    else:
                        print("sending", conn, msg)
                        msg_ = pickle.dumps(msg)
                        # print("raw", msg_)
                        conn.send(msg_)
                
            if self.sock in r:
                """New connections from the unix ipc socket
                """
                client_socket, address = self.sock.accept()
                active_conns.append(client_socket)
                key = id(client_socket)
                conns_by_id[key] = client_socket
                ids_by_conn[client_socket] = key
                print(self.pre, ": connection from", client_socket, address, key) 
                print(self.pre, ": ", conns_by_id, ids_by_conn)
                self.sendMessage__({
                    "class" : "base",
                    "name"  : "open",
                    "parameters" : {},
                    "id" : key  
                })
                continue # there might be stuff in that socket, so select again

            remaining_conns = []
            for conn in active_conns:
                """Messages from the unix ipc socket

                append id & signal to the rest of the Qt system
                """
                conn_ok = True
                if conn in r:
                    #print(self.pre, ": getting some from", r)
                    msg = bytes(0)
                    while True:
                        #print(self.pre, ": receiving")
                        msg_part = conn.recv(512)
                        #print(self.pre, ": received", msg_part)
                        if len(msg_part) < 1:
                            conn_ok = False
                        msg += msg_part
                        if len(msg) < 512:
                            break
                    
                    if conn_ok:
                        # add id, so that rest of the system can distinguish this connection
                        key = ids_by_conn[conn]
                        try:
                            msg = pickle.loads(msg)
                        except Exception as e:
                            print("could not deserialize message from ipc", e)
                            continue
                        if isinstance(msg, dict):
                            pass
                        else:
                            print("ipc message not a dict")
                            continue
                        msg["id"] = key
                        # print(self.pre, ": got ipc command", msg, "from", conn)
                        self.sendMessage__(msg)
                    else:
                        print(self.pre, ": dropping connection", conn)
                        conn.close()
                        self.sendMessage__({
                          "class" : "base",
                          "name"  : "drop",
                          "parameters" : {},
                          "id" : ids_by_conn[conn]  
                        })
                        key = ids_by_conn.pop(conn)
                        conns_by_id.pop(key)
                if conn_ok:
                    remaining_conns.append(conn)
                
            active_conns = remaining_conns

        for conn in active_conns:
            conn.close()
        self.sock.close()



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

        self.thread = IPCQThread(
            "/tmp/test-socket.ipc"
        )

        self.b = QtWidgets.QPushButton(self, "Push Me")
        self.b.clicked.connect(self.b_slot)
        self.lay.addWidget(self.b)

        self.thread.start()


    def b_slot(self):
        pass


    def closeEvent(self, e):
        print("closeEvent!")
        self.thread.close()
        e.accept()


def main():
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if __name__ == "__main__":
    main()
    