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
        self.inst.read_termination = '\n'
        self.inst.write_termination = '\n'
        self.inst.timeout = 10000

        # self.inst.set_visa_attribute(pyvisa.constants.VI_ATTR_ASRL_BAUD, 9600)
        # self.inst.set_visa_attribute(pyvisa.constants.VI_ATTR_ASRL_DATA_BITS, 8)
        # self.inst.set_visa_attribute(pyvisa.constants.VI_ATTR_ASRL_PARITY, pyvisa.constants.VI_ASRL_PAR_NONE)
        # self.inst.set_visa_attribute(pyvisa.constants.VI_ATTR_ASRL_FLOW_CNTRL, pyvisa.constants.VI_ASRL_FLOW_DTR_DSR)
        try:
            print("Opened connection with ", self.query('*IDN?;'))
        except Exception as e:
            print('Error occurred while trying to open connection with keysight oscilloscope.\nError:\n', e)

        self.InputBufferSize = 65536

        print('Scope open completed\n')
        print(self.query('*IDN?;'))
        # self.inst.write('*rst')

    def set_channels(self):  # not updated
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        displayed = [False, False, False, False]
        for channel in range(1, 5):
            resp = self.query(":CHAN" + str(channel) + ":DISPLAY?")
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

    def set(self, trigger_voltage=-1):
        # Currently assumes most setup is done through scope screen interface
        # Setup trigger - complicated - best done on screen for now
        self.inst.write('TRIG:MODE EDGE')
        self.inst.write(':TRIG:EDGE:SOUR CHAN1')
        self.inst.write('TRIG:EDGE:SLOPE NEG')
        self.inst.write('TRIG:EDGE:LEVEL '+str(trigger_voltage))
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

    def arm(self,HRes):
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')

        self.inst.write(':STOP')
        opc = int(self.query('*OPC?'))
        if HRes:
            self.inst.write('ACQUIRE:TYPE HRESolution')
        else:
            self.inst.write('ACQUIRE:TYPE NORMAL')
        # self.inst.write('ACQUIRE:COMPLETE 100')
        # self.inst.write('ACQUIRE:DIGI 1')
        # self.inst.write('ACQUIRE:POINTS AUTO')

        # ese = self.query('*ESE?')
        # self.inst.write('*ESE 1')

        self.inst.write('*CLS')
        self.inst.write(':SINGLE')
        time.sleep(0.1)

        # msg = 'DIGITIZE:'
        # for i, ch in enumerate(self.CHAN):  # for each channel
        #     msg += 'CHAN' + str(i) + ','
        # msg = msg[:-1]
        # self.inst.write(msg)
        # self.inst.write('*OPC')
        # stb = 0
        # while stb ==0:
        #     time.sleep(0.1)
        #     stb = int(self.query('*STB?'))
        # self.query('*ESR?')
        # self.inst.write('*ESE '+ese)




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

    def set_horizontal_position(self, position):
        """
        This command sets or queries the horizontal position as a percent of screen
        width. When Horizontal Delay Mode is turned off, this command is equivalent
        to adjusting the HORIZONTAL POSITION knob on the front panel. When
        Horizontal Delay Mode is turned on, the horizontal position is forced to 50%

        position: float - position as a percentage of the screen width
        """
        self.inst.write("HORIZONTAL:POSITION " + str(position))

    def set_vertical_scale(self, channel, units_per_division):
        n_divisions = 8
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        self.inst.write("CHAN" + str(channel) + ":RANGE " + str(units_per_division * n_divisions).format("e") + " V")

    def set_vertical_offset(self, channel, offset):
        """
        This command sets the vertical offset for the specified analog channel in divisions
        :param channel: channel number
        :param offset: offset for the channel
        :return: None
        """
        pass # probe offset cannot be set on this scope
        # n_divisions = 8
        # if not hasattr(self, 'inst'):
        #     raise ConnectionError('MSO54 not opened')
        # time.sleep(0.25)
        # range= float(self.query(":CHAN"+str(channel)+":RANGE?"))
        # offset_units = offset*range/n_divisions
        # # self.inst.write(":CHAN" + str(channel) + ":OFFSET " + str(offset_units).format("e"))

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
        offset = self.query("CHAN" + str(ch) + ":OFFSET?")
        try:
            offset_float = float(offset)
        except ValueError as e:
            raise e
            # print("Scope returned something that couldnt be processed into a float")
            # offset = self.query("CH" + str(ch) + ":OFFSET?")
            # offset_float = float(offset)

        return offset_float

    def get_horizontal_position(self):
        """
        This command queries the horizontal position as a percent of screen
        width.
        :return float - position as a percentage of the screen width
        """
        msg = self.query("TIMEBASE:REF?")
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
        if unit is not None:
            if str.upper(unit) == "VOLT" or str.upper(unit) == "V":
                self.inst.write("CHAN" + str(channel) + ":UNITS " + unit)
            elif str.upper(unit) == "AMP" or str.upper(unit) == "A":
                self.inst.write("CHAN" + str(channel) + ":UNITS " + unit)
            else:
                raise ValueError("Invalid unit parameter must be: 'AMP', 'A', 'VOLT' or 'V'")
        else:
            unit = "V"
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
        msg = self.query("CHAN" + str(channel) + ":IMPEDANCE?")
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
        return float(self.query(':TIMEBASE:RANGE?')) / n_divisions

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
        try:
            self.query('*OPC?')
            time.sleep(0.2) # needed to allow a subsequent trigger to occur after setting up cursor
            # v_offset = self.get_vertical_offset(channel)
            v_position = self.query(":MARKer:Y1Position?")
        except pyvisa.VisaIOError:
            self.query('*OPC?')
            time.sleep(0.2)  # needed to allow a subsequent trigger to occur after setting up cursor
            # v_offset = self.get_vertical_offset(channel)
            v_position = self.query(":MARKer:Y1Position?")


        self.inst.write("MARKER:X1:DISPLAY 0")

        if position > 1e36:
            time.sleep(0.2)
            v_position = self.query(":MARKer:Y1Position?")
            if position > 1e36:
                raise ValueError("Measurement returning invalid data, measuement = " + str(position))
        position = float(v_position)  # - v_offset
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

    def read(self, n_samples=None):
        timeout = 1
        if not hasattr(self, 'inst'):
            raise ConnectionError('DSOX2024A not opened')
        # turn off header

        timestart = time.time()
        resp = 0
        # while int(resp) != 1 and time.time() - timestart < timeout:
        #     time.sleep(0.05)
        #     resp = self.query(":TER?")
        #     self.query('*OPC?')
        # if int(resp) != 1:
        #     raise TimeoutError("Acquire did not complete")#
        RUN_BIT = 3
        RUN_MASK = 1 << RUN_BIT
        ACQ_DONE = 0
        ACQ_NOT_DONE = 1 << RUN_BIT
        stb = 8
        Acq_State = ACQ_NOT_DONE

        time.sleep(0.5)
        while Acq_State == ACQ_NOT_DONE:
            Status = int(self.query(':OPER:COND?'))
            Acq_State = (Status & RUN_MASK)
            if Acq_State == ACQ_DONE:
                break
            print(Status)
            time.sleep(0.1)
        if Acq_State == ACQ_DONE:  # Acquisition fully completed
            print("Signal acquired.")
        # self.inst.write("WAVEFORM:PREAMBLE OFF")
        # self.query('*OPC?')

        for i, ch in enumerate(self.CHAN):  # for each channel
            if ch:
                print("channel: ",i+1)
                # Specify waveform source
                self.inst.write(':WAVEFORM:SOURCE CHAN' + str(i+1))
                # Specify that we want to transfer N_SAMP points
                if not n_samples:
                    samples = self.N_SAMP
                else:
                    samples = n_samples
                # self.inst.write(':WAVEFORM:POINTS '+str(samples))
                self.inst.write(':WAVEFORM:POINTS MAXIMUM')
                # Specify waveform data format - most sig. byte transferred first
                self.inst.write(":WAVEFORM:FORMAT ASCII")  # charged from SRIbinary, alternative RPB
                # Number of bits per waveform point

                # self.inst.write('WFMOutPre:BIT_Nr '+ str(self.BIT_NR))
                # Number of bytes per data point
                # self.inst.write(':Data:Width '+ str(self.BYTE_NR))


                # Get scale and offset
                # verticalScale  = self.get_vertical_scale(i)

                # yOffset = float(self.query( 'WFMOutpre:YOFF?'))
                # yzero = float(self.query('WFMPRE:YZERO?'))

                # Get the sample interval in seconds

                #
                # # Request the waveform data
                # ADC_wave = self.query_ascii_values(':WAVEFORM:DATA?', container= np.array)
                preable = self.query(':WAVeform:PREAMBLE?')
                try:
                    ADC_wave_raw = self.query(':WAV:DATA?')
                except pyvisa.VisaIOError:
                    print("Failed to read data, retrying...")
                    ADC_wave_raw = self.query(':WAV:DATA?')
                print("Data read successfully")

                preable = list(map(float,preable.split(',')))
                Ts = preable[4]
                n_leading = int(ADC_wave_raw.split("#")[1][0])
                ADC_wave = list(map(np.double, ADC_wave_raw.split("#")[1][n_leading+1:].split(',')))

                # # Read in the data from the buffer, and scale
                self.wave['CH' + str(i + 1)] = {}
                self.wave['CH'+str(i+1)]["Amp"] = ADC_wave
                self.wave['CH'+str(i+1)]["Time"] = Ts*np.arange(1, len(ADC_wave)+1)
                # time.sleep(0.5)

        return self.wave

    def set_samplerate(self,samplerate):
        """
        Not possible to set samplerate on keysight scopes
        :return:
        """
        pass

    def query(self, string):
        N_retry = 3
        retry_counter=0
        resp=None
        while retry_counter < N_retry:
            try:
                resp = self.inst.query(string)
            except pyvisa.VisaIOError:
                retry_counter=+1
                print("Query failed retrying...")
            if resp:
                return resp
        raise pyvisa.VisaIOError



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
