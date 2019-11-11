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
@version 0.8.0 
@brief   Main graphical user interface for the Valkka Live program
"""
import imp
import sys
import pydoc

from valkka.live import constant
from valkka.live.tools import importerror

try:
    import valkka.core
except importerror:
    print(constant.valkka_core_not_found)
    raise SystemExit()

from valkka.live import version
version.check() # checks the valkka version

import json
import pickle
from pprint import pprint, pformat

from valkka.api2 import LiveThread, USBDeviceThread
# from valkka.api2.chains import ManagedFilterchain, ManagedFilterchain2, ViewPort
from valkka.api2.tools import parameterInitCheck

from PySide2 import QtWidgets, QtCore, QtGui  # Qt5

from valkka.live import singleton
from valkka.live.menu import FileMenu, ViewMenu, ConfigMenu, AboutMenu
from valkka.live.gpuhandler import GPUHandler
from valkka.live import style, container, tools, constant
from valkka.live import default
from valkka.live.cpu import CPUScheme
from valkka.live.quickmenu import QuickMenu, QuickMenuElement
from valkka.live.qt.tools import QCapsulate, QTabCapsulate

from valkka.live.datamodel.base import DataModel
from valkka.live.datamodel.row import RTSPCameraRow, EmptyRow, USBCameraRow, MemoryConfigRow
from valkka.live.device import RTSPCameraDevice, USBCameraDevice

from valkka.live.listitem import HeaderListItem, ServerListItem, RTSPCameraListItem, USBCameraListItem
from valkka.live.cameralist import BasicView

from valkka.live.filterchain import FilterChainGroup

pre = "valkka.live :"

class MyGui(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        """ctor
        """
        super(MyGui, self).__init__()
        self.initVars()
        self.initConfigFiles()
        self.readDB()
        self.generateMethods()
        self.setupUi()
        self.startProcesses()
        self.openValkka()
        self.makeLogic()
        self.post()
        
        
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
        
        self.config_win.unSetPropagate()
        self.config_win.close()

        self.closeValkka()
        singleton.data_model.close()
        
        self.closeProcesses()
        e.accept()
    

    def initVars(self):
        """Define files & variables
        """
        self.version_file = tools.getConfigFile("version")
        self.layout_file = tools.getConfigFile("layout")
        
        # singleton.thread = None # a QThread that reads multiprocessing pipes
        
        self.containers_grid = [] # list of instances of valkka.live.container.grid.VideoContainerNxM
        
        self.mvision_classes = tools.scanMVisionClasses() # scans for submodules in namespace valkka.mvision.*
        if (len(self.mvision_classes) > 0):
            self.mvision = True
        else:
            self.mvision = False

    def initConfigFiles(self):
        self.first_start = True
        if (tools.hasConfigDir()):  # this indicates that the program has been started earlier
            ver = self.readVersionNumber()
            print("valkka.live : loading config file for version number")
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
            tools.makeConfigDir()
            self.saveVersionNumber()
            # self.saveConfigFile()
            self.saveWindowLayout()
            self.first_start = True


    def readDB(self):
        """Datamodel includes the following files: config.dat, devices.dat
        """
        singleton.data_model = DataModel(directory = tools.getConfigDir())
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
        container_dic = self.serializeContainers()
        print(pre, "saveWindowLayout : container_dic =", pformat(container_dic))
        with open(self.layout_file, "wb") as f:
            f.write(pickle.dumps(container_dic))
        

    def loadWindowLayout(self):
        self.closeContainers()
        with open(self.layout_file, "rb") as f:
            container_dic = pickle.loads(f.read())
        print("loadWindowLayout: container_dic: ", pformat(container_dic))
        self.deSerializeContainers(container_dic)


    # *** Generate Qt structures ***

    def generateMethods(self):
        """Autogenerate some member functions
        
        - Generates slot functions for launching containers
        """
        for i in range(1, 5):
            # adds member function grid_ixi_slot(self)
            self.makeGridSlot(i, i)

        for cl in self.mvision_classes:
            self.makeMvisionSlot(cl)


    def setupUi(self):
        self.setStyleSheet(style.main_gui)
        self.setWindowTitle("Valkka Live")

        self.setGeometry(QtCore.QRect(100, 100, 500, 500))

        self.w = QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)

        self.filemenu = FileMenu(parent=self)
        self.viewmenu = ViewMenu(parent=self)  # grids up to 4x4
        self.configmenu = ConfigMenu(parent=self)

        if self.mvision:
            mvision_elements = []

            for cl in self.mvision_classes:
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
        self.manage_valkkafs_container = singleton.data_model.getValkkaFSForm()

        self.manage_memory_container.signals.save.connect(self.config_modified_slot)
        self.manage_cameras_container.getForm().signals.save_record.connect(self.config_modified_slot)
        

        self.config_win = QTabCapsulate(
                "Configuration",
                [ 
                    (self.manage_cameras_container. widget, "Camera Configuration"),
                    (self.manage_memory_container.  widget, "Memory Configuration"),
                    (self.manage_valkkafs_container.widget, "Recording Configuration")
                ]
            )

        self.config_win.signals.close.connect(self.config_dialog_close_slot)
        # when the configuration dialog is reopened, inform the camera configuration form .. this way it can re-check if usb cams are available
        self.config_win.signals.show.connect(self.manage_cameras_container.getForm().show_slot) 

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
        self.aboutmenu.about_valkka_live. triggered.connect(self.about_slot)

        # *** Connect autogenerated menu calls into autogenerated slot functions ***
        for i in range(1, 5):
            # gets member function grid_ixi_slot
            slot_func = getattr(self, "grid_%ix%i_slot" % (i, i))
            # gets member function grid_ixi from self.viewmenu.video_grid
            menu_func = getattr(self.viewmenu.video_grid,
                                "grid_%ix%i" % (i, i))
            menu_func.triggered.connect(slot_func)
            # i.e., like this : self.viewmenu.video_grid.grid_1x1.triggered.connect(slot_func)


        # *** autogenerated machine vision menu and slots ***
        for cl in self.mvision_classes:
            getattr(self.mvisionmenu,cl.name).triggered.connect(getattr(self,cl.name+"_slot"))


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
        """
        container_list = [] # list of instances of classes in valkka.live.container, e.g. valkka.live.container.grid.VideoContainerNxM, etc.
        
        for container in self.containers_grid:
            # these are of the type valkka.live.container.grid.VideoContainerNxM
            print("gui: serialize containers : container=", pformat(container))
            container_list.append(container.serialize())
        
        # classnames compatible with local namespace
        return {
            "valkka.live.container.grid.VideoContainerNxM"   : container_list
            }


    def deSerializeContainers(self, dic):
        """Re-creates containers, based on the input dictionary, as returned by self.serializeContainers
        
        This is the inverse of self.serializeContainers
        
        Containers must be closed & self.contiainers etc. list must be cleared before calling this
        """
        # glo = globals()
        # print("glo>",glo)
        singleton.reCacheDevicesById() # singleton.devices_by_id will be used by the containers
        
        # must use makeGridSlot & makeMvisionSlot here!
        
        for key, value in dic.items(): # main container classes
            class_instance = pydoc.locate(key) # key is a complete python module path, e.g. "valkka.live.container.grid.VideoContainerNxM"
            for container_kwargs in value: # value is a list of containers of type key, each list element is a dictionary of serialized parameters
                ok = False
                
                # non-serialized parameters:
                dic = {
                    "parent"            : None,
                    "gpu_handler"       : self.gpu_handler,         # RootContainers(s) pass this downstream to child containers
                    "filterchain_group" : self.filterchain_group    # RootContainers(s) pass this downstream to child containers
                    }
                dic.update(container_kwargs)
                
                # container-specific parameters
                if key == "valkka.live.container.grid.VideoContainerNxM":
                    lis = self.containers_grid
                    print("deSerializeContainers: dic =", dic)
                    child_class = dic["child_class"]
                    
                    # check the children objects of the main video container
                    if child_class == valkka.live.container.video.VideoContainer:
                        ok = True
                    elif child_class == valkka.live.container.mvision.MVisionContainer:
                        """
                        if ( (cl.tag in singleton.process_map) and (len(singleton.process_map[cl.tag])>0) ):
                            ok = True
                        else:
                            print("deSerializeContainers:","Enough!","Can't instantiate more detectors of this type (max number is "+str(cl.max_instances)+")")
                        """
                        ok = True
                        # an example how the child container parameters must be updated
                        # such parameters should be singletons
                        """
                        for child_par in dic["child_pars"]:
                            child_par.update({
                                "thread"        : self.thread,
                                "process_map"   : self.process_map
                                })
                        """
                if ok:
                    container = class_instance(**dic) # instantiate container
                    container.signals.closing.connect(self.rem_grid_container_slot)
                    lis.append(container)
                    

    def closeContainers(self):
        print("gui: closeContainers: containers_grid =", self.containers_grid)
        for container in self.containers_grid:
            container.close()
        self.containers_grid = []
        

    # *** Multiprocess handling ***

    def startProcesses(self):
        """Create and start python multiprocesses
        
        Starting a multiprocess creates a process fork.
        
        In theory, there should be no problem in first starting the multithreading environment and after that perform forks (only the thread requestin the fork is copied), but in practice, all kinds of weird behaviour arises.
        
        Read all about it in here : http://www.linuxprogrammingblog.com/threads-and-fork-think-twice-before-using-them
        """
        singleton.process_map = {} # each key is a list of started multiprocesses
        # self.process_avail = {} # count instances
        
        for mvision_class in self.mvision_classes:
            name = mvision_class.name
            tag  = mvision_class.tag
            num  = mvision_class.max_instances        
            if (tag not in singleton.process_map):
                singleton.process_map[tag] = []
                # self.process_avail[tag] = num
                for n in range(0, num):
                    p = mvision_class()
                    p.start()
                    singleton.process_map[tag].append(p)
        
        
    def closeProcesses(self):
        for key in singleton.process_map:
            for p in singleton.process_map[key]:
                p.stop()
            
    # *** Valkka ***
        
    def openValkka(self):
        self.cpu_scheme = CPUScheme()
        
        # singleton.data_model.camera_collection
        try:
            memory_config = next(singleton.data_model.config_collection.get({"classname" : MemoryConfigRow.__name__}))
        except StopIteration:
            print(pre, "Using default mem config")
            memory_config = default.memory_config

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

        self.filterchain_group = FilterChainGroup(datamodel     = singleton.data_model, 
                                                  livethread    = self.livethread, 
                                                  usbthread     = self.usbthread,
                                                  gpu_handler   = self.gpu_handler, 
                                                  cpu_scheme    = self.cpu_scheme)
        self.filterchain_group.read()
        # self.filterchain_group.update() # TODO: use this once fixed
        
        try:
            from valkka.mvision import multiprocess
        except ImportError:
            pass
        else:
            if self.mvision:
                singleton.thread = multiprocess.QValkkaThread()
                singleton.thread.start()
                
                
    def closeValkka(self):
        # live => chain => opengl
        self.livethread.close()
        self.usbthread.close()
        self.filterchain_group.close()
        self.gpu_handler.close()
        if singleton.thread:
            singleton.thread.stop()


    def reOpenValkka(self):
        print("gui: valkka reinit")
        self.wait_window.show()
        self.saveWindowLayout()
        self.closeContainers()
        self.closeValkka()
        self.openValkka()
        self.loadWindowLayout()
        self.wait_window.hide()


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
        setattr(self, "grid_%ix%i_slot" % (n, m), slot_func)


    def makeMvisionSlot(self, cl):
        def slot_func():
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
                        "thread"       : singleton.thread,
                        "process_map"  : singleton.process_map
                        }, 
                    )
                cont.signals.closing.connect(self.rem_grid_container_slot)
                self.containers_grid.append(cont)
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
        
        
    # explictly defined slot functions

    def exit_slot(self):
        self.close()

    def config_dialog_slot(self):
        self.config_modified = False
        self.config_win.show()
        self.manage_cameras_container.choose_first_slot()
        
    def config_modified_slot(self):
        self.config_modified = True
        
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



def main():
    app = QtWidgets.QApplication(["Valkka Live"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()
