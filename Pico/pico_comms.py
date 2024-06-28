"""This file provides class tc08 containing methods required to communicate with the Picolog tc08 temperature logger. 
Allows the user to set the logger to streaming mode and record data in the form [TIME, TEMP1, TEMP2....]    
"""

import ctypes
import time
from ctypes import cdll


class tc08():
    def __init__(self):
        tc08_adr = "C:/Program Files/Pico Technology/PicoLog 6/usbtc08.dll"
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
                if not self.picodll.usb_tc08_set_channel(self.handle, i, ord(channels.get(i))):
                    print("Failed to set channel number ", str(i))
                    error_code = self.picodll.usb_tc08_get_last_error(self.handle)
                    print("Error code: ", error_code)
                    raise ConnectionError("Could not connect to temperature logger")
                if channels.get(i) != ' ':
                    numchannels = numchannels + 1
            self.channels = channels
            self.numchannels = numchannels
            # This section creates buffers which are required to retreive data from the logger
            bufferArray = []
            buffer_length = 5
            timeBuffer = (ctypes.c_int * buffer_length)();
            bufferArray.append(timeBuffer)
            for b in range(0, numchannels):
                tempBuffer = (ctypes.c_float * buffer_length)();
                bufferArray.append(tempBuffer)
            overflow = (ctypes.c_int)()
            bufferArray.append(overflow)
            self.buffers = bufferArray

    def setSampleInterval(self, interval=0):
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
            print("Error code: ", error_code)
            raise ConnectionError("Could not connect to temperature logger")
        else:
            # print("Running tc-08 with sample interval of ", interval, " ms")
            pass
        return interval

    def record(self):
        '''Obtains data from the logger and returns an array with the form 
        [TIME, TEMP1, TEMP2...]
        '''
        measurement = []
        buffer_length = 5
        timeBuffer = self.buffers[0]
        overflow = (ctypes.c_int)()
        for c in range(0, self.numchannels):
            channel = c + 1
            tempBuffer = self.buffers[channel]
            num_readings = self.picodll.usb_tc08_get_temp(self.handle, ctypes.byref(tempBuffer),
                                                          ctypes.byref(timeBuffer), buffer_length,
                                                          ctypes.byref(overflow),
                                                          channel, 0, 0)
            if num_readings == -1:
               print("Error occurred when running device.")
               error_code = self.picodll.usb_tc08_get_last_error(self.handle)
               print("Error code: ", error_code)
               raise ConnectionError("Could not connect to temperature logger")
            if channel == 1:
                measurement.append(timeBuffer[0] / 1000)
            measurement.append(tempBuffer[0])
        return measurement

    def getTemp(self, channel):
        """ Gets the temps at the current instant. Starting and stopping recording. channel can be a channel number or a list of channel numbers"""
        self.run()
        time.sleep(self.interval/1000)
        T = self.record()
        self.stop()
        if type(channel) is int:
            if type(T[channel]) is float:
                output = T[channel]
            elif type(T[channel]) is list:
                output = T[channel][-1]
            else:
                raise IndexError
        elif type(channel) is list:
            output = []
            for c in channel:
                if type(T[c]) is float:
                    output.append(T[c])
                elif type(T[c]) is list:
                    output.append(T[c][-1])
                else:
                    raise IndexError
        else:
            raise TypeError("invalid type for channel, channel is a "+type(channel).__name__+" not a list or int")

        return output

    def getLatestTemp(self, channel):
        """ Gets the most recent temps assuming the logger is running. channel can be a channel number or a list of channel numbers"""
        T = self.record()
        if type(channel) is int:
            if type(T[channel]) is float:
                output = T[channel]
            elif type(T[channel]) is list:
                output = T[channel][-1]
            else:
                raise IndexError
        elif type(channel) is list:
            output = []
            for c in channel:
                if type(T[c]) is float:
                    output.append(T[c])
                elif type(T[c]) is list:
                    output.append(T[c][-1])
                else:
                    raise IndexError
        else:
            raise TypeError("invalid type for channel, channel is a "+type(channel).__name__+" not a list or int")

        return output


    def stop(self):
        '''Stops the logger from streaming'''
        self.picodll.usb_tc08_stop(self.handle)

    def closeUnit(self):
        '''Closes the connection to the tc08 logger'''
        self.picodll.usb_tc08_close_unit(self.handle)


class ADC_20():
    def __init__(self):
        pico_adr = "C:/Program Files/Pico Technology/PicoLog 6/picohrdl.dll"
        self.picodll = cdll.LoadLibrary(pico_adr)
        self.handle = None
        self.channels = {}
        self.numchannels = None
        self.numsamples = None
        self.interval = None
        self.buffers = []

    def openUnit(self):
        '''Opens communication to the logger and sets the mains frequency rejection'''
        if self.handle is not None:
            print('ADC-20 unit already open')
            return
        op = self.picodll.HRDLOpenUnit()
        if op < 0:
            print('Unit failed to open')
            error_code = ctypes.c_wchar()
            self.picodll.HRDLGetUnitInfo(self.handle, ctypes.byref(error_code), 1, 7)
            print('Error code:', error_code.value)
            raise ConnectionError("Could not connect to data logger")
        elif op == 0:
            print('No units found')
            raise ConnectionError("Could not connect to data logger")
        else:
            print('Unit open')
        self.handle = op
        rej = self.picodll.HRDLSetMains(self.handle, 0)
        if not rej:
            print("Failed to set mains frequency rejection")
            error_code = ctypes.c_wchar()
            self.picodll.HRDLGetUnitInfo(self.handle, ctypes.byref(error_code), 1, 7)
            print('Error code:', error_code.value)
            raise ConnectionError("Could not connect to data logger")
        else:
            print('Mains rejection set correctly')

    def setChannels(self, channels, range, numsamples=1):
        '''Sets the channel arrangement as specified by the dictionary 'channels'. 
        The dictionary should take the form {0:'C', 1:'K, 2:'K'...}. The number key 
        is the channel number and the corresponding string the thermocouple type. 
        Note that channel 0 is reserved for cold junction compensation and must be 'C'.
        range is a dict of form {0:' ', 1:'2.5', 2:'1.25'...} where the value entered sets the voltage
        measurement range +/- 1.25V or +/-2.5V
        '''
        channel_count = ctypes.c_int()
        ch_flag = self.picodll.HRDLGetNumberOfEnabledChannels(self.handle, ctypes.byref(channel_count))
        if ch_flag:
            num_enabled = channel_count.value
            if num_enabled:
                print("Enabled channels detected - ensure all channels are disabled before attempting to set channels")
                raise ConnectionError("Could not connect to data logger")
        numchannels = 0
        channel_scaling = []
        for i in channels:
            if not channels[i] == ' ':
                if range[i] == '2.5':
                    vrange = 0
                elif range[i] == '1.25':
                    vrange = 1
                else:
                    raise ValueError("range incorrectly defined. all enabled channels must have an entry of '1.25' or '2.5'")

            if channels[i] == 'D':
                ch_set = self.picodll.HRDLSetAnalogInChannel(self.handle, i, 1, vrange, 0)
            elif channels[i] == 'S':
                ch_set = self.picodll.HRDLSetAnalogInChannel(self.handle, i, 1, vrange, 1)
            elif channels[i] == ' ':
                continue
            if not ch_set:
                print("Failed to set channel number " + str(i))
                error_code = ctypes.c_wchar()
                self.picodll.HRDLGetUnitInfo(self.handle, ctypes.byref(error_code), 1, 8)
                print('Error code:', error_code.value)
            else:
                minAdc = ctypes.c_int()
                maxAdc = ctypes.c_int()
                raw_adc = self.picodll.HRDLGetMinMaxAdcCounts(self.handle, ctypes.byref(minAdc), ctypes.byref(maxAdc),
                                                              i)
                channel_scaling.append(2500 / maxAdc.value)
            numchannels = numchannels + 1
        self.channels = channels
        self.numchannels = numchannels
        self.numsamples = numsamples
        self.channel_scaling = channel_scaling
        # This section creates buffers which are required to retreive data from the logger
        bufferArray = []
        buffer_length = numsamples * numchannels
        timeBuffer = (ctypes.c_int * buffer_length)();
        bufferArray.append(timeBuffer)
        sampleBuffer = (ctypes.c_int * buffer_length)();
        bufferArray.append(sampleBuffer)
        overflow = (ctypes.c_int)()
        bufferArray.append(overflow)
        self.buffers = bufferArray

    def setSampleInterval(self, interval):
        '''Sets the sample interval for logging temperatures to the requested value. 
        If requested value is too small or no value is specified, uses the minimum sample interval'''
        int_set = self.picodll.HRDLSetInterval(self.handle, interval, 0)
        if int_set:
            self.interval = interval
        else:
            print('Failed to set interval')
            error_code = ctypes.c_wchar()
            self.picodll.HRDLGetUnitInfo(self.handle, ctypes.byref(error_code), 1, 8)
            print('Error code:', error_code.value)
            raise ConnectionError("Could not connect to data logger")

    def run(self):
        '''Runs the logger in streaming mode with the sample interval previously set by setSampleInterval'''
        running = self.picodll.HRDLRun(self.handle, self.numsamples, 2)
        if not running:
            print("Error occurred when running device.")
            raise ConnectionError("Could not connect to data logger")
        else:
            self.failed_measurements = 0
            # print("Running tc-08 with sample interval of ", self.interval, " ms")
        return self.interval

    def record(self, failures = 1):
        '''Obtains data from the logger and returns an array with the form 
        [TIME, DATA1, DATA2...]
        '''
        if self.failed_measurements >= failures:
            print(str(failures) + ' consecutive failed measurements ')
            raise ConnectionError("Could not connect to data logger")
        else:
            ready = self.picodll.HRDLReady(self.handle)
            if not ready:
                print("Logger not ready for data retrieval")
                measurement = None
                self.failed_measurements = self.failed_measurements + 1
            else:
                measurement = []
                timeBuffer = self.buffers[0]
                overflow = (ctypes.c_int)()
                sampleBuffer = self.buffers[1]
                num_readings = self.picodll.HRDLGetTimesAndValues(self.handle, ctypes.byref(timeBuffer),
                                                                  ctypes.byref(sampleBuffer), ctypes.byref(overflow),
                                                                  self.numsamples)
                measurement.append(timeBuffer[0] / 1000)
                for c in range(0, self.numchannels):
                    index = (self.numsamples - 1) * self.numchannels + c
                    sample_measurement = sampleBuffer[index] * self.channel_scaling[c]
                    measurement.append(sample_measurement)
                self.failed_measurements = 0
            return measurement

    def getMeasurement(self, channel):
        """ Gets a single measument at the current instant, running and stopping the logger. channel can be a channel number or a list of channel numbers"""
        self.run()
        time.sleep(self.interval/1000)
        T = self.record()
        self.stop()
        if type(channel) is int:
            if type(T[channel]) is float:
                output = T[channel]
            elif type(T[channel]) is list:
                output = T[channel][-1]
            else:
                raise IndexError
        elif type(channel) is list:
            output = []
            for c in channel:
                if type(T[c]) is float:
                    output.append(T[c])
                elif type(T[c]) is list:
                    output.append(T[c][-1])
                else:
                    raise IndexError
        else:
            raise TypeError("invalid type for channel, channel is a "+type(channel).__name__+" not a list or int")

        return output

    def getLatestMeasurement(self, channel):
        """ Gets the most recent measument from the ADC assuming it is already running. channel can be a channel number or a list of channel numbers"""
        V = self.record()
        if type(channel) is int:
            if type(V[channel]) is float:
                output = V[channel]
            elif type(V[channel]) is list:
                output = V[channel][-1]
            else:
                raise IndexError
        elif type(channel) is list:
            output = []
            for c in channel:
                if type(V[c]) is float:
                    output.append(V[c])
                elif type(V[c]) is list:
                    output.append(V[c][-1])
                else:
                    raise IndexError
        else:
            raise TypeError("invalid type for channel, channel is a "+type(channel).__name__+" not a list or int")

        return output
    def stop(self):
        '''Stops the logger from streaming'''
        self.picodll.HRDLStop(self.handle)

    def closeUnit(self):
        '''Closes the connection to the tc08 logger'''
        self.picodll.HRDLCloseUnit(self.handle)


if __name__ == "__main__":
    channels = {1: 'S', 2: 'S', 3: 'S', 4: 'S', 5: 'S', 6: 'S', 7: 'S', 8: 'S'}
    adc = ADC_20()
    try:
        adc.openUnit()
        adc.setChannels(channels)
        adc.setSampleInterval(500)
        adc.run()
        for x in range(0, 20):
            time.sleep(0.5)
            print(adc.record())
        adc.stop()
        adc.closeUnit()
    except Exception as e:
        print(e)
        adc.stop()
        adc.closeUnit()
        
