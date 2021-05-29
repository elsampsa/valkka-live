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
@version 1.0.1 
@brief   
"""

import sys
import time
from threading import Lock, Event
from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot

from valkka.onvif import OnVif, PTZ, DeviceManagement, Media


class OnvifCommand:

    class Signals(QtCore.QObject):
        reply = Signal(object)

    def __init__(self,
                 service_name=None,
                 method_name=None,
                 **kwargs):
        """
        :param service_name: Values: ptz_service, device_service, media_servic
        :param method_name: SOAP call name
        :param **kwargs: Objects created by the SOAP factory

        Zeep / SOAP call:

        ::

            self.device_service.ws_client.SetSystemDateAndTime(
                DateTimeType = self.factory.SetDateTimeType("Manual")
                ...)


        This would map to service_name = "device_service",
        method_name = "SetSystemDateAndTime",
        kwargs constitute the arguments to the method         
        """
        self.service_name = service_name
        self.method_name = method_name
        self.kwargs = kwargs
        self.signals = self.Signals()
        self.signal = self.signals.reply


class QOnvifThread(QtCore.QThread):
    """QThread handling onvif commands to rtsp cameras

    Send Qt signals to this thread from the Qt main thread
    """
    class Signals(QtCore.QObject):
        # incoming signal that carries and object (++)
        command = Signal(object)

    def __init__(self, ip = None, port = 80, user = "admin", password = "12345"):
        super().__init__()
        assert(ip is not None)
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password

        self.event = Event()
        self.event.clear()
        self.lock = Lock()
        self.incoming = []
        self.signals = self.Signals()
        self.signals.command.connect(self.handleCommand)
        self.command = self.signals.command # alias

    def handleCommand(self, com):
        with self.lock:
            print(">appending", com)
            self.incoming.append(com)
            self.event.set()

    def createServices(self):
        try:
            self.ptz_service = PTZ(self.ip, self.port, self.user, self.password, 
                use_async = False, sub_xaddr_ = None)
        except Exception as e:
            print(e)
            self.ptz_service = None
        try:
            self.device_service = DeviceManagement(self.ip, self.port, self.user, self.password,
                use_async = False, sub_xaddr_ = None)
        except Exception as e:
            print(e)
            self.device_service = None
        try:
            self.media_service = Media(self.ip, self.port, self.user, self.password, 
                use_async = False, sub_xaddr_ = None)
        except Exception as e:
            print(e)
            self.media_service = None

    def run(self):
        """Everything here happens in the multithread, not in the main thread
        """
        self.createServices()
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
                    if comm.service_name == "ptz_service":
                        service = self.ptz_service.ws_client
                    elif comm.service_name == "device_service":
                        service = self.device_service.ws_client
                    elif comm.service_name == "media_service":
                        service = self.media_service.ws_client
                    else:
                        print("QOnvifThread: unknown service", comm.service_name)
                        continue

                    if service is None:
                        comm.signal.emit(None)
                        # this means that the service is not working
                        # properly
                        continue

                    try:
                        method = getattr(service, comm.method_name)
                        reply = method(**comm.kwargs)  # call SOAP
                    except Exception as e:
                        result = e
                    else:
                        result = reply
                    comm.signal.emit(result)

                self.incoming = []
                self.event.clear()

    def close(self):
        self.signals.command.emit(None)
        self.wait()



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

        self.thread = QOnvifThread(
            user = "admin",
            password = "123456",
            ip = "192.168.0.134"
        )

        self.b = QtWidgets.QPushButton(self, "Push Me")
        self.b.clicked.connect(self.b_slot)
        self.lay.addWidget(self.b)

        self.thread.start()


    def b_slot(self):

        com = OnvifCommand(
            service_name = "device_service",
            method_name = "GetSystemDateAndTime"
            # TODO: the signal should be attached here
            # it should *not* be part of the OnvifCommand class..!
        )

        def callback(obj):
            print(">", obj)

        com.signal.connect(callback)
        self.thread.command.emit(com)


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
