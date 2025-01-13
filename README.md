This is a software package being developed for electrical resistivity and temperature measurements during high pressure experiments at beamline 16-BM-B. The software interfaces and controls a current source, voltmeter, and switch system. 
The GUI allows users to set up and adjust settings on the measurment devices, and provides real-time plots of the acquired data. All logged data is written to a text file for further post processing.

Delta_measure_GUI_rev3_multithreaded is the main file, and the various "worker modules" included are used to offload data acquisition to different threads.
