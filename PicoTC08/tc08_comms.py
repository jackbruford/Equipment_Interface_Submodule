"""This file provides class tc08 containing methods required to communicate with the Picolog tc08 temperature logger. 
Allows the user to set the logger to streaming mode and record data in the form [TIME, TEMP1, TEMP2....]    
"""

import ctypes
import time
from ctypes import cdll

class tc08():
    def __init__(self):
        tc08_adr = "C:/Program Files/Pico Technology/PicoLog/usbtc08.dll"
        self.picodll = cdll.LoadLibrary(tc08_adr)
        self.handle = None
        self.channels = {}
        self.numchannels = None
        self.interval = None
        self.buffers = []
    def openUnit(self):
        '''Opens communication to the logger and sets the mains frequency rejection'''
        if self.handle is not None:
           print('tc08 unit already open') 
           return
        op = self.picodll.usb_tc08_open_unit()
        if op < 0:
           print('Unit failed to open') 
           error_code = self.picodll.usb_tc08_get_last_error(0)
           print('Error code:', error_code)
           raise ConnectionError("Could not connect to temperature logger")
        elif op == 0:
            print('No units found')
        else: 
            print('Unit open')
        print(op)    
        self.handle = op
        rej = self.picodll.usb_tc08_set_mains(self.handle, 0)    
        if not rej:
            print("Failed to set mains frequency rejection")
            error_code = self.picodll.usb_tc08_get_last_error(self.handle)
            print('Error code:', error_code)
            raise ConnectionError("Could not connect to temperature logger")
        else:
            print('Mains rejection set correctly')
    def setChannels(self, channels):   
        '''Sets the channel arrangement as specified by the dictionary 'channels'. 
        The dictionary should take the form {0:'C', 1:'K, 2:'K'...}. The number key 
        is the channel number and the corresponding string the thermocouple type. 
        Note that channel 0 is reserved for cold junction compensation and must be 'C'.
        '''
        numchannels = -1
        if channels[0] != 'C':
           print('Channel 0 reserved for cold junction compensation. Failed to set channel 0')
           return
        else:
            for i in channels:
                print(i)
                if not self.picodll.usb_tc08_set_channel(self.handle, i, ord(channels.get(i))):
                    print("Failed to set channel number ",str(i))
                    error_code = self.picodll.usb_tc08_get_last_error(self.handle)
                    print("Error code: ",error_code)
                if channels.get(i) != ' ':
                   numchannels = numchannels + 1 
            self.channels = channels  
            self.numchannels = numchannels
            #This section creates buffers which are required to retreive data from the logger
            bufferArray = []
            buffer_length = 5
            timeBuffer = (ctypes.c_int*buffer_length)();
            bufferArray.append(timeBuffer)
            for b in range(0, numchannels):
                tempBuffer = (ctypes.c_float*buffer_length)();
                bufferArray.append(tempBuffer)
            overflow = (ctypes.c_int)()   
            bufferArray.append(overflow)
            self.buffers = bufferArray
    def setSampleInterval(self, interval = 0):
        '''Sets the sample interval for logging temperatures to the requested value. 
        If requested value is too small or no value is specified, uses the minimum sample interval'''
        minimum_interval = self.picodll.usb_tc08_get_minimum_interval_ms(self.handle)
        if interval < minimum_interval:
           print('Sample interval set to minimum interval, ' + str(minimum_interval) + ' ms') 
           self.interval = minimum_interval
        else: 
           print('Sample interval set to ' + str(interval) + ' ms')
           self.interval = interval
    def run(self):
        '''Runs the logger in streaming mode with the sample interval previously set by setSampleInterval'''
        interval = self.picodll.usb_tc08_run(self.handle, self.interval)
        if not interval:
            print("Error occurred when running device.")
            error_code = self.picodll.usb_tc08_get_last_error(self.handle)
            print("Error code: ",error_code)
            raise ConnectionError("Could not connect to temperature logger")
        else:
            print("Running tc-08 with sample interval of ",interval," ms") 
        return interval    
    def record(self):
        '''Obtains data from the logger and returns an array with the form 
        [TIME, TEMP1, TEMP2...]
        '''
        measurement = []
        buffer_length = 5
        timeBuffer = self.buffers[0];
        overflow = (ctypes.c_int)() 
        for c in range(0, self.numchannels):
            channel = c + 1
            tempBuffer = self.buffers[channel];
            num_readings = self.picodll.usb_tc08_get_temp(self.handle,ctypes.byref(tempBuffer),
                                                    ctypes.byref(timeBuffer),buffer_length,
                                                    ctypes.byref(overflow),
                                                    channel,0,0)
            if channel == 1:
                measurement.append(timeBuffer[0]/1000)
            measurement.append(tempBuffer[0]) 
            self.buffers[channel] = tempBuffer
        return measurement           
    def stop(self):
        '''Stops the logger from streaming'''
        self.picodll.usb_tc08_stop(self.handle)
    def closeUnit(self):
        '''Closes the connection to the tc08 logger'''
        self.picodll.usb_tc08_close_unit(self.handle)
 

    