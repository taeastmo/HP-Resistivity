# import modules
from PyQt5.QtCore import pyqtSignal, QObject
import time
from datetime import datetime

# Worker class to offload Seebeck coefficient data acquisition to a new thread
class Worker_seebeck_measurements(QObject):
    newdata = pyqtSignal(object,object) # signal after new data is acquired
    finished = pyqtSignal() # signal after data logging is complete
    
    def __init__(self,task,device_current,device_switch,filepath):
            super().__init__()
            # assign the stop task and device addresses to "self" variables
            self.task = task
            self.device_current = device_current
            self.device_switch = device_switch
            self.filepath = filepath

    # acquire data from voltmeter, pass it to the main class, and save the data
    def run(self):
        self.task['break'] = False
        print('Seebeck worker thread is active')
        # update plot of voltage drops
        # get absolute time
        self.time_abs_start = time.time()
        
    

        while True:
            # switch voltmeter to CH1 voltage mode 
            self.device_switch.write("open all") # open all channels
            self.device_switch.write("close (@1!2)") # close channel 2 of Bank A (voltage drop across alumel wire)
            self.device_current.write(":form:elem READ,TST,RNUM,AVOL")
            # voltmeter voltage mode settings
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:CHAN 1'") # select channel 1
            time.sleep(500e-3)
            # Acquire voltage drop across alumel 
            self.device_current.write("SYST:COMM:SER:SEND " + "'initiate'") # trigger the device
            time.sleep(500e-3)
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
            time.sleep(500e-3) # set delay to avoid query interuption error
            self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
            data_alumel = float(self.device_current.read()) # read the value from the current source buffer
            time_val_abs_alumel = datetime.fromtimestamp(time.time())
            time_val_rel_alumel = time.time() - self.time_abs_start
            data_total_alumel = [data_alumel, time_val_abs_alumel, time_val_rel_alumel]
            
            
            # switch voltmeter to CH2 voltage mode
            self.device_switch.write("open all") # open all channels
            self.device_switch.write("close (@1!31)") # close channel 1 of Bank D (voltage drop across chromel wire)
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:CHAN 2'") # select channel 2
            time.sleep(0.5)

            # Acquire voltage drop across chromel 
            self.device_current.write("SYST:COMM:SER:SEND " + "'initiate'") # trigger the device
            time.sleep(500e-3)
            self.device_current.write("SYST:COMM:SER:SEND " + "'SENS:DATA:FRESH?'") # send query to voltmeter
            time.sleep(500e-3) # set delay to avoid query interuption error
            self.device_current.write("SYST:COMM:SER:ENT?") # return response to query
            data_chromel = float(self.device_current.read()) # read the value from the current source buffer
            time_val_abs_chromel = datetime.fromtimestamp(time.time())
            time_val_rel_chromel = time.time() - self.time_abs_start
            data_total_chromel = [data_chromel, time_val_abs_chromel, time_val_rel_chromel]

            # signal the slot that new data is available and send the data
            self.newdata.emit(data_total_alumel,data_total_chromel)

            # write the data to a .txt file ### PENDING A TEST ON THIS!!!###
            with open(self.filepath + ".txt",mode = 'a') as txtfile:
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
        print("Worker thread stopped")
        time.sleep(1) 
        self.finished.emit()