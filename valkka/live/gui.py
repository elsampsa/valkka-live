"""
gui.py : Main graphical user interface for the Valkka Live program

Copyright 2018 Sampsa Riikonen

Authors: Sampsa Riikonen

This file is part of the Valkka Live video surveillance program

Valkka Live is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>

@file    gui.py
@author  Sampsa Riikonen
@date    2018
@version 1.2.1 
@brief   Main graphical user interface for the Valkka Live program
"""
import imp
import sys
import pydoc
import json
import pickle
from pprint import pprint, pformat
import argparse

from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot  # Qt5

try:
    import valkka.core
except importerror:
    print(constant.valkka_core_not_found)
    raise SystemExit()

from valkka.api2.logging import *
# from valkka.api2 import LiveThread, USBDeviceThread, ValkkaFS, ValkkaFSManager, ValkkaFSLoadError # old
from valkka.api2 import LiveThread, USBDeviceThread
from valkka.fs import ValkkaSingleFS, ValkkaFSManager, ValkkaFSLoadError
from valkka.api2.tools import parameterInitCheck
from valkka import core # for logging
"""
core.setLogLevel_threadlogger(loglevel_crazy)
core.setLogLevel_valkkafslogger(loglevel_debug)
core.setLogLevel_avthreadlogger(loglevel_debug)
core.setLogLevel_valkkafslogger(loglevel_debug)
"""

"""
def get_valkka_live_universe(main_dir = "live"):
    # imports inside this method, returns the MyGui class
"""
from valkka.live import singleton
# print("singleton.test =", singleton.test)

from valkka.live import constant
from valkka.live.tools import importerror

from valkka.live import version
version.check() # checks the valkka version

from valkka.live.menu import FileMenu, ViewMenu, ConfigMenu, AboutMenu
from valkka.live.gpuhandler import GPUHandler
from valkka.live import style, container, tools, constant
from valkka.live import default
from valkka.live.cpu import CPUScheme
from valkka.live.quickmenu import QuickMenu, QuickMenuElement
from valkka.live.qt.playback import PlaybackController
from valkka.live.qt.tools import QCapsulate, QTabCapsulate, getCorrectedGeom
from valkka.live.tools import nameToClass, classToName

from valkka.live.datamodel.base import DataModel
from valkka.live.datamodel.row import RTSPCameraRow, EmptyRow, USBCameraRow, SDPFileRow, MemoryConfigRow, ValkkaFSConfigRow
# from valkka.live.datamodel.layout_row import VideoContainerNxMRow, PlayVideoContainerNxMRow, CameraListWindowRow, MainWindowRow
from valkka.live.datamodel.layout_row import LayoutContainerRow
from valkka.live.device import RTSPCameraDevice, USBCameraDevice, SDPFileDevice

from valkka.live.listitem import HeaderListItem, ServerListItem, RTSPCameraListItem, USBCameraListItem, SDPCameraListItem
from valkka.live.cameralist import BasicView

from valkka.live.filterchain import LiveFilterChainGroup, PlaybackFilterChainGroup
from valkka.live.chain.multifork import RecordType

from valkka.live.fs import ValkkaSingleFSHandler

pre = "valkka.live :"

class MyGui(QtWidgets.QMainWindow):

    #config_dir = setValkkaLocalDir("live", varname = "config_dir")
    #valkkafs_dir = setValkkaLocalDir("live","fs", varname = "valkkafs_dir")

    def __init__(self, parent=None):
        """ctor
        """
        super(MyGui, self).__init__()
        self.initDirs()
        self.initVars()
        self.initConfigFiles()
        self.readDB()
        self.generateMethods()
        self.setupUi()
        self.startProcesses()
        self.startThreads()
        self.openValkka()
        self.makeLogic()
        self.post()
        

    def getMargins(self):
        # https://doc.qt.io/qt-5/application-windows.html#x11-peculiarities
        if singleton.dx > 0:
            return
        singleton.dy = self.geometry().y() - self.y() # y() : with frame, geometry().y() : without frame
        singleton.dx = self.geometry().x() - self.x()
        singleton.dw = self.frameGeometry().width() - self.width()
        singleton.dh = self.frameGeometry().height() - self.height()
        print("getMargins: dy, dx, dw, dh", singleton.dy, singleton.dx, singleton.dw, singleton.dh)
        # dy, dx, dw, dh 29 4 8 33
        # WARNING!  Must move main window before this starts to give any values other than zero ..!
        
    # *** redefined Qt member functions ***
    
    def closeEvent(self, e):
        """Triggered when the main qt program exits
        """
        print("gui : closeEvent!")
        self.closeContainers()

        # self.manage_cameras_win.unSetPropagate() # don't send signals .. if you don't do this: close => closeEvent => will trigger self.reOpen
        # self.manage_cameras_win.close()
        
        self.camera_list_win.unSetPropagate()
        self.camera_list_win.close()
        
        # self.config_win.unSetPropagate()
        self.config_win.close()

        self.closeProcesses() # closes shmem clients
        self.closeThreads()
        self.closeValkka() # closes filterchains that have shmem servers
        singleton.data_model.close()
        
        e.accept()
    
    def showEvent(self, e):
        if self.first_show:
            self.first_show = False
            print("singleton.load_layout", singleton.load_layout)
            # pre-loading stuff
            if singleton.load_layout:
                print("load layout")
                self.load_window_layout_slot()


    def initDirs(self):
        self.config_dir = singleton.config_dir
        self.valkkafs_dir = singleton.valkkafs_dir


    def initVars(self):
        """Define files & variables
        """
        self.first_show = True # main window visualized for the first time?

        self.version_file = self.config_dir.getFile("version")
        self.layout_file = self.config_dir.getFile("layout")
        
        # singleton.thread = None # a QThread that reads multiprocessing pipes
        
        self.containers_grid = [] # list of instances of valkka.live.container.grid.VideoContainerNxM
        self.containers_playback = []
        
        self.mvision_classes, self.mvision_client_classes, self.mvision_master_classes =\
            tools.scanMVisionClasses(
                singleton.mvision_package_names
            ) 
    
        if (len(self.mvision_classes) > 0 or len(self.mvision_client_classes) > 0):
            self.mvision = True
        else:
            self.mvision = False

        self.valkkafs = None # NEW: list of valkkafs'

        self.config_modified = False # should valkka services be restarted?
        self.valkkafs_modified = False # remove recorded streams?


    def initConfigFiles(self):
        self.first_start = True
        ver = self.readVersionNumber()
        if ver is not None:  # this indicates that the program has been started earlier
            print("valkka.live : loading config file for version number", ver)
            if ver:
                if (ver[0] == version.VERSION_MAJOR and ver[1] == version.VERSION_MINOR):
                    self.first_start = False
                else: # incorrect version number
                    print("valkka.live : clearing config")
                    pass
                    # .. or handle migration somehow
                    
        if self.first_start:  # first time program start
            # TODO: eula could be shown here
            print(pre, "initConfigFiles : first start")
            self.config_dir.reMake()
            self.saveVersionNumber()
            # self.saveConfigFile()
            # self.saveWindowLayout() # clears window layout
            self.first_start = True


    def readDB(self):
        """Datamodel includes the following files: config.dat, devices.dat
        """
        singleton.data_model = DataModel(directory = self.config_dir.get())
        # singleton.data_model = DataModel(directory = tools.getConfigDir())
        if (self.first_start):
            print(pre, "readDB : first start")
            singleton.data_model.clearAll()
            singleton.data_model.saveAll()

        # If camera collection is corrupt
        if not singleton.data_model.checkCameraCollection():
            singleton.data_model.clearCameraCollection()


    def saveVersionNumber(self):
        with open(self.version_file, "w") as f:
            f.write(version.get())
        

    def readVersionNumber(self):
        try:
            with open(self.version_file, "r") as f:
                st = f.read()
            vs = []
            for s in st.split("."):
                vs.append(int(s))
        except:
            print("valkka.live : could not read version number")
            return None
        else:
            return vs


    def saveWindowLayout(self):
        self.serializeContainers()
        

    def loadWindowLayout(self):
        self.closeContainers()
        self.deSerializeContainers()

    # *** Generate Qt structures ***

    def generateMethods(self):
        """Autogenerate some member functions
        
        - Generates slot functions for launching containers
        """
        for i in range(1, 5):
            # adds member function grid_ixi_slot(self)
            self.makeGridSlot(i, i)
            if singleton.use_playback:
                self.makePlaybackGridSlot(i, i)

        for cl in self.mvision_classes:
            self.makeMvisionSlot(cl)

        for cl in self.mvision_client_classes:
            self.makeMvisionClientSlot(cl)
    

    def setupUi(self):
        self.setStyleSheet(style.main_gui)
        self.setWindowTitle(singleton.program_name)

        self.setGeometry(QtCore.QRect(100, 100, 500, 500))

        self.w = QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)

        self.filemenu = FileMenu(parent=self)
        self.viewmenu = ViewMenu(parent=self)  # grids up to 4x4
        self.configmenu = ConfigMenu(parent=self)

        if self.mvision:
            mvision_elements = []

            for cl in self.mvision_classes + self.mvision_client_classes:
                if cl.auto_menu:
                    # # instead: all visible in menus
                    # # but if auto_menu is False, then must be connected
                    # # manually .. actually, we'd need auto_connect switch.
                    el = QuickMenuElement(title = cl.name, method_name = cl.name)
                    mvision_elements.append(el)

            class MVisionMenu(QuickMenu):
                title = "Machine Vision"
                elements = mvision_elements

            self.mvisionmenu = MVisionMenu(parent = self)

        self.aboutmenu = AboutMenu(parent=self)

        # create container and their windows
        self.manage_cameras_container = singleton.data_model.getDeviceListAndForm(None) 
        self.manage_memory_container = singleton.data_model.getConfigForm()

        self.manage_memory_container.signals.save.connect(self.config_modified_slot)
        self.manage_cameras_container.getForm().signals.save_record.connect(self.config_modified_slot)

        tabs = [ 
                    (self.manage_cameras_container. widget, "Camera Configuration"),
                    (self.manage_memory_container.  widget, "Memory Configuration"),
                ]

        if singleton.use_playback:
            self.manage_valkkafs_container = singleton.data_model.getValkkaFSForm()
            self.manage_valkkafs_container.signals.save.connect(self.valkkafs_modified_slot)
            tabs.append(
                (self.manage_valkkafs_container.widget, "Recording Configuration")
            )


        self.config_win = QTabCapsulate(
                "Configuration",
                tabs
            )

        self.config_win.signals.close.connect(self.config_dialog_close_slot)
        self.config_win.signals.close.connect(self.manage_cameras_container.close_slot) 
        # == inform ListAndForm that it has been closed => it knows to close any extra wins / dialogs present
        # when the configuration dialog is reopened, inform the camera configuration form .. this way it can re-check if usb cams are available
        self.config_win.signals.show.connect(self.manage_cameras_container.getForm().show_slot) 
        self.config_win.signals.show.connect(self.manage_cameras_container.choose_first_slot) # so that we have at least one device chosen

        self.makeCameraTree()
        self.camera_list_win = QCapsulate(self.treelist, "Camera List")

        self.wait_label = QtWidgets.QLabel("Restarting Valkka, please wait ..")
        self.wait_window = QCapsulate(self.wait_label, "Wait", nude = True)


    def makeCameraTree(self):
        self.root = HeaderListItem()
        self.treelist = BasicView(parent = None, root = self.root)
        self.updateCameraTree()


    def updateCameraTree(self):
        self.treelist.reset_()

        self.server = ServerListItem(
            name = "Localhost", ip = "127.0.0.1", parent = self.root)
        """
        self.server1 = ServerListItem(
            name="First Server", ip="192.168.1.20", parent=self.root)
        """
        """
        self.camera1 = RTSPCameraListItem(camera=RTSPCameraDevice(
            ip="192.168.1.4", username="admin", password="1234"), parent=self.server1)
        self.camera2 = RTSPCameraListItem(camera=RTSPCameraDevice(
            ip="192.168.1.4", username="admin", password="1234"), parent=self.server1)
        """
        devices = []

        for row in singleton.data_model.camera_collection.get():
            # print(pre, "makeCameraTree : row", row)
            if (row["classname"] == RTSPCameraRow.__name__):
                row.pop("classname")
                devices.append(
                    RTSPCameraListItem(
                        camera = RTSPCameraDevice(**row),
                        parent = self.server
                    )
                )
            elif (row["classname"] == USBCameraRow.__name__):
                row.pop("classname")
                devices.append(
                    USBCameraListItem(
                        camera = USBCameraDevice(**row),
                        parent = self.server
                    )
                )
            elif (row["classname"] == SDPFileRow.__name__):
                row.pop("classname")
                devices.append(
                    SDPCameraListItem(
                        sdpfile = SDPFileDevice(**row),
                        parent = self.server
                    )
                )

        self.treelist.update()
        self.treelist.expandAll()


    def makeLogic(self):
        # *** When camera list has been closed, re-create the cameralist tree and update filterchains ***
        # self.manage_cameras_win.signals.close.connect(self.updateCameraTree) # now put into save_camera_config_slot
        
        # self.manage_cameras_win.signals.close.connect(self.filterchain_group.update) # TODO: use this once fixed
        # self.manage_cameras_win.signals.close.connect(self.filterchain_group.read) # TODO: eh.. lets be sure of this .. (are we releasing slots in the LiveThread etc.)
        
        # self.manage_cameras_win.signals.close.connect(self.save_camera_config_slot)
        # self.manage_memory_container.signals.save.connect(self.save_memory_conf_slot)

        # *** Menu bar connections ***
        # the self.filemenu.exit attribute was autogenerated
        self.filemenu.exit.               triggered.connect(self.exit_slot)
        self.filemenu.save_window_layout. triggered.connect(self.save_window_layout_slot)
        self.filemenu.load_window_layout. triggered.connect(self.load_window_layout_slot)

        """
        self.configmenu.manage_cameras.   triggered.connect(
            self.manage_cameras_slot)
        self.configmenu.memory_usage.     triggered.connect(
            self.memory_usage_slot)
        """
        
        self.configmenu.configuration_dialog.triggered.connect(self.config_dialog_slot)
        
        self.viewmenu.camera_list.        triggered.connect(self.camera_list_slot)
        self.aboutmenu.about_program.     triggered.connect(self.about_slot)

        # *** Connect autogenerated menu calls into autogenerated slot functions ***
        for i in range(1, 5):
            # gets member function grid_ixi_slot
            slot_func = getattr(self, "grid_%ix%i_slot" % (i, i))
            # gets member function grid_ixi from self.viewmenu.video_grid
            menu_func = getattr(self.viewmenu.video_grid,
                                "grid_%ix%i" % (i, i))
            menu_func.triggered.connect(slot_func)
            # i.e., like this : self.viewmenu.video_grid.grid_1x1.triggered.connect(slot_func)

        if singleton.use_playback:
            for i in range(1, 5):
                # gets member function grid_ixi_slot
                slot_func = getattr(self, "playback_grid_%ix%i_slot" % (i, i))
                # gets member function grid_ixi from self.viewmenu.video_grid
                menu_func = getattr(self.viewmenu.playback_video_grid,
                                    "grid_%ix%i" % (i, i))
                menu_func.triggered.connect(slot_func)
                # i.e., like this : self.viewmenu.video_grid.grid_1x1.triggered.connect(slot_func)


        # *** autogenerated machine vision menu and slots ***
        for cl in self.mvision_classes + self.mvision_client_classes:
            slot_func_name = cl.name+"_slot"
            if hasattr(self, slot_func_name):
                # print(">", cl.name)
                getattr(self.mvisionmenu,cl.name).triggered.connect(getattr(self,slot_func_name))


    def post(self):
        pass

    # *** Container handling ***

    def serializeContainers(self):
        """Serializes the current view of open video grids (i.e. the view)
        
        returns a dictionary where the keys are complete classnames
        each value corresponds to a list of containers of the class described by the key
        
        each serialized container looks like this:
        
        ::
        
            dic={
                "kwargs"     : {}, # parameters that we're used to instantiate this class
                }


        A concrete example:

        ::

            {'valkka.live.container.grid.VideoContainerNxM': [
                {   # individual serialized container
                    'child_class': <class 'valkka.live.container.video.VideoContainer'>,
                    'child_pars': [{'device_id': -1}],
                    'geom': (604, 0, 300, 300),
                    'm_dim': 1,
                    'n_dim': 1,
                    'n_xscreen': 0,
                    'title': 'Video Grid'
                },
                ...
                ]
            }

        - TODO: this stuff should be moved to the db .. ?  Or just keep using files..?
        - Different row types: 
            VideoContainerNxM : columns: child_class, child_pars, geom, etc.., LAYOUT_ID
            PlayVideoContainerNxM : .., LAYOUT_ID
            CameraListWindow : .., LAYOUT_ID
        - LAYOUT_ID identifies to which layout they belong

        """
        """
        container_list = [] # list of instances of classes in valkka.live.container, e.g. valkka.live.container.grid.VideoContainerNxM, etc.
        
        for container in self.containers_grid:
            # these are of the type valkka.live.container.grid.VideoContainerNxM
            print("gui: serialize containers : container=", pformat(container))
            container_list.append(container.serialize())
        
        # TODO: serialize self.containers_playback

        # classnames compatible with local namespace
        return {
            "valkka.live.container.grid.VideoContainerNxM"   : container_list
            }
        """
        singleton.data_model.layout_collection.clear()

        container_list = []
        for container in self.containers_grid:
            ser = container.serialize()
            # print(ser)
            # {'title': 'Video Grid', 'n_xscreen': 0, 'child_class': <class 'valkka.live.container.video.VideoContainer'>, 
            # 'child_pars': [{'device_id': -1}, {'device_id': -1}, {'device_id': -1}, {'device_id': -1}], 'geom': (604, 0, 300, 300), 'n_dim': 2, 'm_dim': 2}
            # singleton.data_model.layout_collection.new(VideoContainerNxMRow, ser) # nopes ..
            ser.update({"type":"VideoContainerNxM"})
            container_list.append(ser)

        for container in self.containers_playback:
            ser = container.serialize()
            ser.update({"type":"PlayVideoContainerNxM"})
            container_list.append(ser)

        ser = {"type": "QMainWindow", "geom": getCorrectedGeom(self)}
        container_list.append(ser)
        """
        if self.camera_list_win.isVisible():
            ser = {"type": "CameraListWindow", "geom": getCorrectedGeom(self.camera_list_win)}
            container_list.append(ser)
        """

        for widget_name in singleton.serializable_widgets:
            # key: "camera_list_win"
            # widget = self.camera_list_win
            # geom = getCorrectedGeom(widget)
            # ser = {"type" : key, "geom": geom}
            # ser.update(widget.serialize())
            print("serializeContainers:", widget_name)
            if hasattr(self, widget_name):
                print("serializeContainers: has", widget_name)
                window = getattr(self, widget_name)
                # the widget is actually QMainWindow instance
                widget = window.getWidget()
                ser = {
                    "type"      : widget_name,
                    "geom"      : getCorrectedGeom(window),
                    "visible"   : widget.isVisible()
                }
                if hasattr(widget, "serialize"):
                    ser.update(widget.serialize())
                else:
                    pass
            else:
                print("WARNING: could not find member", widget_name)
                continue
            print("serializeContainers: ser=", ser)
            container_list.append(ser)

        singleton.data_model.layout_collection.new(LayoutContainerRow, {"layout" : container_list})

        print(singleton.data_model.layout_collection)
        singleton.data_model.layout_collection.save()
        

    def deSerializeContainers(self):
        """Re-creates containers, based on the list saved into layout_collection
        
        This is the inverse of self.serializeContainers
        
        Containers must be closed & self.containers etc. list must be cleared before calling this
        """
        # glo = globals()
        # print("glo>",glo)
        singleton.reCacheDevicesById() # singleton.devices_by_id will be used by the containers
        
        try:
            row = next(singleton.data_model.layout_collection.get())
        except StopIteration:
            return
        
        container_list = row["layout"]

        # print(">", container_list)
        for container_dic in container_list:
            t = container_dic.pop("type") # get the type & remove it from the dict

            if t == "VideoContainerNxM":
                container_dic["child_class"] = nameToClass(container_dic.pop("child_class")) # swap from class name to class instance
                container_dic["geom"] = tuple(container_dic["geom"])  # woops.. tuple does not json-serialize, but is changed to list .. so change it back to tuplee
                # non-serializable parameters:
                dic = {
                    "parent"            : None,
                    "gpu_handler"       : self.gpu_handler,         # RootContainers(s) pass this downstream to child containers
                    "filterchain_group" : self.filterchain_group    # RootContainers(s) pass this downstream to child containers
                    }
                container_dic.update(dic)
                # now container has the parameters to instantiate the object
                print(">", container_dic)
                cont = container.VideoContainerNxM(**container_dic) # instantiate container
                cont.signals.closing.connect(self.rem_grid_container_slot)
                self.containers_grid.append(cont)
            
            if t == "PlayVideoContainerNxM" and singleton.use_playback:
                container_dic["child_class"] = nameToClass(container_dic.pop("child_class")) # swap from class name to class instance
                container_dic["geom"] = tuple(container_dic["geom"])  # woops.. tuple does not json-serialize, but is changed to list .. so change it back to tuplee
                # non-serializable parameters:
                dic = {
                    "parent"              : None,
                    "gpu_handler"         : self.gpu_handler,            # RootContainers(s) pass this downstream to child containers
                    "filterchain_group"   : self.filterchain_group_play,
                    "valkkafsmanager"     : self.valkkafsmanager,
                    "playback_controller" : self.playback_controller
                    }
                container_dic.update(dic)
                # now container has the parameters to instantiate the object
                print(">", container_dic)
                cont = container.PlayVideoContainerNxM(**container_dic) # instantiate container
                cont.signals.closing.connect(self.rem_playback_grid_container_slot)
                self.containers_playback.append(cont)
            
            elif t == "QMainWindow":
                geom = container_dic["geom"]
                self.setGeometry(geom[0], geom[1], geom[2], geom[3])
                """    
                elif t == "CameraListWindow":
                    geom = container_dic["geom"]
                    self.camera_list_win.setVisible(True)
                    self.camera_list_win.setGeometry(geom[0], geom[1], geom[2], geom[3])
                """

            elif t in singleton.serializable_widgets:
                if hasattr(self, t):
                    window = getattr(self, t)
                    geom = container_dic["geom"]
                    window.setGeometry(geom[0], geom[1], geom[2], geom[3])
                    window.setVisible(container_dic["visible"])
                    widget = window.getWidget()
                    if hasattr(widget, "deSerialize"):
                        method = getattr(widget, "deSerialize")
                        method(container_dic)
                    else:
                        continue
                else:
                    print("deSerializeContainers: could not find widget", t)
                    continue


    def closeContainers(self):
        print("gui: closeContainers: containers_grid =", self.containers_grid)
        for container in self.containers_grid:
            container.close()
        self.containers_grid = []

        for container in self.containers_playback:
            container.close()
        self.containers_playback = []


    # *** Multiprocess handling ***

    def startProcesses(self):
        """Create and start python multiprocesses
        
        Starting a multiprocess creates a process fork.
        
        In theory, there should be no problem in first starting the multithreading environment and after that perform forks (only the thread requestin the fork is copied), but in practice, all kinds of weird behaviour arises.
        
        Read all about it in here : http://www.linuxprogrammingblog.com/threads-and-fork-think-twice-before-using-them
        """
        singleton.process_map = {} # each key is a list of started multiprocesses
        # self.process_avail = {} # count instances

        singleton.client_process_map = {}
        singleton.master_process_map = {}
        
        def span(mvision_classes: list, process_map: dict):
            for mvision_class in mvision_classes:
                name = mvision_class.name
                tag  = mvision_class.tag
                num  = mvision_class.max_instances
                if (tag not in process_map):
                    process_map[tag] = []
                    # self.process_avail[tag] = num
                    for n in range(0, num):
                        print("startProcesses: spanning", tag, n)
                        # verbose = True
                        verbose = singleton.mvision_verbose
                        p = mvision_class(verbose = verbose)
                        # p.start()
                        p.go()
                        process_map[tag].append(p)
            
        span(self.mvision_classes, singleton.process_map)
        span(self.mvision_client_classes, singleton.client_process_map)
        span(self.mvision_master_classes, singleton.master_process_map)
        
        
    def closeProcesses(self):
        #print("closeProcesses: client map", singleton.client_process_map)
        #print("closeProcesses: master map", singleton.master_process_map)

        def stop(process_map):
            for key in process_map:
                for p in process_map[key]:
                    # print("closeProcesses: stop:", p)
                    # p.stop()
                    p.requestStop()

        def wait(process_map):
            for key in process_map:
                for p in process_map[key]:
                    p.waitStop()

        stop(singleton.process_map)
        stop(singleton.client_process_map)
        stop(singleton.master_process_map)

        wait(singleton.process_map)
        wait(singleton.client_process_map)
        wait(singleton.master_process_map)

        
    # *** Valkka ***
        
    def openValkka(self):
        self.cpu_scheme = CPUScheme()
        
        # singleton.data_model.camera_collection
        try:
            memory_config = next(singleton.data_model.config_collection.get({"classname" : MemoryConfigRow.__name__}))
        except StopIteration:
            print(pre, "Using default mem config")
            singleton.data_model.writeDefaultMemoryConfig()
            memory_config = default.get_memory_config()

        try:
            valkkafs_config = next(singleton.data_model.valkkafs_collection.get({"classname" : ValkkaFSConfigRow.__name__}))
        except StopIteration:
            print(pre, "Using default valkkafs config")
            singleton.data_model.writeDefaultValkkaFSConfig()
            valkkafs_config = default.get_valkkafs_config()

        n_frames = round(memory_config["msbuftime"] * default.fps / 1000.) # accumulated frames per buffering time = n_frames

        if (memory_config["bind"]):
            self.cpu_scheme = CPUScheme()
        else:
            self.cpu_scheme = CPUScheme(n_cores = -1)

        self.gpu_handler = GPUHandler(
            n_720p  = memory_config["n_720p"] * n_frames, # n_cameras * n_frames
            n_1080p = memory_config["n_1080p"] * n_frames,
            n_1440p = memory_config["n_1440p"] * n_frames,
            n_4K    = memory_config["n_4K"] * n_frames,
            msbuftime = memory_config["msbuftime"],
            verbose = False,
            cpu_scheme = self.cpu_scheme
        )

        self.livethread = LiveThread(
            name = "live_thread",
            verbose = False,
            affinity = self.cpu_scheme.getLive()
        )
        
        self.usbthread = USBDeviceThread(
            name = "usb_thread",
            verbose = False,
            affinity = self.cpu_scheme.getUSB()
        )

        # see datamodel.row.ValkkaFSConfigRow
        blocksize = valkkafs_config["blocksize"]
        n_blocks  = valkkafs_config["n_blocks"]
        #fs_flavor = valkkafs_config["fs_flavor"] 
        #record    = valkkafs_config["record"]
    
        self.filterchain_group = LiveFilterChainGroup(
            datamodel     = singleton.data_model, 
            livethread    = self.livethread, 
            usbthread     = self.usbthread,
            gpu_handler   = self.gpu_handler, 
            cpu_scheme    = self.cpu_scheme,
            vaapi         = singleton.vaapi)
        self.filterchain_group.read()

        # TODO: RecordType..?
        if singleton.use_playback:
            print("openValkka: ValkkaFS **PLAYBACK & RECORDING ACTIVATED**")
            # ValkkaSingleFSHandler: 
            # directory handling and valkkafs <-> stream id association
            self.valkka_fs_handler = ValkkaSingleFSHandler(
                basedir = singleton.valkkafs_dir.get(),
                blocksize = blocksize * 1024*1024, # MB
                n_blocks = n_blocks
            )
            if self.valkkafs_modified:
                print("openValkka: removing all recorded streams")
                self.valkka_fs_handler.clear()
                self.valkka_fs_handler.wipe()

            for row in singleton.data_model.camera_collection.get():
                _id=row["_id"] # get stream id
                slot=row["slot"]
                classname=row["classname"]
                if classname!="EmptyRow":
                    # print(">", row)
                    self.valkka_fs_handler.load(_id)
                    # ..creates new valkka if doesn't exist
            self.valkkafsmanager = ValkkaFSManager(
                self.valkka_fs_handler.tolist()
                )
            self.valkkafsmanager.start()
            #self.filterchain_group.setRecording(RecordType.always, self.valkkafsmanager)# OLD
            # self.filterchain_group: source for live stream
            # self.filterchain_group_play: sink where the playback/saved stream should
            # be sent
            self.filterchain_group_play = PlaybackFilterChainGroup(
                datamodel     = singleton.data_model,
                gpu_handler   = self.gpu_handler, 
                cpu_scheme    = self.cpu_scheme)
            self.filterchain_group_play.read()
            # print("openValkka: self.filterchain_group_play: len=", len(self.filterchain_group_play))
            # connect live & playback filterchains with the manager
            for valkkafs, inputfilter in self.valkkafsmanager.iterateFsInput():
                _id = self.valkka_fs_handler.getId(valkkafs)
                if _id is None:
                    print("WARNING: main: could not get id for", valkkafs)
                    continue
                playback_fc=self.filterchain_group_play.get(_id=_id)
                if playback_fc is None:
                    print("WARNING: main: could not find _id", _id,\
                        "in playback filterchain group")
                    """
                    for chain in self.filterchain_group_play.chains:
                        print(">>", chain)
                        for key, getter in chain.iterateGetters():
                            print(">", key, getter())
                    """
                    continue
                live_fc=self.filterchain_group.get(_id=_id)
                if live_fc is None:
                    print("WARNING: main: could not find _id", _id,\
                        "in live filterchain group")
                    continue
                self.valkkafsmanager.map_(
                    valkkafs=valkkafs,
                    # read & cached stream is sent/output'd here:
                    framefilter=playback_fc.getInputFilter(),
                    write_slot=live_fc.slot,
                    read_slot=playback_fc.slot,
                    _id=_id
                )
                # frames coming from the live stream are sent to
                # valkkafsmanager's correct inputfilter
                # (there is one corresponding to each valkkafs)
                live_fc.connectRecTo(
                    inputfilter,
                    RecordType.always
                    )
                # TODO: disconnect at exit..?

            # self.filterchain_group.update() # TODO: use this once fixed
            self.playback_controller = PlaybackController(
                valkkafs_manager = self.valkkafsmanager
            )

                
    def closeValkka(self):
        # live => chain => opengl
        #self.livethread.close()
        # self.usbthread.close()

        print("Closing live & usb threads")
        # close filterchains from beginning-to-end => threads first
        self.livethread.requestClose()
        self.usbthread.requestClose()
        self.livethread.waitClose()
        self.usbthread.waitClose()
        
        print("Closing filterchains")
        self.filterchain_group.close()
        if singleton.use_playback:
            self.filterchain_group_play.close()

        print("Closing OpenGLThreads")
        self.gpu_handler.close()

        print("Closing ValkkaFS threads")
        if singleton.use_playback:
            self.playback_controller.close()
            self.valkkafsmanager.close()
        
        # print("Closing multiprocessing frontend")
        """
        if singleton.thread:
            singleton.thread.stop()
        """

    def reOpenValkka(self):
        print("gui: valkka reinit")
        self.wait_window.show()
        self.saveWindowLayout() # overwrites the layout
        self.closeContainers()
        self.closeValkka()
        self.openValkka()
        self.loadWindowLayout()
        self.wait_window.hide()


    def startThreads(self):
        print(">startThreads")
        if singleton.start_www:
            from valkka.web.thread import WWWQThread, WebSocketThread
            self.www_thread = WWWQThread(
                singleton.ipc_dir.getFile("pyramid.ipc"),
                singleton.www_module
            )
            self.ws_thread = WebSocketThread(
                singleton.ipc_dir.getFile("ws.ipc")
            )
            self.ws_thread.signals.base.connect(self.ws_message_slot)
            print(">startThread: starting")
            self.www_thread.start()
            self.ws_thread.start()


    def closeThreads(self):
        if singleton.start_www:
            self.ws_thread.close()
            self.www_thread.close()


    def ws_message_slot(self, obj):
        print("Main thread got ws message", obj)
        id_ = obj["id"]
        # let's do ping-pong game with the web frontend
        self.ws_thread.command.emit({
            "id" : id_,
            "class" : "base",
            "name"  : "pong",
            "parameters" : None
        })



    # *** slot generators ***

    def makeGridSlot(self, n, m):
        """Create a n x m video grid, show it and add it to the list of video containers
        """
        def slot_func():
            cont = container.VideoContainerNxM(
                gpu_handler         = self.gpu_handler, 
                filterchain_group   = self.filterchain_group, 
                n_dim               = n, 
                m_dim               = m
                )
            cont.signals.closing.connect(self.rem_grid_container_slot)
            self.containers_grid.append(cont)
            self.getMargins()
        setattr(self, "grid_%ix%i_slot" % (n, m), slot_func)


    def makePlaybackGridSlot(self, n, m):
        """Create a n x m video grid, show it and add it to the list of video containers
        """
        def slot_func():
            cont = container.PlayVideoContainerNxM(
                gpu_handler         = self.gpu_handler, 
                filterchain_group   = self.filterchain_group_play, 
                n_dim               = n, 
                m_dim               = m,
                valkkafsmanager     = self.valkkafsmanager,
                playback_controller = self.playback_controller
                )
            cont.signals.closing.connect(self.rem_playback_grid_container_slot)
            self.containers_playback.append(cont)
        setattr(self, "playback_grid_%ix%i_slot" % (n, m), slot_func)


    def makeMvisionSlot(self, cl):
        if hasattr(cl, "auto_connect") and cl.auto_connect == False:
            return
        def slot_func():
            # print(">process_map", singleton.process_map)
            if ( (cl.tag in singleton.process_map) and (len(singleton.process_map[cl.tag])>0) ):
                cont = container.VideoContainerNxM(
                    parent            = None,
                    gpu_handler       = self.gpu_handler,
                    filterchain_group = self.filterchain_group,
                    title             = cl.name,
                    n_dim             = 1,
                    m_dim             = 1,
                    child_class       = container.MVisionContainer,
                    child_class_pars  = {
                        "mvision_class": cl,
                        }, 
                    )
                cont.signals.closing.connect(self.rem_grid_container_slot)
                self.containers_grid.append(cont)
            else:
                QtWidgets.QMessageBox.about(self,"Enough!","Can't instantiate more detectors of this type (max number is "+str(cl.max_instances)+")")     
        setattr(self, cl.name+"_slot", slot_func)


    def makeMvisionClientSlot(self, cl):
        if hasattr(cl, "auto_connect") and cl.auto_connect == False:
            return
        def slot_func():
            # print(">process_map", singleton.process_map)
            if ( (cl.tag in singleton.client_process_map) and len(singleton.client_process_map[cl.tag]) > 0 ):
                master_tag = cl.master
                if singleton.get_avail_master_process(master_tag) is not None:
                    cont = container.VideoContainerNxM(
                        parent            = None,
                        gpu_handler       = self.gpu_handler,
                        filterchain_group = self.filterchain_group,
                        title             = cl.name,
                        n_dim             = 1,
                        m_dim             = 1,
                        child_class       = container.MVisionClientContainer,
                        child_class_pars  = {
                            "mvision_class": cl,
                            }, 
                        )
                    cont.signals.closing.connect(self.rem_grid_container_slot)
                    self.containers_grid.append(cont)
                else:
                    QtWidgets.QMessageBox.about(self,"Enough!","Can't instantiate more master processes for this detector")    
            else: 
                QtWidgets.QMessageBox.about(self,"Enough!","Can't instantiate more detectors of this type (max number is "+str(cl.max_instances)+")")     
        setattr(self, cl.name+"_slot", slot_func)


    # *** SLOTS ***

    # container related slots

    def rem_grid_container_slot(self, cont):
        print("gui: rem_grid_container_slot: removing container:",cont)
        print("gui: rem_grid_container_slot: containers:",self.containers_grid)
        try:
            self.containers_grid.remove(cont)
        except ValueError:
            print("gui: could not remove container",cont)
        print("gui: rem_grid_container_slot: containers now:", pformat(self.containers_grid))


    def rem_playback_grid_container_slot(self, cont):
        print("gui: rem_playback_grid_container_slot: removing container:",cont)
        print("gui: rem_playback_grid_container_slot: containers:",self.containers_playback)
        try:
            self.containers_playback.remove(cont)
        except ValueError:
            print("gui: could not remove container",cont)
        print("gui: rem_playback_grid_container_slot: containers now:", pformat(self.containers_playback))



        
    # explictly defined slot functions

    def exit_slot(self):
        self.close()

    def config_dialog_slot(self):
        self.config_modified = False
        self.valkkafs_modified = False
        self.config_win.show()
        self.manage_cameras_container.choose_first_slot()
        
    def config_modified_slot(self):
        self.config_modified = True # restart valkka services
        
    def valkkafs_modified_slot(self):
        self.config_modified = True # restart valkka services
        self.valkkafs_modified = True # reset streams

    def camera_list_slot(self):
        self.camera_list_win.show()
    
    def config_dialog_close_slot(self):
        if (self.config_modified):
            self.updateCameraTree()
            self.reOpenValkka()
    
    def save_window_layout_slot(self):
        self.saveWindowLayout()

    def load_window_layout_slot(self):
        self.loadWindowLayout()

    def about_slot(self):
        QtWidgets.QMessageBox.about(self, "About", constant.program_info % (version.get(), version.getValkka()))


"""
def process_cl_args():

    def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")

    parser = argparse.ArgumentParser("valkka-live")
    parser.register('type','bool',str2bool)    
    # parser.add_argument("command", action="store", type=str,                 
    #    help="mandatory command)")
    parser.add_argument("--quiet", action="store", type=bool, default=False, 
        help="less verbosity")

    parser.add_argument("--reset", action="store", type=bool, default=False, 
        help="less verbosity")

    parser.add_argument("--load", action="store", type=bool, default=False, 
        help="load the saved layout")

    parsed_args, unparsed_args = parser.parse_known_args()
    return parsed_args, unparsed_args


def main():
    raise(BaseException("use main.py instead"))

    parsed_args, unparsed_args = process_cl_args()
    
    #print(parsed_args, unparsed_args)
    #return

    if len(unparsed_args) > 0:
        print("Unknown command-line argument", unparsed_args[0])
        return

    if parsed_args.quiet:
        # core.setLogLevel_valkkafslogger(loglevel_debug)
        print("libValkka verbosity set to fatal messages only")
        core.fatal_log_all()

    MyGui = get_valkka_live_universe()

    if parsed_args.reset:
        singleton.config_dir.reMake()

    app = QtWidgets.QApplication(["Valkka Live"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()
"""