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
@version 0.2.0 
@brief   Main graphical user interface for the Valkka Live program
"""


from valkka_live import constant
import imp
try:
    imp.find_module('valkka')
except ImportError:
    print(constant.valkka_core_not_found)
    raise SystemExit()

from valkka_live import version
version.check() # checks the valkka version

import sys
import json
import pickle
from valkka.api2 import LiveThread
from valkka.api2.chains import ManagedFilterchain, ManagedFilterchain2, ViewPort
from valkka.api2.tools import parameterInitCheck
from PySide2 import QtWidgets, QtCore, QtGui  # Qt5
from valkka_live.menu import FileMenu, ViewMenu, ConfigMenu, AboutMenu
from valkka_live.gpuhandler import GPUHandler
from valkka_live import style, container, tools, constant
from valkka_live import default
from valkka_live.cpu import CPUScheme
from valkka_live.quickmenu import QuickMenu, QuickMenuElement

from valkka_live.datamodel import DataModel
from valkka_live.listitem import HeaderListItem, ServerListItem, RTSPCameraListItem
from valkka_live.cameralist import BasicView
from valkka_live.filterchain import FilterChainGroup

pre = "valkka_live :"

class MyGui(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.initVars()
        self.initConfigFiles()
        self.readDB()
        self.generateMethods()
        self.setupUi()
        self.openValkka()
        self.makeLogic()
        self.post()


    def initVars(self):
        self.thread = None # a QThread that reads multiprocess pipes
        self.containers = []
        self.mvision_containers = []
        self.mvision_classes = tools.scanMVisionClasses()
        if (len(self.mvision_classes) > 0):
            self.mvision = True
        else:
            self.mvision = False

    def initConfigFiles(self):
        # self.config_file = tools.getConfigFile("config")
        self.version_file = tools.getConfigFile("version")
        self.first_start = True
        if (tools.hasConfigDir()):  # this indicates that the program has been started earlier
            ver = self.readVersionNumber()
            print("valkka_live : loading config file for version number", ver)
            if ver:
                if (ver[0] == version.VERSION_MAJOR or ver[1] == version.VERSION_MINOR):
                    self.first_start = False
                else: # incorrect version number
                    pass
                    # .. or handle migration somehow
                    
        if self.first_start:  # first time program start
            # TODO: eula could be shown here
            print(pre, "initConfigFiles : first start")
            tools.makeConfigDir()
            self.saveVersionNumber()
            # self.saveConfigFile()
            self.save_window_layout()
            self.first_start = True


    def readDB(self):
        """Datamodel includes the following files: config.dat, devices.dat
        """
        self.dm = DataModel(directory = tools.getConfigDir())
        if (self.first_start):
            print(pre, "readDB : first start")
            self.dm.clearAll()
            self.dm.saveAll()

        # If camera collection is corrupt
        if not self.dm.checkCameraCollection():
            self.dm.clearCameraCollection()


    def generateMethods(self):
        """Generate some member functions
        """
        for i in range(1, 5):
            # adds member function grid_ixi_slot(self)
            self.make_grid_slot(i, i)

        for cl in self.mvision_classes:
            self.make_mvision_slot(cl)


    def QCapsulate(self, widget, name, blocking = False):
        """Helper function that encapsulates QWidget into a QMainWindow
        """

        class QuickWindow(QtWidgets.QMainWindow):

            class Signals(QtCore.QObject):
                close = QtCore.Signal()

            def __init__(self, blocking = False, parent = None):
                super().__init__(parent)
                self.propagate = True # send signals or not
                self.setStyleSheet(style.main_gui)
                if (blocking):
                    self.setWindowModality(QtCore.Qt.ApplicationModal)
                self.signals = self.Signals()

            def closeEvent(self, e):
                if (self.propagate):
                    self.signals.close.emit()
                e.accept()
                
            def setPropagate(self):
                self.propagate = True
                
            def unSetPropagate(self):
                self.propagate = False
                

        win = QuickWindow(blocking = blocking)
        win.setCentralWidget(widget)
        win.setLayout(QtWidgets.QHBoxLayout())
        win.setWindowTitle(name)
        return win


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
        self.manage_cameras_container = self.dm.getDeviceListAndForm(None)
        self.manage_cameras_win = self.QCapsulate(
            self.manage_cameras_container.widget, "Camera Configuration", blocking = True)

        self.manage_memory_container = self.dm.getConfigForm()
        self.manage_memory_win = self.QCapsulate(
            self.manage_memory_container.widget, "Memory Configuration", blocking = True)

        self.makeCameraTree()
        self.camera_list_win = self.QCapsulate(
            self.treelist, "Camera List")

        # self.camera_list_win.show()
        # self.treelist.show()


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

        for row in self.dm.camera_collection.get():
            print(pre, "makeCameraTree : row", row)
            if (row["classname"] == DataModel.RTSPCameraRow.__name__):
                row.pop("classname")
                devices.append(
                    RTSPCameraListItem(
                        camera = DataModel.RTSPCameraDevice(**row),
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
        self.manage_cameras_win.signals.close.connect(self.save_camera_config_slot)
        self.manage_memory_container.signals.save.connect(self.save_memory_conf_slot)

        # *** Menu bar connections ***
        # the self.filemenu.exit attribute was autogenerated
        self.filemenu.exit.               triggered.connect(self.exit_slot)
        self.filemenu.save_window_layout. triggered.connect(
            self.save_window_layout_slot)
        self.filemenu.load_window_layout. triggered.connect(
            self.load_window_layout_slot)

        self.configmenu.manage_cameras.   triggered.connect(
            self.manage_cameras_slot)
        self.configmenu.memory_usage.     triggered.connect(
            self.memory_usage_slot)

        self.viewmenu.camera_list.  triggered.connect(self.camera_list_slot)
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
        """
        self.mvision_container = container.VideoContainerNxM(
            parent            = None,
            gpu_handler       = self.gpu_handler,
            filterchain_group = self.filterchain_group,
            title             = "MVision",
            n_dim             = 1,
            m_dim             = 1,
            child_class       = container.MVisionContainer,
            child_class_pars  = mvision
            )
        """


    def serializeContainers(self):
        """Serializes the current view of open video grids (i.e. the view)
        """

        """ each serialized container looks like this:
        dic={# these are used when re-instantiating the view
            "classname"  : self.__class__.__name__,
            "kwargs"     : {}, # parameters that we're used to instantiate this class
            # these parameters are used by deserialize
            "x"          : self.window.x(),
            "y"          : self.window.y(),
            "width"      : self.window.width(),
            "height"     : self.window.height(),
            "streams"    : streams
            }
        """
        container_list = []
        mvision_container_list = []
        
        for container in self.containers:
            container_list.append(container.serialize())
        
        for container in self.mvision_containers:
            mvision_container_list.append(container.serialize())
            
        return {"container_list" : container_list, "mvision_container_list" : mvision_container_list}


    """
    def saveConfigFile(self):
        configdump = json.dumps({
            "containers": self.serializeContainers()
        })

        f = open(self.config_file, "w")
        f.write(configdump)
        f.close()
        self.saveVersionNumber()


    def loadConfigFile(self):
        try:
            f = open(self.config_file, "r")
        except FileNotFoundError:
            config = constant.config_skeleton
        else:
            config = json.loads(f.read())
        return config
    """


    def saveVersionNumber(self):
        f = open(self.version_file, "w")
        f.write(version.get())
        f.close()


    def readVersionNumber(self):
        try:
            f = open(self.version_file, "r")
            st = f.read()
            f.close()
            vs = []
            for s in st.split("."):
                vs.append(int(s))
        except:
            print("valkka_live : could not read version number")
            return None
        else:
            return vs


    def openValkka(self):
        self.cpu_scheme = CPUScheme()
        
        # self.dm.camera_collection
        try:
            memory_config = next(self.dm.config_collection.get({"classname" : DataModel.MemoryConfigRow.__name__}))
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
            # verbose = True,
            verbose = False,
            affinity = self.cpu_scheme.getLive()
        )

        self.filterchain_group = FilterChainGroup(datamodel = self.dm, livethread = self.livethread, gpu_handler = self.gpu_handler, cpu_scheme = self.cpu_scheme)
        self.filterchain_group.read()
        # self.filterchain_group.update() # TODO: use this once fixed
        
        try:
            from valkka_mvision import multiprocess
        except ImportError:
            pass
        else:
            if self.mvision:
                self.thread = multiprocess.QValkkaThread()
                self.thread.start()
                
                
    def closeValkka(self):
        # live => chain => opengl
        self.livethread.close()
        self.filterchain_group.close()
        self.gpu_handler.close()
        if self.thread:
            self.thread.stop()


    def reOpenValkka(self):
        self.save_window_layout("tmplayout")
        self.closeContainers()
        self.closeValkka()
        self.openValkka()
        self.load_window_layout("tmplayout")


    def closeContainers(self):
        for container in self.containers:
            container.close()
        for container in self.mvision_containers:
            container.close()
        self.containers = []
        self.mvision_containers = []


    def closeEvent(self, e):
        print("gui : closeEvent!")
        self.closeContainers()

        self.manage_cameras_win.unSetPropagate() # don't send signals .. if you don't do this: close => closeEvent => will trigger self.reOpen
        self.manage_cameras_win.close()
        self.camera_list_win.close()

        self.closeValkka()
        self.dm.close()
        e.accept()

    # slot function makers

    def make_grid_slot(self, n, m):
        """Create a n x m video grid, show it and add it to the list of video containers
        """
        def slot_func():
            self.containers.append(
                container.VideoContainerNxM(
                    gpu_handler=self.gpu_handler, filterchain_group=self.filterchain_group, n_dim=n, m_dim=m)
            )
        setattr(self, "grid_%ix%i_slot" % (n, m), slot_func)


    def make_mvision_slot(self, cl):
        def slot_func():
            self.mvision_containers.append(
                container.VideoContainerNxM(
                parent            = None,
                gpu_handler       = self.gpu_handler,
                filterchain_group = self.filterchain_group,
                title             = cl.name,
                n_dim             = 1,
                m_dim             = 1,
                child_class       = container.MVisionContainer,
                child_class_pars  = {"mvision_class": cl}, # serializable parameters (for re-creating this container)
                child_class_pars_ = {"thread" : self.thread} # non-serializable parameters
                )
            )
        setattr(self, cl.name+"_slot", slot_func)


    def save_window_layout(self, filename = "layout"):
        container_dic = self.serializeContainers()
        print(pre, "save_window_layout : container_dic =",container_dic)
        # f = open(tools.getConfigFile(filename), "w")
        # f.write(json.dumps(container_list))
        f = open(tools.getConfigFile(filename), "wb")
        f.write(pickle.dumps(container_dic))
        f.close()


    def load_window_layout(self, filename = "layout"):
        self.closeContainers()
        
        # f = open(tools.getConfigFile(filename), "r")
        # container_list = json.loads(f.read())
        f = open(tools.getConfigFile(filename), "rb")
        container_dic = pickle.loads(f.read())
        f.close()
        print("load_window_layout: container_dic: ", container_dic)
        namespace = container.__dict__
        devices_by_id = self.dm.getDevicesById({"classname" : DataModel.RTSPCameraRow.__name__})

        for cont in container_dic["container_list"]:
            classname = cont["classname"]
            kwargs = cont["kwargs"]
            kwargs["gpu_handler"] = self.gpu_handler
            kwargs["filterchain_group"] = self.filterchain_group
            class_instance = namespace[classname]

            container_instance = class_instance(
                **kwargs)  # create the container
            # move it to the right position
            container_instance.deSerialize(cont, devices_by_id)
            self.containers.append(container_instance)

        for cont in container_dic["mvision_container_list"]:
            print("\nload_window_layout: mvision:", cont)



    # explictly defined slot functions

    def exit_slot(self):
        self.close()

    def manage_cameras_slot(self):
        self.manage_cameras_win.show()

    def memory_usage_slot(self):
        self.manage_memory_win.show()

    def camera_list_slot(self):
        self.camera_list_win.show()

    def save_memory_conf_slot(self):
        self.manage_memory_win.close()
        self.reOpenValkka()

    def save_camera_config_slot(self):
        self.updateCameraTree()
        self.reOpenValkka()

    def save_window_layout_slot(self):
        self.save_window_layout()

    def load_window_layout_slot(self):
        self.load_window_layout()

    def about_slot(self):
        QtWidgets.QMessageBox.about(self, "About", constant.program_info % (version.get(), version.getValkka()))





def main():
    app = QtWidgets.QApplication(["test_app"])
    mg = MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()
