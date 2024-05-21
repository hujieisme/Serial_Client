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
global app, data, p_list, curve_list
p_list = []
curve_list = []

class Plot_Widget(pg.PlotWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setYRange(0, 1)
        self.setXRange(0, 20000)
        self.enableAutoRange('xy', False)
        self.setLabel('bottom', 'Points', units='/s')
        self.setLabel('left', 'Value', units='/3.3V')
        self.setLabel('right', ' ')
        self.showGrid(x=True, y=True)


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.VL = None
        self.HL = None
        self.pages_manager = None
        self.plot_page = None
        self.setting_page = None
        self.coms = None

        self.flag = bool(0)
        self.flag_2 = bool(0)
        self.flag_3 = bool(0)
        self.flag_hex = bool(1)
        self.channals_num = 2
        self.str2send = ''
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

        self.resize(600, 400)
        self.setWindowTitle("数据流串口终端")
        self.setWindowIcon(QIcon('graphs.ico'))
        self.action.triggered.connect(self.setting_page_show)
        self.action_2.triggered.connect(self.plot_page_show)
        self.setting_page.pushButton.clicked.connect(self.update_Coms)
        self.setting_page.pushButton_2.clicked.connect(self.open_close_coms)
        self.setting_page.pushButton_3.clicked.connect(self.write_bound_rate)
        self.action_3.triggered.connect(self.start_MCU)
        self.setting_page.pushButton_7.clicked.connect(self.sendcommand)
        self.setting_page.pushButton_8.clicked.connect(self.set_channals)
        self.setting_page.checkBox_11.stateChanged.connect(self.hexornot)

        self.pages_manager = QStackedWidget(self)
        self.pages_manager.addWidget(self.setting_page)
        self.pages_manager.addWidget(self.plot_page)

        self.setCentralWidget(self.pages_manager)

    def init_Plot(self):
        global data
        global p_list, curve_list

        self.plot_page = QWidget()
        data = np.zeros((10, 20000))
        self.VL = QVBoxLayout()
        self.HL = QHBoxLayout()
        self.plot_page.setLayout(self.VL)
        p = Plot_Widget()
        p.setLabel('top', 'CH1')
        curve = p.plot(pen='y')
        p_list.append(p)
        curve_list.append(curve)
        p = Plot_Widget()
        p.setLabel('top', 'CH2')
        curve = p.plot(pen='g')
        p_list.append(p)
        curve_list.append(curve)
        self.VL.addWidget(p_list[0])
        self.VL.addWidget(p_list[1])
        curve_list[0].setData(data[0])
        curve_list[1].setData(data[1])

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
                                         bytesize=serial.EIGHTBITS,
                                         stopbits=serial.STOPBITS_ONE,
                                         timeout=0.2)
                if "macos" in sys_platform:
                    UART = serial.Serial(str(self.coms[self.setting_page.comboBox.currentIndex()])[0:21],
                                         int(self.setting_page.comboBox_2.currentText()),
                                         timeout=0.2)
                if UART.isOpen():
                    self.statusBar.showMessage("串口已成功打开!", 3000)
                    lock = threading.Lock()
                    RX_THREAD = UART_RX_TREAD('URX1', lock)
                    RX_THREAD.setDaemon(True)
                    RX_THREAD.start()
                    RX_THREAD.resume()
            except:
                self.statusBar.showMessage("串口或被占用，打开失败", 3000)
                self.flag = 0
                self.setting_page.pushButton_2.setText("打开串口")
        else:
            self.flag = 0
            self.setting_page.pushButton_2.setText("打开串口")
            RX_THREAD.pause()
            UART.close()

    def update_Coms(self):
        self.setting_page.comboBox.clear()
        self.coms = list(serial.tools.list_ports.comports())
        for i in range(len(self.coms)):
            comport = list(self.coms[i])
            number, name = comport[0], comport[1]
            self.setting_page.comboBox.addItem(str(number))
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
        self.resize(600, 400)

    def plot_page_show(self):
        self.pages_manager.setCurrentIndex(1)
        self.resize(800, 600)

    def start_MCU(self):
        global UART
        if not self.flag_3:
            self.action_3.setIcon(QIcon('Stop.svg'))
            self.flag_3 = 1
            if UART.isOpen():
                self.plot_page_show()
                UART.write("START\r\n".encode('utf-8'))
        else:
            self.action_3.setIcon(QIcon('Run.svg'))
            self.flag_3 = 0
            UART.write("STOP\r\n".encode('utf-8'))
        # UART.send("START\r\n")

    def sendcommand(self):
        print('OK')

    def set_channals(self):
        global data, UART
        global p_list, curve_list

        self.str2send = 'SET'
        self.channals_num = 0
        p_list.clear()
        curve_list.clear()
        # item = self.VL.takeAt(0)
        # while item is not None:
        #     if item.widget():
        #         self.VL.removeItem(item)
        #         del item
        #     item = self.VL.takeAt(0)
        for i in range(self.plot_page.layout().count()):
            self.plot_page.layout().itemAt(i).widget().deleteLater()

        if self.setting_page.checkBox_1.isChecked():
            self.str2send += '1'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH1')
            curve = p.plot(pen='y')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_2.isChecked():
            self.str2send += '2'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH2')
            curve = p.plot(pen='g')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_3.isChecked():
            self.str2send += '3'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH3')
            curve = p.plot(pen='b')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_4.isChecked():
            self.str2send += '4'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH4')
            curve = p.plot(pen='w')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_5.isChecked():
            self.str2send += '5'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH5')
            curve = p.plot(pen='p')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_6.isChecked():
            self.str2send += '6'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH6')
            curve = p.plot(pen='r')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_7.isChecked():
            self.str2send += '7'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH7')
            curve = p.plot(pen='g')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_8.isChecked():
            self.str2send += '8'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH8')
            curve = p.plot(pen='y')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_9.isChecked():
            self.str2send += '9'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH9')
            curve = p.plot(pen='b')
            p_list.append(p)
            curve_list.append(curve)
        if self.setting_page.checkBox_10.isChecked():
            self.str2send += 'A'
            self.channals_num += 1
            p = Plot_Widget()
            p.setLabel('top', 'CH10')
            curve = p.plot(pen='w')
            p_list.append(p)
            curve_list.append(curve)
        for i in range(self.channals_num):
            self.VL.addWidget(p_list[i])

        self.plot_page_show()
        self.str2send += '\r\n'
        UART.write(self.str2send.encode('utf-8'))

    def hexornot(self):
        if self.setting_page.checkBox_11.isChecked():
            self.str2send = 'HEX0'
            self.str2send += '\r\n'
            UART.write(self.str2send.encode('utf-8'))
            self.flag_hex = 0
        else:
            self.str2send = 'HEX1'
            self.str2send += '\r\n'
            UART.write(self.str2send.encode('utf-8'))
            self.flag_hex = 1


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
        self.rx_remain = ''
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
                    char = UART.read(size=2000)
                    self.rx_buf = char
                    self.thread_process.start()
            else:
                break

    def pause(self):
        self.mEvent.clear()

    def resume(self):
        self.mEvent.set()

    def processing(self):
        if gui.flag_hex:
            if self.rx_remain == '':
                self.rx_buf = self.rx_buf.partition(b'\r\n')[2]
                self.rx_buf = self.rx_buf.rpartition(b'\r\n')[0]
            else:
                self.rx_buf = self.rx_remain + self.rx_buf
                self.rx_buf, buf, self.rx_remain = self.rx_buf.rpartition(b'\r\n')
            self.rx_buf = self.rx_buf.split(b'\r\n')
            self.nums = []
            for x in self.rx_buf:
                if len(x) == 2 * int(gui.channals_num):
                    for i in range(int(gui.channals_num)):
                        self.nums.append(x[2 * i:2 * (i + 1)])
            for i in range(len(self.nums)):
                self.nums[i] = int.from_bytes(self.nums[i], byteorder='big')/4096
        else:
            self.rx_buf = str(self.rx_buf, encoding="utf-8")
            if self.rx_remain == '':
                self.rx_buf = self.rx_buf.partition('\r\n')[2]
                self.rx_buf = self.rx_buf.rpartition('\r\n')[0]
            else:
                self.rx_buf = self.rx_remain + self.rx_buf
                self.rx_buf, buf, self.rx_remain = self.rx_buf.rpartition('\r\n')
            self.rx_buf = self.rx_buf.split('\r\n')
            buf = ''
            self.nums = []
            for x in self.rx_buf:
                if len(x) == 5 * int(gui.channals_num):
                    buf += x
            self.nums = buf.split()
            self.nums = [int(x)/4096 for x in self.nums]
        self.thread_plot.start()

    def plotting(self):
        global data, gui
        global p_list, curve_list

        size = int(len(self.nums) / gui.channals_num)
        self.sum += size
        print(self.sum)
        for i in range(size):
            for j in range(int(gui.channals_num)):
                data[j][i] = self.nums[gui.channals_num * i + j]
        data = np.roll(data, 20000 - size, axis=1)
        for i in range(int(gui.channals_num)):
            curve_list[i].setData(data[i])

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
