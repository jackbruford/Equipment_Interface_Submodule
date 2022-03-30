### Interface code for Tektronix MSO54 Oscilloscope ###
# @author: J Bruford, based on MATLAB script written by: G Jones

import pyvisa
import numpy as np
from struct import unpack


class MSO54:
    def __init__(self):
        self.N_SAMP = 1250  # number of samplestocapture
        self.BIT_NR = 12  # Numberofbitsperwaveformpoint
        self.BYTE_NR = 2  # Number of bytes per waveform point - NOTE: Must change binblockread() precision if this value
        # is changed!
        self.RESOURCE_STRING = 'USB::0x0699::0x0522::C012598::INSTR'  # Use Tek's VISA Resource Manager to find the resource string
        self.CHAN = []  # Oscilloscope channels to use - all channels listed must be enabled on scope first otherwise might crash
        self.wave = {}  # output waveform data from scope
        self.status = []
        self.rm = pyvisa.ResourceManager()

    def open(self):
        if hasattr(self, 'inst'):
            raise ConnectionError('MSO54 already open. Exiting without doing anything.')

        self.inst = self.rm.open_resource(self.RESOURCE_STRING)
        # On some PC this doesnt work if the following two lines are uncommented
        # self.inst.read_termination = '\n'
        # self.inst.write_termination = '\n'
        self.inst.timeout = 1000
        try:
            print("Opened connection with ", self.inst.query('*IDN?;'))
        except Exception as e:
            print('Error occurred while trying to open connection with multimeter.\nError:\n', e)
        self.inst.timeout = 1000

        self.InputBufferSize = 65536

        print('Scope open completed\n')

    def set_channels(self):
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        resp = self.inst.query("DATa:SOUrce:AVAILable?")
        self.CHAN = [str(item) for item in resp.split(",")]

    def close(self):
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not open. Cannot close')
        else:
            self.inst.close()
            delattr(self, 'inst')

    def set(self):
        # Currently assumes most setup is done through scope screen interface
        # Setup trigger - complicated - best done on screen for now
        self.inst.write('TRIG:A:TYPE EDGE')
        self.inst.write('TRIG:A:EDGE:SOURCE CH1')
        self.inst.write('TRIG:A:EDGE:SLOPE FALL')
        self.inst.write('TRIG:A:LEVEL:CH1 10')
        self.inst.write('TRIG:A:MODE NORMAL')
        self.inst.write('ACQuire:StopAfter Sequence')

    def arm(self):
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        self.inst.write('ACQuire:State 1')

    def set_horizontal_scale(self, T_per_division):
        """
        Method for adjusting the horizontal scale, T_per_division is in seconds
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        self.inst.write("HORIZONTAL:MODE:SCALE " + str(T_per_division))

    def set_vertical_scale(self, channel, units_per_division):
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        self.inst.write("CH" + str(channel) + ":SCALE " + str(units_per_division).format("e"))

    def set_vertical_offset(self, channel, offset):
        """
        This command sets or queries the vertical offset for the specified analog channel.
        :param channel: channel number
        :param offset: offset for the channel
        :return: None
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        self.inst.write("CH" + str(channel) + ":SCALE " + str(offset).format("e"))

    # def set_vertical

    def read(self):
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        # turn off header
        self.inst.write("HEADER OFF")
        self.set_channels()

        for i, ch in enumerate(self.CHAN):  # for each channel
            # Specify waveform source
            self.inst.write(':Data:Source ' + ch)
            # Specify waveform data format - most sig. byte transferred first
            self.inst.write(':Data:Encdg ASCI')  # charged from SRIbinary, alternative RPB
            # Number of bits per waveform point
            self.inst.write('WFMOutPre:BIT_Nr ' + str(self.BIT_NR))
            # Number of bytes per data point
            self.inst.write('Data:Width ' + str(self.BYTE_NR))
            # Specify that we want to transfer N_SAMP points
            self.inst.write(':Data:Start 1')
            self.inst.write(':Data:Stop ' + str(self.N_SAMP))

            # Get scale and offset
            verticalScale = float(self.inst.query('WFMOUTPre:YMULT?'))
            yOffset = float(self.inst.query('WFMOutpre:YOFF?'))
            yzero = float(self.inst.query('WFMPRE:YZERO?'))

            # Get the sample interval in seconds
            Ts = float(self.inst.query('WFMOutPre:XINcr?'))

            # Request the waveform data
            ADC_wave = self.inst.query_ascii_values('CURVE?', container=np.array)

            # Read in the data from the buffer, and scale
            self.wave[ch] = list((ADC_wave - yOffset) * verticalScale + yzero)

        # Get time series
        self.wave['t'] = Ts * np.arange(1, self.N_SAMP)
        return self.wave
