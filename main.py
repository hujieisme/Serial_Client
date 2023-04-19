import os
import sys
import platform

from qtpy import uic
from qtpy.QtCore import QThread, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import *
import qdarkstyle
import serial

import serial.tools.list_ports
import threading

import numpy as np
import pyqtgraph as pg

UI_FILE = os.path.join(os.path.dirname(__file__), 'MainWindow.ui')
Setting_Page = os.path.join(os.path.dirname(__file__), 'setting_page.ui')
Plot_Page = os.path.join(os.path.dirname(__file__), 'plot_page.ui')
sys_platform = platform.platform().lower()


global UART
global RX_THREAD
global gui
global app, data, \
    curve1, p1, curve2, p2, \
    curve3, p3, curve4, p4, \
    curve5, p5, curve6, p6, \
    curve7, p7, curve8, p8, \
    curve9, p9, curve10, p10

class Plot_Widget(pg.PlotWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setYRange(0, 1)
        self.setXRange(0, 32000)
        self.enableAutoRange('xy', False)
        self.setLabel('bottom', 'Points', units='/s')
        self.setLabel('left', 'Value', units='/3.3V')
        self.setLabel('right', ' ')
        self.showGrid(x=True, y=True)


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pages_manager = None
        self.plot_page = None
        self.setting_page = None
        self.coms = None
        self.flag = bool(0)
        self.flag_2 = bool(0)
        self.callBack = []
        app = pg.mkQApp("Plotting Example")
        self.init_UI()

    def init_UI(self):

        uic.loadUi(UI_FILE, self)
        self.setting_page = QWidget()
        uic.loadUi(Setting_Page, self.setting_page)
        self.update_Coms()
        self.init_Plot()

        # uic.loadUi(Plot_Page, self.plot_page)

        self.resize(250, 280)
        self.setWindowTitle("数据流串口终端")
        self.setWindowIcon(QIcon('graphs.ico'))
        self.action.triggered.connect(self.setting_page_show)
        self.action_2.triggered.connect(self.plot_page_show)
        self.setting_page.pushButton.clicked.connect(self.update_Coms)
        self.setting_page.pushButton_2.clicked.connect(self.open_close_coms)
        self.setting_page.pushButton_3.clicked.connect(self.write_bound_rate)

        self.pages_manager = QStackedWidget(self)
        self.pages_manager.addWidget(self.setting_page)
        self.pages_manager.addWidget(self.plot_page)

        self.setCentralWidget(self.pages_manager)

    def init_Plot(self):
        global data
        global curve1, p1, curve2, p2, \
            curve3, p3, curve4, p4, \
            curve5, p5, curve6, p6, \
            curve7, p7, curve8, p8, \
            curve9, p9, curve10, p10

        self.plot_page = QWidget()
        data = np.zeros((10, 32000))
        VL = QVBoxLayout()
        HL = QHBoxLayout()
        self.plot_page.setLayout(VL)
        p1 = Plot_Widget()
        p1.setLabel('top', 'CH1')
        curve1 = p1.plot(pen='y')
        p2 = Plot_Widget()
        p2.setLabel('top', 'CH2')
        curve2 = p2.plot(pen='g')
        VL.addWidget(p1)
        VL.addWidget(p2)
        curve1.setData(data[0])
        curve2.setData(data[1])

    def open_close_coms(self):
        global UART
        global RX_THREAD

        if not self.flag:
            self.flag = 1
            self.setting_page.pushButton_2.setText("关闭串口")
            self.statusBar.showMessage("串口已关闭!", 3000)
            try:
                if "windows" in sys_platform:
                    UART = serial.Serial(str(self.coms[self.setting_page.comboBox.currentIndex()])[0:5],
                                         int(self.setting_page.comboBox_2.currentText()),
                                         timeout=0.2)
                if "macos" in sys_platform:
                    UART = serial.Serial(str(self.coms[self.setting_page.comboBox.currentIndex()])[0:21],
                                         int(self.setting_page.comboBox_2.currentText()),
                                         timeout=0.2)
                if UART.isOpen():
                    self.statusBar.showMessage("串口已成功打开!", 3000)
                    self.plot_page_show()
                    lock = threading.Lock()
                    RX_THREAD = UART_RX_TREAD('URX1', lock)
                    RX_THREAD.setDaemon(True)
                    RX_THREAD.start()
                    RX_THREAD.resume()
            except:
                self.statusBar.showMessage("串口或被占用，打开失败", 3000)
        else:
            self.flag = 0
            self.setting_page.pushButton_2.setText("打开串口")
            RX_THREAD.pause()
            UART.close()

    def update_Coms(self):
        self.setting_page.comboBox.clear()
        self.coms = list(serial.tools.list_ports.comports())
        for i in range(len(self.coms)):
            self.setting_page.comboBox.addItem(str(self.coms[i]))
        self.statusBar.showMessage("串口设备已更新!", 3000)

    def write_bound_rate(self):
        if not self.flag_2:
            self.setting_page.comboBox_2.setEditable(1)
            self.flag_2 = 1
            self.statusBar.showMessage("输入波特率", 3000)
        else:
            self.setting_page.comboBox_2.setEditable(0)
            self.flag_2 = 0

    def setting_page_show(self):
        self.pages_manager.setCurrentIndex(0)
        self.resize(250, 280)

    def plot_page_show(self):
        self.pages_manager.setCurrentIndex(1)
        self.resize(800, 600)

class UART_RX_TREAD(threading.Thread):  # 数据接收进程 部分重构
    global gui
    global UART
    global RX_THREAD

    def __init__(self, name, lock):
        threading.Thread.__init__(self)
        self.mName = name
        self.mLock = lock
        self.mEvent = threading.Event()
        self.rx_buf = ''
        self.nums = []
        self.sum = 0
        self.thread_process = ProcessingThread()
        self.thread_process.signal.connect(self.processing)
        self.thread_plot = ProcessingThread()
        self.thread_plot.signal.connect(self.plotting)


    def run(self):
        while True:
            self.mEvent.wait()
            self.mLock.acquire()
            if UART.isOpen():
                while True:
                    char = UART.read(size=4000)
                    self.rx_buf = char
                    self.thread_process.start()
            else:
                break

    def pause(self):
        self.mEvent.clear()

    def resume(self):
        self.mEvent.set()

    def processing(self):

        self.rx_buf = self.rx_buf.partition(b'\r\n')[2]
        self.rx_buf = self.rx_buf.rpartition(b'\r\n')[0]
        self.rx_buf = self.rx_buf.split(b'\r\n')
        self.nums = []
        for x in self.rx_buf:
            if len(x) == 4:
                self.nums.append(x[0:2])
                self.nums.append(x[2:4])
        for i in range(len(self.nums)):
            self.nums[i] = int.from_bytes(self.nums[i], byteorder='big')/4096
        self.thread_plot.start()

    def plotting(self):
        global data
        global curve1, p1, curve2, p2, \
            curve3, p3, curve4, p4, \
            curve5, p5, curve6, p6, \
            curve7, p7, curve8, p8, \
            curve9, p9, curve10, p10

        size = int(len(self.nums) / 2)
        self.sum += size
        print(self.sum)
        for i in range(size):
            data[0][i] = self.nums[2*i]
            data[1][i] = self.nums[2*i + 1]
        data = np.roll(data, 32000 - size, axis=1)
        curve1.setData(data[0])
        curve2.setData(data[1])


class ProcessingThread(QThread):
    signal = Signal()

    def __init__(self):
        super().__init__()

    def run(self):
        self.signal.emit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = MainWindow()
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    gui.show()
    app.exec_()
