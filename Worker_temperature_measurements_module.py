# import modules
from PyQt5.QtCore import pyqtSignal, QObject
import time
from datetime import datetime
import random

# Worker class to offload sample temperature data acquisition to a new thread
class Worker_temperature_measurements(QObject):
    newdata = pyqtSignal(object,object) # signal after new data is acquired
    finished = pyqtSignal() # signal after data logging is complete
    
    # def __init__(self,task,device_current,device_switch,filepath):
    def __init__(self,task,filepath):
            super().__init__()
            # assign the stop task and device addresses to "self" variables
            self.task = task
            # self.device_current = device_current
            # self.device_switch = device_switch
            self.filepath = filepath

    # acquire data from voltmeter, pass it to the main class, and save the data
    def run(self):
        self.task['break'] = False
        print('Temperature worker thread is active')
        # update plot of voltage drops
        # get absolute time
        self.time_abs_start = time.time()

        i = 0

        while True:
            i = i + 1
            # # Acquire sample top face temperature
            # self.device_switch.write("open all") # open all channels
            # self.device_switch.write("close (@1!5)") # close Bank A channel 5 (top sample face temperature)
            # time.sleep(500e-3)
            # self.device_current.write("SYST:COMM:SER:SEND " + "'initiate'") # trigger the device
            # self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
            # time.sleep(500e-3) # set delay to avoid query interuption error
            # self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
            # data_top = float(self.device_current.read()) # read the value from the current source buffer
            Ttop_time_abs = datetime.fromtimestamp(time.time())
            Ttop_time_rel = time.time() - self.time_abs_start
            data_top = i + random.randint(round(-0.1*i),round(0.1*i))
            data_total_top = [data_top, Ttop_time_abs, Ttop_time_rel]
            time.sleep(1)
            
            
            
            # # Acquire sample bottom face temperature
            # self.device_switch.write("open all") # open all switcher channels
            # self.device_switch.write("close (@1!8)") # close Bank A channel 8 (sample bottom face temperature)
            # time.sleep(500e-3)
            # self.device_current.write("SYST:COMM:SER:SEND " + "'initiate'") # trigger the device
            # self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
            # time.sleep(500e-3) # set delay to avoid query interuption error
            # self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
            # data_bot = float(self.device_current.read()) # read the value from the current source buffer
            Tbot_time_abs = datetime.fromtimestamp(time.time())
            Tbot_time_rel = time.time() - self.time_abs_start
            data_bot = data_top + 2
            data_total_bot = [data_bot, Tbot_time_abs, Tbot_time_rel]

            # signal the slot that new data is available and send the data
            self.newdata.emit(data_total_top,data_total_bot)

            # write the data to a .txt file ### PENDING A TEST ON THIS!!!###
            with open(self.filepath + ".txt",mode = 'a') as txtfile:
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

        print('Worker thread stopped')
        time.sleep(1) 
        self.finished.emit()