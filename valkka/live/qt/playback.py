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
@version 1.2.2 
@brief   A controller that brings together TimeLineWidget, CalendarWidget and the ValkkaFSManager
"""

# stdlib
import sys
import datetime
import logging
import time

# Qt
# from PySide2 import QtCore, QtWidgets, QtGui
from valkka.live.qimport import QtWidgets, QtCore, QtGui, Signal, Slot  # Qt5

# from local directory
# take these from valkka_examples:
from .playwidget import TimeLineWidget, CalendarWidget

# valkka
from valkka.fs import ValkkaFSManager, formatMstimestamp, formatMstimeTuple
from valkka.api2.tools import getLogger, setLogger, parameterInitCheck


class WidgetSet:
    """Set of control widgets

    We might have many of these, all connected to the
    same PlaybackController
    """

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
    """ValkkaFSManager has several callbacks that can be continued 
    here as qt signals

    in connectFSManager__:

    ::

        ValkkaFSManager.setTimeCallback
            valkkafsmanager_set_time_cb(self, mstime = 0, valkkafs = None)
                Signals.set_time(mstime)
        
        ValkkaFSManager.setTimeLimitsCallback
            valkkafsmanager_set_cached_time_limits_cb(self, timerange = (0,0), valkkafs = None)
                Signals.set_cached_time_limits(timerange)

        ValkkaFSManager.setBlockCallback
            valkkafsmanager_block_cb(self, timerange = (0,0), valkkafs = None)
                Signals.new_block(timerange)

   Those signals are then connected to the TimeLineWidget in 
   connectTimeLineWidget__:

   ::

        Signals.set_fs_time_limits
            TimeLineWidget.set_fs_time_limits_slot(timerange)

        Signals.set_cached_time_limits
            TimeLineWidget.set_block_time_limits_slot(timerange)

        TimeLineWidget.Signals.seek_click
            self.timeline_widget_seek_click_slot(t)
                ValkkaFSManager.seek(t)

        Signals.set_time
            TimeLineWidget.set_time_slot(mstime)


    connectInternal__: translate from new_block signal
    to filesystem timelimits signal:

    ::

        Signals.new_block
            self.new_block_slot(timerange)
                Signals.set_fs_time_limits(timerange)


    connectCalendarWidget__:

    ::

        Signals.set_fs_time_limits
            CalendarWidget.set_fs_time_limits_slot

        CalendarWidget.Signals.set_day_click
            TimeLineWidget.set_day_click_slot



    TODO

    use the register/deregister scheme from Valkka Live here




    """
    parameter_defs = {
        #"timeline_widget"   : None,
        "valkkafs_manager"  : None,
        #"play_button"       : None,
        #"stop_button"       : None,
        #"calendar_widget"   : None,
        #"zoom_to_fs_button" : None
        }
    
    
    class Signals(QtCore.QObject):
        set_time = QtCore.Signal(object)                # current time
        set_fs_time_limits = QtCore.Signal(object)      # filesystem time limits.   Carries a tuple
        set_cached_time_limits = QtCore.Signal(object)  # loaded frames time limits.  Carries a tuple
        new_block = QtCore.Signal(object)               # a new block has been created
        
    
    def __init__(self, **kwargs):
        parameterInitCheck(PlaybackController.parameter_defs, kwargs, self)
        self.signals = PlaybackController.Signals()
        self.logger = getLogger(self.__class__.__name__)
        # setLogger(self.logger, logging.DEBUG) # TODO: unify logging somehow
        # this timer is currently disabled (see createConnections__)
        self.timelimit_check_timer = QtCore.QTimer() # timer for check timelimits
        self.timelimit_check_timer.setInterval(10000) # every ten seconds
        self.timelimit_check_timer.setSingleShot(False)
        
        self.widget_sets = []
        self.createConnections__()
        """
        # self.new_block_slot__() # fetch the initial time limits
        self.calendar_widget.reset_day_slot_click()
        self.timeline_widget.zoomToFS()
        """

    def close(self):
        for widget_set in self.widget_sets:
            self.deregister__(widget_set)
        self.widget_sets = []


    def register(self, widget_set: WidgetSet):
        self.connectTimeLineWidget__(widget_set)
        self.connectButtons__(widget_set)
        self.connectCalendarWidget__(widget_set)
        widget_set.calendar_widget.reset_day_slot_click()
        widget_set.calendar_widget.reset_day_slot_click()
        self.widget_sets.append(widget_set)
        self.valkkafs_manager.update() # propagates all info from callbacks to signals
        widget_set.timeline_widget.zoom_fs_limits_slot()

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
        self.connectFSManager__()
        self.connectInternal__()
        #self.connectTimeLineWidget__()
        #self.connectButtons__()
        #self.connectCalendarWidget__()
        
    def connectInternal__(self):
        self.signals.new_block.connect(self.new_block_slot__)
        
    def connectFSManager__(self):
        """cpp callbacks to qt signals
        """
        """
        self.valkkafs_manager.setTimeCallback(lambda mstime: self.signals.set_time.emit(mstime))
        self.valkkafs_manager.setTimeLimitsCallback(lambda tup: self.signals.set_cached_time_limits(tup))
        """
        self.valkkafs_manager.setTimeCallback(self.valkkafsmanager_set_time_cb)
        self.valkkafs_manager.setTimeLimitsCallback(self.valkkafsmanager_set_cached_time_limits_cb)
        self.valkkafs_manager.setBlockCallback(self.valkkafsmanager_block_cb)
        
    def connectTimeLineWidget__(self, widget_set):
        """Connections between PlaybackController and TimeLineWidget
        """
        timeline_widget = widget_set.timeline_widget
        # from ValkkaFSManager to widgets
        self.signals.set_fs_time_limits.connect(timeline_widget.set_fs_time_limits_slot) # (1)
        self.signals.set_cached_time_limits.connect(timeline_widget.set_block_time_limits_slot) # (2)
        self.signals.set_time.connect(timeline_widget.set_time_slot)
        # from widgets to ValkkaFSManager
        timeline_widget.signals.seek_click.connect(self.timeline_widget_seek_click_slot)  # WTF!?
        
    def disconnectTimeLineWidget__(self, widget_set):
        timeline_widget = widget_set.timeline_widget
        # from ValkkaFSManager to widgets
        self.signals.set_fs_time_limits.disconnect(timeline_widget.set_fs_time_limits_slot) # (1)
        self.signals.set_cached_time_limits.disconnect(timeline_widget.set_block_time_limits_slot) # (2)
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
            widget_set.zoom_to_fs_button.clicked.connect(
                widget_set.timeline_widget.zoom_fs_limits_slot
            )

    def disconnectButtons__(self, widget_set):
        widget_set.play_button.clicked.disconnect(self.play_slot__)  # (1)
        widget_set.stop_button.clicked.disconnect(self.stop_slot__)  # (2)
        if widget_set.zoom_to_fs_button is not None:
            widget_set.zoom_to_fs_button.clicked.disconnect(
                widget_set.timeline_widget.zoom_fs_limits_slot
            )

    def connectCalendarWidget__(self, widget_set):
        """Connections between PlaybackController and the Calendar
        
        ::
        
            PlaybackController.signals.timelimit => CalendarWidget.set_fs_time_limits_slot  [Inform CalendarWidget about time range so it can show active days]  (1)
            CalendarWidget.signals.set_day => TimeLineWidget.set_day_slot  [Inform TimeLineWidget about the maximum timerange of 24 hrs to be shown]   (2)
        """
        self.signals.set_fs_time_limits.connect(
            widget_set.calendar_widget.set_fs_time_limits_slot)  # (1)
        widget_set.calendar_widget.signals.set_day_click.connect(
            widget_set.timeline_widget.set_day_click_slot)  # (2)
        
    def disconnectCalendarWidget__(self, widget_set):
        self.signals.set_fs_time_limits.disconnect(
            widget_set.calendar_widget.set_fs_time_limits_slot)  # (1)
        widget_set.calendar_widget.signals.set_day_click.disconnect(
            widget_set.timeline_widget.set_day_click_slot)  # (2)

        
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
        self.valkkafs_manager.seek(t)
        
    # *** ValkkaFSManager connects to these slots ***
    def valkkafsmanager_set_time_cb(self, mstime = 0, valkkafs = None):
        """Time is progressing in playback
        
        - TODO: Inform calendar (the day might be changed)
        - Inform TimeLineWidget to move the time bar
        """
        self.signals.set_time.emit(mstime)
    
    def valkkafsmanager_set_cached_time_limits_cb(self, timerange = (0,0), valkkafs = None):
        self.signals.set_cached_time_limits.emit(timerange)
        
    def valkkafsmanager_block_cb(self, timerange = (0,0), valkkafs = None):
        self.signals.new_block.emit(timerange)
        
    
    # *** Internal slots ***
    
    def new_block_slot__(self, timerange):
        """Global timerange comes with the signal
        """
        # timerange = self.valkkafs_manager.getTimeRange()
        if timerange == (0,0) or timerange is None:
            self.logger.info("new_block_slot__ : no timerange from ValkkaFS")
            # fabricate a dummy time : this exact moment # TODO: why not None?
            current_time = int(time.time() * 1000)
            timerange = (
                current_time,
                current_time + 1
                )
        self.logger.debug("new_block_slot__ : timerange = %s", 
            formatMstimeTuple(timerange))
        self.signals.set_fs_time_limits.emit(timerange)
        

    def play_slot__(self):
        """Tell ValkkaFSManager to play
        """
        self.logger.debug("play_slot__")
        self.valkkafs_manager.play()
        
        
    def stop_slot__(self):
        """Tell ValkkaFSManager to stop
        """
        self.logger.debug("stop_slot__")
        self.valkkafs_manager.stop()
        
        
    def zoom_to_fs_slot__(self):
        """Zoom to filesystem limits
        """
        self.timeline_widget.zoomToFS()
    

class MyGui(QtWidgets.QMainWindow):


    def __init__(self, parent=None):
        super(MyGui, self).__init__()
        self.setupUi()
    

    def setupUi(self):
        from valkka.fs import ValkkaSingleFS

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
        self.zoom_button = QtWidgets.QPushButton("zoom", self.buttons)
        self.buttons_lay.addWidget(self.play_button)
        self.buttons_lay.addWidget(self.stop_button)
        self.buttons_lay.addWidget(self.zoom_button)
        
        self.lay.addWidget(self.buttons)
        self.lay.addWidget(self.calendarwidget)
        
        self.valkkafs = ValkkaSingleFS.newFromDirectory(
            dirname         = "/home/sampsa/tmp/testvalkkafs",
            blocksize       = 1 * 1024 * 1024, # back to bytes
            n_blocks        = 3, 
            device_size     = None, # calculate from blocksize and n_blocks
            partition_uuid  = None,
            # verbose         = True
            verbose         = False
        )

        self.manager = ValkkaFSManager([self.valkkafs])

        # self.manager.setOutput_(925412, 1) # id => slot
        
        self.playback_controller = PlaybackController(
            #calendar_widget     = self.calendarwidget,
            #timeline_widget     = self.timelinewidget,
            valkkafs_manager    = self.manager,
            #play_button         = self.play_button,
            #stop_button         = self.stop_button
            )

        self.widget_set = WidgetSet(
            timeline_widget     = self.timelinewidget,
            play_button         = self.play_button,
            stop_button         = self.stop_button,
            calendar_widget     = self.calendarwidget,
            zoom_to_fs_button   = self.zoom_button
        )

        self.playback_controller.register(
            self.widget_set
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


 
