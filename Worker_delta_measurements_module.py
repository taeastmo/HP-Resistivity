# import modules
from PyQt5.QtCore import pyqtSignal, QObject
import time
from datetime import datetime

# Worker class to offload resistance data acquisition to a new thread
class Worker_delta_measurements(QObject):
    newdata = pyqtSignal(object) # signal after new data is acquired
    finished = pyqtSignal() # signal after data logging is complete
    
    def __init__(self,task,device_current,filepath):
            super().__init__()
            # define a task that will contain a stop message to abort this thread
            self.task = task
            self.device_current = device_current
            self.filepath = filepath
#         The DATA code queries the Model 6220/6221 for the contents of the buffer. 
#     When you see ENTER100000 this indicates you need to read data from the box. 
#     The number is the recommended number of bytes to read. 
#     This depends on how many buffer points were filled. 
#     This command selects a starting point "0" and a 
#     number of buffer points to download "<DATACOUNT>".

# :trac:data:sel? 0,3000
# ENTER4000000

    # acquire data from voltmeter, pass it to the main class, and save the data
    def run(self):
        self.task['break'] = False
        print('Resistance measurement worker thread is active')

        # get absolute start time
        self.time_abs_start = time.time()
        
        # update plot of resistances2
        i = 0
        while True:
            resistances = self.device_current.query_ascii_values("sens:data:fresh?")[0]
            time_val_abs = datetime.fromtimestamp(time.time())
            # time_val_rel = self.device_current.query_ascii_values("sens:data:fresh?")[1]
            time_val_rel = time.time() - self.time_abs_start
            data = [resistances, time_val_abs, time_val_rel]
            time.sleep(0.1)
            if i > 0: # skips plotting the first point, it keeps plotting an overflow value on the first loop
                self.newdata.emit(data)
            # write the data to a .txt file
            with open(self.filepath + ".txt",mode = 'a') as txtfile:
                txtfile.write('\n')
                txtfile.write(str(time_val_abs) + " " + str(time_val_rel) + " " + str(resistances)) 
            i = i + 1
            # check for "stop" flag that is sent when stop button is pressed
            if self.task['break'] == True:
                print('Stopping worker thread')
                break 
        print('Worker thread stopped')
        time.sleep(1) 
        self.finished.emit()