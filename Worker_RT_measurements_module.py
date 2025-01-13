### Need to consider if it is worth it to use the built in Keithley "Delta measurements." ###
### Could I just program this in myself? It seems like it would be a lot of work up front but 
### then I would have a simplified setup because I could remove the RS32 cable...

# import modules
from PyQt5.QtCore import pyqtSignal, QObject
import time
from datetime import datetime
from PyQt5 import QtCore

# Worker class to offload sample temperature and resistance data acquisition to a new thread
class Worker_RT_measurements(QObject):
    newdata_temp = pyqtSignal(object,object) # signal after new temperature data is acquired
    newdata_res = pyqtSignal(object) # signal after new resistance data is acquired
    finished = pyqtSignal() # signal after data logging is complete
    
    def __init__(self, task, device_current, device_switch, filepath_temp, filepath_res, current_setpoint_high, \
                 current_setpoint_low, volt_range, units):
            super().__init__()
            # assign the stop task and device addresses to "self" variables
            self.task = task
            self.device_current = device_current
            self.device_switch = device_switch
            self.filepath_temp = filepath_temp
            self.filepath_res = filepath_res
            self.current_setpoint_high = current_setpoint_high
            self.current_setpoint_low = current_setpoint_low
            self.volt_range = volt_range
            self.units = units
    # acquire data from voltmeter, pass it to the main class, and save the data
    def run(self):
        self.task['break'] = False
        print('RT worker thread is active')
        # update plot of voltage drops
        # get absolute time
        self.time_abs_start = time.time()

        i = 0

        while True:
        ############################################# TEMPERATURE MEASUREMENT #################################################
            if i > 0: # WHY DOES THIS PREVENT AN ERROR???
                self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
                time.sleep(0.1) # set delay to avoid query interuption error
                self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
                self.device_current.read()
                time.sleep(0.1)
                
            
            # self.device_current.write("source:current:AMPL 0")
            # self.device_current.write("OUTPUT:STAT OFF") # turn off power source
            # self.device_current.write("TRACE:CLE")

            # reset the voltmeter and current source
            self.device_current.write("SYST:COMM:SER:SEND '*rst; status:preset; *cls'")
            self.device_current.write("*rst; status:preset; *cls")
            time.sleep(0.5)
            
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

                i = i + 1



        ############################################## DELTA (RESISTANCE) MEASUREMENT ##################################################
           
            # open all channels
            self.device_switch.write("open all")
            # close Bank A channel 2 (for resistance measurements)
            self.device_switch.write("close (@1!2)")
            self.device_current.write(":form:elem READ,TST,RNUM,AVOL")
            self.device_current.write("source:delta:delay 0.01") # 10 ms delay
            self.device_current.write("source:delta:count INF") # number of counts
            self.device_current.write("current:compliance 10") # compliance value
            self.device_current.write("UNIT " + str(self.units)) # get measurement units from GUI
            self.device_current.write(":SYST:COMM:SERIal:SEND ':sens:volt:nplc 5'")
            time.sleep(500e-3)
            self.device_current.write(":SYST:COMM:SERIal:SEND ':sens:volt:rang " + str(self.volt_range) + "'") # get voltage range from GUI
            time.sleep(500e-3)
            # DC moving filter parameters
            self.device_current.write(":SYST:COMM:SERIal:SEND ':SENS:VOLT:CHAN1:DFIL:TCONtrol MOV'")
            self.device_current.write(":SYST:COMM:SERIal:SEND ':SENS:VOLT:CHAN1:DFIL:COUNt 100'")
            self.device_current.write(":SYST:COMM:SERIal:SEND ':SENS:VOLT:CHAN1:DFIL:STATe ON'")
            # set current output
            self.device_current.write("source:delta:high " + str(self.current_setpoint_high))
            self.device_current.write("source:delta:low " + str(self.current_setpoint_low))

            time.sleep(400e-3)
            # arm Delta
            self.device_current.write("source:delta:arm")
            time.sleep(500e-3)
            # start Delta measurements
            self.device_current.write("INIT:IMM")
            print("initiating delta measurements")
            time.sleep(500e-3)

            # let the delta measurements run for a few seconds
            timeout = 10   # [seconds]
            timeout_start = time.time()

            i = 0
            while time.time() < timeout_start + timeout:
                resistances = self.device_current.query_ascii_values("sens:data:fresh?")[0]
                time_val_abs = datetime.fromtimestamp(time.time())
                # time_val_rel = self.device_current.query_ascii_values("sens:data:fresh?")[1]
                time_val_rel = time.time() - self.time_abs_start
                data = [resistances, time_val_abs, time_val_rel]
                # abort the Delta measurements
                # self.device_current.write("SOUR:SWE:ABOR")
                time.sleep(0.1)

                if i > 1:
                    self.newdata_res.emit(data)
                    # write the data to a .txt file
                    with open(self.filepath_res + ".txt", mode = 'a') as txtfile:
                        txtfile.write('\n')
                        txtfile.write(str(time_val_abs) + " " + str(time_val_rel) + " " + str(resistances)) 
                i = i + 1

                # check for "stop" flag that is sent when stop button is pressed
                if self.task['break'] == True:
                    print('Stopping worker thread')
                    break 

            # abort the delta measurements
            self.device_current.write("SOUR:SWE:ABOR")
            print("Aborting measurements")
                
            # check for "stop" flag that is sent when stop button is pressed
            if self.task['break'] == True:
                print('Stopping worker thread')
                break 
        
        print("Worker thread stopped")
        time.sleep(1) 
        self.finished.emit()