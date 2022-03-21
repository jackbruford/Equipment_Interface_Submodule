### Interface code for Tektronix MSO54 Oscilloscope ###
# @author: J Bruford, based on MATLAB script written by: G Jones

import pyvisa
import numpy as np

class MSO54:
    def __init__(self):
        self.N_SAMP = 1250   # number of samplestocapture
        self.BIT_NR = 12     # Numberofbitsperwaveformpoint
        self.BYTE_NR = 2     # Number of bytes per waveform point - NOTE: Must change binblockread() precision if this value
        # is changed!
        self.RESOURCE_STRING = 'USB::0x0699::0x0522::C012598::INSTR' #Use Tek's VISA Resource Manager to find the resource string
        self.CHAN = ['CH1','CH2','CH3','CH4']  #Oscilloscope channels to use - all channels listed must be enabled on scope first otherwise might crash
        self.wave = []  #output waveform data from scope
        self.status = []
        self.rm = pyvisa.ResourceManager()

    def open(self):
        if hasattr(self, 'inst'):
            print('MSO54 already open. Exiting without doing anything.')
            raise  # device already exists

        self.inst = self.rm.open_resource(self.RESOURCE_STRING)
        self.inst.read_termination ="\n"
        self.inst.write_termination = "\n"
        self.inst.timeout = 1000
        try:
            print("Opened connection with ", self.inst.query('*IDN?;'))
        except Exception as e:
            print('Error occurred while trying to open connection with multimeter.\nError:\n', e)
        self.inst.timeout = 1000


        self.InputBufferSize = 65536

        print('Scope open completed\n')
        print(self.inst.query('*IDN?;'))

    def close(self):
        if not hasattr(self, 'inst'):
            print('MSO54 not open. Cannot close')
            raise  # device already exists
        else:
            self.inst.close()


    def set(self):
        #Currently assumes most setup is done through scope screen interface
        # Setup trigger - complicated - best done on screen for now
        self.inst.write('TRIG:A:TYPE EDGE')
        self.inst.write('TRIG:A:EDGE:SOURCE CH1')
        self.inst.write('TRIG:A:EDGE:SLOPE FALL')
        self.inst.write('TRIG:A:LEVEL:CH1 10')
        self.inst.write('TRIG:A:MODE NORMAL')
        self.inst.write('ACQuire:StopAfter Sequence')
    def arm(self):
        self.inst.write('ACQuire:State 1')

    def read(self):
        wave = {}
        for i, ch in enumerate(self.CHAN): #for each channel
            # Specify waveform source
            self.inst.write(':Data:Source ' + ch)
            # Specify waveform data format - most sig. byte transferred first
            self.inst.write(':Data:Encdg SRIBinary')
            # Number of bits per waveform point
            self.inst.write('WFMOutPre:BIT_Nr '+ str(self.BIT_NR))
            # Number of bytes per data point
            self.inst.write('Data:Width '+ str(self.BYTE_NR))
            # Specify that we want to transfer N_SAMP points
            self.inst.write(':Data:Start 1')
            self.inst.write(':Data:Stop '+str(self.N_SAMP))
            #Get scale and offset
            verticalScale  = self.inst.query('WFMOUTPre:YMULT?')
            yOffset = self.inst.query( 'WFMOutpre:YOFF?')
            #Get the sample interval in seconds
            Ts = self.inst.query('WFMOutPre:XINcr?')
            # Request the waveform data
            rawdata = self.inst.query('CURVE?')
            curve = np.array(list(map(float, rawdata.split(","))))
            # Read in the data from the buffer, and scale
            wave[ch] = list(float(verticalScale) * curve + float(yOffset))

        # Get time series
        wave['t'] = Ts*np.arange(1,self.N_SAMP)

