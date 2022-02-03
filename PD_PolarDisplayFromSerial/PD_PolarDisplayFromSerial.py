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
    def __init__(self, serialPort='COM7', baudrate=57600, serialTimeout=0.1, plotResolution=50):
        
        self.serialDataPoolingEnabled = 0
        self.canvasInitialized = 0
        
        # Data acquisition related
        self.s = serial.Serial()
        self.s.baudrate = baudrate
        self.s.timeout = serialTimeout
        self.s.port = serialPort
        
        self.plotData = zeros([plotResolution, 2])
        self.plotResolution = plotResolution
        self.thread = None

        self.currentSpeed = "NaN"
        self.currentStepSkip = "NaN"
        self.currentTimeBudget = "NaN"
        self.loopTime = "NaN"

        self.rootWindow = tk.Tk()         # Main Tkinter window
        self.init_window()

        # Place default data in entries
        self.entry_serialTimeout.insert(tk.END,str(serialTimeout))
        self.entry_serialBaud.insert(tk.END,str(baudrate))
        self.entry_serialPort.insert(tk.END,str(serialPort))

        self.rootWindow.mainloop()        # GUI main loop. Note, its continuous loop.
        
        self.serial_stop()       # Close serial when GUI is closed.

    def serial_try_open(self):
        # Get values in GUI entry fields
        self.s.baudrate = int(self.entry_serialBaud.get())
        self.s.timeout = float(self.entry_serialTimeout.get())
        self.s.port = self.entry_serialPort.get()

        # Variable for COM Thread to execute the while() loop
        self.serialDataPoolingEnabled = 1

        # Try to open serial port
        if self.s.isOpen():
            self.serial_stop()                                                  # If it is open, restart it with diff.
            self.s.open()                                                       # parameters
        else:
            self.s.open()

        # Flush plotted data
        self.plotData = zeros([self.plotResolution, 2])
        print("[INFO] Creating serial com thread")

        # Create thread
        if self.thread is None:
            self.thread = threading.Thread(target=self.serial_monitor_thread)
            self.thread.start()
            sleep(0.001)

        print("[INFO] COM opened successfully.")

    def serial_stop(self):
        print("[INFO] Closing serial com thread")
        if self.s.isOpen():
            self.serialDataPoolingEnabled = 0                   # Disable thread's while() loop, so it can stop
            self.thread.join()                                  # Close the thread
            self.s.close()                                      # Close serial port
            self.thread = None
            print("[INFO] Success")
        else:
            print("[INFO] The port is already closed!")

    def serial_monitor_thread(self):
        print("[INFO] Success")
        while self.serialDataPoolingEnabled:
            # While there is some data read it all. May observe severe delays when data flows too fast, as buffer fills.
            while self.s.inWaiting() > 10:
                # Read a whole frame
                currentLine = self.s.readline

                # Try to get a whole frame
                while not (currentLine.startswith(b'$') and currentLine.endswith(b'\n')):
                    currentLine = self.s.readline()

                # Parse received line
                line_full = currentLine.replace(b'$', b'')
                line_full = line_full.replace(b',', b' ')
                line_full = line_full.replace(b';', b' ')
                line_as_list = line_full.split() # should extract mod2 n. numbers

                # Append new plotData as last and remove the first one
                self.plotData = np.vstack([self.plotData, [np.radians(float(line_as_list[0]) * 0.9), float(line_as_list[1])]])
                self.plotData = np.delete(self.plotData, 0, 0)
                self.currentSpeed = (line_as_list[2]).decode('utf-8')         # Read current speed
                self.currentStepSkip = (line_as_list[3]).decode('utf-8')      # Read current step skip
                self.currentTimeBudget = (line_as_list[4]).decode('utf-8')    # Read current time budget

                if self.canvasInitialized == 1:
                    self.loopTime = (line_as_list[5]).decode('utf-8')

                # Print debug data
                print('[INFO] Data received: ', currentLine, 'converted to: ', line_as_list )
                print('RX_Q:' + str(self.s.inWaiting())+" Cspd:"+
                      str(self.currentSpeed)+" Cskp: "+
                      str(self.currentStepSkip)+" CTme: "+
                      str(self.currentTimeBudget)+" DSize:("+
                      str(self.plotData[:,0].size)+" "+
                      str(self.plotData[:,1].size)+") ")

    def plot_init(self):
        # Create figure for plotting
        self.fig = plt.figure(figsize=(5, 5))                           # Matplotlib plot size
        self.ax = self.fig.add_subplot(111, polar=True)                 # Plot type
        self.headingLine, = self.ax.plot([], [], '-k', linewidth=0.5)   # Create heading indicator
        self.radarLine, = self.ax.plot([], [])                          # Create surrounding plot

        # Set plot details
        self.ax.set_facecolor('w')
        self.ax.set_theta_zero_location("N")
        self.ax.set_rlabel_position(359)
        self.ax.set_yticks([100, 200, 300, 400])
        self.ax.set_rmax(400)
        self.ax.set_rticks([0, 100, 200, 300, 400])  # Less radial ticks
        self.ax.set_title("Surroundings", va='bottom')
        self.ax.grid(True)

    def update_canvasLabels(self):
        self.canvas_label_currentSpeed.config(text="Current speed: " + self.currentSpeed + " RPM")
        self.canvas_label_currentStepSkip.config(text="Step jump: " + self.currentStepSkip + " steps")
        self.canvas_label_currentTimeBudget.config(text="Time budget: " + self.currentTimeBudget + " ms")
        self.canvas_label_loopTime.config(text="Loop time : " + self.loopTime + " ms")
        if self.s.isOpen():
            serialState = "Open"
        else :
            serialState = "Closed"
        self.canvas_label_serialStatus.config(text="Status: "+serialState)

    def update_speed(self):
        if self.s.isOpen():
            self.currentSpeed = self.entry_motorSpeed.get()
            if self.currentSpeed >'0':
                self.s.write(("@" + self.entry_motorSpeed.get()+'\r\n').encode('utf-8'))
                self.update_canvasLabels()
                self.s.flushInput()
        else:
            print("[ERROR] Please open the port first")

    def update_step_skip(self):
        if self.s.isOpen():
            self.currentStepSkip = self.entry_stepSkip.get()
            if self.currentStepSkip != '0':
                self.s.write(("%" + self.entry_stepSkip.get()+'\r\n').encode('utf-8'))
                self.update_canvasLabels()
                self.s.flushInput()
            self.plotResolution = abs(int(400/int(self.currentStepSkip)))           # Adjust buffer size
            self.plotData = zeros([self.plotResolution,2])                          # Flush existing data
        else:
            print("[ERROR] Please open the port first")

    def update_time_budget(self):
        if self.s.isOpen():
            self.currentTimeBudget = self.entry_timeBudget.get()
            if self.currentTimeBudget > '0':
                self.s.write(("&" + self.entry_timeBudget.get() + '\r\n').encode('utf-8'))
                self.update_canvasLabels()
                self.s.flushInput()
        else:
            print("[ERROR] Please open the port first")

    def init_window(self):

        def animate(i):
            self.update_canvasLabels()
            self.radarLine.set_data(self.plotData[:, 0], self.plotData[:, 1])
            self.headingLine.set_data(
                [self.plotData[self.plotResolution - 1, 0], self.plotData[self.plotResolution - 1, 0]],
                [0, 400])

        # Plot related
        self.plot_init()                                                # Set up matplotlib polar plot

        # Canvas related
        self.rootWindow.title("Polar plot")                                   # Set window title
        self.rootWindow.geometry("1000x800")                                  # Set dimensions of the main window
        self.mainCanvas = tk.Canvas(self.rootWindow, height=120,width=100)

        self.plotCanvas = FigureCanvasTkAgg(self.fig, master=self.rootWindow)         # Contain matplotlib plot
        self.plotCanvas = self.plotCanvas.get_tk_widget()                       # Convert it to canvas

        # Create Entries
        self.entry_motorSpeed = tk.Entry(self.rootWindow)                             # Create speed entry
        self.entry_timeBudget = tk.Entry(self.rootWindow)                             # Create speed entry
        self.entry_stepSkip = tk.Entry(self.rootWindow)                               # Create speed entry
        self.entry_serialBaud = tk.Entry(self.rootWindow)
        self.entry_serialPort = tk.Entry(self.rootWindow)
        self.entry_serialTimeout = tk.Entry(self.rootWindow)

        # Create Buttons
        self.button_motorSpeedApply = tk.Button(                                # Create speed button
            self.rootWindow,
            text='Apply new speed',
            command=lambda: self.update_speed(),
            bg="#ff1a1a",
            font=('Arial', 10))  # Create speed entry apply button
        self.button_timeBudgetApply = tk.Button(  # Create speed button
            self.rootWindow,
            text='Apply new time budget',
            command=lambda: self.update_time_budget(),
            bg="#ffff1a",
            font=('Arial', 10))  # Create speed entry apply button
        self.button_startSerial = tk.Button(
            self.rootWindow,
            text='Open serial connection',
            command=lambda: self.serial_try_open(),
            bg="#1aff1a",
            font=('Arial', 10))
        self.button_stopSerial = tk.Button(
            self.rootWindow,
            text='Close serial connection',
            command=lambda: self.serial_stop(),
            bg="#ff1a1a",
            font=('Arial', 10))
        self.button_stepSkipApply = tk.Button(  # Create speed button
                self.rootWindow,
                text='Apply new step skip',
                command=lambda: self.update_step_skip(),
                bg="#1affff",
                font=('Arial', 10))  # Create speed entry apply button

        # Create Labels
        self.canvas_label_serialStatus = tk.Label(self.rootWindow, text="Status: Not connected",highlightcolor="#ff0000",
                                                  anchor='nw',font=('Arial', 10))
        self.canvas_label_currentSpeed = tk.Label(self.rootWindow, text="Current speed: NaN", anchor='nw', font=('Arial', 10))
        self.canvas_label_currentTimeBudget = tk.Label(self.rootWindow, text="Current time budget: NaN", anchor='nw',
                                                       font=('Arial', 10))
        self.canvas_label_currentStepSkip = tk.Label(self.rootWindow, text="Current motor skip: NaN", anchor='nw', font=('Arial', 10))
        self.canvas_label_loopTime = tk.Label(self.rootWindow, text="Loop time: NaN", anchor='nw', font=('Arial', 10))

        self.canvas_label_serialBaud  = tk.Label(self.rootWindow, text="Baud rate:", anchor='nw', font=('Arial', 10))
        self.canvas_label_serialTimeout  = tk.Label(self.rootWindow, text="Timeout:", anchor='nw', font=('Arial', 10))
        self.canvas_label_serialPort  = tk.Label(self.rootWindow, text="Port:", anchor='nw', font=('Arial', 10))

        # Place main canvas
        self.mainCanvas.pack(fill='both')

        # Arrange Entries
        self.mainCanvas.create_window(10, 10, window=self.entry_motorSpeed, width=50, height=25, anchor='nw')
        self.mainCanvas.create_window(10, 35, window=self.entry_timeBudget, width=50, height=25, anchor='nw')
        self.mainCanvas.create_window(10, 60, window=self.entry_stepSkip, width=50, height=25, anchor='nw')
        self.mainCanvas.create_window(500, 10, window=self.entry_serialPort, width=100, height=25, anchor='nw')
        self.mainCanvas.create_window(500, 35, window=self.entry_serialBaud, width=100, height=25, anchor='nw')
        self.mainCanvas.create_window(500, 60, window=self.entry_serialTimeout, width=100, height=25, anchor='nw')

        # Arrange Buttons
        self.mainCanvas.create_window(70, 10, window=self.button_motorSpeedApply, width=150, height=25, anchor='nw')
        self.mainCanvas.create_window(70, 35, window=self.button_timeBudgetApply, width=150, height=25, anchor='nw')
        self.mainCanvas.create_window(70, 60, window=self.button_stepSkipApply, width=150, height=25, anchor='nw')
        self.mainCanvas.create_window(610,10, window=self.button_startSerial, width=150, height=25, anchor='nw')
        self.mainCanvas.create_window(610,35, window=self.button_stopSerial, width=150, height=25, anchor='nw')

        # Arrange Labels
        self.canvas_label_currentSpeed.place(x=230, y=10, anchor='nw')
        self.canvas_label_currentTimeBudget.place(x=230, y=35, anchor='nw')
        self.canvas_label_currentStepSkip.place(x=230, y=60, anchor='nw')
        self.canvas_label_loopTime.place(x=230, y=85, anchor='nw')
        self.canvas_label_serialStatus.place(x=610, y=60, anchor='nw')
        self.canvas_label_serialPort.place(x=465, y=10, anchor='nw')
        self.canvas_label_serialBaud.place(x=432, y=35, anchor='nw')
        self.canvas_label_serialTimeout.place(x=442,y=60,anchor='nw')

        # Add matplotlib canvas to picutre
        self.plotCanvas.pack(fill='both', expand=1)
        self.canvasInitialized = 1

        # Start animation
        self.ani = animation.FuncAnimation(self.fig, animate, interval=20, frames=1)    # Start animation


serPlot = serialPolarPlot(serialPort='COM7', baudrate=57600, serialTimeout=0.1, plotResolution=50)