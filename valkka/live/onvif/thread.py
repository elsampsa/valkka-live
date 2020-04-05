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
@version 0.12.2 
@brief   
"""

import sys
import time
from threading import Lock, Event
from PySide2 import QtCore, QtWidgets

from valkka.onvif import OnVif, PTZ, DeviceManagement, Media


class QOnvifThread(QtCore.QThread):
    """QThread handling onvif commands to rtsp cameras

    Send Qt signals to this thread from the Qt main thread
    """
    class Signals(QtCore.QObject):
        command = QtCore.Signal(object) # incoming signal that carries and object (++)


    def __init__(self, ip, port, user, password):
        super().__init__()
        #self.ptz_service = PTZ(ip, port, user, password, False, None)
        #self.device_service = DeviceManagement(ip, port, user, password, False, None)
        #self.media_service = Media(ip, port, user, password, False, None)

        self.event = Event()
        self.event.clear()
        self.lock = Lock()        
        self.incoming = []
        self.signals = self.Signals()
        self.signals.command.connect(self.handleCommand)


    def handleCommand(self, com):
        with self.lock:
            print(">appending", com)
            self.incoming.append(com)
            self.event.set()


    def run(self):
        """Everything here happens in the multithread, not in the main thread
        """
        ok = True
        while ok:
            print(">waitin'")
            self.event.wait()
            with self.lock:
                print(">", self.incoming)
                for comm in self.incoming:
                    print("QOnvifThread: got command", comm)
                    if comm is None:
                        print("QOnvifThread: exit!")
                        ok = False
                        break

                    """the command object could consist of..
                    ["method_name", {dictionary of kwargs}]
                    then just:

                    ::

                        method = getattr(self,method_name) # get the method
                        method(**kwargs) # call the method

                    """
                self.incoming = []
                self.event.clear()



    def close(self):
        self.signals.command.emit(None)
        self.wait()

            

if __name__ == "__main__":

    thread = QOnvifThread(None, None, None, None)
    thread.start()
    print("thread started")
    time.sleep(2)
    print("sending hello")
    thread.signals.command.emit("hello")
    time.sleep(2)
    print("closing")
    thread.close()


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
            