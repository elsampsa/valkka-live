"""
playwidget.py : TimeLineWidget and CalendarWidget for Valkka

Copyright 2019 Sampsa Riikonen

Authors: Petri Eränkö, Sampsa Riikonen

This file is part of the Valkka Python3 examples library

Valkka Python3 examples library is free software: you can redistribute it and/or modify it under the terms of the MIT License.  This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the MIT License for more details.

@file    playwidget.py
@author  Petri Eränkö
@author  Sampsa Riikonen
@date    2017
@version 0.12.0 
@brief
"""

import sys
import numpy
import time, datetime
import logging
from valkka.live.tools import getLogger
from PySide2 import QtWidgets, QtCore, QtGui


def formatMstimestamp(mstime):
    t = datetime.datetime.fromtimestamp(mstime/1000)
    return "%s:%s" % (t.minute, t.second)


def genTimeStamps(time_tuple, time_tuple1, stimestep):
    time0=int(time.mktime(time_tuple))
    time1=int(time.mktime(time_tuple1))
    
    tvals=numpy.arange(time0, time1+stimestep, stimestep)
    struct_times = []
    mstimestamps = []
    for t in tvals:
        struct_times.append(time.localtime(t))
        mstimestamps.append(int(round(1000*t)))
    return struct_times, mstimestamps



def time_partition(dt, parts = [1,60,3600,24*3600]):
    res=[]
    for i, p in enumerate(parts):
        n=dt%p
        dt-=n
        if (i>0):
            res.append(int(n/parts[i-1]))
    res.append(int(dt/parts[i]))
    return res



class MouseClickContext:
    """
    Sniffs mouse clicks.  Distinguishes between:
    
    - Single click
    - Long click
    - Double click
    
    The scheme here is:

    - user clicks => atPressEvent
    - user releases => a timer is started
    - user clicks again => atPressEvent.  If timer active => this is a double click
    - If timer goes off before a new click => this is a single click
    - Once the click has completed, use a callback defined by the user
    - .. user can then inspect the MouseClickContext that comes with the call for single / double click
    """
  
    t_long_click = 2    # definition of "long" click in seconds
    t_double_click = 500  # definition of double click in milliseconds
  
    def __init__(self, callback = None):
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.callback = callback
        self.timer.timeout.connect(self.timer_slot)
    
    def atPressEvent(self, e):
        self.t = time.time()
        if (self.timer.isActive()):
            print("timer active!")
            self.double_click_flag = True
        else: 
            print("reset")
            self.double_click_flag = False
            self.button = e.button()
            self.pos = e.globalPos()
  
    def atReleaseEvent(self, e):
        dt = time.time() - self.t
        if (dt > self.t_long_click): # a "long" click
            self.long_click_flag = True
        else:
            self.long_click_flag = False
        self.timer.start(self.t_double_click)

    def getPos(self):
        return self.pos
    
    def timer_slot(self):
        if self.callback is not None:
            print("callback", self.double_click_flag)
            self.callback(self)
        

class TimeDiff:
  
    def __init__(self, t1, t2): # time in seconds
        res = time_partition(t2 - t1, parts=[1,60,3600,24*3600]) # sec,min,hour,24hrs
        self.tm_sec =res[0]
        self.tm_min =res[1]
        self.tm_hour=res[2]
        self.tm_24h =res[3]
        # self.tm_30d =res[4]
        # self.tm_year=res[5]

    def __str__(self):
        st=""
        # for name in ["tm_sec","tm_min","tm_hour","tm_24h","tm_30d","tm_year"]:
        for name in ["tm_sec","tm_min","tm_hour","tm_24h"]:
            st+=name+"="+str(getattr(self,name))+" "
        return st



class CalendarWidget(QtWidgets.QCalendarWidget):
  
    class Signals(QtCore.QObject):
        set_day_click  = QtCore.Signal(object)

    #stylesheet="""
    #QTableView{
    #selection-background-color: white;
    #selection-color: black;
    #;
    #"""

    def __init__(self, day: datetime.date, parent = None):
        super().__init__(parent)
        self.signals = self.Signals()
        self.makeTools()
        self.day_min = None
        self.day_max = None
        self.setDay(day)
        # self.setSelectionMode(QtWidgets.QCalendarWidget.NoSelection)
        # self.setStyleSheet(self.stylesheet)
        self.setGridVisible(True)
        self.clicked.connect(self.dateClick_slot)

  
    def makeTools(self):
        # brush
        self.color_base=QtCore.Qt.transparent
        # pen
        # self.pen_color =QtGui.QColor(255,0,0)
        self.pen_color =QtGui.QColor(0, 0, 200, 80)
        self.pen_base  =QtGui.QPen(self.pen_color, 1, QtCore.Qt.SolidLine)
        self.pen_base.setWidth(5)
        # font
        # self.font_base=QtGui.QFont('Arial', QtGui.QFont.Light)
        # self.font_base.setPixelSize(24)
        self.def_format=QtGui.QTextCharFormat()
        self.def_format.setBackground(QtGui.QColor(0, 0, 200, 80))
        
        self.current_day_highlight = QtGui.QTextCharFormat()
        self.current_day_highlight.setBackground(QtGui.QColor(0, 0, 200, 80))


    def setDay(self, day: datetime.date):
        """Setting the day acts as a global initializator
        """
        assert(isinstance(day, datetime.date))
        self.day = day
        # from datetime.date to Qt's QDate
        self.qday = QtCore.QDate(self.day.year, self.day.month, self.day.day)
        self.setSelectedDate(self.qday)
        
        
    def qDateToDate(self, qday):
        return datetime.date(year = qday.year(), month = qday.month(), day = qday.day())


    # qdt=QtCore.QDateTime(QtCore.QDate.currentDate())
    # mstimestamp=qdt.toMSecsSinceEpoch()
    # self.updateCells()
    # self.setSelectedDate(qdt.date())

    """
    print("CalendarWidget: chooseDate_slot:",qd)
    qtd=QtCore.QDateTime(qd)
    self.cmstimestamp=qtd.toMSecsSinceEpoch()
    print("CalendarWidget: mstimestamp",self.cmstimestamp)
    t0 =self.cmstimestamp-self.dt
    t1 =self.cmstimestamp+self.dt
    print("CalendarWidget: dateClick_slot: t0=",time.localtime(t0/1000.))
    self.time_limits_signal.emit([t0,t1])
    """
    """
    tf=self.dateTextFormat(qd)
    print("CalendarWidget: dateClick_slot: tf=",tf)
    tf.setFontItalic(True)
    tf=self.current_day_highlight
    # tf.setFontWeight(5)
    self.setDateTextFormat(qd,tf)
    # self.setDateTextFormat(None)
    """
    # self.setDateTextFormat(qd,self.def_format)

    
    def paintCell(self, qp, rect, qdate):
        """Paint current day with a frame
        """
        super().paintCell(qp, rect, qdate)
        if self.qday == qdate:
            # print("CalendarWidget: painting with a frame")
            qp.setBrush(self.color_base)
            qp.setPen(self.pen_base)
            qp.drawRect(rect.adjusted(0, 0, -1, -1))


    def dateClick_slot(self, qday):
        print("CalendarWidget: dateClick_slot")
        day = self.qDateToDate(qday)
        self.signals.set_day_click.emit(day) # inform controller that user clicked a day
        self.setDay(day)
  

    # *** Slots ****

    def set_fs_time_limits_slot(self, limits: tuple):
        """Shows active days based on the millisecond timestamp limits
        """
        self.day_min = datetime.date.fromtimestamp(limits[0]/1000)
        self.day_max = datetime.date.fromtimestamp(limits[1]/1000)
        print("CalendarWidget: set_fs_time_limits_slot %s -> %s" %(str(self.day_min), str(self.day_max)))
        
        self.setDateRange(
            QtCore.QDate(self.day_min.year, self.day_min.month, self.day_min.day),
            QtCore.QDate(self.day_max.year, self.day_max.month, self.day_max.day)
            )
        
    def set_day_slot(self, day: datetime.date):
        self.setDay(day)
        
    def reset_day_slot(self):
        if self.day_min is not None:
            self.set_day_slot(self.day_min)
        
    def reset_day_slot_click(self):
        """As if user clicked the minimum day
        """
        if self.day_min is not None:
            self.set_day_slot(self.day_min)
            self.signals.set_day_click.emit(self.day_min)
        


class TimeLineWidget(QtWidgets.QWidget):
    """A custom rectangular area with the following elements:

    UPPER_MARGIN                 | TIMEBAR
    LABELS                       |
    TIMESCALE                    |
    AREA                         |
    LOWER_MARGIN                 |


    Zoomable, pannable, clickable
    """

    class Signals(QtCore.QObject):
        seek_click = QtCore.Signal(object)


    # widget minimum dimensions
    hmin = 100
    wmin = 600

    # minimum visible time scale
    dt_min = 10000 # 10 secs

    # mouse click behaviour
    dc_treshold=0.5  # double-click treshold
    lc_treshold=1   # "long-click" treshold
    md_treshold=0.5  # if dragged this long time, then it is a drag


    # mouse click place flavors
    mouse_place_normal=0
    mouse_place_selection=1  # in the selection margin
    mouse_place_upper=2  # in the margin, but below selection margin
    mouse_place_lower=3  # lower margin

    mintimescale=5000           # 5 sec
    maxtimescale=2 * 24 * 3600 * 1000  # two days


    def __init__(self, day, parent=None):
        super().__init__(parent)
        self.signals = TimeLineWidget.Signals()
        self.logger = getLogger(__name__ + "." + self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        self.setFSTimeLimits(None)
        self.setBlockTimeLimits(None)
        self.setSelTimeLimits(None)

        self.makeTools()
        self.setDay(day)
        self.setupUi()


    def setLogLevel(self, level):
        getLogger(self.logger, level = level)


    def setDay(self, day: datetime.date):
        """Setting the day acts as a global initializator
        """
        self.mstime=None

        # TODO: set mintime and maxtime according to the day
        # Global time limits.  Any time outside this range is invisible
        
        assert(isinstance(day, datetime.date))
        t = day.timetuple()
        self.mintime = round(time.mktime(t)*1000)
        self.maxtime = self.mintime + 24*3600*1000
        
        # currently zoomed-in time
        self.t0=self.mintime
        self.t1=self.maxtime

        self.mouse_press_x = 0
        self.mouse_press_y = 0

        self.mouse_press_t = 0
        self.mouse_press_old_t = 0

        self.mouse_click_ctx = MouseClickContext(self.postMouseRelease)

        self.set_time_timer = QtCore.QTimer(self)
        self.set_time_timer.setSingleShot(True)

        self.struct_times_major = []
        self.struct_times_minor = []
        self.mstimestamps_major = []
        self.mstimestamps_minor = []

        self.makeTickMarks()
        self.reScale()
        self.repaint()


    def setFSTimeLimits(self, limits: tuple = None):
        """Marks filesystem time limits
        """
        self.fstimelimits = limits


    def setBlockTimeLimits(self, limits: tuple = None):
        """Currently loaded time limits
        """
        self.blocktimelimits = limits


    def setSelTimeLimits(self, limits: tuple = None):
        """Marks selection time limits
        """
        self.seltimelimits = limits


    def setupUi(self):
        self.setMinimumSize(self.wmin, self.hmin)


    def zoomTo(self, t0, t1):  # wheel event => calls
        """All zooming should go through this routine
        
        - Checks the boundaries
        - Enforces the minimum scale
        
        """
        t0 = max(self.mintime, t0)
        t1 = min(self.maxtime, t1)
        
        if (t1 - t0) <= self.dt_min: # discard smaller scales
            return
        
        self.t0 = t0
        self.t1 = t1
        
        # self.dt=t1 - t0
        self.makeTickMarks()
        self.reScale()
        self.repaint()


    def zoomToFS(self):
        if self.fstimelimits is not None:
            self.zoomTo(self.fstimelimits[0], self.fstimelimits[1])


    def panTo(self, t):
        dt = self.t1 - self.t0
        t0 = t
        t1 = t0 + dt
        self.logger.debug("panTO %i, %i, %i, %i", t0, t1, self.T0, self.T1)
        t0=max(self.mintime, t0)
        t1=min(self.maxtime, t1)
        self.t0=t0
        self.t1=t1
        self.makeTickMarks()
        self.reScale()
        self.repaint()


    def panRight(self):  # pans some reasonable amount
        dt = self.t1 - self.t0
        dt=int(round(dt / 10.))
        t=self.t0 + dt
        self.panTo(t)


    def panLeft(self):
        dt = self.t1 - self.t0
        dt=int(round(dt / 10.))
        t=self.t0 - dt
        self.panTo(t)


    def reScale(self):
        # y-scale
        self.h=self.height() - (self.umy + self.lmy)  # visible height
        # self.dy             =max(self.h/max(self.nline,1),self.dy_per_device)
        # # space per entry  # true height

        self.w=self.width() - (self.umx + self.lmx)

        dt = self.t1 - self.t0
        # x
        self.msec_per_pixel = dt / self.w
        # warning: in python2 this would result in rounding errors
        self.pixel_per_msec = 1 / self.msec_per_pixel

        self.reScaleVars()

        self.logger.debug("reScale: width, height  %i %i", self.w, self.h)
        self.logger.debug("reScale: msec per pixel %f", self.msec_per_pixel)
        self.logger.debug("reScale: pixel per msec %f", self.pixel_per_msec)
        self.logger.debug("reScale: max msec       %i", int(self.msec_per_pixel * self.w))
        # self.logger.debug("reScale: dy             %i", self.dy)


    def reScaleVars(self):
        pass
        """# clean this old mess for parts when they're implemented
        self.logger.debug(
            "StreamControlArea: reScaleVars: nline, parts",self.nline,self.parts)
        # don't forget margins..
        for j in range(self.nline):
        self.logger.debug("StreamControlArea: reScaleVars: j=",j)
        self.parts[j,:]=numpy.array([int(j*self.dy),int((j+1)*self.dy)],dtype=numpy.int64)
        self.parts[j]=self.parts[j]                         +self.lmy
        """

    def zoom(self, t, dire):
        right = self.t1 - t
        left = t - self.t0
        if (dire > 0):  # zoom!
            remright = right / 10.
            remleft = (left / right) * remright
            right = self.t1 - remright
            left = self.t0 + remleft
        else:       # unzoom!
            right=t + right / 0.9
            left=t - left / 0.9

        d=(right - left)

        self.zoomTo(int(round(left)), int(round(right)))


    def makeTickMarks(self):
        """Creates major and minor timestamps and labels
        """
        self.struct_times_days=[]
        self.mstimestamps_days=[]

        self.struct_times_major=[]
        self.mstimestamps_major=[]

        self.struct_times_minor=[]
        self.mstimestamps_minor=[]

        stime0=self.t0 / 1000  # from msec to sec
        stime1=self.t1 / 1000

        t0=time.localtime(stime0)  # time structs
        t1=time.localtime(stime1)

        # a timescale:
        # check the timespan
        # then, generate a struct_time, starting from a nearby time instant
        # that rounds to a desided accuracy, i.e. seconds, minutes, hours, etc.

        # time differences, partitioned in secs, mins, hours, etc.
        tdf=TimeDiff(stime0, stime1)

        smt=t0.tm_isdst  # summer time flag..

        # tm_wday, etc. must be zeroed.. otherwise this is not consistent (see
        # below)
        end_tuple=(t1.tm_year, t1.tm_mon, t1.tm_mday,
                   t1.tm_hour, t1.tm_min, t1.tm_sec, 0, 0, smt)

        start_day_tuple=(t0.tm_year, t0.tm_mon, t0.tm_mday, 0,
                         0, 0, 0, 0, smt)  # used to generate the day labels
        end_day_tuple=(t1.tm_year, t1.tm_mon, t1.tm_mday, 0, 0, 0, 0, 0, smt)

        # rule of thumb: stimestep_major ~ upper value / 5 <=> upper value ~ 5
        # x stimestep_major

        """
        if (tdf.tm_year>=1): # 1 year is supposed to be the max
            self.logger.debug("StreamControlArea: year>1 timescale")
            start_tuple_major=start_tuple_minor=(t0.tm_year,0,0,0,0,0,0,0,smt)
            stimestep_major=3600*24*30*12  # major ticks: years
            # minor ticks: months # this is more complicated .. months don't
            # have a fixed number of days.. # TODO: implement this right
            stimestep_minor=3600*24*30
        elif (tdf.tm_30d>=1):
            start_tuple_major=start_tuple_minor=(t0.tm_year,0,0,0,0,0,0,0,smt)
            if (6<tdf.tm_30d<=12):
                stimestep_major=3600*24*30 # major ticks: 1 month
                stimestep_minor=3600*24*7  # minor ticks: 7 days
            if (1<=tdf.tm_30d<=6):
                stimestep_major=3600*24*7  # major ticks: 7 days
                stimestep_minor=3600*24    # minor ticks: 1 day
        """

        if (tdf.tm_24h >= 1):
            self.logger.debug("StreamControlArea: day>1 timescale")
            start_tuple_major=start_tuple_minor=(
                t0.tm_year, t0.tm_mon, t0.tm_mday, 0, 0, 0, 0, 0, smt)
            stimestep_major=3600 * 24 * 5  # major ticks: 5 days
            stimestep_minor=3600 * 24    # minor ticks: 1 day
            if (15 < tdf.tm_24h <= 30):
                stimestep_major=3600 * 24 * 5  # major ticks: 5 days
                stimestep_minor=3600 * 24    # minor ticks: 1 day
            elif (5 < tdf.tm_24h <= 15):
                stimestep_major=3600 * 24    # major ticks: 1 day
                stimestep_minor=3600 * 12    # minor ticks: 12 hrs
            elif (1 <= tdf.tm_24h <= 5):
                stimestep_major=3600 * 12    # major ticks: 12 hrs
                stimestep_minor=3600 * 2     # minor ticks: 2 hrs

        elif (tdf.tm_hour >= 1):
            start_tuple_major=start_tuple_minor=(
                t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, 0, 0, 0, 0, smt)
            self.logger.debug("StreamControlArea: hour>1 timescale")
            if (20 < tdf.tm_hour <= 24):
                stimestep_major=3600 * 5  # major ticks: 4 hrs
                stimestep_minor=3600   # minor ticks: 1 hr
            elif (10 < tdf.tm_hour <= 20):
                stimestep_major=3600 * 2  # major ticks: 2 hrs
                stimestep_minor=60 * 30  # minor ticks: 30 min
            elif (5 < tdf.tm_hour <= 10):
                stimestep_major=int(3600 * 1.5)  # major ticks: 1.5 hrs
                stimestep_minor=60 * 30  # minor ticks: 30 min
            elif (1 <= tdf.tm_hour <= 5):
                stimestep_major=60 * 30  # major ticks
                stimestep_minor=60 * 5  # minor ticks

        elif (tdf.tm_min >= 1):
            self.logger.debug("StreamControlArea: minute>1 timescale")
            if (20 < tdf.tm_min <= 60):
                start_tuple_major=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min - \
                                   t0.tm_min % 10, 0, 0, 0, smt); stimestep_major=60 * 10  # major ticks: 10 min
                start_tuple_minor=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min,
                                   0, 0, 0, smt); stimestep_minor=60    # minor ticks: 1  min
            elif (10 < tdf.tm_min <= 20):
                start_tuple_major=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min - \
                                   t0.tm_min % 5, 0, 0, 0, smt); stimestep_major=60 * 5  # major ticks: 5  min
                start_tuple_minor=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min,
                                   0, 0, 0, smt); stimestep_minor=15    # minor ticks: 15 sec
            elif (5 < tdf.tm_min <= 10):
                start_tuple_major=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min - \
                                   t0.tm_min % 2, 0, 0, 0, smt); stimestep_major=60 * 2    # major ticks: 2 min
                start_tuple_minor=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min,
                                   0, 0, 0, smt); stimestep_minor=10      # minor ticks: 10 sec
            elif (1 <= tdf.tm_min <= 5):
                start_tuple_major=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min,
                                   0, 0, 0, smt); stimestep_major=60 * 1    # major ticks: 1 min
                start_tuple_minor=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min,
                                   0, 0, 0, smt); stimestep_minor=1       # minor ticks: 1 sec

        else:
            self.logger.debug("StreamControlArea: small timescale!")
            if (10 < tdf.tm_sec <= 60):
                start_tuple_major=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min,
                                   t0.tm_sec - t0.tm_sec % 10, 0, 0, smt); stimestep_major=10    # major ticks: 10 sec
                start_tuple_minor=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min,
                                   t0.tm_sec, 0, 0, smt); stimestep_minor=2     # minor ticks: 2 sec
            else:
                start_tuple_major=(t0.tm_year, t0.tm_mon, t0.tm_mday, t0.tm_hour, t0.tm_min,
                                   t0.tm_sec, 0, 0, smt); stimestep_major=1    # major ticks: 1
                start_tuple_minor=None


        # self.logger.debug("StreamControlArea: generating timestamps: major: start, end, timestep: %i, %i, %i",
        #    start_tuple_major, end_tuple, stimestep_major)

        self.struct_times_major, self.mstimestamps_major=genTimeStamps(
            start_tuple_major, end_tuple, stimestep_major)
        if (start_tuple_minor != None):
            # self.logger.debug("StreamControlArea: generating timestamps: minor: start, end, timestep: %i, %i, %i",
            #    start_tuple_minor, end_tuple, stimestep_minor)
            self.struct_times_minor, self.mstimestamps_minor=genTimeStamps(
                start_tuple_minor, end_tuple, stimestep_minor)
        else:
            self.struct_times_minor=[]; self.mstimestamps_minor=[]

        self.struct_times_days, self.mstimestamps_days=genTimeStamps(
            start_day_tuple, end_day_tuple, 24 * 3600)


    def resizeEvent(self, e):
        self.logger.debug("StreamControlArea: resizeEvent")
        self.reScale()
        # self.y_limit_signal.emit([self.dy, self.h])
        super().resizeEvent(e)


    # *** painting ***
    def makeTools(self):
        # first, some drawing related constants:
        # margins
        # "lower y margin" : let's follow the qt coordinates:  0 => downwards in the screen
        # y
        self.lmy=20  # lower margin y
        self.umy=10
        # x
        self.lmx=10
        self.umx=10
        # y-coordinate to start to draw the ticks from
        self.ytick=5
        # tick mark lengths
        self.matick=4
        self.mitick=2

        self.yofs=0


        """
        +-------------------------+  = 0
        |                         |
        |-------------------------|  = self.ytick
        |  ^   ^   ^   ^   ^   ^  |
        +-------------------------+  = self.lmy
        |                         |  .. events, etc. start here
        """

        self.wtria=6  # the selection triangle length


        # qpainter related things:
        self.painter=QtGui.QPainter()
        self.font=QtGui.QFont('Arial', QtGui.QFont.Light)
        self.font.setPixelSize(15)

        self.color_canvas=QtGui.QColor(255, 255, 255)
        self.pen_canvas=QtGui.QPen(self.color_canvas, 1, QtCore.Qt.SolidLine)
        self.pen_canvas.setWidth(1)

        self.color_bg=QtGui.QColor(255, 255, 255)
        # self.color_bg        =QtGui.QColor(0, 0, 0)
        self.pen_bg=QtGui.QPen(self.color_bg, 1, QtCore.Qt.SolidLine)
        self.pen_bg.setWidth(1)

        self.color_timebar=QtGui.QColor(0, 0, 200, 80)
        self.pen_timebar=QtGui.QPen(self.color_timebar, 1, QtCore.Qt.SolidLine)
        self.pen_timebar.setWidth(4)

        self.color_tick_bg=QtGui.QColor("lightblue")
        self.pen_tick_bg=QtGui.QPen(self.color_tick_bg, 1, QtCore.Qt.SolidLine)
        self.pen_tick_bg.setWidth(1)

        self.color_tick_major=QtGui.QColor(50, 50, 50)
        self.pen_tick_major=QtGui.QPen(
            self.color_tick_major, 1, QtCore.Qt.SolidLine)
        self.pen_tick_major.setWidth(2)
        self.font_tick_major=QtGui.QFont('Arial', QtGui.QFont.Light)
        self.font_tick_major.setPixelSize(12)

        self.color_tick_days=QtGui.QColor(255, 255, 255)
        self.pen_tick_days=QtGui.QPen(
            self.color_tick_days, 1, QtCore.Qt.SolidLine)
        self.pen_tick_days.setWidth(4)
        self.font_tick_days=QtGui.QFont('Arial', QtGui.QFont.Bold)
        self.font_tick_days.setPixelSize(16)
        self.font_tick_days.setBold(True)

        self.color_tick_minor=QtGui.QColor(100, 100, 100)
        self.pen_tick_minor=QtGui.QPen(
            self.color_tick_minor, 1, QtCore.Qt.SolidLine)
        self.pen_tick_minor.setWidth(1)

        self.color_devname=QtGui.QColor(100, 0, 0, 80)
        self.pen_devname=QtGui.QPen(self.color_devname, 1, QtCore.Qt.SolidLine)
        self.pen_devname.setWidth(2)
        self.font_devname=QtGui.QFont('Arial', QtGui.QFont.Light)
        self.font_devname.setPixelSize(16)

        self.color_fstimelimits=QtGui.QColor("lightgray")
        self.pen_fstimelimits=QtGui.QPen(self.color_fstimelimits, 1, QtCore.Qt.SolidLine)
        self.pen_fstimelimits.setWidth(1)
        
        self.color_blocktimelimits=QtGui.QColor(0, 0, 255, 20)
        self.pen_blocktimelimits=QtGui.QPen(self.color_blocktimelimits, 1, QtCore.Qt.SolidLine)
        self.pen_blocktimelimits.setWidth(1)
        
        self.color_times=QtGui.QColor(200, 200, 200)
        self.pen_times=QtGui.QPen(self.color_times, 1, QtCore.Qt.SolidLine)
        self.pen_times.setWidth(1)

        self.color_events=QtGui.QColor(0, 200, 0)
        self.pen_events=QtGui.QPen(self.color_events, 1, QtCore.Qt.SolidLine)
        self.pen_events.setWidth(4)

        self.color_frames=QtGui.QColor(150, 150, 150)
        self.pen_frames=QtGui.QPen(self.color_frames, 1, QtCore.Qt.SolidLine)
        self.pen_frames.setWidth(1)

        self.color_sel=QtGui.QColor(0, 0, 100, 40)
        self.pen_sel=QtGui.QPen(self.color_sel, 1, QtCore.Qt.SolidLine)
        self.pen_sel.setWidth(1)

        fm=QtGui.QFontMetrics(self.font_devname)
        # self.dy_per_device=int(round(fm.height())) + 20
        # self.dy_per_device=self.dy_per_device*2 # testing..


    def paintEvent(self, e):
        # http://zetcode.com/gui/pyqt5/painting/
        self.painter.begin(self)
        self.drawWidget(self.painter)
        self.painter.end()


    def paintCanvas(self, qp):
        qp.setPen(self.pen_canvas)
        qp.setBrush(self.color_canvas)
        x0 = 0
        x1=self.width()
        y0 = 0
        y1=self.height()
        rect=[
            QtCore.QPoint(x0, y0),
            QtCore.QPoint(x1, y0),
            QtCore.QPoint(x1, y1),
            QtCore.QPoint(x0, y1)
        ]
        # qp.drawPolygon(QtGui.QPolygon(rect))
        qp.drawPolygon(QtGui.QPolygon(rect))
        


    def paintBackground(self, qp):
        dt = self.t1 - self.t0
        qp.setPen(self.pen_bg)
        qp.setBrush(self.color_bg)                  # paint also the margins
        x0=0
        x1=int(round(self.pixel_per_msec * dt)) + self.umx + self.lmx
        y0=0
        y1=self.h + self.umy + self.lmy
        rect=[
        QtCore.QPoint(x0, y0),
        QtCore.QPoint(x1, y0),
        QtCore.QPoint(x1, y1),
        QtCore.QPoint(x0, y1)
        ]
        qp.drawPolygon(QtGui.QPolygon(rect))


    def paintTickMargin(self, qp):
        dt = self.t1 - self.t0
        qp.setPen(self.pen_tick_bg)
        # paint also the margins
        qp.setBrush(self.color_tick_bg)
        x0=0
        x1=int(round(self.pixel_per_msec * dt)) + self.umx + self.lmx
        y0=0
        y1=self.lmy
        rect=[
        QtCore.QPoint(x0, y0),
        QtCore.QPoint(x1, y0),
        QtCore.QPoint(x1, y1),
        QtCore.QPoint(x0, y1)
        ]
        qp.drawPolygon(QtGui.QPolygon(rect))


    def paintTickMarks(self, qp):
        if (self.struct_times_days != None):
            qp.setPen(self.pen_tick_days)
            qp.setBrush(self.color_tick_days)
            qp.setFont(self.font_tick_days)
            metrics=qp.fontMetrics()
            for n, time_struct in enumerate(self.struct_times_days):
                if (n == 0):
                    mstime=self.t0
                else:
                    mstime=self.mstimestamps_days[n]
                if (mstime >= self.t0):
                    x0=int(round(self.pixel_per_msec * (mstime - self.t0))) + self.lmx
                    y0=0
                    timestr=str(time_struct.tm_mday) + ". " + \
                                str(time_struct.tm_mon) + ". " + str(time_struct.tm_year)
                    fx=0
                    fy=int(round(metrics.height()))
                    qp.drawText(QtCore.QPoint(x0 + fx, y0 + fy), timestr)

        if (self.struct_times_major != None):
            qp.setPen(self.pen_tick_major)
            qp.setBrush(self.color_tick_major)
            qp.setFont(self.font_tick_major)
            metrics=qp.fontMetrics()
            for n, time_struct in enumerate(self.struct_times_major):
                mstime=self.mstimestamps_major[n]
                if (mstime >= self.t0):
                    x0=int(round(self.pixel_per_msec * (mstime - self.t0))) + self.lmx
                    x1=x0
                    y0=self.ytick
                    y1=y0 + self.matick
                    qp.drawLine(QtCore.QLine(x0, y0, x0, y1))
                    timestr=str(time_struct.tm_hour) + ":" + \
                                str(time_struct.tm_min) + ":" + str(time_struct.tm_sec)
                    fx=-int(round(metrics.width(timestr) / 2))
                    fy=int(round(metrics.height()))
                    qp.drawText(QtCore.QPoint(x0 + fx, y1 + fy), timestr)

        if (self.struct_times_minor != None):
            qp.setPen(self.pen_tick_minor)
            qp.setBrush(self.color_tick_minor)
            for n, time_struct in enumerate(self.struct_times_minor):
                    mstime=self.mstimestamps_minor[n]
                    if (mstime >= self.t0):
                        x0=int(round(self.pixel_per_msec * (mstime - self.t0))) + self.lmx
                        x1=x0
                        y0=self.ytick
                        y1=y0 + self.mitick
                        qp.drawLine(QtCore.QLine(x0, y0, x0, y1))


    """
    def paintDeviceNames(self, qp):
        qp.setPen(self.pen_devname)
        qp.setBrush(self.color_devname)
        qp.setFont(self.font_devname)
        metrics=qp.fontMetrics()
        for n in range(self.nline):
            x0=0
            y0=int(round(n * self.dy)) + self.lmy + self.yofs
            namestr=self.device_names[n]
            fx=0
            fy=int(round(metrics.height()))
            qp.drawText(QtCore.QPoint(x0 + fx, y0 + fy), namestr)
    """


    def paintTimeBar(self, qp):
        if (self.mstime != None):
            qp.setPen(self.pen_timebar)
            qp.setBrush(self.color_timebar)
            x0=int(round((self.mstime - self.t0) * self.pixel_per_msec)) + self.lmx
            y0=0
            y1=self.h + self.lmy + self.umy
            qp.drawLine(QtCore.QLine(x0, y0, x0, y1))


    def paintSelection(self, qp):
        return  # selection disabled for the moment..

        if (self.mstime == None):
            return

        if (self.mstime != None):
            self.sel0=self.mstime - 5000  # testing..
            self.sel1=self.mstime + 5000

        if (self.sel0 != None and self.sel1 != None):
            # first, paint the shader
            qp.setPen(self.pen_sel)
            qp.setBrush(self.color_sel)
            x0=int(round((self.sel0 - self.t0) * self.pixel_per_msec)) + self.lmx
            x1=int(round((self.sel1 - self.t0) * self.pixel_per_msec)) + self.lmx
            y0=0 + self.ytick + self.mitick
            y1=self.h + self.lmy + self.umy
            rect=[
                QtCore.QPoint(x0, y0),
                QtCore.QPoint(x1, y0),
                QtCore.QPoint(x1, y1),
                QtCore.QPoint(x0, y1)
            ]
            qp.drawPolygon(QtGui.QPolygon(rect))
            # second, paint the triangles
            # (x0,y0) => (x0+dx,0) => (x0-dx,0) => (x0,y0)
            triangle=[
                QtCore.QPoint(x0, y0),
                QtCore.QPoint(x0 + self.wtria, 0),
                QtCore.QPoint(x0 - self.wtria, 0)
            ]
            qp.drawPolygon(QtGui.QPolygon(triangle), 2)
            triangle=[
                QtCore.QPoint(x1, y0),
                QtCore.QPoint(x1 + self.wtria, 0),
                QtCore.QPoint(x1 - self.wtria, 0)
            ]
            qp.drawPolygon(QtGui.QPolygon(triangle), 2)


    def paintLimits(self, limits, qp, pen, brush):
        qp.setPen(pen)
        qp.setBrush(brush)
        
        if limits[0] < 0 or limits[1] < 0:
            self.logger.critical("bad paintLimits: %i, %i, %i, %i", x0, x1, y0, y1)
            return

        x0 = int(round(self.pixel_per_msec * (limits[0] - self.t0))) + self.lmx
        x1 = int(round(self.pixel_per_msec * (limits[1] - self.t0)))
        y0 = self.ytick + self.mitick
        y1 = self.h + self.lmy + self.umy
        
        self.logger.debug("paintLimits: %i, %i, %i, %i", x0, x1, y0, y1)
        
        rect=[
            QtCore.QPoint(x0, y0),
            QtCore.QPoint(x1, y0),
            QtCore.QPoint(x1, y1),
            QtCore.QPoint(x0, y1)
            ]
        
        qp.drawPolygon(QtGui.QPolygon(rect))
    
    
    def paintFSLimits(self, qp):
        self.paintLimits(self.fstimelimits, qp, self.pen_fstimelimits, self.color_fstimelimits)
        """
        for n, times in enumerate(self.fstimelimits):
            # margins # TODO! properly
            if (times != None and (None not in times)):
                x0=int(round(self.pixel_per_msec * (times[0] - self.t0))) + self.lmx
                x1=int(round(self.pixel_per_msec * (times[1] - self.t0)))
                # shift all y coordinates by margin
                y0=int(round(n * self.dy)) + self.lmy + self.yofs
                y1=int(round((n + 1) * self.dy)) + self.lmy + self.yofs
                rect=[
                QtCore.QPoint(x0, y0),
                QtCore.QPoint(x1, y0),
                QtCore.QPoint(x1, y1),
                QtCore.QPoint(x0, y1)
                ]
                qp.drawPolygon(QtGui.QPolygon(rect))
        """


    def paintBlockLimits(self, qp):
        self.paintLimits(self.blocktimelimits, qp, self.pen_blocktimelimits, self.color_blocktimelimits)
        

    """ # numpy based
    def paintEvents(self,qp):
        self.logger.debug("StreamControlArea: paintEvents:",self.events)
        qp.setPen(self.pen_events)
        qp.setBrush(self.color_events)
        for n, events in enumerate(self.events):
        if (type(events)!=type(None)): # events is a 1d numpy array
            y0=int(round(n*self.dy))                               + \
                self.lmy+self.yofs
            y1=int(round((n+1)*self.dy))                           + \
                self.lmy+self.yofs
            # for i in range(events.shape[0]):
            for t in events: # so, numpy can give us a iterator nowadays..
            # t =events[i]
            x0=int(round(self.pixel_per_msec*(t-self.t0)))       +self.lmx
            qp.drawLine(QtCore.QLine(x0,y0,x0,y1))
    """

    def paintEvents(self, qp):
        # self.logger.debug("StreamControlArea: paintEvents:", self.events)
        qp.setPen(self.pen_events)
        qp.setBrush(self.color_events)
        """
        for n, events in enumerate(self.events):
            if (type(events) != type(None)):  # events is a 1d numpy array
                y0=int(round(n * self.dy)) + self.lmy + self.yofs
                y1=int(round((n + 1) * self.dy)) + self.lmy + self.yofs
                for t in events:
                    # t =events[i]
                    x0=int(round(self.pixel_per_msec * (t.mstime - self.t0))) + self.lmx
                    qp.drawLine(QtCore.QLine(x0, y0, x0, y1))
        """

    def drawWidget(self, qp):
        self.paintCanvas(qp)
        self.paintBackground(qp)
        if self.fstimelimits is not None:
            self.paintFSLimits(qp)
        if self.seltimelimits is not None:
            self.paintSelectionLimits(qp)
        if self.blocktimelimits is not None:
            self.paintBlockLimits(qp)            
        self.paintEvents(qp)
        # self.paintDeviceNames(qp)
        self.paintTickMargin(qp)
        self.paintTickMarks(qp)
        self.paintTimeBar(qp)
        self.paintSelection(qp)


    def findPart(self, y):
        indexes=numpy.where((y >= self.parts[:, 0]) & (y < self.parts[:, 1]))[0]
        if (len(indexes) < 1):
            return None
        else:
            return indexes[0]


    def findNearestEvent(self, i, x):
        if (len(self.scaledevents) == 0 or (type(self.scaledevents[i]) == type(None))):
            return None, None
        else:
            a=self.scaledevents[i]
            dval=numpy.abs(a - x)
            print(dval)
            imin=dval.argmin()
            minval=dval[imin]
            return imin, minval * self.msec_per_pixel
            # returns index, distance in ms


    def postMouseRelease(self, ctx):
        """This callback is called by MouseClickContext, once the single vs. double click has been resolved (i.e. once the timer has timed out)
        """
        """
        if (click.fdouble):
            print("StreamControlArea: postMouseRelease: double click!")
            i=self.findPart(self.mouse_press_y)
        if (i != None):
            ie, dms=self.findNearestEvent(i, self.mouse_press_x)
        """
        if ctx.double_click_flag:
            self.logger.debug("postMouseRelease: double click")
        if (self.mouse_place_flavor == self.mouse_place_normal):
            mstime = int(round((self.mouse_press_x - self.lmx) * self.msec_per_pixel)) + self.t0
            print("mstime1=",mstime)
            if self.fstimelimits is not None: 
                if mstime >= self.fstimelimits[0] and mstime <= self.fstimelimits[1]:
                    self.mstime = mstime
                else:
                    self.logger.debug("postMouseRelease: click outside fs time limits")
                    return
            else:
                print("mstime2=",mstime)
                self.mstime = mstime
                
            print("mstime3=",mstime)
            self.logger.debug("postMouseRelease: mstime now %s", str(self.mstime))
            # self.time_signal.emit(self.mstime)
            self.repaint()
            self.signals.seek_click.emit(self.mstime)


  
    # *** mouse events ***
    def mousePressEvent(self, e):
        self.mouse_click_ctx.atPressEvent(e)
        pos = e.pos()
        x = pos.x()
        y = pos.y()

        self.logger.debug("StreamControlArea: mousePressEvent: x, y = %i %i", x, y)

        # save the coordinates
        self.mouse_press_x = x
        self.mouse_press_y = y
    
        if (y < self.ytick):
            self.mouse_place_flavor = self.mouse_place_selection
        elif (y > (self.lmy + self.h)):
            self.mouse_place_flavor = self.mouse_place_lower
        else:
            self.mouse_place_flavor = self.mouse_place_normal


    def mouseReleaseEvent(self, e):
        self.mouse_click_ctx.atReleaseEvent(e)
        pos = e.pos()     # spatial
        # t=time.time()   # temporal
        x = pos.x()
        y = pos.y()

        dx = x - self.mouse_press_x
        # dt  = t -self.mouse_press_t
        e.accept()


    def mouseMoveEvent(self, e):
        self.logger.debug("StreamControlArea: mouseMoveEvent (drag)")
        # TODO: so, here we could send "drag" signals to FrameReceiver(s)


    def wheelEvent(self, e):
        x = e.pos().x()
        t = self.t0 + (self.msec_per_pixel * x)
        # delta=e.delta()
        delta = e.angleDelta().y()
        if (delta > 0):
            self.zoom(t, 1)
        else:
            self.zoom(t, -1)
        # self.time_limit_signal.emit([self.t0, self.t1])
        e.accept()


    """
    def closeEvent(self, e):
        super().closeEvent(e)
    """

    # ***** SLOTS ******
    def set_fs_time_limits_slot(self, limits: tuple):
        assert(isinstance(limits, tuple))
        self.setFSTimeLimits(limits)
        self.repaint()
        
    def set_block_time_limits_slot(self, limits: tuple):
        assert(isinstance(limits, tuple))
        self.logger.debug("set_block_time_limits_slot : %s -> %s", formatMstimestamp(limits[0]), formatMstimestamp(limits[1]))
        self.setBlockTimeLimits(limits)
        self.repaint()
    
    def set_day_click_slot(self, day: datetime.date):
        self.logger.debug("set_day_click_slot %s", str(day))
        assert(isinstance(day, datetime.date))
        self.setDay(day)
    
    def set_time_slot(self, mstimestamp: int):
        self.logger.debug("set_time_slot %i", mstimestamp)
        """
        if self.fstimelimits is not None: 
            if mstime >= self.fstimelimits[0] and mstime <= self.fstimelimits[1]:
                self.mstime = mstime
                self.logger.debug("postMouseRelease: click outside fs time limits")
        else:
        """
        self.mstime = mstimestamp
        self.repaint()

    def zoom_fs_limits_slot(self):
        self.logger.debug("zoom_fs_limits_slot")
        self.zoomToFS()



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
        
        t = int(time.mktime(datetime.date.today().timetuple())*1000)    
        self.timelinewidget.setFSTimeLimits((t + int(1000*2*3600), t + int(1000*20*3600)))
        
        t = int(time.mktime(datetime.date.today().timetuple())*1000)    
        self.timelinewidget.setBlockTimeLimits((t + int(1000*6*3600), t + int(1000*14*3600)))
        
        self.calendarwidget = CalendarWidget(datetime.date.today(), parent = self.w)
        self.lay.addWidget(self.calendarwidget)
        
        d = datetime.date.today()
        d0 = datetime.date(year = d.year, month = d.month, day = d.day - 2)
        d1 = datetime.date(year = d.year, month = d.month, day = d.day + 3)
        
        t0 = int(time.mktime(d0.timetuple())*1000)
        t1 = int(time.mktime(d1.timetuple())*1000)
        
        self.calendarwidget.set_fs_time_limits_slot((t0, t1))
    
    
    
def main():
    app=QtWidgets.QApplication(["test_app"])
    mg=MyGui()
    mg.show()
    app.exec_()


if (__name__ == "__main__"):
    main()
