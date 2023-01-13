import pyvisa

import time
import matplotlib.pyplot as plt
import numpy as np


class Keithley:
    def __init__(self, _v_range=100, _i_range=3):
        self.v_range = _v_range
        self.i_range = _i_range
        self.sample_rate = 20
        self.apperture = 1/self.sample_rate
        self.n_samples = 100
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(self.RESOURCE_STRING)
        # self.inst.read_termination ="\n"
        # self.inst.write_termination = "\n"
        self.inst.timeout = 1000
        try:
            print("Opened connection with ", self.inst.query('*IDN?;'))
        except Exception as e:
            print('Error occurred while trying to open connection with multimeter.\nError:\n', e)
        self.inst.timeout = 1000
        self.inst.write('*RST')
        self.inst.write('*CLS')
        self.inst.write('*LANG SCPI')
        # print(self.inst.query('*LANG?;'))

    def voltage_measurement(self):
        self.inst.write(':SENS:FUNC "VOLT:DC"')
        self.inst.write(':SENS:VOLT:APER %f' % self.apperture)  # set the apperture duration (duration the adc intergrates over)
        self.inst.write(':SENS:VOLT:RANG %f' % self.v_range)
        self.inst.write(':SENS:VOLT:INP AUTO') # Set input impedance
        return self.inst.query(':READ?')

    def current_measurement(self, aper=0.05):
        self.inst.write(':SENS:FUNC "CURR:DC"')
        self.inst.write(':SENS:CURR:APER %f' % aper)  # set the apperture duration (duration the adc intergrates over) default 0.24 is max 1e-5 is min
        self.inst.write(':SENS:CURR:RANG %f' % self.i_range)
        return self.inst.query(':READ?')

    def zero_measurement(self):
        self.inst.write('FUNC "VOLT"')
        self.inst.write('SENSE:AZER:ONCE')

    def configureBuffers_SCPI_Trig_Digitize(self):
        self.inst.write(':SENSE:VOLT:AZER OFF')  # Turns off autozero
        self.inst.write(':SENSE:VOLT:RANG %f' % self.v_range)

        self.inst.write(':SENS:DIG:FUNC "VOLT"')
        self.inst.write(':SENSE:DIG:VOLT:SRATE  %f' % self.sample_rate)
        self.inst.write(':SENSE:DIG:VOLT:APER AUTO')# %f' % self.apperture) #set the apperture duration (duration the adc intergrates over)

        # self.inst.write(':TRACE:CLEAR')
        self.inst.write(':TRACE:POINTS %f, "defbuffer1"' % self.n_samples)
        self.inst.write(':TRIGGER:LOAD "LoopUntilEvent", COMMAND, 0, ENTER, 0, "defbuffer1"')
        self.inst.write(':DISPlay:SCReen GRAPh')
        self.inst.write('*WAI')
        self.inst.write(':INIT')

    def configureBuffers_Ext_Trig_Digitize(self):
        """Digitize gives 4.5 digit accuracy """
        self.inst.write(':SENSE:VOLT:AZER OFF')  # Turns off autozero
        self.inst.write(':SENS:DIG:FUNC "VOLT"')
        self.inst.write(':SENSE:DIG:VOLT:RANG %f' % self.v_range)


        self.inst.write(':SENSE:DIG:VOLT:SRATE  %f' % self.sample_rate)
        self.inst.write(':SENSE:DIG:VOLT:APER AUTO')# %f' % self.apperture) #set the apperture duration (duration the adc intergrates over)
        # #
        # self.inst.write(':TRACE:CLEAR')
        self.inst.write(':TRACE:POINTS %f, "defbuffer1"' % self.n_samples)
        self.inst.write(':TRIGGER:EXT:IN:EDGE RISING')
        self.inst.write(':TRIGGER:LOAD "LoopUntilEvent", EXTERNAL, 50, ENTER, 0, "defbuffer1"')
        self.inst.write(':DISPlay:SCReen GRAPh')
        self.inst.write('*WAI')
        self.inst.write(':INIT')

    def configureBuffers_Ext_Trig_Measure(self):
        """Measure gives higher accuracy but does not control the sample rate and is slower than digitize"""
        self.inst.write(':SENSE:VOLT:AZER OFF')  # Turns off autozero
        self.inst.write(':SENS:DIG:FUNC "VOLT"')
        self.inst.write(':SENSE:DIG:VOLT:RANG %f' % self.v_range)


        self.inst.write(':SENSE:DIG:VOLT:SRATE  %f' % self.sample_rate)
        self.inst.write(':SENSE:VOLT:APER AUTO')# %f' % self.apperture) #set the apperture duration (duration the adc intergrates over)
        # #
        # self.inst.write(':TRACE:CLEAR')
        self.inst.write(':TRACE:POINTS %f, "defbuffer1"' % self.n_samples)
        self.inst.write(':TRIGGER:LOAD "LoopUntilEvent", EXTERNAL, 50, ENTER, 0, "defbuffer1"')
        self.inst.write(':DISPlay:SCReen GRAPh')
        self.inst.write('*WAI')
        self.inst.write(':INIT')

    def trigger(self):
        self.inst.write('*TRG')

    def getBufferedData(self):
        nPointsInBuffer = int(self.inst.query(':TRACE:ACTUAL?'))
        nRemainingInBuffer = nPointsInBuffer
        startIndex = 1
        idx = startIndex
        rawdata = str()
        while nRemainingInBuffer>10:
            rawdata = rawdata + self.inst.query(':TRACE:DATA? %d, %d, "defbuffer1", READ, REL' % (idx, idx+10)) +","
            nRemainingInBuffer = nRemainingInBuffer-10
            idx = idx+10

        rawdata = rawdata + self.inst.query('TRACE:DATA? %d, %d, "defbuffer1", READ, REL' % (idx, idx + 1 + nPointsInBuffer % 10))

        dataList = np.array(list(map(float, rawdata.split(","))))

        time_idx = np.arange(1, len(dataList), 2)
        data_idx = np.arange(0, len(dataList), 2)

        #buffer is circular so data needs to be reordered by time stamp
        sorted_time = np.sort(dataList[time_idx])
        sorted_data = dataList[data_idx[np.argsort(dataList[time_idx])]]

        return {'data': list(sorted_data), 'time': list(sorted_time)}

    def close(self):
        """Closes the serial connection to the device"""
        try:
            self.inst.close()

            print('Closed serial connection to device.')
        except:
            print("Error occurred while trying to close visa connection.")

    def fetch(self):
        """Fetches the current value in the multimeter"""
        self.ser.write(bytes(':fetch?\n', 'ascii'))
        response = self.ser.readline()
        return float(response)


class DMM6500(Keithley):
    """
    PEG has two DM6500 Multimeters. One has an assset code sitcker on top, one does not
        Asset code 28859 resource string = 'USB0::0x05E6::0x6500::04497105::INSTR'
        No asset code resource string = 'USB0::0x05E6::0x6500::04396331::INSTR'
    """
    def __init__(self, _Resource_String = 'USB0::0x05E6::0x6500::04396331::INSTR',_v_range=100):
        self.RESOURCE_STRING = _Resource_String
        super().__init__(_v_range)

class MM2000(Keithley):
    def __init__(self):
        self.n_sample = 300
        self.interval_in_ms = 5e-3
        self.RESOURCE_STRING = 'ASRL10::INSTR'
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(self.RESOURCE_STRING)
        try:
            print("Opened connection with ", self.inst.query('*IDN?;'))
        except Exception as e:
            print('Error occurred while trying to open connection with multimeter.\nError:\n', e)
        self.inst.timeout = 10000
        self.inst.write("*rst; status:preset; *cls")

    def configureBuffers(self):
        #todo not convinced below code is correctly setting the sample rate
        self.inst.write(':SYSTEM:AZERO:STATE OFF')
        # self.inst.write(':SENSE:VOLT:DC:NPLC 0.01')
        self.inst.write(':DISPLAY:ENABLE OFF')
        self.inst.write(':SENSE:FUNC "VOLT:DC"')
        self.inst.write(':SENSE:VOLT:DC:RANGE:AUTO OFF')
        self.inst.write(':VOLT:DC:RANGE 5')
        self.inst.write(':VOLT:DC:DIGITS 6')
        self.inst.write(':TRACE:CLEAR')
        self.inst.write(':TRACE:POINTS %f' % self.n_sample)
        self.inst.write(':TRACE:FEED SENSE')
        self.inst.write(':INIT:CONT OFF')
        # self.inst.write(':TRIG:SOURCE IMMEDIATE')
        self.inst.write(':TRIG:SOURCE BUS')
        self.inst.write(':SAMPLE:COUNT %f' % self.n_sample)
        self.inst.write("TRIG:DELAY %f" % (self.interval_in_ms / 1000.0))
        self.inst.write('*WAI') #wait for all previous commands to execute
        self.inst.write(':ABORT')


    def trigger(self):
        self.inst.write('INIT')
        self.inst.write('*TRG')

    def getBufferedData(self):
        rawdata = self.inst.query(':TRACE:DATA?')
        if rawdata == "\n":
            raise Exception("No data in buffer")

        self.inst.write(':TRACe:CLEAR')

        dataList = list(map(float, rawdata.split(",")))

        times = list(self.interval_in_ms*np.arange(0, len(dataList))/1000)
        return {'data': dataList, 'time': times}

if __name__ == "__main__":
    keith = DMM6500('USB0::0x05E6::0x6500::04497105::INSTR', _v_range=100)
    kenny = DMM6500('USB0::0x05E6::0x6500::04396331::INSTR', _v_range=100)
    # keith.zero_measurement()
    # kenny.zero_measurement()
    keith.configureBuffers_Ext_Trig_Digitize()
    kenny.configureBuffers_Ext_Trig_Digitize()
    print("Multimeters configured\nTriggering...")
    time.sleep(10)
    # keith.trigger()
    # kenny.trigger()
    time.sleep(1)

    d1 = keith.getBufferedData()
    d2 = kenny.getBufferedData()

    plt.figure(1)
    plt.plot(d1["time"], d1["data"])
    plt.figure(2)
    plt.plot(d2["time"], d2["data"])

    plt.show()
