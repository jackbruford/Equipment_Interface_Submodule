import serial
import array
import time
import pdb

WAITTIME = 2# wait interval between retries
RESPONSE_WAIT = 0.1 # wait interval between writing and reading to power supply
CHECK_DELAY = 1 # wait between setting a value and checking it
# This is the base class for the PSI8000 and EL9000 EaDevices, and contains
# common functionality implementing the RS232 communications
class EaDevice:
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'v': 0, 'i': 0, 'p': 0}
        self.volt_nom = 720
        self.curr_nom = 15
        self.p_nom = 3000

    def connect(self, port_string, brate=57600, parity='O', tout=2):
        """Opens up a serial connection to the device"""
        try:
            self.ser.port = port_string
            self.ser.baudrate = brate
            self.ser.parity = parity
            self.ser.timeout = tout
            self.ser.open()
            if self.ser.isOpen():
                print('Opened serial connection over port ', port_string)
            else:
                print('Failed to open serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to open serial connection.\nError:\n', se)

    def disconnect(self):
        """Closes the serial connection to the device"""
        try:
            self.ser.close()
            if not self.ser.isOpen():
                print('Closed serial connection to device.')
            else:
                print('Failed to close serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to close serial connection.\nError:\n', se)

    def get_dev_info(self):
        """Not Implemented. Queries device to get factory information from it"""

    def make_SD(self, data_length, direction, broadcast, transmission_type):
        """Creates the start delimiter byte"""
        send_byte = (transmission_type << 6) | (broadcast << 5) | (direction << 4) | data_length - 1
        return send_byte

    def make_message(self, SD, device_node, obj, data=None):
        message = array.array('B', (SD, device_node, obj))  # First part of message
        if data != None:
            message.extend(data)  # Add data to message
        CS = sum(message)
        message.extend((CS >> 8, CS & 255))  # Finish message with checksum
        return message

    def decode_message(self, message):
        # Check that checksum is correct
        CS = sum(message[0:-2])
        if (CS >> 8 != message[-2]) or (CS & 255 != message[-1]):
            print('WARNING: Received checksum does not match transmission in EA device')
            return 1
        SD = message[0]
        data_length = (SD & 0b00001111) + 1
        direction = SD & 0b00010000  # direction (1 means from PC to device)
        broadcast = SD & 0b00100000
        t_type = (SD & 0b11000000) >> 6  # Transmission type (00 reserved, 1 Query, 2 Query answer, 3 send data)
        DN = message[1]
        OBJ = message[2]
        data = message[3:-2]
        # Sanity checks
        if len(data) != data_length:
            print('WARNING: Received data does not match stated length in EAdevice')
            return 1
        return data

    def query_output(self):
        SD = self.make_SD(6, 1, 1, 1)
        OBJ = 71
        out_message = self.make_message(SD, 1, OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(11)
        data = self.decode_message(in_message)
        if data == 1:
            self.ser.write(out_message)
            in_message = self.ser.read(11)
            data = self.decode_message(in_message)
            if data == 1:
                raise ConnectionError("An error occurred in EAdevice.query_output(), one retry attempted")
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n', extra)
        self.output['v'] = self.volt_nom * (data[0] * (16 ** 2) + data[1]) / 25600
        self.output['i'] = self.curr_nom * (data[2] * (16 ** 2) + data[3]) / 25600
        self.output['p'] = self.p_nom * (data[4] * (16 ** 2) + data[5]) / 25600
        print(self.output)

    def set_remote(self, remote):
        SD = self.make_SD(2, 1, 1, 3)
        OBJ = 54  # Power supply control object
        if remote == 1:
            data = (0x10, 0x10)  # Mask:0x10, remote on:1
        elif remote == 0:
            data = (0x10, 0)  # Mask:0x10, remote off:0
        out_message = self.make_message(SD, 1, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n', extra)

    def output_on(self, output):
        SD = self.make_SD(2, 1, 1, 3)
        OBJ = 54  # Power supply control object
        if output == 1:
            data = (0x01, 1)  # Mask, output
        elif output == 0:
            data = (0x01, 0)  # Mask, output
        out_message = self.make_message(SD, 1, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n', extra)

    def set_v(self, voltage):
        if voltage > self.volt_nom:
            print('WARNING: Requested voltage is greater than device maximum. Ignoring request.')
            return
        SD = self.make_SD(2, 1, 0, 3)
        OBJ = 50
        v = int(25600 * voltage / self.volt_nom)
        data = (v >> 8, v & 0b0000000011111111)
        out_message = self.make_message(SD, 1, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n', extra)

    def set_i(self, current):

        if current > self.curr_nom:
            print('WARNING: Requested current is greater than device maximum.')  # Ignoring request.')
            # return
        SD = self.make_SD(2, 1, 0, 3)
        OBJ = 51
        i = int(25600 * current / self.curr_nom)
        data = (i >> 8, i & 0b11111111)
        out_message = self.make_message(SD, 1, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n', extra)

    def set_p(self, power):
        if power > self.p_nom:
            print('WARNING: Requested power is greater than device maximum. Ignoring request.')
            return
        SD = self.make_SD(2, 1, 0, 3)
        OBJ = 52
        p = int(25600 * power / self.p_nom)
        data = (p >> 8, p & 0b0000000011111111)
        out_message = self.make_message(SD, 1, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n', extra)

    def set_OVP_threshold(self, ovp, channel):
        OVC = ovp
        SD = self.make_SD(2, 1, 0, 3)
        OBJ = 38
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")
        OVP_thre = int(25600 * OVC / self.set_v(1, channel))
        data = (OVP_thre >> 8, OVP_thre & 0b0000000011111111)
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            #    print('WARNING: Unexpected data received. Data:\n',extra)
            print(extra)

    def set_OCP_threshold(self, ocp, channel):
        OVC = ocp
        SD = self.make_SD(2, 1, 0, 3)
        OBJ = 39
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")
        OVC_thre = int(25600 * OVC / self.set_i(1, channel))
        data = (OVC_thre >> 8, OVC_thre & 0b0000000011111111)
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)


# This class is for devices in the PSI8000 family, and contains functions specific
# to the control of power supplies
class PSI8000(EaDevice):
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'v': 0, 'i': 0, 'p': 0}
        self.volt_nom = 720
        self.curr_nom = 15
        self.p_nom = 3000

    def query_state(self):
        SD = self.make_SD(2, 1, 1, 1)
        DN = 0  # device node
        OBJ = 70  # Status object
        out_message = self.make_message(SD, DN, OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(7)
        data = self.decode_message(in_message)
        if data == 1:
            self.ser.write(out_message)
            in_message = self.ser.read(7)
            data = self.decode_message(in_message)
            if data == 1:
                raise ConnectionError("an error occured in EL9000.query_state(), 1 retry attempted")
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n', extra)
        self.state['remote'] = data[0] & 0b00000011  # 1 if device is in remote control mode
        self.state['analogue_control'] = data[0] & 32  # controlled by analogue interface?
        self.state['func_man_active'] = data[0] & 64  # function manager
        self.state['output_on'] = data[1] & 0b00000001
        self.state['contr_state'] = data[1] & 0b00000110  # Controller state (0:CV 1:CR 2:CC 3:CP)
        self.state['alarm_active'] = data[1] & 16
        print(self.state)


# This class is for electronic loads in the EL9000 family.
class EL9000(EaDevice):
    def __init__(self):
        super().__init__()
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'v': 0, 'i': 0, 'p': 0}
        self.volt_nom = 750
        self.curr_nom = 25
        self.p_nom = 2400

    def query_state(self):
        SD = self.make_SD(2, 1, 1, 1)
        DN = 0  # device node
        OBJ = 70  # Status object
        out_message = self.make_message(SD, DN, OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(7)
        data = self.decode_message(in_message)
        if data == 1:
            self.ser.write(out_message)
            in_message = self.ser.read(7)
            data = self.decode_message(in_message)
            if data == 1:
                raise ConnectionError("an error occured in EL9000.query_state(), 1 retry attempted")
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n', extra)
        self.state['remote'] = data[0] & 0b00000011  # 1 if device is in remote control mode
        self.state['input_on'] = data[1] & 0b00000001
        controller_states = {0: 'CV',
                             1: 'CR',
                             2: 'CC',
                             3: 'CP'}
        self.state['controller_state'] = controller_states[(data[1] & 0b00000110) >> 1]
        regulation_modes = {0: 'CR1',
                            1: 'CR2',
                            2: 'CP',
                            3: 'CC',
                            4: 'CP'}
        self.state['chosen_regulation_mode'] = regulation_modes[(data[1] & 0b00111000) >> 3]
        print(self.state)

    ##    def set_regulation_mode(self,regmode):
    ##        regulation_modes = {'CC':0,
    ##                            'CV':1,
    ##                            'CP':2,
    ##                            'CR1':3,
    ##                            'CR2':4}
    ##        SD = self.make_SD(2,1,1,3)
    ##        OBJ = 54    #Power supply control object
    ##        data = (0x0E, regulation_modes[regmode])    #Mask:0x0E
    ##        out_message = self.make_message(SD,1,OBJ,data)
    ##        self.ser.write(out_message)
    ##        time.sleep(0.01)
    ##        if self.ser.inWaiting() > 0:
    ##            extra = self.ser.read_all()
    ##            print('WARNING: Unexpected data received. Data:\n',extra)

    # Creating a copy of the functions named 'output' to 'input', as this makes more sense for load
    def input_on(self, on):
        self.output_on(on)

    def query_input(self):
        self.query_output()


# This class is for the PSB9000 bidirectional DC supply/load, using SCPI comms. It also works for the PSI9750-06DT
# On the PSI9750-06DT it was found necessary to increase the timeout to 500ms in the power supply communications menu
class PSB9000():
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'v': 0, 'i': 0, 'p': 0}
        self.volt_nom = 750
        self.curr_nom = 60
        self.p_nom = 15000

    def connect(self, port_string, brate=57600, parity='O', tout=2):
        """Opens up a serial connection to the device"""
        try:
            self.ser.port = port_string
            self.ser.baudrate = brate
            self.ser.parity = parity
            self.ser.timeout = tout
            self.ser.open()
            if self.ser.isOpen():
                print('Opened serial connection over port ', port_string)
                self.ser.write(bytes('*IDN?\n', 'ascii'))
                idn = self.ser.readline().decode('utf-8')
                print(idn)
            else:
                print('Failed to open serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to open serial connection.\nError:\n', se)

    def disconnect(self):
        """Closes the serial connection to the device"""
        try:
            self.ser.close()
            if not self.ser.isOpen():
                print('Closed serial connection to device.')
            else:
                print('Failed to close serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to close serial connection.\nError:\n', se)

    def set_remote(self, remote):
        if remote == 1:
            self.ser.write(bytes('SYST:LOCK 1\n', 'ascii'))
        elif remote == 0:
            self.ser.write(bytes('SYST:LOCK 0\n', 'ascii'))

    def set_v(self, volt, RETRIES: int = 2):
        """
        Turns on or off the output of the power supply and checks that this has taken affect will retry a set number of
        times, specified by RETRIES before raising an error
        volt - int  Output voltage setpoint
        RETRIES - int   Optional arguement specifying the number of retries before raising an erro
        """
        retry_counter = 0
        while retry_counter < RETRIES:
            self.ser.write(bytes('SOUR:VOLT ' + str(volt) + 'V\n', 'ascii'))
            time.sleep(CHECK_DELAY)
            self.ser.write(bytes('SOUR:VOLT?\n', 'ascii'))
            time.sleep(RESPONSE_WAIT)
            resp = self.ser.readline().decode('utf-8')

            if resp != '':
                if float(resp.split('V')[0]) == volt:
                    # print("Voltage set to:", float(resp.split('V')[0]), " V, ", volt, " V requested")
                    return 0
            print("Failed to set voltage, retrying. Response:", resp)
            retry_counter += 1
            time.sleep(WAITTIME)
        raise ConnectionError("After " + str(RETRIES) + " retries the voltage of the PS could not be set")

    def set_i(self, current, direction, RETRIES:int =2):
        """
        Turns on or off the output of the power supply and checks that this has taken affect will retry a set number of
        times, specified by RETRIES before raising an error
        output - int    1 or 0, where 0 turns the PS off and 1 turns the PS on)
        RETRIES - int   Optional arguement specifying the number of retries before raising an erro
        """
        retry_counter = 0
        while retry_counter < RETRIES:
            if direction == "SINK":
                self.ser.write(bytes('SINK:CURR ' + str(current) + '\n', 'ascii'))
                time.sleep(CHECK_DELAY)
                self.ser.write(bytes('SINK:CURR?\n', 'ascii'))
                time.sleep(RESPONSE_WAIT)
                resp = self.ser.readline().decode('utf-8')
                if resp != '':
                    if float(resp.split('A')[0]) == current:
                        # print("Current set to:", float(resp.split('A')[0]), " A")
                        return 0
                retry_counter += 1
                time.sleep(WAITTIME)
                print("Failed to set sink current, retrying. Response:", resp)
            elif direction == "SOURCE":
                self.ser.write(bytes('SOUR:CURR ' + str(current) + '\n', 'ascii'))
                time.sleep(CHECK_DELAY)
                self.ser.write(bytes('SOURCE:CURRENT?\n', 'ascii'))
                time.sleep(RESPONSE_WAIT)
                resp = self.ser.readline().decode('utf-8')
                if resp != '':
                    if float(resp.split('A')[0]) == current:
                        print("Current set to:", float(resp.split('A')[0]), " A")
                        return 0
                retry_counter += 1
                time.sleep(WAITTIME)
                print("Failed to set source current, retrying. Response:", resp)
            else:
                raise ValueError("direction must be SINK or SOURCE")
        raise ConnectionError("After " + str(RETRIES) + " retries the current of the PS could not be set")

    def query_output(self):
        self.ser.write(bytes('MEAS:VOLT?\n', 'ascii'))
        v = self.ser.readline().decode('utf-8')
        # Strip out the number
        v = float(v.split(' ')[0])
        self.ser.write(bytes('MEAS:CURR?\n', 'ascii'))
        i = self.ser.readline().decode('utf-8')
        i = float(i.split(' ')[0])
        self.ser.write(bytes('MEAS:POW?\n', 'ascii'))
        p = self.ser.readline().decode('utf-8')
        p = float(p.split(' ')[0])
        self.output['v'] = v
        self.output['i'] = i
        self.output['p'] = p
        print(self.output)

    def output_on(self, output: int, RETRIES:int =2):
        """
        Turns on or off the output of the power supply and checks that this has taken affect will retry a set number of
        times, specified by RETRIES before raising an error
        output - int    1 or 0, where 0 turns the PS off and 1 turns the PS on)
        RETRIES - int   Optional arguement specifying the number of retries before raising an erro
        """
        retry_counter = 0
        while retry_counter < RETRIES:
            if output == 1:
                self.ser.write(bytes('OUTP ON\n', 'ascii'))
                self.ser.readline().decode('utf-8')
            else:
                self.ser.write(bytes('OUTP OFF\n', 'ascii'))
                self.ser.readline().decode('utf-8')
            time.sleep(CHECK_DELAY)
            self.ser.write(bytes('OUTPUT?\n', 'ascii'))
            time.sleep(RESPONSE_WAIT)
            resp = self.ser.readline().decode('utf-8')
            if resp != '':
                if (resp == "ON\n" and output == 1) or (resp == "OFF\n" and output == 0):
                    return 0

            retry_counter += 1
        raise ConnectionError("After "+str(RETRIES) + " retries the output of the PS could not be set")

    def read_alarm(self):
        # Read status subregister condition byte
        self.ser.write(bytes('STAT:QUES?\n', 'ascii'))
        err = self.ser.readline().decode('utf-8')
        err = int(err)
        if err == 0:
            print('No alarm detected')
        else:
            print('Alarm detected, code: ' + str(err))
            self.ser.write(bytes('SYST:ERR?\n', 'ascii'))
            err_mess = self.ser.readline().decode('utf-8')
            print(err_mess)
        return [err, err_mess]

    def set_ovp_threshold(self, ovp):
        # TODO: Intermittently working. Seems to work best immediately after switch on
        self.ser.write(bytes('VOLT:PROT ' + str(ovp) + '\n', 'ascii'))

    def set_ocp_threshold(self, ocp):
        # TODO: Intermittently working. Seems to work best immediately after switch on
        self.ser.write(bytes('SOUR:CURR:PROT ' + str(ocp) + '\n', 'ascii'))


class PS2400B(EaDevice):
    def __init__(self, v_nom):
        """
        Init method for PS2400B device, takes v_nom as a parameter which is the power supply max voltage (either 42 or 84)
        """
        super().__init__()

        if v_nom != 42 and v_nom != 84:
            raise ValueError("Max voltage of the EA2400 series owned by PEG group is 42 or 84 V. Enter 42 or 84.")

        self.ser = serial.Serial()
        self.state = {}
        self.output = {'V_ps': 0, 'I_ps': 0}
        self.volt_nom = v_nom
        self.curr_nom = 10
        self.p_nom = 160

    def connect(self, port_string, brate=57600, parity=serial.PARITY_NONE, tout=2):
        """Opens up a serial connection to the device"""
        try:
            self.ser.port = port_string
            self.ser.baudrate = brate
            self.ser.parity = parity
            self.ser.timeout = tout
            self.ser.open()
            if self.ser.isOpen():
                print('Opened serial connection over port ', port_string)
            else:
                print('Failed to open serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to open serial connection.\nError:\n', se)

    def query_state_ps(self):
        SD = self.make_SD(2, 1, 1, 1)
        DN = 1  # device node is not necessarily 0. Needs to be set externally
        OBJ = 71  # Actual Values and Device State Object
        out_message = self.make_message(SD, DN, OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(11)
        data = self.decode_message(in_message)  # The order is >>Remote
        if data == 1:
            self.ser.write(out_message)
            in_message = self.ser.read(11)
            data = self.decode_message(in_message)
            if data == 1:
                raise ConnectionError("an error occured in EL9000.query_state_ps(), 1 retry attempted")
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            # print('WARNING: Unexpected data received. Data:\n',extra)
            # print ("Query state (PS) message: ", extra)
        # build byte 0 which checks whether the device is in remote mode
        self.state['remote'] = data[0] & 0b00000011  # 1 if device is in remote control mode (this is in byte 0)
        # build byte 1 which checks whether the device is on, in which controller state, whether it's tracking, and whether protections for overcurrent, overvoltage, overpower etc are on
        self.state['output_on'] = data[1] & 0b00000001  # 0 if the device is off
        controller_states = {0: 'CV',
                             2: 'CC'}
        self.state['controller_state'] = controller_states[(data[1] & 0b00000110) >> 1]
        self.state['tracking'] = (data[1] & 0b00001000) >> 3  # the data is sent to bit 3 in byte 1
        self.state['OVP active'] = (data[1] & 0b00010000) >> 4  # the data is sent to bit 4 in byte 1
        self.state['OCP active'] = (data[1] & 0b00100000) >> 5  # the data is sent to bit 5 in byte 1
        self.state['OPP active'] = (data[1] & 0b01000000) >> 6  # the data is sent to bit 6 in byte 1
        self.state['OTP active'] = (data[1] & 0b10000000) >> 7  # the data is sent to bit 7 in byte 1

        print(self.state)

    def set_remote(self, remote, channel):
        SD = self.make_SD(2, 1, 1, 3)
        OBJ = 54
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")  # Power supply control object
        # DN = self.select_Output_Channel()
        # A conditional statement may be required in this area to account for the
        # Device Node/Channel of the Power Supply

        if remote == 1:
            data = (0x10, 0x10)  # Mask:0x10, remote on:1
        elif remote == 0:
            data = (0x10, 0)  # Mask:0x10, remote off:0
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)  # This pyserial method writes to the output
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()

    def set_v(self, voltage, channel):  # applies to both the load and the power supply
        if voltage > self.volt_nom:
            print('WARNING: Requested voltage is greater than device maximum. Ignoring request.')
            return
        SD = self.make_SD(2, 1, 1, 3)
        OBJ = 50
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")
        v = int(25600 * voltage / self.volt_nom)
        data = (v >> 8, v & 0b0000000011111111)
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)
        #    print ("Set voltage (PS) message: ", extra)
        return v

    def set_i(self, current, channel):  # applies to both the load and the power supply
        if current > self.curr_nom:
            print('WARNING: Requested current is greater than device maximum. Ignoring request.')
            return
        SD = self.make_SD(2, 1, 1, 3)
        OBJ = 51
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")
        i = int(25600 * current / self.curr_nom)
        data = (i >> 8, i & 0b11111111)
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)
        #    print ("Set current (PS) message: ", extra)
        return i

    def output_on(self, output, channel):
        SD = self.make_SD(2, 1, 1, 3)
        OBJ = 54
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")  # Power supply control object
        if output == 1:
            data = (0x01, 0x01)  # Mask, output
        elif output == 0:
            data = (0x01, 0)  # Mask, output
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            # print('WARNING: Unexpected data received. Data:\n',extra)
            # print ("Turn on output (PS) message: ",extra)

    def set_remote(self, remote, channel):
        SD = self.make_SD(2, 1, 1, 3)
        OBJ = 54
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")  # Power supply control object
        # DN = self.select_Output_Channel()
        # A conditional statement may be required in this area to account for the
        # Device Node/Channel of the Power Supply

        if remote == 1:
            data = (0x10, 0x10)  # Mask:0x10, remote on:1
        elif remote == 0:
            data = (0x10, 0)  # Mask:0x10, remote off:0
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)  # This pyserial method writes to the output
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()

    def query_output(self, channel):
        SD = self.make_SD(6, 1, 1, 1)
        OBJ = 71
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")

            # A conditional statement is needed in this area to account for the fact that the device node may
        #  be 1 for the power supply

        out_message = self.make_message(SD, DN, OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(11)
        data = self.decode_message(in_message)

        if data == 1:
            print("Expected data length:", (SD & 0b00001111) + 1)
            print("in_message: ", in_message)
            self.ser.write(out_message)
            in_message = self.ser.read(11)
            data = self.decode_message(in_message)
            if data == 1:
                time.sleep(0.1)
                print("Expected data length:", (SD & 0b00001111) + 1)
                print("in_message: ", in_message)
                self.ser.write(out_message)
                in_message = self.ser.read(11)
                data = self.decode_message(in_message)
                if data == 1:
                    raise ConnectionError(
                        "Receiving an int from the power supply, 2 reattempt made in PS2400B.query_output")
        if type(data) is bytes:
            if len(data) < 2:
                print("Expected data length:", (SD & 0b00001111) + 1)
                print("in_message: ", in_message)
                self.ser.write(out_message)
                in_message = self.ser.read(11)
                data = self.decode_message(in_message)
                if len(data) < 2:
                    raise ConnectionError("Receiving less than two bytes frm from the power supply, 1 reattempt made")

        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)
        #    print ("Query output (PS) message: ", extra)
        try:
            self.output['V_ps'] = self.volt_nom * (data[2] * (16 ** 2)) / 25600
            self.output['I_ps'] = self.curr_nom * (data[4] * (16 ** 2)) / 25600
        except IndexError as e:
            print("data: ", data)
            print("datatype:", type(data))
            raise e
        self.output['V_ps'] = self.volt_nom * (data[2] * (16 ** 2)) / 25600
        self.output['I_ps'] = self.curr_nom * (data[4] * (16 ** 2)) / 25600

        return self.output
