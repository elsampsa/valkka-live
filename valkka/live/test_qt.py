from PySide2 import QtWidgets, QtCore, QtGui # Qt5
import sys

 
class MyGui(QtWidgets.QMainWindow):

  
  def __init__(self,parent=None):
    super(MyGui, self).__init__()
    self.setupUi()
    

  def setupUi(self):
    self.setGeometry(QtCore.QRect(100,100,500,500))

    # create widget inside this window
    self.w =QtWidgets.QFrame(self)
    self.w.setAutoFillBackground(True)
    self.w.setStyleSheet("QFrame {background-color: blue;}")
    self.setCentralWidget(self.w)

    # lets create another window with a widget inside
    self.another_window =QtWidgets.QMainWindow()
    self.w2 =QtWidgets.QFrame(self.another_window)
    self.w2.setAutoFillBackground(True)
    self.w2.setStyleSheet("QFrame {background-color: green;}")
    self.another_window.setCentralWidget(self.w2)
    self.another_window.show()


  def closeEvent(self,e):
    print("closeEvent!")
    e.accept()


def main():
  app=QtWidgets.QApplication(["test_app"])
  mg=MyGui()
  mg.show()
  app.exec_()


if (__name__=="__main__"):
  main()
 
