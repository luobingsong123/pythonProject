# 按钮用
# -*- coding: UTF-8 -*-
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot

# 文本框用
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QAction, QMessageBox, QTextEdit
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QCoreApplication
from PyQt5.Qt import QLineEdit


class App(QWidget):  # 定义类，固定格式
    def __init__(self):
        super().__init__()  # 子类构造函数调用super().__init__()
        self.title = "Python3正则表达式测试工具"  # 窗口的标题为。。。
        self.left = 500  # 打开的位置位于左500
        self.top = 200  # 打开的位置为了上200
        self.width = 520  # 窗体宽度
        self.height = 400  # 窗体高度
        self.initUI()  # 调用initUI函数

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # 这里开始是一个按钮的设置
        # 在窗体内创建按钮
        self.button1 = QPushButton("测 试", self)
        # 方法setToolTip在用户将鼠标停留在按钮上时显示的消息
        self.button1.setToolTip("点击打印")
        # 按钮坐标x, y
        self.button1.move(400, 230)
        # 按钮与鼠标点击事件相关联
        self.button1.clicked.connect(self.on_click)

        # 建立一个文本框（单行）
        self.textbox = QLineEdit(self)  # QLineEdit是单行文本框。QTextEdit是多行文本框。
        self.textbox.move(30, 230)
        self.textbox.resize(320, 25)  # 宽，高
        self.textbox.text()  # 返回文本框的内容

        # 建立一个按钮2
        self.button2 = QPushButton('退出', self)
        self.button2.move(400, 5)

        # 设置按钮2的鼠标点击事件想关联
        self.button2.clicked.connect(self.on_click2)

        # 建立一个多行的输入文本框-textEdit
        self.textEdit = QTextEdit(self)
        self.textEdit.move(30, 40)
        self.textEdit.resize(460, 140)  # 宽，高
        self.textEdit.toPlainText()  # 返回多行文本框的文本内容

        # 建立一个多行的输出文本框-textEdit_out
        self.textEdit_out = QTextEdit(self)
        self.textEdit_out.move(30, 290)
        self.textEdit_out.resize(460, 70)  # 宽，高

        # 创建3个标签
        self.label1 = QLabel(self)
        self.label2 = QLabel(self)
        self.label3 = QLabel(self)
        # setText():设置Qlabel的文本内容
        self.label1.setText('请输入正则表达式')
        self.label1.move(30, 210)

        self.label2.setText('请输入需要匹配的原文本内容')
        self.label2.move(30, 20)

        self.label3.setText('正则表达式匹配结果')
        self.label3.move(30, 270)

        self.show()

    # 创建鼠标点击事件
    @pyqtSlot()
    def on_click(self):
        # 正则表达式用
        import re
        text_all = self.textEdit.toPlainText()  # 多行文本框的内容
        re1 = self.textbox.text()  # 单行文本框的内容，即正则表达式
        a = re.compile(re1, re.I)  # 不区分大小写。取得的值为list形式
        b = a.findall(text_all)
        c = '\n'.join(b)
        # 以文本的形式输出到多行文本框-textEdit_out
        self.textEdit_out.setPlainText(c)  # 设置多行文本框的内容-setPlainText()

    # 退出按钮
    def on_click2(self):
        self.button2.clicked.connect(QCoreApplication.instance().quit)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
