from socket import socket, AF_INET, SOCK_DGRAM, timeout
from configparser import ConfigParser
from os import path, system
from json import loads
from logger import get_logger

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
sensor_ip = config.get('sensor', 'ip')
sensor_port = int(config.get('sensor', 'port'))

client_socket = socket(AF_INET, SOCK_DGRAM)
client_socket.settimeout(20)
logr = get_logger(__file__)


def relayOn():
    try:
        client_socket.sendto("relayOn".encode(), (sensor_ip, sensor_port))
        client_socket.recvfrom(1024)
        return True
    except timeout:
        logr.warning("nodemcu powered off")
        return False


def relayOff():
    try:
        client_socket.sendto("relayOff".encode(), (sensor_ip, sensor_port))
        client_socket.recvfrom(1024)
        return True
    except timeout:
        logr.warning("nodemcu powered off")
        return False


def getSensorData():
    client_socket.sendto("getSensorData".encode(),
                         (sensor_ip, sensor_port))
    message, _ = client_socket.recvfrom(1024)
    return loads(message.decode())


def pingNodeMcu():
    response = system("ping -c 2 " + sensor_ip + " > /dev/null")
    if(response == 0):
        return True
    else:
        return False


def resetEnergy():
    try:
        client_socket.sendto("resetSensorEnergy".encode(),
                             (sensor_ip, sensor_port))
        message, _ = client_socket.recvfrom(1024)
        return message.decode()
    except timeout:
        return "timeout"


def resetNodeMcu():
    try:
        client_socket.sendto("rebootDevice".encode(),
                             (sensor_ip, sensor_port))
        message, _ = client_socket.recvfrom(1024)
        return message.decode()
    except timeout:
        return "timeout"
