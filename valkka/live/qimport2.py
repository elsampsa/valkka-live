import sys
if 'PyQt5' in sys.modules:
    # PyQt5
    print("Using PyQt5")
    from PyQt5.QtGui import * 
    from PyQt5.QtWidgets import * 
    from PyQt5.QtCore import * 
    from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
else:
    # PySide2
    print("Using PySide2")
    from PySide2.QtGui import * 
    from PySide2.QtWidgets import * 
    from PySide2.QtCore import *
    from PySide2.QtCore import Signal, Slot
