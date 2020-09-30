import sys
if 'PyQt5' in sys.modules:
    # PyQt5
    print("Using PyQt5")
    from PyQt5 import QtGui, QtWidgets, QtCore
    from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
else:
    # PySide2
    print("Using PySide2")
    from PySide2 import QtGui, QtWidgets, QtCore
    from PySide2.QtCore import Signal, Slot
