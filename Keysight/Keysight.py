### Interface code for Keysight Oscilloscope ###
# @author: J Bruford

import pyvisa
import numpy as np
import time
from struct import unpack


class KeysightScope:
    def __init__(self, samplerate):
        self.samplerate = samplerate
        self.N_SAMP = 1250  # number of samplestocapture
        self.BIT_NR = 12  # Numberofbitsperwaveformpoint
        self.BYTE_NR = 2  # Number of bytes per waveform point - NOTE: Must change binblockread() precision if this value
        # is changed!
        self.CHAN = []  # Oscilloscope channels to use - all channels listed must be enabled on scope first otherwise might crash
        self.wave = {}  # output waveform data from scope
        self.status = []
        self.rm = pyvisa.ResourceManager()

    def open(self):
        if hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A already open. Exiting without doing anything.')

        self.inst = self.rm.open_resource(self.RESOURCE_STRING)
        self.inst.read_termination = "\n"
        self.inst.write_termination = "\n"
        self.inst.timeout = 10000
        try:
            print("Opened connection with ", self.inst.query('*IDN?;'))
        except Exception as e:
            print('Error occurred while trying to open connection with keysight oscilloscope.\nError:\n', e)
        self.inst.timeout = 100

        self.InputBufferSize = 65536

        print('Scope open completed\n')
        print(self.inst.query('*IDN?;'))

    def set_channels(self):  # not updated
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        displayed = [False, False, False, False]
        for channel in range(1, 5):
            resp = self.inst.query(":CHAN" + str(channel) + ":DISPLAY?")
            if resp == "1":
                displayed[channel - 1] = True
            elif resp == "0":
                displayed[channel - 1] = False
            else:
                raise IOError("resp was not as expected in set channels")
        self.CHAN = displayed

    def close(self):
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not open. Cannot close')
        else:
            self.inst.close()
            delattr(self, 'inst')

    def set(self):
        # Currently assumes most setup is done through scope screen interface
        # Setup trigger - complicated - best done on screen for now
        self.inst.write('TRIG:MODE EDGE')
        self.inst.write(':TRIG:EDGE:SOUR CHAN1')
        self.inst.write('TRIG:EDGE:SLOPE NEG')
        self.inst.write('TRIG:EDGE:LEVEL 10')
        self.inst.write('TRIG:SWEEP NORMAL')

        # self.inst.write('ACQuire:StopAfter Sequence')

    def run(self):
        """
        This command sets the scope to continually acquire data
        :return:
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        self.inst.write(':RUN')

    def arm(self):
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        self.inst.write(':SINGLE')
        self.inst.write('ACQUIRE:TYPE NORMAL')
        self.inst.write('ACQUIRE:COMPLETE 100')
        print(self.CHAN)
        self.inst.write('ACQUIRE:DIGI 1')
        self.inst.write('ACQUIRE:POINTS AUTO')

        msg = 'DIGITIZE:'
        for i, ch in enumerate(self.CHAN):  # for each channel
            msg += 'CHAN' + str(i) + ','
        msg = msg[:-1]
        self.inst.write(msg)

    def set_horizontal_scale(self, T_per_division):
        """
        Method for adjusting the horizontal scale, T_per_division is in seconds
        """
        n_divisions = 10
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        self.inst.write("TIMEBASE:MODE MAIN")
        self.inst.write("TIMEBASE:RANGE " + str(T_per_division * n_divisions))
        self.inst.write(
            "TIMEBASE:REF LEFT")  # sets the time reference to one division from the left side of the screen,
        # to the center of the screen, or to one division from the right side of the screen. {LEFT | CENT | RIGH}

    def set_vertical_scale(self, channel, units_per_division):
        n_divisions = 8
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        self.inst.write("CHAN" + str(channel) + ":RANGE " + str(units_per_division * n_divisions).format("e") + " V")

    def set_vertical_position(self, channel, offset):
        """
        This command sets or queries the vertical offset for the specified analog channel.
        :param channel: channel number
        :param offset: offset for the channel
        :return: None
        """
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        self.inst.write("CHAN" + str(channel) + ":OFFSET " + str(offset).format("e") + " V")

    def get_vertical_position(self, ch: int):
        if not hasattr(self, 'inst'):
            raise ConnectionError('MSO54 not opened')
        offset = self.inst.query("CHAN" + str(ch) + ":OFFSET?")
        try:
            offset_float = float(offset)
        except ValueError as e:
            raise e
            # print("Scope returned something that couldnt be processed into a float")
            # offset = self.inst.query("CH" + str(ch) + ":OFFSET?")
            # offset_float = float(offset)

        return offset_float

    def get_horizontal_position(self):
        """
        This command queries the horizontal position as a percent of screen
        width.
        :return float - position as a percentage of the screen width
        """
        msg = self.inst.query("TIMEBASE:REF?")
        if msg == 'LEFT':
            return float(10)
        elif msg == 'CENT':
            return float(50)
        elif msg == 'RIGH':
            return float(90)
        else:
            raise ValueError("Queryn for timebase reference returened: " + msg + ". This is not a accepted value")

    def set_set_viewstyle(self, mode, waveveiw=1):
        # Not possible to change viewstyle on this scope
        pass

    def set_channel_alt_units(self, channel: int, unit: str):
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")

        if str.upper(unit) == "VOLT" or str.upper(unit) == "V":
            self.inst.write("CHAN" + str(channel) + ":UNITS " + unit)
        elif str.upper(unit) == "AMP" or str.upper(unit) == "A":
            self.inst.write("CHAN" + str(channel) + ":UNITS " + unit)
        else:
            raise ValueError("Invalid unit parameter must be: 'AMP', 'A', 'VOLT' or 'V'")

    def set_channel_label(self, channel: int, label: str):
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        self.inst.write("CHAN" + str(channel) + ":LABEL '" + label + "'")

    def set_channel_termination(self, channel: int, termination: str):
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        if termination != "50" and termination != "1M":
            raise ValueError("termination must be either '50' or '1M'")
        if termination == "50":
            self.inst.write("CHAN" + str(channel) + ":IMPEDANCE FIFTY")
        elif termination == "1M":
            self.inst.write("CHAN" + str(channel) + ":IMPEDANCE ONEMEG")

    def get_channel_terminationn(self, channel: int):
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        msg = self.inst.query("CHAN" + str(channel) + ":IMPEDANCE?")
        if msg == "ONEM":
            return float(1e6)
        elif msg == "FIFT":
            return float(50)

    def set_channel_bandwidth(self, channel: int, bandwidth: str):
        """
        Sets the bandwidth of the channel
        the keysight scopes bandwidth cannot be changed
        :param channel:
        :param bandwidth:
        :return:
        """
        pass

    def get_channel_bandwidth(self, channel):
        """
        bandwidth cannot be set on the keysight scopes
        :param channel:
        :return:
        """
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        return float(-1)

    def set_channel_ext_attenuation(self, channel: int, gain: float):
        """
        Sets the external atteniation of the channel
        :param channel:
        :param gain:
        :return:
        """
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")
        self.inst.write("CHAN" + str(channel) + ":PROBE " + str(gain))

    def set_displayed_channels(self, channels: list):
        """
        This mehtod sets the visible channels on the scope
        :param channels: a list of length 4 each element a bool representing if the channel is displayed or not
        :return:
        """
        if len(channels) != 4:
            raise ValueError("channels must be a list of length 4")
        for channel_num, channel in enumerate(channels):
            if channel:
                self.inst.write(":CHAN" + str(channel_num + 1) + ":DISPLAY 1")
            else:
                self.inst.write(":CHAN" + str(channel_num + 1) + ":DISPLAY 0")

    def get_scale(self):
        """
        This command queries the sample rate. The value returned indicate the horizontal scale is set this in s/division.
        :return: samplerate in samples per second
        """
        n_divisions = 10
        return float(self.inst.query("TIME:RANGE?") / n_divisions)

    def get_n_divisons(self):
        """
        This command queries the number of divisions the screen is divided over
        :return: number of divisions
        """
        return int(10)

    def measure_cursor_horizontal_poition(self, position, channel):
        if channel > 4 or channel < 1:
            raise ValueError("Invalid channel number")

        self.inst.write(":MARKER:MODE WAVEFORM")
        self.inst.write("MARKER:X1:DISPLAY 1")
        self.inst.write("MARKER:X2:DISPLAY 0")
        self.inst.write(":MARKER:X1Y1SOURCE CHANNEL" + str(channel))
        self.inst.write(":MARKER:X1Position " + str(position))

        # v_offset = self.get_vertical_offset(channel)
        v_position = self.inst.query(":MARKer:Y1Position?")

        self.inst.write("MARKER:X1:DISPLAY 0")
        position = float(v_position)  # - v_offset
        if position > 99e36:
            raise ValueError("Measurement returning invalid data, measuement = " + str(position))
        return position

    def get_samplerate(self):
        """
        This command queries the sample rate.
        :return: samplerate in samples per second
        """
        return float(self.samplerate)

    def get_n_samples_on_display(self):
        """
        This function computes the number of samples displayed on the screen
        :return: number of samples as an int
        """

        n_divisions = self.get_n_divisons()
        samplerate = self.get_samplerate()
        t_division = self.get_scale()
        n_samples = int(n_divisions * t_division * samplerate)
        return n_samples

    def read(self):
        timeout = 1
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        # turn off header

        timestart = time.time()
        resp = 0
        while int(resp) != 1 and time.time() - timestart < timeout:
            resp = self.inst.query(":TER?")  # todo this line does not seem to correctly check for triggering

        if int(resp) != 1:
            raise TimeoutError("Aquire did not complete")

        self.set_channels()

        self.inst.write("WAVEFORM:PREAMBLE OFF")
        for i, ch in enumerate(self.CHAN):  # for each channel
            # Specify waveform source
            self.inst.write(':WAVEFORM:SOURCE CHAN' + str(i))
            # Specify waveform data format - most sig. byte transferred first
            self.inst.write(":WAVEFORM:FORMAT ASCII")  # charged from SRIbinary, alternative RPB
            # Number of bits per waveform point
            # self.inst.write('WFMOutPre:BIT_Nr '+ str(self.BIT_NR))
            # Number of bytes per data point
            # self.inst.write(':Data:Width '+ str(self.BYTE_NR))
            # Specify that we want to transfer N_SAMP points
            self.inst.write(':WAVEFORM:POINTS ' + str(self.N_SAMP))

            # Get scale and offset
            # todo fix below
            # verticalScale  = self.get_vertical_scale(i)

            # yOffset = float(self.inst.query( 'WFMOutpre:YOFF?'))
            # yzero = float(self.inst.query('WFMPRE:YZERO?'))

            # Get the sample interval in seconds
            Ts = float(self.inst.query('WAVEFORM:XINC?'))

            #
            # # Request the waveform data
            # ADC_wave = self.inst.query_ascii_values(':WAVEFORM:DATA?', container= np.array)
            ADC_wave_raw = self.inst.query(':WAVEFORM:DATA?')
            n_leading = int(ADC_wave_raw[1])
            ADC_wave = map(np.double,ADC_wave_raw[2+n_leading:])
            # # Read in the data from the buffer, and scale
            self.wave[ch] = ADC_wave


        # Get time series
        self.wave['t'] = Ts*np.arange(1, self.N_SAMP)
        return ADC_wave


class DSOX2024A(KeysightScope):
    def __init__(self):
        self.samplerate = 1e9  # interleaved samplerate
        super().__init__(self.samplerate)
        self.RESOURCE_STRING = 'USB0::0x0957::0x1796::MY56202075::INSTR'  # Use pyvisa Resource Manager to find the resource string for Keysight scope


class MSOX4024A(KeysightScope):
    def __init__(self):
        self.samplerate = 2.5e9
        super().__init__(self.samplerate)
        self.RESOURCE_STRING = 'USB0::0x0957::0x17B6::MY53110104::INSTR'  # Use pyvisa Resource Manager to find the resource string for Keysight scope
        # interleaved samplerate
