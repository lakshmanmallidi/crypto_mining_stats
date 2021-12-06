import ConnectWiFi
import os
import machine
from power_module import pzem004t_v3
import socket


def isFileExists():
    try:
        open("idx", "r")
        return True
    except OSError:
        return False


def relayOn(relayPin):
    if(not isFileExists()):
        with open("idx", "w"):
            pass
    relayPin.off()


def relayOff(relayPin):
    if(isFileExists()):
        os.remove("idx")
    relayPin.on()


def getPinValue(relayPin):
    return relayPin.value()


os.dupterm(None, 1)
relayPin = machine.Pin(5, machine.Pin.OUT)
if(isFileExists()):
    relayOn(relayPin)
else:
    relayOff(relayPin)
ConnectWiFi.connect()
power_sensor = pzem004t_v3()
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('192.168.43.107', 12000))

while True:
    message, address = server_socket.recvfrom(1024)
    if(message.decode() == "getSensorData"):
        data = power_sensor.getDataAsJson()
        server_socket.sendto(data.encode(), address)
    elif(message.decode() == "relayOn"):
        relayOn(relayPin)
        server_socket.sendto("relay on".encode(), address)
    elif(message.decode() == "relayOff"):
        relayOff(relayPin)
        server_socket.sendto("relay off".encode(), address)
    elif(message.decode() == "getRelayState"):
        val = getPinValue(relayPin)
        server_socket.sendto(str(val).encode(), address)
    elif(message.decode() == "resetSensorEnergy"):
        data = power_sensor.resetEnergy()
        if(data == True):
            server_socket.sendto("reset success".encode(), address)
        else:
            server_socket.sendto("reset failed".encode(), address)
    elif(message.decode() == "rebootDevice"):
        server_socket.sendto("rebooting".encode(), address)
        machine.reset()
    else:
        server_socket.sendto(message, address)
