import serial
import array
import time
import pdb

#This is the base class for all EaDevices, and contains common functionality
#implementing the RS232 communications
class EaDevice:
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'V_ps':0,'I_ps':0}
		#Nominal values of voltage (V) current (A) and power (W)
        self.volt_nom = 84
        self.curr_nom = 10
 
#Only applicable to  power supply 2000 series
        self.tracking=0
        self.DN=0                           #DN is the device node; 0 for channel 1 and 1 for channel 2
        self.OVP = 0                        # overvoltage threshold
        self.OVC = 0                        # overcurrent threshold

        
#Created the below function because the baud rate is different for the power supply and electronic load
    def connect_ps(self, port_string_ps, brate_ps=115200, parity_ps ='O', tout_ps = 2):
        """Opens up a serial connection to the Power Supply"""
        try:
            self.ser.port = port_string_ps
            self.ser.baudrate = brate_ps
            self.ser.parity = parity_ps
            self.ser.timeout = tout_ps
            self.ser.stopbits = 1   #investigate why this line was included, otherwise delete it
            self.ser.open()
            if self.ser.isOpen():
                print('Opened serial connection to the power supply over port ', port_string_ps)
            else:
                print('Failed to open serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to open serial connection.\nError:\n', se)    

    def disconnect(self):
        """Closes the serial connection to the device"""
        try:
            self.ser.close()
            if not self.ser.isOpen():
                print('Closed serial connection to power supply.')
            else:
                print('Failed to close serial connection')
        except serial.serialutil.SerialException as se:
            print('Error occurred while trying to close serial connection.\nError:\n', se)

    def select_Output_Channel(self):
        '''select the output channel of the power supply'''
        DN = 2
        _channel = str (input("Select power supply output. \nEnter a for output 1, and b for output 2:  "))
        if _channel == "a":
            return DN == 0                                             #Sets the channel to device node 1
        #elif (_channel == 1 and self.set_tracking(0)!=1):
        elif _channel == "b":
            return DN == 1 
        else :
            print("Selected device node is invalid")                                           #Sets the channel to device node 2

#Recall the above two methods only apply to the power supply

#This function was renamed to start_delimiter, and a conditional statement was created above it
    def make_SD(self, data_length, direction, broadcast, transmission_type):
        """Creates the start delimiter byte"""
        send_byte = (transmission_type << 6) | (broadcast << 5) | (direction << 4) | data_length-1
        return send_byte

#This function was renamed to 'make_telegram'
    def make_message(self, SD,device_node,obj,data=None):
        message = array.array('B',(SD,device_node,obj))                         #First part of message
        if data != None:
            message.extend(data)                                                #Add data to message
        CS = sum(message)
        message.extend((CS>>8,CS&255))                                          #Finish message with checksum
        return message

#This function was renamed to 'receive_telegram', excluding the sanity checks included here
    def decode_message(self, message):
        #Check that checksum is correct
        CS = sum(message[0:-2])
        if (CS>>8 != message[-2]) or (CS&255 != message[-1]):                  #limited in some ways. May break down if leading byte of checksum is not equal to 0
            print('WARNING: Received checksum does not match transmission')
            return 1 
        SD = message[0]
        data_length = (SD & 0b00001111) + 1
        direction = SD & 0b00010000                                             #direction (1 means from PC to device)
        broadcast = SD & 0b00100000
        t_type = (SD & 0b11000000)>>6                                           #Transmission type (00 reserved, 1 Query, 2 Query answer, 3 send data)
        DN = message[1]
        OBJ = message[2]
        data = message[3:-2]
        #Sanity checks
        if len(data) != data_length:
            print('WARNING: Received data does not match stated length')
            return 1
        return data

#This function was reproduced with some minor nomenclature variations. Revise
    def query_output_ps(self):
        SD = self.make_SD(6,1,1,1)
        OBJ = 71
        DN = 0

        #A conditional statement is needed in this area to account for the fact that the device node may
        #  be 1 for the power supply

        out_message = self.make_message(SD,DN,OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(11)
        data = self.decode_message(in_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)
        #    print ("Query output (PS) message: ", extra)
        self.output['V_ps'] = self.volt_nom * (data[2]*(16**2)) / 25600
        self.output['I_ps'] = self.curr_nom * (data[4]*(16**2)) / 25600
        print(self.output)

#The function below was renamed 'set_remote_control' and implemented in a similar fashion
    def set_remote(self, remote, channel):
        SD = self.make_SD(2,1,1,3)
        OBJ = 54
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")                                                             #Power supply control object
        #DN = self.select_Output_Channel()
        #A conditional statement may be required in this area to account for the 
        # Device Node/Channel of the Power Supply

        if remote == 1:
            data = (0x10, 0x10)                                                #Mask:0x10, remote on:1
        elif remote == 0:
            data = (0x10, 0)                                                   #Mask:0x10, remote off:0
        out_message = self.make_message(SD, DN, OBJ,data)
        self.ser.write(out_message)                                            #This pyserial method writes to the output
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            #print('WARNING: Unexpected data received. Data:\n',extra)
            #print ("Set remote (PS) message: ", extra)

    ### DEPRACTATED AFTER ADDING CHANNEL PARAMETER TO THE ABOVE FUNCTION
    # def set_remote_ps2(self, remote):
    #     SD = self.make_SD(2,1,1,3)
    #     OBJ = 54
    #     DN = 1                                                               #Power supply control object
    #     #DN = self.select_Output_Channel()
    #     #A conditional statement may be required in this area to account for the
    #     # Device Node/Channel of the Power Supply
    #
    #     if remote == 1:
    #         data = (0x10, 0x10)                                                #Mask:0x10, remote on:1
    #     elif remote == 0:
    #         data = (0x10, 0)                                                   #Mask:0x10, remote off:0
    #     out_message = self.make_message(SD, DN, OBJ,data)
    #     self.ser.write(out_message)                                            #This pyserial method writes to the output
    #     time.sleep(0.01)
    #     if self.ser.inWaiting() > 0:
    #         extra = self.ser.read_all()
    #         #print('WARNING: Unexpected data received. Data:\n',extra)
    #         #print ("Set remote (PS) message: ", extra)
        
    def output_on(self, output, channel):
        SD = self.make_SD(2,1,1,3)
        OBJ = 54
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")                                                               #Power supply control object
        if output == 1:
            data = (0x01, 0x01)                                                    #Mask, output
        elif output == 0:
            data = (0x01, 0)                                                    #Mask, output
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            #print('WARNING: Unexpected data received. Data:\n',extra)
            #print ("Turn on output (PS) message: ",extra)

#I created the below method to set tracking
    def set_tracking(self, tracking):
        SD = self.make_SD(2,1,1,3)
        OBJ = 54
        DN = 1                                                                     #Power supply control object
        if tracking == 1:
            data = (0xf0, 0xf0)                                                    #Mask, output
        elif tracking == 0:
            data = (0xf0, 0xe0)                                                    #Mask, output
        out_message = self.make_message(SD, DN, OBJ, data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n', extra)
            print (extra)
        return tracking

    def set_v(self,voltage, channel):                                                    #applies to both the load and the power supply
        if voltage > self.volt_nom:
            print('WARNING: Requested voltage is greater than device maximum. Ignoring request.')
            return
        SD = self.make_SD(2,1,1,3)
        OBJ = 50
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")
        v = int(25600 * voltage / self.volt_nom)
        data = (v>>8, v & 0b0000000011111111)
        out_message = self.make_message(SD,DN,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)
        #    print ("Set voltage (PS) message: ", extra)
        return v

    def set_i(self, current, channel):                                                    #applies to both the load and the power supply
        if current > self.curr_nom:
            print('WARNING: Requested current is greater than device maximum. Ignoring request.')
            return
        SD = self.make_SD(2,1,1,3)
        OBJ = 51
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")
        i = int(25600 * current / self.curr_nom)
        data = (i>>8, i & 0b11111111)
        out_message = self.make_message(SD,DN,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)
        #    print ("Set current (PS) message: ", extra)
        return i



    def set_OVP_threshold(self, channel):
        OVC = 1.2 * self.set_v(1,channel)
        SD = self.make_SD(2,1,0,3)
        OBJ = 38
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")
        OVP_thre = int(25600 * OVC / self.set_v(1,channel))
        data = (OVP_thre >>8, OVP_thre & 0b0000000011111111)
        out_message = self.make_message(SD,DN,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)
            print (extra)

    def set_OCP_threshold(self, channel):
        OVC = 1.2 * self.set_i(1,channel)
        SD = self.make_SD(2,1,0,3)
        OBJ = 39
        if channel == 1:
            DN = 0
        elif channel == 2:
            DN = 1
        else:
            raise ValueError("Not a valid channel")
        OVC_thre = int(25600 * OVC / self.set_i(1,channel))
        data = (OVC_thre >>8, OVC_thre & 0b0000000011111111)
        out_message = self.make_message(SD,DN,OBJ,data)
        self.ser.write(out_message)
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
        #    print('WARNING: Unexpected data received. Data:\n',extra)


#This class is for devices in the PS2000 family, and contains functions specific
#to the control of power supplies. Needs some work.
class PS2400B(EaDevice):
    def __init__(self):
        self.ser = serial.Serial()
        self.state = {}
        self.output = {'V_ps':0,'I_ps':0}
        self.volt_nom = 42
        self.curr_nom = 10
        self.p_nom = 160
        
    def query_state_ps(self):
        SD = self.make_SD(2,1,1,1)
        DN = 1                                                           #device node is not necessarily 0. Needs to be set externally
        OBJ = 71                                                                #Actual Values and Device State Object      
        out_message = self.make_message(SD,DN,OBJ)
        self.ser.write(out_message)
        in_message = self.ser.read(11)
        data = self.decode_message(in_message)                                  #The order is >>Remote
        time.sleep(0.01)
        if self.ser.inWaiting() > 0:
            extra = self.ser.read_all()
            #print('WARNING: Unexpected data received. Data:\n',extra)
            #print ("Query state (PS) message: ", extra)
#build byte 0 which checks whether the device is in remote mode
        self.state['remote']            = data[0] & 0b00000011                  #1 if device is in remote control mode (this is in byte 0)
#build byte 1 which checks whether the device is on, in which controller state, whether it's tracking, and whether protections for overcurrent, overvoltage, overpower etc are on
        self.state['output_on']         = data[1] & 0b00000001                  #0 if the device is off
        controller_states = {0:'CV',
                            2:'CC'}
        self.state['controller_state']  = controller_states[(data[1] & 0b00000110)>>1]
        self.state['tracking']          = (data[1] & 0b00001000)>>3             #the data is sent to bit 3 in byte 1
        self.state['OVP active']        = (data[1] & 0b00010000)>>4             #the data is sent to bit 4 in byte 1
        self.state['OCP active']        = (data[1] & 0b00100000)>>5             #the data is sent to bit 5 in byte 1
        self.state['OPP active']        = (data[1] & 0b01000000)>>6             #the data is sent to bit 6 in byte 1
        self.state['OTP active']        = (data[1] & 0b10000000)>>7             #the data is sent to bit 7 in byte 1

        print(self.state)

def main():
    ps1 = PS2400B()
    ps1.connect_ps('COM14')

    ps1.set_remote(1)
    ps1.set_tracking(1)
    ps1.output_on(1)                #this function works only when the PS is in remote mode
    ps1.query_state()               #verified
    ps1.set_v(4.40)                 #verified
    time.sleep(10)
    ps1.query_output()              #verified
    
    
    time.sleep(5)
 

    ps1.output_on(0)                #turn off output
    ps1.set_remote(0)
    ps1.disconnect()
