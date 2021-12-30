import threading

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import numpy as np
from numpy import zeros
import serial
from time import sleep

class serialPolarPlot:
    def __init__(self, serialPort='COM5', baudrate=57600, serialTimeout=0.1, plotPtsCnt=50):
        self.data = zeros([plotPtsCnt, 2])
        self.plotPtsCnt = plotPtsCnt
        self.s = serial.Serial()
        self.s.baudrate = baudrate
        self.s.timeout = serialTimeout
        self.s.port = serialPort
        self.currentLine=''
        self.s.open()
        self.thread = None
        while not (self.s.isOpen()):
            print("[ERROR] Cannot open COM port. Is the device connected at", self.s.port, "with baud", self.s.baudrate,
                  "? Is the port used elsewhere?")
            sleep(1)
            self.s.open()
        print("[INFO] COM opened successfully.")

    def readSerialStart(self):
        print("[INFO] Creating serial com thread")
        if self.thread == None:
            self.thread = threading.Thread(target=self.getCOMDataThread)
            self.thread.start()
            sleep(0.001)

    def getCOMDataThread(self):
        print("[INFO] Success")
        while True:
            # print("[INFO] S1, ",self.s.inWaiting())
            while self.s.inWaiting() > 10:
                self.currentLine = self.s.readline()
                while not (self.currentLine.startswith(b'$') and self.currentLine.endswith(b'\n')):
                    # print('[INFO] Bad data: ', self.currentLine)
                    self.currentLine = self.s.readline()
                line_full = self.currentLine.replace(b'$', b' ')
                line_as_list = line_full.split() # should extract mod2 n. numbers
                if len(line_as_list)%2 == 0 :
                    for i in range(0, len(line_as_list), 2):
                        # Append new data as last and remove the first one
                        self.data = np.vstack([self.data, [np.radians(float(line_as_list[i]) * 0.9), float(line_as_list[i+1])]])
                        self.data = np.delete(self.data, 0, 0)
                # print('[INFO] Data received: ', self.currentLine, 'converted to: ', line_as_list )
            sleep(0.0001)


def plot_init(axIn):
    # Create figure for plotting
    axIn.set_facecolor('w')
    axIn.set_theta_zero_location("N")
    axIn.set_rlabel_position(359)
    axIn.set_yticks([100, 200, 300, 400])
    axIn.set_rmax(400)
    axIn.set_rticks([0, 100, 200, 300, 400])  # Less radial ticks
    axIn.set_title("Surroundings", va='bottom')
    axIn.grid(True)


# Performance parameters
serPlot = serialPolarPlot(serialPort='COM5', baudrate=57600, serialTimeout=0.1, plotPtsCnt=50)
serPlot.readSerialStart()

# Initialize plots
fig = plt.figure(figsize=(5, 5))
ax = fig.add_subplot(111, polar=True)
plot_init(ax)
headingLine, = ax.plot([], [], '-k', linewidth=0.5)
radarLine, = ax.plot([], [])

def animate(i):
    radarLine.set_data(serPlot.data[:,0], serPlot.data[:,1])
    headingLine.set_data([serPlot.data[serPlot.plotPtsCnt - 1,0],serPlot.data[serPlot.plotPtsCnt - 1,0]], [0, 400])
    # print('[INFO] Anim Exec')

# This function is called periodically from FuncAnimation
ani = animation.FuncAnimation(fig, animate, interval=20, frames=1)
plt.show()
'''
while True:
    if serPlot.s.inWaiting() > 8:
        currentLine = serPlot.s.readline()
        while not (serPlot.currentLine.startswith(b'$') and serPlot.currentLine.endswith(b'\n')):
            print('[INFO] Bad data: ', serPlot.currentLine)
            serPlot.currentLine = serPlot.s.readline()
        line_full = serPlot.currentLine.replace(b'$', b'')
        line_as_list = line_full.split(b'\t')

        # Append new data as last and remove the first one
        serPlot.data = np.vstack([serPlot.data, [np.radians(float(line_as_list[0]) * 0.9), float(line_as_list[1])]])
        serPlot.data = np.delete(serPlot.data, 0, 0)
        print('[INFO] Data received: ', serPlot.currentLine)
    sleep(0.01)
'''
