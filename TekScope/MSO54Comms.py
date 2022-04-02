### Interface code for Tektronix MSO54 Oscilloscope ###
# @author: J Bruford, based on MATLAB script written by: G Jones

import pyvisa
import numpy as np
from struct import unpack


class MSO54:
    def __init__(self):
        self.N_SAMP = 1250 # number of samplestocapture
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
        self.CHAN = [str(item) for item in resp[:-1].split(",")]

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

    def run(self):
        """
        This command sets the scope to continually acquire data
        :return:
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        self.inst.write('ACQUIRE:STOPAFTER RUNSTOP')
        self.inst.write('ACQuire:State RUN')

    def arm(self):
        """
        This comand sets the scope to capture a single waveform
        :return:
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')

        self.inst.write('ACQUIRE:STOPAFTER SEQUENCE')
        self.inst.write('ACQuire:State 1')
    def set_mode(self, mode):
        """
        Can be used to set sample or high res mode on the scope

        Sample mode: The most basic of all the modes, sample mode delivers the highest accuracy for timing interval
        measurements. It retains and displays the first point from each sample interval, discarding the others. In
        many DSOs, sample mode interleaves the digitizers of two or more channels to achieve the instrument’s maximum
        sample rate.

        High Resolution (Hi-Res) mode: A Tektronix-patented process that calculates and displays the average of all
        the values in each sample interval. It runs at the highest sampling rate of the digitizer, providing maximum
        detail in the acquired waveform. It does not interleave channels. Because it works with more data per sample
        interval, Hi-Res mode increases the effective vertical measurement resolution. Sample, Peak Detect,
        and Hi-Res modes operate in real time, using the acquired data from one trigger event. Therefore these modes
        are suitable for the most demanding, single-shot measurements at frequencies up to the oscilloscope’s upper
        bandwidth limit. The remaining modes require a repetitive signal.

        :param mode:
        :return:
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')

        if mode != "SAMPLE" and mode != "HIRES":
            raise ValueError("Mode must be either 'SAMPLE' or 'HIRES'")

        self.inst.write("ACQUIRE:MODE " + mode)



    def set_horizontal_scale(self, T_per_division):
        """
        Method for adjusting the horizontal scale, T_per_division is in seconds
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        self.inst.write("HORIZONTAL:MODE:SCALE " + str(T_per_division))

    def set_vertical_scale(self, channel: int, units_per_division: float):
        """
        This command sets or returns the vertical scale for the specified analog channel. 9 divisions on screen
        :param channel: channel number
        :param units_per_division:
        :return: None
        """
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
        self.inst.write("CH"+ str(channel) + ":OFFSET " + str(offset).format("e"))

    def set_vertical_position(self, channel, position):
        """
        This command sets the vertical position for the specified analog channel.
        :param channel: channel number
        :param position: sets the position for the channel in divisions
        :return: None
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        self.inst.write("CH"+ str(channel) + ":POSITION " + str(position))

    def set_horizontal_position(self, position):
        """
        This command sets or queries the horizontal position as a percent of screen
        width. When Horizontal Delay Mode is turned off, this command is equivalent
        to adjusting the HORIZONTAL POSITION knob on the front panel. When
        Horizontal Delay Mode is turned on, the horizontal position is forced to 50%

        position: float - position as a percentage of the screen width
        """
        self.inst.write("HORIZONTAL:POSITION " + str(position))

    def set_set_viewstyle(self, mode, waveveiw = 1):
        """
        The command sets or queries the waveform layout style used by the display, either stacked or overlayed
        :param mode: string specifying which of the two modes 'STACKED' or 'OVERLAY'
        :param waveveiw: optional argument specifying the waveview to modify, 1 by default
        :return: None

        """
        if mode != "STACKED" and mode != "OVERLAY":
            raise ValueError("Arg mode can only be 'STACKED' or 'OVERLAY'")

        self.inst.write("DISPLAY:WAVEVIEW"+str(waveveiw)+":VIEWSTYLE  " + str(mode))

    def set_channel_alt_units(self, channel: int, unit: str):
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")

        if unit:

            self.inst.write("CH"+str(channel)+":PROBEFUNC:EXTUNITS:STATE 1")
            self.inst.write("CH"+str(channel)+":PROBEFUNC:EXTUNITS '"+unit+"'")
        else:
            self.inst.write("CH" + str(channel) + ":PROBEFUNC:EXTUNITS:STATE 0")

    def set_channel_label(self, channel: int, label: str):
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        self.inst.write("CH"+str(channel)+":LABEL:NAME '"+label+"'")

    def set_channel_termination(self, channel: int, termination: str):
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        if termination != "50" and termination != "1M":
            raise ValueError("termination must be either '50' or '1M'")
        if termination == "50":
            self.inst.write("CH"+str(channel)+":TERMINATION 50")
        elif termination == "1M":
            self.inst.write("CH"+str(channel)+":TERMINATION 1.0E6")

    def set_channel_bandwidth(self, channel: int, bandwidth: str):
        """
        Sets the bandwidth of the channel
        if 50 ohm terminated can select: 20MHz, 250MHz, 1GHz
        if 1M ohm terminated can select: 20MHz, 250MHz, 500MHz
        :param channel:
        :param bandwidth:
        :return:
        """
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        if bandwidth != "20MHz" and bandwidth != "250MHz" and bandwidth != "500MHz" and bandwidth != "1GHz":
            raise ValueError("bandwidth must be either '20MHz', '250MHz', '500MHz' or '1Ghz'")

        if bandwidth == "20MHz":
            self.inst.write("CH"+str(channel)+":BANDWIDTH 20E6")
        elif bandwidth == "250MHz":
            self.inst.write("CH"+str(channel)+":BANDWIDTH 250E6")
        elif bandwidth == "500MHz":
            self.inst.write("CH"+str(channel)+":BANDWIDTH 500E6")
        elif bandwidth == "1GHz":
            self.inst.write("CH"+str(channel)+":BANDWIDTH 1E9")

    def set_channel_ext_attenuation(self, channel: int, gain: float):
        """
        Sets the external atteniation of the channel
        :param channel:
        :param gain:
        :return:
        """
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        self.inst.write("CH" + str(channel) + ":PROBEFUNC:EXTATTEN " + str(gain))


    def set_displayed_channels(self, channels: list, waveveiw = 1):
        """
        This mehtod sets the visible channels on the scope
        :param channels: a list of length 4 each element a bool representing if the channel is displayed or not
        :return:
        """
        if len(channels) != 4:
            raise ValueError("channels must be a list of length 4")
        for channel_num, channel in enumerate(channels):
            if channel:
                self.inst.write("DISplay:WAVEView"+str(waveveiw)+":CH"+str(channel_num+1)+":STATE 1")
            else:
                self.inst.write("DISplay:WAVEView" + str(waveveiw) + ":CH" + str(channel_num + 1) + ":STATE 0")


    def get_samplerate(self):
        """
        This command queries the sample rate.
        :return: samplerate in samples per second
        """
        return float(self.inst.query("HORIZONTAL:MODE:SAMPLERATE?"))

    def get_scale(self):
        """
        This command queries the sample rate. The value returned indicate the horizontal scale is set this in s/division.
        :return: samplerate in samples per second
        """
        return float(self.inst.query("HORizontal:MODE:SCAle?"))

    def get_n_divisons(self):
        """
        This command queries the number of divisions the screen is divided over
        :return: number of divisions
        """
        return int(self.inst.query("HORIZONTAL:DIVISIONS?"))

    def get_n_samples_on_display(self):
        """
        This function computes the number of samples displayed on the screen
        :return: number of samples as an int
        """

        n_divisions = self.get_n_divisons()
        samplerate = self.get_samplerate()
        t_division = self.get_scale()
        n_samples = int(n_divisions*t_division*samplerate)
        return n_samples


    def read(self, n_samples=None):
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        # turn off header
        self.inst.write("HEADER OFF")
        self.set_channels()

        if not n_samples:
            samples = self.N_SAMP
        else:
            samples = n_samples
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
            self.inst.write(':Data:Stop ' + str(samples))

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
        self.wave['t'] = np.array(Ts * np.arange(0, samples))
        return self.wave


