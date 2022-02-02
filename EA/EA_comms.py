import serial
import array
import time
import pdb

#This is the base class for the PSI8000 and EL9000 EaDevices, and contains 
#common functionality implementing the RS232 communications
class EaDevice:
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'v':0,'i':0,'p':0}
        self.volt_nom = 720
        self.curr_nom = 15
        self.p_nom = 3000
        
    def connect(self,port_string,brate=57600,parity='O',tout=2):
        """Opens up a serial connection to the device"""
        try:
            self.ser.port = port_string
            self.ser.baudrate = brate
            self.ser.parity = parity
            self.ser.timeout=tout
            self.ser.open()
            if self.ser.isOpen():
                print('Opened serial connection over port ',port_string)
            else:
                print('Failed to open serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to open serial connection.\nError:\n',se)

    def disconnect(self):
        """Closes the serial connection to the device"""
        try:
            self.ser.close()
            if not self.ser.isOpen():
                print('Closed serial connection to device.')
            else:
                print('Failed to close serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to close serial connection.\nError:\n',se)

    def get_dev_info(self):
        """Not Implemented. Queries device to get factory information from it"""
        
    def make_SD(self,data_length,direction,broadcast,transmission_type):
        """Creates the start delimiter byte"""
        send_byte = (transmission_type << 6) | (broadcast << 5) | (direction << 4) | data_length-1
        return send_byte

    def make_message(self,SD,device_node,obj,data=None):
        message = array.array('B',(SD,device_node,obj)) #First part of message
        if data != None:
            message.extend(data)    #Add data to message
        CS = sum(message)
        message.extend((CS>>8,CS&255))  #Finish message with checksum
        return message

    def decode_message(self,message):
        #Check that checksum is correct
        CS = sum(message[0:-2])
        if (CS>>8 != message[-2]) or (CS&255 != message[-1]):
            print('WARNING: Received checksum does not match transmission')
            return 1 
        SD = message[0]
        data_length = (SD & 0b00001111) + 1
        direction = SD & 0b00010000    #direction (1 means from PC to device)
        broadcast = SD & 0b00100000
        t_type = (SD & 0b11000000)>>6 #Transmission type (00 reserved, 1 Query, 2 Query answer, 3 send data)
        DN = message[1]
        OBJ = message[2]
        data = message[3:-2]
        #Sanity checks
        if len(data) != data_length:
            print('WARNING: Received data does not match stated length')
            return 1
        return data

    def query_output(self):
        SD = self.make_SD(6,1,1,1)
        OBJ = 71
        out_message = self.make_message(SD,1,OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(11)
        data = self.decode_message(in_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n',extra)
        self.output['v'] = self.volt_nom * (data[0]*(16**2) + data[1]) / 25600
        self.output['i'] = self.curr_nom * (data[2]*(16**2) + data[3]) / 25600
        self.output['p'] = self.p_nom * (data[4]*(16**2) + data[5]) / 25600
        print(self.output)

    def set_remote(self,remote):
        SD = self.make_SD(2,1,1,3)
        OBJ = 54    #Power supply control object
        if remote == 1:
            data = (0x10, 0x10)    #Mask:0x10, remote on:1
        elif remote == 0:
            data = (0x10, 0)    #Mask:0x10, remote off:0
        out_message = self.make_message(SD,1,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n',extra)

    def output_on(self,output):
        SD = self.make_SD(2,1,1,3)
        OBJ = 54    #Power supply control object
        if output == 1:
            data = (0x01, 1)    #Mask, output
        elif output == 0:
            data = (0x01, 0)    #Mask, output
        out_message = self.make_message(SD,1,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n',extra)

    def set_v(self,voltage):
        if voltage > self.volt_nom:
            print('WARNING: Requested voltage is greater than device maximum. Ignoring request.')
            return
        SD = self.make_SD(2,1,0,3)
        OBJ = 50
        v = int(25600 * voltage / self.volt_nom)
        data = (v>>8, v & 0b0000000011111111)
        out_message = self.make_message(SD,1,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n',extra)

    def set_i(self,current):
        if current > self.curr_nom:
            print('WARNING: Requested current is greater than device maximum.')# Ignoring request.')
            #return
        SD = self.make_SD(2,1,0,3)
        OBJ = 51
        i = int(25600 * current / self.curr_nom)
        data = (i>>8, i & 0b11111111)
        out_message = self.make_message(SD,1,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n',extra)

    def set_p(self,power):
        if power > self.p_nom:
            print('WARNING: Requested power is greater than device maximum. Ignoring request.')
            return
        SD = self.make_SD(2,1,0,3)
        OBJ = 52
        p = int(25600 * power / self.p_nom)
        data = (p>>8, p & 0b0000000011111111)
        out_message = self.make_message(SD,1,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n',extra)

#This class is for devices in the PSI8000 family, and contains functions specific
#to the control of power supplies
class PSI8000(EaDevice):
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'v':0,'i':0,'p':0}
        self.volt_nom = 720
        self.curr_nom = 15
        self.p_nom = 3000
        
    def query_state(self):
        SD = self.make_SD(2,1,1,1)
        DN = 0      #device node
        OBJ = 70    #Status object      
        out_message = self.make_message(SD,DN,OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(7)
        data = self.decode_message(in_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n',extra)
        self.state['remote']            = data[0] & 0b00000011   #1 if device is in remote control mode
        self.state['analogue_control']  = data[0] & 32 #controlled by analogue interface?
        self.state['func_man_active']   = data[0] & 64  #function manager
        self.state['output_on']         = data[1] & 0b00000001
        self.state['contr_state']       = data[1] & 0b00000110  #Controller state (0:CV 1:CR 2:CC 3:CP)
        self.state['alarm_active']      = data[1] & 16
        print(self.state)

#This class is for electronic loads in the EL9000 family.
class EL9000(EaDevice):
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'v':0,'i':0,'p':0}
        self.volt_nom = 750
        self.curr_nom = 25
        self.p_nom = 2400
        
    def query_state(self):
        SD = self.make_SD(2,1,1,1)
        DN = 0      #device node
        OBJ = 70    #Status object      
        out_message = self.make_message(SD,DN,OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(7)
        data = self.decode_message(in_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            print('WARNING: Unexpected data received. Data:\n',extra)
        self.state['remote']            = data[0] & 0b00000011   #1 if device is in remote control mode
        self.state['input_on']         = data[1] & 0b00000001
        controller_states = {0:'CV',
                            1:'CR',
                            2:'CC',
                            3:'CP'}
        self.state['controller_state'] = controller_states[(data[1] & 0b00000110)>>1]
        regulation_modes = {0:'CR1',
                            1:'CR2',
                            2:'CP',
                            3:'CC',
                            4:'CP'}
        self.state['chosen_regulation_mode'] = regulation_modes[(data[1] & 0b00111000)>>3]
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

    #Creating a copy of the functions named 'output' to 'input', as this makes more sense for load
    def input_on(self,on):
        self.output_on(on)

    def query_input(self):
        self.query_output()

    
# This class is for the PSB9000 bidirectional DC supply/load, using SCPI comms
class PSB9000():
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'v':0,'i':0,'p':0}
        self.volt_nom = 750
        self.curr_nom = 60
        self.p_nom = 15000

    def connect(self,port_string,brate=57600,parity='O',tout=2):
        """Opens up a serial connection to the device"""
        try:
            self.ser.port = port_string
            self.ser.baudrate = brate
            self.ser.parity = parity
            self.ser.timeout=tout
            self.ser.open()
            if self.ser.isOpen():
                print('Opened serial connection over port ',port_string)
                self.ser.write(bytes('*IDN?\n','ascii'))
                idn = self.ser.readline().decode('utf-8')
                print(idn)
            else:
                print('Failed to open serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to open serial connection.\nError:\n',se)

    def disconnect(self):
        """Closes the serial connection to the device"""
        try:
            self.ser.close()
            if not self.ser.isOpen():
                print('Closed serial connection to device.')
            else:
                print('Failed to close serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to close serial connection.\nError:\n',se)

    def set_remote(self,remote):
        if remote == 1:
            self.ser.write(bytes('SYST:LOCK 1\n','ascii'))
        elif remote == 0:
            self.ser.write(bytes('SYST:LOCK 0\n','ascii'))
            
    def set_v(self):
        return

    def set_i(self,current):
        self.ser.write(bytes('SINK:CURR '+str(current)+'\n','ascii'))

    def query_output(self):
        self.ser.write(bytes('MEAS:VOLT?\n','ascii'))
        v = self.ser.readline().decode('utf-8')
        # Strip out the number
        v = float(v.split(' ')[0])
        self.ser.write(bytes('MEAS:CURR?\n','ascii'))
        i = self.ser.readline().decode('utf-8')
        i = float(i.split(' ')[0])
        self.ser.write(bytes('MEAS:POW?\n','ascii'))
        p = self.ser.readline().decode('utf-8')
        p = float(p.split(' ')[0])
        self.output['v'] = v
        self.output['i'] = i
        self.output['p'] = p
        print(self.output)

    def output_on(self,output):
        if output == 1:
            self.ser.write(bytes('OUTP ON\n','ascii'))
        else:
            self.ser.write(bytes('OUTP OFF\n','ascii'))

    def read_alarm(self):
        #Read status subregister condition byte
        self.ser.write(bytes('STAT:QUES?\n','ascii'))
        err = self.ser.readline().decode('utf-8')
        err = int(err)
        if err == 0:
            print('No alarm detected')
        else:
            print('Alarm detected, code: '+str(err))
            self.ser.write(bytes('SYST:ERR?\n','ascii'))
            err_mess = self.ser.readline().decode('utf-8')
            print(err_mess)
