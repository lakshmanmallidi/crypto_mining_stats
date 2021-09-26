from machine import UART
from time import sleep


class pzem004t_v3():
    voltage = [0x01, 0x04, 0x00, 0x00, 0x00, 0x01, 0x31, 0xCA]
    current = [0x01, 0x04, 0x00, 0x01, 0x00, 0x02, 0x20, 0x0B]
    power = [0x01, 0x04, 0x00, 0x03, 0x00, 0x02, 0x81, 0xCB]
    energy = [0x01, 0x04, 0x00, 0x05, 0x00, 0x02, 0x61, 0xCA]
    frequency = [0x01, 0x04, 0x00, 0x07, 0x00, 0x01, 0x80, 0x0B]
    power_factor = [0x01, 0x04, 0x00, 0x08, 0x00, 0x01, 0xB0, 0x08]

    def __init__(self):
        self.uart = UART(0, 9600, timeout=1)

    def getVoltage(self):
        self.uart.write(bytes(pzem004t_v3.voltage))
        sleep(0.1)
        data = self.uart.read()
        if(data != None):
            voltage = 0.1*((256*data[3])+data[4])
            return voltage
        return None

    def getCurrent(self):
        self.uart.write(bytes(pzem004t_v3.current))
        sleep(0.1)
        data = self.uart.read()
        if(data != None):
            current = 0.001 * \
                ((256*data[3])+data[4]+(1024*data[5])+(512*data[6]))
            return current
        return None

    def getPower(self):
        self.uart.write(bytes(pzem004t_v3.power))
        sleep(0.1)
        data = self.uart.read()
        if(data != None):
            power = 0.1*((256*data[3])+data[4] + (1024*data[5])+(512*data[6]))
            return power
        return None

    def getEnergy(self):
        self.uart.write(bytes(pzem004t_v3.energy))
        sleep(0.1)
        data = self.uart.read()
        if(data != None):
            energy = (256*data[3])+data[4]+(1024*data[5])+(512*data[6])
            return energy
        return None

    def getFrequency(self):
        self.uart.write(bytes(pzem004t_v3.frequency))
        sleep(0.1)
        data = self.uart.read()
        if(data != None):
            frequency = 0.1*((256*data[3])+data[4])
            return frequency
        return None

    def getPowerFactor(self):
        self.uart.write(bytes(pzem004t_v3.power_factor))
        sleep(0.1)
        data = self.uart.read()
        if(data != None):
            power_factor = 0.01*((256*data[3])+data[4])
            return power_factor
        return None

    def getDataAsDict(self):
        return {"voltage": self.getVoltage(), "current": self.getCurrent(),
                "power": self.getPower(), "energy": self.getEnergy(),
                "freqency": self.getFrequency(), "power_factor": self.getPowerFactor()}
