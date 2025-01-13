# Author : Tyler Eastmond, teastmond@anl.gov
# Date last revised: 2/3/2023
# Recent updates:
    # Adding ability to measure sample temperature and resistance or seebeck data at alternating intervals


#####################################################################################################################################    
# import modules
import sys
import pyvisa
import time
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtGui import QPalette, QColor
from pyqtgraph import plot, InfiniteLine, InfLineLabel
from PyQt5.QtCore import QThread 
from Delta_measure_GUI_tabbedPlots_rev3_ui import Ui_MainWindow
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox
from datetime import datetime
from pathlib import Path
# import worker classes for multithreading functionality
from Worker_delta_measurements_module import Worker_delta_measurements
from Worker_seebeck_measurements_module import Worker_seebeck_measurements
from Worker_temperature_measurements_module import Worker_temperature_measurements
from Worker_RT_measurements_module import Worker_RT_measurements
from Worker_ST_measurements_module import Worker_ST_measurements
# from Delta_measurement_methods import *

# get device addresses and assign to variables
rm = pyvisa.ResourceManager()
device_addresses = rm.list_resources()
print(device_addresses)
address_current = device_addresses[2]
address_switch = device_addresses[3]
device_current = rm.open_resource(address_current)
device_switch = rm.open_resource(address_switch)
print(device_current)
# device_volt = rm.open_resource(address)
# Turn of annoying current source beeper
device_current.write("system:beeper:state OFF")

volt_comm = True
switch_comm = True
current_comm = True


# subclass QWidget
class Color(QWidget):
    def __init__(self, color):
        super(Color, self).__init__()

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)
    

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.task = {'break': False} # dict with flag for thread stopping
        

        # set app window title
        self.setWindowTitle("Thermoelectric Measurements")
        
        # set up clicking signals for push buttons
        # Resistance measurement buttons
        self.resetBox.clicked.connect(self.resetBox_clicked)
        self.startBox.clicked.connect(self.startBox_clicked)
        self.stopBox.clicked.connect(self.stopBox_clicked)
        # Seebeck measurement buttons
        self.start_seebeck.clicked.connect(self.start_seebeck_clicked)
        self.stop_seebeck.clicked.connect(self.stop_seebeck_clicked)
        # Temperature measurement buttons
        self.start_temp.clicked.connect(self.start_temp_clicked)
        self.stop_temp.clicked.connect(self.stop_temp_clicked)
        # RT (resistance and temperature) measurement buttons
        self.start_RT.clicked.connect(self.start_RT_clicked)
        self.stop_RT.clicked.connect(self.stop_RT_clicked)
        # ST (Seebeck and temperature) measurement buttons
        self.start_ST.clicked.connect(self.start_ST_clicked)
        self.stop_ST.clicked.connect(self.stop_ST_clicked)
        # Plot zoom setting boxes
        self.x_zoom_button.clicked.connect(self.x_zoom_button_clicked)
        self.y_zoom_button.clicked.connect(self.y_zoom_button_clicked)
        self.zoom_reset_button.clicked.connect(self.zoom_reset_button_clicked)
        

        # set device communication indicators
        if volt_comm == True:
            self.volt_comm_status.setText('Yes')
            self.volt_comm_status.setStyleSheet("background-color: lime")
        else:
            self.volt_comm_status.setStyleSheet("background-color: red")

        if switch_comm == True:
            self.switch_comm_status.setText('Yes')
            self.switch_comm_status.setStyleSheet("background-color: lime")
        else:
            self.switch_comm_status.setStyleSheet("background-color: red")

        if current_comm == True:
            self.current_comm_status.setText('Yes')
            self.current_comm_status.setStyleSheet("background-color: lime")
        else:
            self.current_comm_status.setStyleSheet("background-color: red")


        # Add items for dropdown menus
        self.comboBox1.addItems(['Volts','Ohms'])
        self.comboBox2.addItems(['0.01', '0.1', '1', '10'])
        
        # set up signals for comboboxes
        self.comboBox1.currentIndexChanged.connect(self.comboBox1_content)
        self.comboBox2.currentIndexChanged.connect(self.comboBox2_content)

        # set up defaults for comboboxes
        self.comboBox2.setCurrentIndex(2) # set default voltage range to 1 V

        # set default of current limits
        self.I_high_set.setText('0.100')
        self.I_low_set.setText('-0.100')

        # set default filepath
        # self.filepath_input.setText('\\Users\\teast\\Documents\\Tyler\\Work\\HPCAT_Postdoc\\Data\\2023-1\\20230322_Bi8\\RT_measurements')
        # self.filepath_input.setText('/Users/teast/Documents/Tyler/Work/HPCAT_Postdoc/Data/2023-1/20230218_NaCl1/RT_measurements')
        # self.filepath_input.setText('Z:\\Eastmond\\HPCAT_Postdoc\\Data\\2024-offline\\202402_Mar\\Bi_L2_1pt5mm_1')
        self.filepath_input.setText('Z:\\Eastmond\\HPCAT_Postdoc\\Data\\2024-offline\\202410_Oct\\Cu_L2_D1500um_1')

        # set up signals for current limit boxes
        self.set_current_button.clicked.connect(self.set_current_button_clicked)
        
        # set up signals for file saving
        self.file_save_confirm.clicked.connect(self.get_filepath_info) 

        # set indicator light color
        self.v_comm_indicator = Color("red")
        self.v_comm_indicator.setStyleSheet("Qwidget {background-color: red; }")
  
        # resistance data live plot widget
        self.graphWidget.setBackground('w')
        self.graphWidget.addLegend()
        styles = {"color": 'k', "font-size": "18px"}
        self.graphWidget.setLabel("left",'Voltage drop (V)',**styles)
        self.graphWidget.setLabel("bottom",'Time (s)',**styles)
        # initiate empty plot
        self.data_line = self.graphWidget.plot([],[],pen = pg.mkPen(color = 'k'), symbolPen = 'k', \
            symbolBrush = 'k', symbolSize = 10, symbol = 'x', name = 'Sample resistance')

        # temperature data live plot widget
        self.graphWidget_2.setBackground('w')
        self.graphWidget_2.addLegend()
        styles = {"color": 'k', "font-size": "18px"}
        self.graphWidget_2.setLabel("left",'Temperature (C)',**styles)
        self.graphWidget_2.setLabel("bottom",'Time (s)',**styles)
        # initialize empty plot
        self.data_line1 = self.graphWidget_2.plot([],[],pen = pg.mkPen(color = 'k'), symbolPen = 'k', \
            symbolBrush = 'k', symbolSize = 10, symbol = 'x', name = 'Sample top face temperature')
        self.data_line2 = self.graphWidget_2.plot([],[],pen = pg.mkPen(color = 'r'), symbolPen = 'k', \
            symbolBrush = 'r', symbolSize = 10, symbol = 'x', name = 'Sample bottom face temperature')
        self.temp_marker = InfiniteLine(pos = 0,angle = 0, movable = True)
        self.graphWidget_2.addItem(self.temp_marker)
        self.temp_marker_label = InfLineLabel(self.temp_marker, movable = True, position = 0.9)
        self.temp_marker_label.setFormat('{value}')
        self.time_marker = InfiniteLine(pos = 0, angle = 90, movable = True)
        self.graphWidget_2.addItem(self.time_marker)
        self.time_marker_label = InfLineLabel(self.time_marker, movable = True, position = 0.9)
        self.time_marker_label.setFormat('{value}')

      
        
        # self.data_temp_marker = self.graphWidget_2.InfiniteLine(pos = 100,angle = 0)
        # self.data_temp_marker = self.graphWidget_2.addLine(x = None, y = 0, pen = pg.mkPen(color = 'b'), name = 'Target temperature')

        # seebeck data live plot widget
        self.graphWidget_3.setBackground('w')
        self.graphWidget_3.addLegend()
        styles = {"color": 'k', "font-size": "18px"}
        self.graphWidget_3.setLabel("left",'Voltage Drop (V)',**styles)
        self.graphWidget_3.setLabel("bottom",'Time (s)',**styles)
        # Inititae empty plots
        self.data_line_a = self.graphWidget_3.plot([],[],pen = pg.mkPen(color = 'k'), symbolPen = 'k', \
            symbolBrush = 'k', symbolSize = 10, symbol = 'x', name = 'Alumel voltage drop')
        self.data_line_c = self.graphWidget_3.plot([],[],pen = pg.mkPen(color = 'r'), symbolPen = 'k', \
            symbolBrush = 'r', symbolSize = 10, symbol = 'x', name = 'Chromel voltage drop')
        
       
        # initialize arrays for resistance measurements
        self.resistances = []
        self.time_val_abs = []
        self.time_val_rel = []

        # initialize arrays for temperature measurements
        self.Tsample_top = []
        self.Tsample_bottom = []
        self.Ttop_time_abs= []
        self.Ttop_time_rel = []
        self.Tbot_time_abs= []
        self.Tbot_time_rel = []

        # initialize arrays for voltage measurements (Seebeck coefficients)
        self.Vdrop_chromel = []
        self.Vdrop_alumel = []
        self.time_chromel_abs = []
        self.time_chromel_rel = []
        self.time_alumel_abs = []
        self.time_alumel_rel = []

##################################################################################################

    # register push button clicks and check communication with voltmeter  
    def resetBox_clicked(self):
        print("resetting devices")
        device_current.write("*rst; status:preset; *cls")
        # turn off beeper
        device_current.write("system:beeper:state OFF")
        # initialize and reset the switcher
        device_switch.write("*rst; status:preset; *cls") # reset the device, clear error codes
        # open all switcher channels
        device_switch.write("open all")
        # initialize and reset the voltmeter
        device_current.write("SYST:COMM:SER:SEND '*rst; status:preset; *cls'")
        device_current.write("SYST:COMM:SER:SEND 'system:beeper:state OFF'")
        # verify that current source can communicate with voltmeter
        time.sleep(1)
        com_verify = device_current.query("source:DELTA:NVPRESENT?")
        if com_verify == "1\n":
            print("Communication with Keithley 2182A verified")
        else:
            print("No communcation with Keithley 2182A")

####################################################################################################
    
    def startBox_clicked(self):
        # disable other program buttons
        self.resetBox.setEnabled(False)
        self.start_seebeck.setEnabled(False)
        self.stop_seebeck.setEnabled(False)
        self.start_temp.setEnabled(False)
        self.stop_temp.setEnabled(False)
        self.start_RT.setEnabled(False)
        self.stop_RT.setEnabled(False)
        self.start_ST.setEnabled(False)
        self.stop_ST.setEnabled(False)


        # open all channels
        device_switch.write("open all")
        # close Bank A channel 2 (for resistance measurements)
        device_switch.write("close (@1!2)")
        # reset devices 
        device_current.write(":sour:swe:abort")
        device_current.write(":sour:wave:abor")
        device_current.write("*rst") 
        
        time.sleep(500e-3)
        # device_current.write("WAIT500")
        device_current.write(":form:elem READ,TST,RNUM,AVOL")
        device_current.write(":sour:delt:high " + str(self.I_high_set.text()))
        device_current.write(":sour:delt:low " + str(self.I_low_set.text()))
        device_current.write(":sour:delt:count INF")
        device_current.write(":sour:delt:delay 0.01")
        device_current.write(":sour:curr:comp 10")
        device_current.write("UNIT " +  str(self.comboBox1.itemText(self.comboBox1.currentIndex())))
        # device_current.write(":sour:curr:filt:stat <DELTADAMPING>")
        # device_current.write(":sour:curr:rang <DELTACURRRANGE>")
        device_current.write(":SYST:COMM:SERIal:SEND '*rst'")
        device_current.write(":SYST:COMM:SER:SEND 'system:beeper:state OFF'")
        
        time.sleep(400e-3)
        device_current.write(":SYST:COMM:SERIal:SEND ':sens:volt:nplc 5'")
        time.sleep(1500e-3)
        device_current.write(":SYST:COMM:SERIal:SEND ':sens:volt:rang " + str(self.comboBox2.itemText(self.comboBox2.currentIndex())) + "'")
        # device_current.write(":SYST:COMM:SERIal:SEND ':sens:volt:rang?'")
        # print(device_current.write(":SYST:COMM:SERIal:SEND 'READ?'"))
        # DC moving filter parameters
        device_current.write(":SYST:COMM:SERIal:SEND ':SENS:VOLT:CHAN1:DFIL:TCONtrol MOV'")
        device_current.write(":SYST:COMM:SERIal:SEND ':SENS:VOLT:CHAN1:DFIL:COUNt 100'")
        device_current.write(":SYST:COMM:SERIal:SEND ':SENS:VOLT:CHAN1:DFIL:STATe ON'")
        time.sleep(500e-3)
        device_current.write(":sour:delt:arm")
        time.sleep(1000e-3)
        device_current.write(":init:imm")    

        # # different filter types, can play around with these later
        # :sens:aver:wind 0
        # :sens:aver:stat <DELTAFILTERSTATE>
        # :sens:aver:coun <DELTAFILTERCOUNT>
        # :sens:aver:tcon <DELTAFILTERTYPE>


        # # set Delta delay
        # device_current.write("source:delta:delay 0.3") # 0.3 second delay
        # # set Delta count
        # device_current.write("source:delta:count INF") # number of counts
        # # set current limit
        # device_current.write("source:delta:high " + str(self.I_high_set.text()))
        # # set buffer 
        # # device_current.write("TRAC:POIN 1000") # set number of buffer points
        # # arm Delta
        # device_current.write("source:delta:arm")
        # time.sleep(1)
        # start Delta measurements
        # device_current.write("INIT:IMM")
        
        # # create a new thread to offload the data acquisition
        self.thread = QThread()
        # Create a worker object
        self.worker = Worker_delta_measurements(self.task,device_current,self.full_path_res)
        # self.worker = Worker_delta_measurements(self.task,self.full_path_res,self.filepath)
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.run) # run the acquisition function in the worker
        self.worker.newdata.connect(self.update_resistance_plot) # update the plot when new data is available
        self.worker.finished.connect(self.thread.quit) # quit the thread
        self.worker.finished.connect(self.thread.wait) # wait until thread finishes running 
        self.thread.finished.connect(self.thread.deleteLater) # delete thread
        self.worker.finished.connect(self.thread.deleteLater) # delete worker
        self.worker.finished.connect(self.delete_vars) # reset data arrays after thread finishes
        self.thread.start() # Start the thread
        print('Initiating resistance measurements') 


    def stopBox_clicked(self):
        # send "stop" flag to the worker thread
        self.task['break'] = True
        # disarm Delta measurements
        device_current.write("SOUR:SWE:ABOR")
        print('Stopping devices, data acquisition aborted')
        # enable other program buttons
        self.resetBox.setEnabled(True)
        self.start_seebeck.setEnabled(True)
        self.stop_seebeck.setEnabled(True)
        self.start_temp.setEnabled(True)
        self.stop_temp.setEnabled(True)
        self.start_RT.setEnabled(True)
        self.stop_RT.setEnabled(True)
        self.start_ST.setEnabled(True)
        self.stop_ST.setEnabled(True)
        

######################################################################################################  

    def start_temp_clicked(self):
        # disable other program buttons
        self.resetBox.setEnabled(False)
        self.startBox.setEnabled(False)
        self.stopBox.setEnabled(False)
        self.start_seebeck.setEnabled(False)
        self.stop_seebeck.setEnabled(False)
        self.start_RT.setEnabled(False)
        self.stop_RT.setEnabled(False)
        self.start_ST.setEnabled(False)
        self.stop_ST.setEnabled(False)
        # set power source to output zero current
        device_current.write("source:current:AMPL 0")
        device_current.write("OUTPUT:STAT OFF") # turn off power source
        # voltmeter temperature mode settings
        device_current.write(":SYST:COMM:SER:SEND " + "'system:beeper:state OFF'")
        device_current.write("SYST:COMM:SER:SEND " + "'SENS:TEMP:TRAN TC'") # select thermocouple sensor
        device_current.write("SYST:COMM:SER:SEND " + "'SENS:TEMP:RJUN:RSEL INT'") # select internal reference
        device_current.write("SYST:COMM:SER:SEND " + "'SENS:TEMP:TC K'") # Set for type K thermocouple.
        device_current.write("SYST:COMM:SER:SEND " + "'SENS:CHAN 1'") # select channel 1
        device_current.write("SYST:COMM:SER:SEND " + "'UNIT:TEMP C'") # Read in °C
        device_current.write("SYST:COMM:SER:SEND " + "'SENS:FUNC " + "''TEMP''" + "'") # set voltmeter to measure temperature
        # tell the device to trigger internally
        device_current.write("SYST:COMM:SER:SEND " + "'trigger:source immediate'")
        # create a new thread to offload the data acquisition
        self.thread = QThread()
        # Create a worker object
        # self.worker = Worker_temperature_measurements(self.task, device_current, device_switch, self.full_path_temp)
        self.worker = Worker_temperature_measurements(self.task, self.full_path_temp)
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.run) # run the acquisition function in the worker
        self.worker.newdata.connect(self.update_temperature_plot) # update the plot when new data is available
        self.worker.finished.connect(self.thread.quit) # quit the thread
        self.worker.finished.connect(self.thread.wait) # wait until thread finishes running 
        self.thread.finished.connect(self.thread.deleteLater) # delete thread
        self.worker.finished.connect(self.thread.deleteLater) # delete worker
        self.worker.finished.connect(self.delete_vars) # reset data arrays after thread finishes
        self.thread.start() # Start the thread
        print('Initiating temperature measurements')         

    
    def stop_temp_clicked(self):
        # send "stop" flag to the thread
        self.task['break'] = True
        print('Stopping devices, data acquisition aborted')
        # disable other program buttons
        self.resetBox.setEnabled(True)
        self.startBox.setEnabled(True)
        self.stopBox.setEnabled(True)
        self.start_seebeck.setEnabled(True)
        self.stop_seebeck.setEnabled(True)
        self.start_RT.setEnabled(True)
        self.stop_RT.setEnabled(True)
        self.start_ST.setEnabled(True)
        self.stop_ST.setEnabled(True)
   

#######################################################################################################

    
    def start_seebeck_clicked(self):
        # disable other program buttons
        self.resetBox.setEnabled(False)
        self.startBox.setEnabled(False)
        self.stopBox.setEnabled(False)
        self.start_temp.setEnabled(False)
        self.stop_temp.setEnabled(False)
        self.start_RT.setEnabled(False)
        self.stop_RT.setEnabled(False)
        self.start_ST.setEnabled(False)
        self.stop_ST.setEnabled(False)
        # set power source to output zero current
        device_current.write("source:current:AMPL 0")
        device_current.write("OUTPUT:STAT OFF")
        # tell the device to trigger internally
        device_current.write("SYST:COMM:SER:SEND " + "'trigger:source immediate'")
        # set voltmeter to measure volts and get the range from the GUI
        device_current.write("SYST:COMM:SER:SEND " + "'SENS:FUNC " + "''VOLT''" + "'")
        device_current.write("SYST:COMM:SER:SEND ':sens:volt:rang " + str(self.comboBox2.itemText(self.comboBox2.currentIndex())) + "'")
        # device_current.write("SYST:COMM:SER:SEND " + "'INITiate:CONTinuous ON'") # continuous triggering
        # device_current.write("OUTPUT:STAT ON") # for testing only    
        # create a new thread to offload the data acquisition
        self.thread = QThread()
        # Create a worker object
        self.worker = Worker_seebeck_measurements(self.task, device_current, device_switch, self.full_path_volt)
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.run) # run the acquisition function in the worker
        self.worker.newdata.connect(self.update_Vdrop_plot) # update the plot when new data is available
        self.worker.finished.connect(self.thread.quit) # quit the thread
        self.worker.finished.connect(self.thread.wait) # wait until thread finishes running 
        self.thread.finished.connect(self.thread.deleteLater) # delete thread
        self.worker.finished.connect(self.thread.deleteLater) # delete worker
        self.worker.finished.connect(self.delete_vars) # reset data arrays after thread finishes
        self.thread.start() # Start the thread
        print('Initiating seebeck measurements') 

    
    def stop_seebeck_clicked(self):
        # send "stop" flag to the worker thread
        self.task['break'] = True
        print('Stopping devices, data acquisition aborted')
        # disable other program buttons
        self.resetBox.setEnabled(True)
        self.startBox.setEnabled(True)
        self.stopBox.setEnabled(True)
        self.start_temp.setEnabled(True)
        self.stop_temp.setEnabled(True)
        self.start_RT.setEnabled(True)
        self.stop_RT.setEnabled(True)
        self.start_ST.setEnabled(True)
        self.stop_ST.setEnabled(True)


#############################################################################################################
# start resistance + temperature measurements
    
    def start_RT_clicked(self):
        # disable other program buttons
        self.resetBox.setEnabled(False)
        self.startBox.setEnabled(False)
        self.stopBox.setEnabled(False)
        self.start_temp.setEnabled(False)
        self.stop_temp.setEnabled(False)
        self.start_seebeck.setEnabled(False)
        self.stop_seebeck.setEnabled(False)
        self.start_ST.setEnabled(False)
        self.stop_ST.setEnabled(False)
       
        # create a new thread to offload the data acquisition
        self.thread = QThread()
        # Create a worker object
        self.worker = Worker_RT_measurements(self.task, device_current, device_switch, self.full_path_temp, self.full_path_res, \
                                             self.I_high_set.text(), self.I_low_set.text(), self.comboBox2.itemText(self.comboBox2.currentIndex()), \
                                                self.comboBox1.itemText(self.comboBox1.currentIndex()))
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.run) # run the acquisition function in the worker
        self.worker.newdata_temp.connect(self.update_temperature_plot) # update the temperature plot when new data is available
        self.worker.newdata_res.connect(self.update_resistance_plot) # update the resistance plot when new data is available
        self.worker.finished.connect(self.thread.quit) # quit the thread
        self.worker.finished.connect(self.thread.wait) # wait until thread finishes running 
        self.thread.finished.connect(self.thread.deleteLater) # delete thread
        self.worker.finished.connect(self.thread.deleteLater) # delete worker
        self.worker.finished.connect(self.delete_vars) # reset data arrays after thread finishes
        self.thread.start() # Start the thread
        print('Initiating resistance-temperature measurements')         

    
    def stop_RT_clicked(self):
        # send "stop" flag to the thread
        self.task['break'] = True
        # disarm Delta measurements
        device_current.write("SOUR:SWE:ABOR")
        print('Stopping devices, data acquisition aborted')
        # disable other program buttons
        self.resetBox.setEnabled(True)
        self.startBox.setEnabled(True)
        self.stopBox.setEnabled(True)
        self.start_temp.setEnabled(True)
        self.stop_temp.setEnabled(True)
        self.start_seebeck.setEnabled(True)
        self.stop_seebeck.setEnabled(True)
        self.start_ST.setEnabled(True)
        self.stop_ST.setEnabled(True)


#####################################################################################################
# start seebeck + temperature measurements
    
    def start_ST_clicked(self):
        # disable other program buttons
        self.resetBox.setEnabled(False)
        self.startBox.setEnabled(False)
        self.stopBox.setEnabled(False)
        self.start_temp.setEnabled(False)
        self.stop_temp.setEnabled(False)
        self.start_seebeck.setEnabled(False)
        self.stop_seebeck.setEnabled(False)
        self.start_RT.setEnabled(False)
        self.stop_RT.setEnabled(False)
       
        # create a new thread to offload the data acquisition
        self.thread = QThread()
        # Create a worker object
        self.worker = Worker_ST_measurements(self.task, device_current, device_switch, self.full_path_temp, self.full_path_volt, self.comboBox2.itemText(self.comboBox2.currentIndex()))
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.run) # run the acquisition function in the worker
        self.worker.newdata_temp.connect(self.update_temperature_plot) # update the temperature plot when new data is available
        self.worker.newdata_volt.connect(self.update_Vdrop_plot) # update the resistance plot when new data is available
        self.worker.finished.connect(self.thread.quit) # quit the thread
        self.worker.finished.connect(self.thread.wait) # wait until thread finishes running 
        self.thread.finished.connect(self.thread.deleteLater) # delete thread
        self.worker.finished.connect(self.thread.deleteLater) # delete worker
        self.worker.finished.connect(self.delete_vars) # reset data arrays after thread finishes
        self.thread.start() # Start the thread
        print('Initiating resistance-temperature measurements')   

    
    def stop_ST_clicked(self):
        # send "stop" flag to the thread
        self.task['break'] = True
        # disarm Delta measurements
        device_current.write("SOUR:SWE:ABOR")
        print('Stopping devices, data acquisition aborted')
        # disable other program buttons
        self.resetBox.setEnabled(True)
        self.startBox.setEnabled(True)
        self.stopBox.setEnabled(True)
        self.start_temp.setEnabled(True)
        self.stop_temp.setEnabled(True)
        self.start_seebeck.setEnabled(True)
        self.stop_seebeck.setEnabled(True)
        self.start_RT.setEnabled(True)
        self.stop_RT.setEnabled(True)
        

################################################################################################################################

    def delete_vars(self):
        # reinitialize arrays for next round of measurements
        self.resistances = []
        self.time_val_abs = []
        self.time_val_rel = []
        self.Tsample_top = []
        self.Tsample_bottom = []
        self.Ttop_time_abs= []
        self.Ttop_time_rel = []
        self.Tbot_time_abs= []
        self.Tbot_time_rel = []
        self.Vdrop_chromel = []
        self.Vdrop_alumel = []
        self.time_chromel_abs = []
        self.time_chromel_rel = []
        self.time_alumel_abs = []
        self.time_alumel_rel = []

    
    # get combo box values
    def comboBox1_content(self,index):
        print(index)
        voltmeter_units = self.comboBox1.itemText(index)
        device_current.write("UNIT " +  voltmeter_units)
        print(voltmeter_units)


    def comboBox2_content(self,index):
        voltmeter_range = self.comboBox2.itemText(index)
        # set voltage range
        device_current.write("SYST:COMM:SER:SEND " + "'VOLT:RANG " + voltmeter_range + "'")
        print(voltmeter_range)


    # set high and low current limits
    def set_current_button_clicked(self):
        current_high = float(self.I_high_set.text()) # high current limit in amps
        current_low = float(self.I_low_set.text()) # low current limit in amps
        current_max = .105 # limit the maximum absolute value of current. Can only change this here for now
        # check that setpoint is less than the max limit
        if abs(current_high) > current_max or abs(current_low) > current_max:
            print("Max current limit set to " + str(current_max) + " amps")
            msg = QMessageBox()
            msg.setWindowTitle("Error")
            msg.setText("Maximum absolute value of current limit is " + str(current_max) + " amps")
            msg.exec_()
        else:
            device_current.write("source:delta:high " + str(current_high))
            device_current.write("source:delta:low " + str(current_low))


    # generate 3 text files (1 for each measurement type) and save at filepath/filename + _res OR _temp OR _volt
    def get_filepath_info(self):
        self.filepath = self.filepath_input.text()
        self.filename_base = self.filename_input.text()
        self.full_path_res = self.filepath + '\\' + self.filename_base + '_res'     # resistance file
        self.full_path_temp = self.filepath + '\\' + self.filename_base + '_temp'   # temperature file
        self.full_path_volt = self.filepath + '\\' + self.filename_base + '_volt'   # voltage file
        # safety check to ensure previous files are not overwritten
        path1 = Path(self.full_path_res + '.txt')
        path2 = Path(self.full_path_temp + '.txt')
        path3 = Path(self.full_path_volt + '.txt')
        
        if path1.is_file() or path2.is_file() or path3.is_file() == True: # if any of these filenames already exist, print an error message
            msg = QMessageBox()
            msg.setWindowTitle("Warning")
            msg.setText("This filename already exists. Please choose a different name.")
            msg.exec_()
        else: # continue to write the base files
            # get timestamp
            date_today = datetime.fromtimestamp(time.time())
            # write resistance file
            with open(self.full_path_res + ".txt",mode = 'w') as txtfile:
                txtfile.write('Thermoelectric measurements: ' + str(date_today)) 
                txtfile.write('\n')
                txtfile.write('Day Time_stamp(s) Time(s)_relative Voltage_drop(V)')
                # write resistance file
            with open(self.full_path_temp + ".txt",mode = 'w') as txtfile:
                txtfile.write('Thermoelectric measurements: ' + str(date_today)) 
                txtfile.write('\n')
                txtfile.write('Day Time_stamp(s) Time(s)_relative Top_face_temperature(C) Bottom_face_temperature(C)')
                # write resistance file
            with open(self.full_path_volt + ".txt",mode = 'w') as txtfile:
                txtfile.write('Thermoelectric measurements: ' + str(date_today)) 
                txtfile.write('\n')
                txtfile.write('Day Time_stamp(s) Time(s)_relative Vdrop_Alumel(V) Vdrop_Chromel(V)')


    def update_resistance_plot(self, data):
        self.resistances.append(data[0])
        self.time_val_rel.append(data[2])
        self.data_line.setData(self.time_val_rel, self.resistances)  # Update the data
    

    def update_Vdrop_plot(self,data_total_alumel,data_total_chromel):
        self.Vdrop_alumel.append(data_total_alumel[0])
        self.time_alumel_rel.append(data_total_alumel[2])
        self.Vdrop_chromel.append(data_total_chromel[0])
        self.time_chromel_rel.append(data_total_chromel[2])
        self.data_line_a.setData(self.time_alumel_rel, self.Vdrop_alumel)  # Update the alumel data
        self.data_line_c.setData(self.time_chromel_rel, self.Vdrop_chromel)  # Update the chromel data


    def update_temperature_plot(self, data_total_top, data_total_bot):
        self.Tsample_top.append(data_total_top[0])
        self.Ttop_time_rel.append(data_total_top[2])
        self.Tsample_bottom.append(data_total_bot[0])
        self.Tbot_time_rel.append(data_total_bot[2])
        self.data_line1.setData(self.Ttop_time_rel, self.Tsample_top)  # Update the top face temperature data
        self.data_line2.setData(self.Tbot_time_rel, self.Tsample_bottom)  # Update the bottom face temperature data 

    def x_zoom_button_clicked(self):
        self.graphWidget.plotItem.setMouseEnabled(y = False)
        self.graphWidget.plotItem.setMouseEnabled(x = True)
        self.graphWidget_2.plotItem.setMouseEnabled(y = False)
        self.graphWidget_2.plotItem.setMouseEnabled(x = True)
        self.graphWidget_3.plotItem.setMouseEnabled(y = False)
        self.graphWidget_3.plotItem.setMouseEnabled(x = True)

    def y_zoom_button_clicked(self):
        self.graphWidget.plotItem.setMouseEnabled(x = False)
        self.graphWidget.plotItem.setMouseEnabled(y = True)
        self.graphWidget_2.plotItem.setMouseEnabled(x = False)
        self.graphWidget_2.plotItem.setMouseEnabled(y = True)
        self.graphWidget_3.plotItem.setMouseEnabled(x = False)
        self.graphWidget_3.plotItem.setMouseEnabled(y = True)

    def zoom_reset_button_clicked(self):
        self.graphWidget.plotItem.setMouseEnabled(x = True)
        self.graphWidget.plotItem.setMouseEnabled(y = True)    
        self.graphWidget_2.plotItem.setMouseEnabled(x = True)
        self.graphWidget_2.plotItem.setMouseEnabled(y = True) 
        self.graphWidget_3.plotItem.setMouseEnabled(x = True)
        self.graphWidget_3.plotItem.setMouseEnabled(y = True)    
    
   


   


app = QtWidgets.QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()

