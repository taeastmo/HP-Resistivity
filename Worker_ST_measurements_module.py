# import modules
from PyQt5.QtCore import pyqtSignal, QObject
import time
from datetime import datetime
from PyQt5 import QtCore

# Worker class to offload sample temperature and resistance data acquisition to a new thread
class Worker_ST_measurements(QObject):
    newdata_temp = pyqtSignal(object,object) # signal after new temperature data is acquired
    newdata_volt = pyqtSignal(object,object) # signal after new resistance data is acquired
    finished = pyqtSignal() # signal after data logging is complete
    
    def __init__(self, task, device_current, device_switch, filepath_temp, filepath_volt, volt_range):
            super().__init__()
            # assign the stop task and device addresses to "self" variables
            self.task = task
            self.device_current = device_current
            self.device_switch = device_switch
            self.filepath_temp = filepath_temp
            self.filepath_volt = filepath_volt
            self.volt_range = volt_range
    # acquire data from voltmeter, pass it to the main class, and save the data
    def run(self):
        self.task['break'] = False
        print('ST worker thread is active')

        # Ensure current source output is turned off
        self.device_current.write("source:current:AMPL 0")
        self.device_current.write("OUTPUT:STAT OFF") # turn off power source
        # update plot of voltage drops
        # get absolute time
        self.time_abs_start = time.time()

        while True:
        ############################################# TEMPERATURE MEASUREMENT #################################################
            
            # Acquire sample top face temperature
            # voltmeter temperature mode settings
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:TEMP:TRAN TC'") # select thermocouple sensor
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:TEMP:RJUN:RSEL INT'") # select internal reference
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:TEMP:TC K'") # Set for type K thermocouple.
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:CHAN 1'") # select channel 1
            self.device_current.write("SYST:COMM:SER:SEND " + "'UNIT:TEMP C'") # Read in °C
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:FUNC " + "''TEMP''" + "'") # set voltmeter to measure temperature
            self.device_current.write("SYST:COMM:SER:SEND " + "'trigger:source immediate'") # tell device to trigger internally
            
            # timed while loop to acquire temperature for a few seconds
            timeout = 6   # [seconds]
            timeout_start = time.time()
            while time.time() < timeout_start + timeout:
                self.device_switch.write("open all") # open all channels
                self.device_switch.write("close (@1!5)") # close Bank A channel 5 (top sample face temperature)
                time.sleep(500e-3)
                self.device_current.write("SYST:COMM:SER:SEND " + "'initiate'") # trigger the device
                self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
                time.sleep(500e-3) # set delay to avoid query interuption error
                self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
                # print(self.device_current.read())
                data_top = float(self.device_current.read()) # read the value from the current source buffer
                Ttop_time_abs = datetime.fromtimestamp(time.time())
                Ttop_time_rel = time.time() - self.time_abs_start
                data_total_top = [data_top, Ttop_time_abs, Ttop_time_rel]
                
                # Acquire sample bottom face temperature
                self.device_switch.write("open all") # open all switcher channels
                self.device_switch.write("close (@1!8)") # close Bank A channel 8 (sample bottom face temperature)
                time.sleep(500e-3)
                self.device_current.write("SYST:COMM:SER:SEND " + "'initiate'") # trigger the device
                self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
                time.sleep(500e-3) # set delay to avoid query interuption error
                self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
                data_bot = float(self.device_current.read()) # read the value from the current source buffer
                Tbot_time_abs = datetime.fromtimestamp(time.time())
                Tbot_time_rel = time.time() - self.time_abs_start
                data_total_bot = [data_bot, Tbot_time_abs, Tbot_time_rel]

                # signal the slot that new data is available and send the data
                self.newdata_temp.emit(data_total_top,data_total_bot)
    
                # write the data to a .txt file 
                with open(self.filepath_temp + ".txt",mode = 'a') as txtfile:
                    txtfile.write('\n')
                    # write top face temperature
                    txtfile.write(str(Ttop_time_abs) + " " + str(Ttop_time_rel) + " " + str(data_top) + " ") 
                    txtfile.write('\n')
                    # write bottom face temperature
                    txtfile.write(str(Tbot_time_abs) + " " + str(Tbot_time_rel) + " " + " " + str(data_bot)) 

                # check for "stop" flag that is sent when stop button is pressed
                if self.task['break'] == True:
                    print('Stopping worker thread')
                    break 

        ############################################## SEEBECK MEASUREMENT ##################################################
           

            # let the seebeck measurements run for a few seconds
            timeout = 6   # [seconds]
            timeout_start = time.time()

            while time.time() < timeout_start + timeout:

                # switch voltmeter to CH1 voltage mode 
                self.device_switch.write("open all") # open all channels
                self.device_switch.write("close (@1!2)") # close channel 2 of Bank A (voltage drop across alumel wire)
                # voltmeter voltage mode settings
                self.device_current.write(":form:elem READ,TST,RNUM,AVOL")
                self.   device_current.write("SYST:COMM:SER:SEND ':sens:volt:rang " + str(self.volt_range) + "'")
                self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:CHAN 1'") # select channel 1
                time.sleep(500e-3)
                self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:FUNC " + "''VOLT''" + "'") # set voltmeter to measure voltage
                # Acquire voltage drop across alumel 
                self.device_current.write("SYST:COMM:SER:SEND " + "'initiate'") # trigger the device
                time.sleep(500e-3)
                self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
                time.sleep(500e-3) # set delay to avoid query interuption error
                self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
                # time.sleep(500e-3)
                data_alumel = float(self.device_current.read()) # read the value from the current source buffer
                time_val_abs_alumel = datetime.fromtimestamp(time.time())
                time_val_rel_alumel = time.time() - self.time_abs_start
                data_total_alumel = [data_alumel, time_val_abs_alumel, time_val_rel_alumel]
                
                
                # switch voltmeter to CH2 voltage mode
                self.device_switch.write("open all") # open all channels
                self.device_switch.write("close (@1!31)") # close channel 1 of Bank D (voltage drop across chromel wire)
                self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:CHAN 2'") # select channel 2
                time.sleep(500e-3)
                # Acquire voltage drop across chromel 
                self.device_current.write("SYST:COMM:SER:SEND " + "'initiate'") # trigger the device
                time.sleep(500e-3)
                self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
                time.sleep(500e-3) # set delay to avoid query interuption error
                self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
                # time.sleep(500e-3)
                data_chromel = float(self.device_current.read()) # read the value from the current source buffer
                time_val_abs_chromel = datetime.fromtimestamp(time.time())
                time_val_rel_chromel = time.time() - self.time_abs_start
                data_total_chromel = [data_chromel, time_val_abs_chromel, time_val_rel_chromel]

                # signal the slot that new data is available and send the data
                self.newdata_volt.emit(data_total_alumel,data_total_chromel)

                # write the data to a .txt file ### PENDING A TEST ON THIS!!!###
                with open(self.filepath_volt + ".txt",mode = 'a') as txtfile:
                    txtfile.write('\n')
                    # write Vdrop across alumel
                    txtfile.write(str(time_val_abs_alumel) + " " + str(time_val_rel_alumel) + " " + str(data_alumel) + " ") 
                    txtfile.write('\n')
                    # write Vdrop across chromel
                    txtfile.write(str(time_val_abs_chromel) + " " + str(time_val_rel_chromel) + " " + " " + str(data_chromel))
                    # check for "stop" flag that is sent when stop button is pressed
                    if self.task['break'] == True:
                        print('Stopping worker thread')
                        break 
                
            # check for "stop" flag that is sent when stop button is pressed
            if self.task['break'] == True:
                print('Stopping worker thread')
                break 
        
        print("Worker thread stopped")
        time.sleep(0.5) 
        self.finished.emit()