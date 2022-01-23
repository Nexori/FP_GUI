import threading                            # DAQ
import tkinter as tk                        # GUI
import matplotlib.pyplot as plt             # PLOTS
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np                          # DATA STORAGE
from numpy import zeros
import serial                               # SERIAL COMMUNICATION
from time import sleep                      # DELAYS


class serialPolarPlot:
    def __init__(self, serialPort='COM7', baudrate=57600, serialTimeout=0.1, plotPtsCnt=50):
        # Data acquisition related
        self.canvasInitalized = 0
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
        self.cSpeed = "NaN"
        self.cStepSkip = "NaN"
        self.cTimeBudget = "NaN"
        self.lpTime = "NaN"
        self.readSerialStart()
        self.root = tk.Tk()         # Main Tkinter window

        self.init_window()
        self.root.mainloop()

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
                line_full = self.currentLine.replace(b'$', b'')
                line_full = line_full.replace(b',', b' ')
                line_full = line_full.replace(b';', b' ')
                line_as_list = line_full.split() # should extract mod2 n. numbers
                # Append new data as last and remove the first one
                self.data = np.vstack([self.data, [np.radians(float(line_as_list[0]) * 0.9), float(line_as_list[1])+np.random.randint(100, 150)]])
                self.data = np.delete(self.data, 0, 0)
                self.cSpeed = (line_as_list[2]).decode('utf-8')         # Read current speed
                self.cStepSkip = (line_as_list[3]).decode('utf-8')      # Read current step skip
                self.cTimeBudget = (line_as_list[4]).decode('utf-8')    # Read current time budget
                if self.canvasInitalized == 1:
                    self.lpTime = (line_as_list[5]).decode('utf-8')
                # print('[INFO] Data received: ', self.currentLine, 'converted to: ', line_as_list )
                print('RX_Q:' + str(self.s.inWaiting())+" Cspd:"+
                      str(self.cSpeed)+" Cskp: "+
                      str(self.cStepSkip)+" CTme: "+
                      str(self.cTimeBudget)+" DSize:("+
                      str(self.data[:,0].size)+" "+
                      str(self.data[:,1].size)+") ")

    def plot_init(self):
        # Create figure for plotting
        self.ax.set_facecolor('w')
        self.ax.set_theta_zero_location("N")
        self.ax.set_rlabel_position(359)
        self.ax.set_yticks([100, 200, 300, 400])
        self.ax.set_rmax(400)
        self.ax.set_rticks([0, 100, 200, 300, 400])  # Less radial ticks
        self.ax.set_title("Surroundings", va='bottom')
        self.ax.grid(True)

    def updLabels(self):
        self.cSpeedLabel.config(text="Current speed: " + self.cSpeed + " RPM")
        self.cStepSkipLabel.config(text="Step jump: " + self.cStepSkip + " steps")
        self.cTimeBudgetLabel.config(text="Time budget: " + self.cTimeBudget + " ms")
        self.lpTimeLabel.config(text="Loop time : " + self.lpTime + " ms")

    def updSpd(self):
        self.cSpeed = self.entry_motorSpeed.get()
        if self.cSpeed >'0':
            self.s.write(("@" + self.entry_motorSpeed.get()+'\r\n').encode('utf-8'))
            self.updLabels()
            self.s.flushInput()

    def updStepSkip(self):
        self.cStepSkip = self.entry_stepSkip.get()
        if self.cStepSkip != '0':
            self.s.write(("%" + self.entry_stepSkip.get()+'\r\n').encode('utf-8'))
            self.updLabels()
        self.s.flushInput()
        # Adjust buffer size
        self.plotPtsCnt = abs(int(400/int(self.cStepSkip)))
        self.data = zeros([self.plotPtsCnt,2])

    def updTimeBudget(self):
        self.cTimeBudget = self.entry_timeBudget.get()
        if self.cTimeBudget > '0':
            self.s.write(("&" + self.entry_timeBudget.get() + '\r\n').encode('utf-8'))
            self.updLabels()
            self.s.flushInput()

    def init_window(self):

        def animate(i):
            self.updLabels()
            self.radarLine.set_data(self.data[:, 0], self.data[:, 1])
            self.headingLine.set_data(
                [self.data[self.plotPtsCnt - 1, 0], self.data[self.plotPtsCnt - 1, 0]],
                [0, 400])
            # print('[INFO] Anim Exec')

        # Plot related
        self.fig = plt.figure(figsize=(5, 5))                           # Matplotlib plot size
        self.ax = self.fig.add_subplot(111, polar=True)                 # Plot type
        self.plot_init()                                                # Set up plot features

        self.headingLine, = self.ax.plot([], [], '-k', linewidth=0.5)   # Create heading indicator
        self.radarLine, = self.ax.plot([], [])                          # Create surrounding plot

        # Canvas related
        self.root.title("Polar plot")                                   # Set title
        self.root.geometry("1000x800")                                  # Dimensions of main window
        self.mainCanvas = tk.Canvas(self.root, height=120,width=100)

        self.plotCanvas = FigureCanvasTkAgg(self.fig, master=self.root)         # Contain matplotlib plot
        self.plotCanvas = self.plotCanvas.get_tk_widget()                       # Convert it to canvas

        self.entry_motorSpeed = tk.Entry(self.root)                             # Create speed entry
        self.entry_timeBudget = tk.Entry(self.root)                             # Create speed entry
        self.entry_stepSkip = tk.Entry(self.root)                               # Create speed entry

        self.button_motorSpeedApply = tk.Button(                                # Create speed button
            self.root,
            text='Apply new speed',
            command=lambda: self.updSpd(),
            bg="#ff1a1a",
            font=('Arial', 10))  # Create speed entry apply button
        self.button_timeBudgetApply = tk.Button(  # Create speed button
            self.root,
            text='Apply new time budget',
            command=lambda: self.updTimeBudget(),
            bg="#1aff1a",
            font=('Arial', 10))  # Create speed entry apply button
        self.button_stepSkipApply = tk.Button(  # Create speed button
            self.root,
            text='Apply new step skip',
            command=lambda: self.updStepSkip(),
            bg="#1affff",
            font=('Arial', 10))  # Create speed entry apply button
        self.cSpeedLabel = tk.Label(self.root, text="Current speed: NaN", anchor='nw', font=('Arial', 10))
        self.cTimeBudgetLabel = tk.Label(self.root, text="Current time budget: NaN", anchor='nw', font=('Arial', 10))
        self.cStepSkipLabel = tk.Label(self.root, text="Current motor skip: NaN", anchor='nw', font=('Arial', 10))
        self.lpTimeLabel = tk.Label(self.root, text="Loop time: NaN", anchor='nw', font=('Arial', 10))
        ## Arrange
        self.mainCanvas.pack(fill='both')

        # Entries
        self.mainCanvas.create_window(10, 10, window=self.entry_motorSpeed, width=50, height=25,anchor='nw')   # Place it on canvas
        self.mainCanvas.create_window(10, 35, window=self.entry_timeBudget, width=50, height=25,anchor='nw')  # Place it on canvas
        self.mainCanvas.create_window(10, 60, window=self.entry_stepSkip, width=50, height=25,anchor='nw')  # Place it on canvas

        # Buttons
        self.mainCanvas.create_window(70, 10, window=self.button_motorSpeedApply,width=150,height=25,anchor='nw')     # Place it on canvas
        self.mainCanvas.create_window(70, 35, window=self.button_timeBudgetApply, width=150, height=25,anchor='nw')  # Place it on canvas
        self.mainCanvas.create_window(70, 60, window=self.button_stepSkipApply, width=150, height=25,anchor='nw')  # Place it on canvas

        # Labels
        self.cSpeedLabel.place(x=230, y=10, anchor='nw')
        self.cTimeBudgetLabel.place(x=230, y=35, anchor='nw')
        self.cStepSkipLabel.place(x=230, y=60, anchor='nw')
        self.lpTimeLabel.place(x=230, y=85, anchor='nw')

        self.plotCanvas.pack(fill='both', expand=1)  # Place it on canvas
        self.canvasInitalized = 1

        self.ani = animation.FuncAnimation(self.fig, animate, interval=20, frames=1)    # Start animation

# Performance parameters
serPlot = serialPolarPlot(serialPort='COM7', baudrate=57600, serialTimeout=0.1, plotPtsCnt=50)

