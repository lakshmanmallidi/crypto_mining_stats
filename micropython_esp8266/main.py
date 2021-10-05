import ConnectWiFi
import os
import machine
from power_module import pzem004t_v3
import socket


def relayOn(relayPin):
    relayPin.off()


def relayOff(relayPin):
    relayPin.on()


os.dupterm(None, 1)
relayPin = machine.Pin(5, machine.Pin.OUT)
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
    elif(message.decode() == "resetSensorEnergy"):
        data = power_sensor.resetEnergy()
        if(data == True):
            server_socket.sendto("reset success".encode(), address)
        else:
            server_socket.sendto("reset failed".encode(), address)
