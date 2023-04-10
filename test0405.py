import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

def update():
    global curve1, data, ptr, p6
    curve.setData(data[ptr%10])
    if ptr == 0:
        p6.enableAutoRange('xy', False)
    ptr += 1

app = pg.mkQApp("Plotting Example")

win = pg.GraphicsLayoutWidget(show=True, title="hello")
win.resize(600, 400)
win.setWindowTitle('Hello')

pg.setConfigOptions(antialias=True)

p6 = win.addPlot(title="serial data")
curve1 = p6.plot(pen='y')
data = np.random.normal(size=(10, 10000))
ptr = 0

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)



if __name__ == '__main__':
    pg.exec()