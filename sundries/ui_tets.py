import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# 将控制台输出写入文本小部件
class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))


class GenMast(QMainWindow):
    def __init__(self):
        super().__init__()
        # QMainWindow.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint)
        self.process = QTextEdit(self, readOnly=True)
        self.initUI()

        """自定义输出流"""
        sys.stdout = Stream(newText=self.onUpdateText)

    """将控制台输出写入文本小部件"""

    def onUpdateText(self, text):
        cursor = self.process.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.process.setTextCursor(cursor)
        self.process.ensureCursorVisible()

    def closeEvent(self, event):
        """关闭时关闭应用程序"""
        sys.stdout = sys.__stdout__
        super().closeEvent(event)

    """主界面信息"""

    def initUI(self):
        """ 显示框信息"""
        self.process.ensureCursorVisible()
        self.process.setLineWrapColumnOrWidth(580)
        self.process.setLineWrapMode(QTextEdit.FixedPixelWidth)
        self.process.setFixedWidth(600)
        self.process.setFixedHeight(405)
        self.process.move(290, 10)

        """主窗口"""
        self.setFixedSize(910, 425)
        # self.setGeometry(500, 300, 900, 425)
        self.setWindowTitle('SmartCamera1.1.1.988-huaxia-987')
        self.show()

if __name__ == '__main__':
    """运行应用程序"""
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(app.deleteLater)
    gui = GenMast()  # 主程序入口
    sys.exit(app.exec_())
