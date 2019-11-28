"""
playback.py : A controller that brings together TimeLineWidget, CalendarWidget and the ValkkaFSManager

Copyright 2019 Sampsa Riikonen

Authors: Petri Eränkö, Sampsa Riikonen

This file is part of the Valkka Python3 examples library

Valkka Python3 examples library is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    playback.py
@author  Petri Eränkö
@author  Sampsa Riikonen
@date    2019
@version 0.9.0 
@brief   A controller that brings together TimeLineWidget, CalendarWidget and the ValkkaFSManager
"""

# stdlib
import sys
import datetime
import logging
import time

# valkka core
from valkka.api2 import  ValkkaFS, ValkkaFSManager, formatMstimestamp

# Qt
from PySide2 import QtCore, QtWidgets, QtGui

# valkka live
from valkka.live.qt.playwidget import TimeLineWidget, CalendarWidget
from valkka.live.tools import parameterInitCheck

"""
- Create one ValkkaFSManager per fs
- Create one PlaybackController per ValkkaFSManager
- Connect terminals to the controller (aka signal router)
"""


class WidgetSet:

    parameter_defs = { 
        "timeline_widget"   : None,
        "play_button"       : None,
        "stop_button"       : None,
        "calendar_widget"   : None,
        "zoom_to_fs_button" : None
        }
    
    def __init__(self, **kwargs):
        parameterInitCheck(WidgetSet.parameter_defs, kwargs, self)


class PlaybackController:
    """Signal router

    - signals and slots that end with **_click** originate from interaction with user (i.e. from a click)
    
    ::
        Signal routing

        ValkkaFSManager        method in this class


        setTimeCallback  ----> valkkafsmanager_set_time_cb
                               emits signal: set_time


        Signals of this class

        set_time 
        --> self.timeline_widget.set_time_slot


    """
    
    parameter_defs = { 
        "valkkafs_manager"  : None
    }
    
    
    class Signals(QtCore.QObject):
        set_time = QtCore.Signal(object)                # current time
        set_fs_time_limits = QtCore.Signal(object)      # filesystem time limits.   Carries a tuple
        set_block_time_limits = QtCore.Signal(object)   # loaded frames time limits.  Carries a tuple
        new_block = QtCore.Signal()                     # a new block has been created
        
    
    def __init__(self, **kwargs):
        parameterInitCheck(PlaybackController.parameter_defs, kwargs, self)
        self.signals = PlaybackController.Signals()
        
        """
        # this timer is currently disabled (see createConnections__)
        self.timelimit_check_timer = QtCore.QTimer() # timer for check timelimits
        self.timelimit_check_timer.setInterval(10000) # every ten seconds
        self.timelimit_check_timer.setSingleShot(False)
        """
        
        self.widget_sets = []
        self.createConnections__()
        """
        self.check_timelimit_slot__() # fetch the initial time limits
        self.calendar_widget.reset_day_slot_click()
        self.timeline_widget.zoomToFS()
        """

    def close(self):
        for widget_set in self.widget_sets:
            self.deregister__(widget_set)
        self.widget_sets = []
        self.valkkafs_manager.clearTime()
        
    def register(self, widget_set: WidgetSet):
        self.connectTimeLineWidget__(widget_set)
        self.connectButtons__(widget_set)
        self.connectCalendarWidget__(widget_set)

        widget_set.calendar_widget.reset_day_slot_click()
        widget_set.timeline_widget.zoomToFS()
        
        self.check_timelimit_slot__() # fetch the initial time limits
        widget_set.calendar_widget.reset_day_slot_click()
        
        self.widget_sets.append(widget_set)

    def deregister__(self, widget_set: WidgetSet):
        self.disconnectTimeLineWidget__(widget_set)
        self.disconnectButtons__(widget_set)
        self.disconnectCalendarWidget__(widget_set)

    def deregister(self, widget_set: WidgetSet):
        self.deregister__(widget_set)
        self.widget_sets.remove(widget_set)
        if len(self.widget_sets) < 1:
            self.valkkafs_manager.clearTime()
        # TODO: create a diagram of this mess!


    def createConnections__(self):
        """Connect signals to slots
        """
        # internal
        # self.timelimit_check_timer.timeout.connect(self.check_timelimit_slot__)
    
        self.connectFSManager__()
        #self.connectTimeLineWidget__()
        #self.connectButtons__()
        #self.connectCalendarWidget__()
        # self.timelimit_check_timer.start() # let's update only when there's a new block instead of regular intervals
        
        
    def connectFSManager__(self):
        """cpp callbacks to qt signals
        """
        """
        self.valkkafs_manager.setTimeCallback(lambda mstime: self.signals.set_time.emit(mstime))
        self.valkkafs_manager.setTimeLimitsCallback(lambda tup: self.signals.set_block_time_limits(tup))
        """
        self.valkkafs_manager.setTimeCallback(self.valkkafsmanager_set_time_cb)
        self.valkkafs_manager.setTimeLimitsCallback(self.valkkafsmanager_set_block_time_limits_cb)
        self.valkkafs_manager.setBlockCallback(self.valkkafsmanager_block_cb)
        
        self.signals.new_block.connect(self.check_timelimit_slot__)
        

    def connectTimeLineWidget__(self, widget_set):
        """Connections between PlaybackController and TimeLineWidget:
        
        ::
        
            PlaybackController.signals.set_fs_time_limits => TimeLineWidget.set_fs_time_limits_slot  [inform TimeLineWidget about filesystem time limits change] (1)
            PlaybackController.signals.set_block_time_limits => TimeLineWidget.set_block_time_limits_slot  [inform TimeLineWidget about loaded block timel imits change] (2)
            TimeLineWidget.signals.seek_click => PlaybackController.timeline_widget_seek_click_slot  [inform PlaybackController about a seek event]  (3)
            
        """
        timeline_widget = widget_set.timeline_widget

        # from ValkkaFSManager to widgets
        self.signals.set_fs_time_limits.connect(timeline_widget.set_fs_time_limits_slot) # (1)
        self.signals.set_block_time_limits.connect(timeline_widget.set_block_time_limits_slot) # (2)
        self.signals.set_time.connect(timeline_widget.set_time_slot)
        
        # from widgets to ValkkaFSManager
        timeline_widget.signals.seek_click.connect(self.timeline_widget_seek_click_slot)  # (3)
        

    def disconnectTimeLineWidget__(self, widget_set):
        timeline_widget = widget_set.timeline_widget

        # from ValkkaFSManager to widgets
        self.signals.set_fs_time_limits.disconnect(timeline_widget.set_fs_time_limits_slot) # (1)
        self.signals.set_block_time_limits.disconnect(timeline_widget.set_block_time_limits_slot) # (2)
        self.signals.set_time.disconnect(timeline_widget.set_time_slot)
        
        # from widgets to ValkkaFSManager
        timeline_widget.signals.seek_click.disconnect(self.timeline_widget_seek_click_slot)  # (3)
        

    def connectButtons__(self, widget_set):
        """Connect play and stop buttons
        
        ::
            play : QPushButton => PlaybackController.play_slot    (1)
            stop : QPushButton => PlaybackController.stop_slot    (2)
        """
        widget_set.play_button.clicked.connect(self.play_slot__)  # (1)
        widget_set.stop_button.clicked.connect(self.stop_slot__)  # (2)
        if widget_set.zoom_to_fs_button is not None:
            widget_set.zoom_to_fs_button.clicked.connect(widget_set.timeline_widget.zoom_fs_limits_slot)


    def disconnectButtons__(self, widget_set):
        widget_set.play_button.clicked.disconnect(self.play_slot__)  # (1)
        widget_set.stop_button.clicked.disconnect(self.stop_slot__)  # (2)
        

    def connectCalendarWidget__(self, widget_set):
        """Connections between PlaybackController and the Calendar
        
        ::
        
            PlaybackController.signals.timelimit => CalendarWidget.set_fs_time_limits_slot  [Inform CalendarWidget about time range so it can show active days]  (1)
            CalendarWidget.signals.set_day => TimeLineWidget.set_day_slot  [Inform TimeLineWidget about the maximum timerange of 24 hrs to be shown]   (2)
        """
        self.signals.set_fs_time_limits.connect(widget_set.calendar_widget.set_fs_time_limits_slot)  # (1)
        widget_set.calendar_widget.signals.set_day_click.connect(widget_set.timeline_widget.set_day_click_slot)  # (2)
        

    def disconnectCalendarWidget__(self, widget_set):
        self.signals.set_fs_time_limits.disconnect(widget_set.calendar_widget.set_fs_time_limits_slot)  # (1)
        widget_set.calendar_widget.signals.set_day_click.disconnect(widget_set.timeline_widget.set_day_click_slot)  # (2)
        

    # *** TimeLineWidget connects to these slots ***
    def timeline_widget_seek_click_slot(self, t):
        """TimeLineWidget has been clicked in time t
        
        - Check that time is within limits in (this is done also by ValkkaFSManager)
        - Call ValkkaFSManager.seek(t)
            - set target time in FileCacheThread
            - tells ValkkaFSReaderThread to send frames
            - .. from there it goes correctly through connected filterchains to OpenGLThread
            
        :param t:   millisecond timestamp
        """
        # self.valkkafs_manager.timeCallback__(t) # DEBUGGING
        # print("PlaybackController: user clicked seek to: %i == %s" % (t, formatMstimestamp(t))) # DEBUGGING
        self.valkkafs_manager.smartSeek(t)
        
    # *** Callbacks used by the ValkkaFSManager ***
    def valkkafsmanager_set_time_cb(self, t):
        if len(self.widget_sets) < 1:
            return
        self.signals.set_time.emit(t)
    
    def valkkafsmanager_set_block_time_limits_cb(self, tup):
        if len(self.widget_sets) < 1:
            return
        self.signals.set_block_time_limits.emit(tup)
        
    def valkkafsmanager_block_cb(self):
        if len(self.widget_sets) < 1:
            print("valkkafsmanager_block_cb: no clients")
            return
        print("valkkafsmanager_block_cb: emitting new_block")
        self.signals.new_block.emit()
        
    
    # *** Internal slots ***
    
    def check_timelimit_slot__(self):
        """It's time to check recording time limits
        
        - Call ValkkaFSManager.getTimeRange()
        - That call makes a copy of the blocktable (from cpp => python) and checks the filesystem timelimits
        - Emit timelimit signal with a tuple containing the time range
        """
        timerange = self.valkkafs_manager.getTimeRange()
        
        if len(timerange) < 1: # empty tuple implies no frames
            print("PlaybackController: check_timelimit_slot__ : WARNING! no timerange from ValkkaFS")
            # fabricate a dummy time : this exact moment
            current_time = int(time.time() * 1000)
            timerange = (
                current_time,
                current_time + 1
                )
        print("check_timelimit_slot__ : timerange =", timerange)
        print("check_timelimit_slot__ : %s -> %s" % ( formatMstimestamp(timerange[0]), formatMstimestamp(timerange[1]) ) )
        self.signals.set_fs_time_limits.emit(timerange)
        
    def play_slot__(self):
        """Tell ValkkaFSManager to play
        """
        print("play_slot__")
        self.valkkafs_manager.play()
        
        
    def stop_slot__(self):
        """Tell ValkkaFSManager to stop
        """
        print("stop_slot__")
        self.valkkafs_manager.stop()
        
        
    """
    def zoom_to_fs_slot__(self):
        #Zoom to filesystem limits
        self.timeline_widget.zoomToFS()
    """




class MyGui(QtWidgets.QMainWindow):


    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.setupUi()
    

    def setupUi(self):
        self.setGeometry(QtCore.QRect(100,100,800,800))
        self.w=QtWidgets.QWidget(self)
        self.setCentralWidget(self.w)
        self.lay=QtWidgets.QVBoxLayout(self.w)
        
        self.timelinewidget = TimeLineWidget(datetime.date.today(), parent = self. w)
        self.timelinewidget.setLogLevel(logging.DEBUG)
        self.lay.addWidget(self.timelinewidget)
        
        self.calendarwidget = CalendarWidget(datetime.date.today(), parent = self.w)
        
        self.buttons = QtWidgets.QWidget(self.w)
        self.buttons_lay = QtWidgets.QHBoxLayout(self.buttons)
        self.play_button = QtWidgets.QPushButton("play", self.buttons)
        self.stop_button = QtWidgets.QPushButton("stop", self.buttons)
        self.buttons_lay.addWidget(self.play_button)
        self.buttons_lay.addWidget(self.stop_button)
        
        self.lay.addWidget(self.buttons)
        self.lay.addWidget(self.calendarwidget)
        
        self.valkkafs = ValkkaFS.loadFromDirectory(dirname="/home/sampsa/tmp/testvalkkafs")
        self.manager = ValkkaFSManager(self.valkkafs)

        self.manager.setOutput_(925412, 1) # id => slot
        
        self.playback_controller = PlaybackController(
            calendar_widget     = self.calendarwidget,
            timeline_widget     = self.timelinewidget,
            valkkafs_manager    = self.manager,
            play_button         = self.play_button,
            stop_button         = self.stop_button
            )
        
        """
        t = int(time.mktime(datetime.date.today().timetuple())*1000)    
        self.timelinewidget.setFSTimeLimits((t + int(1000*2*3600), t + int(1000*20*3600)))
        
        t = int(time.mktime(datetime.date.today().timetuple())*1000)    
        self.timelinewidget.setBlockTimeLimits((t + int(1000*6*3600), t + int(1000*14*3600)))
        
        
        d = datetime.date.today()
        d0 = datetime.date(year = d.year, month = d.month, day = d.day - 2)
        d1 = datetime.date(year = d.year, month = d.month, day = d.day + 3)
        
        t0 = int(time.mktime(d0.timetuple())*1000)
        t1 = int(time.mktime(d1.timetuple())*1000)
        
        self.calendarwidget.set_fs_time_limits_slot((t0, t1))
        """
        
        
    
def main():
    app=QtWidgets.QApplication(["test_app"])
    mg=MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()


 
