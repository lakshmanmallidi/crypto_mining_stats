from configparser import ConfigParser
from os import path, system, remove
from socket import socket, error
from time import sleep
from logger import get_logger

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
miner_ip = config.get('miner', 'ip')
miner_port = int(config.get('miner', 'port'))
logr = get_logger(__file__)


def pingMiner():
    response = system("ping -c 2 " + miner_ip + " > /dev/null")
    if(response == 0):
        return True
    else:
        return False


def getMinerLog():
    miner_socket = socket()
    try:
        miner_socket.connect((miner_ip, miner_port))
        sleep(1)
        miner_socket.sendall("estats".encode())
        sleep(2)
        log = miner_socket.recv(10240).decode()
        return log
    except error as e:
        return "miner powered off"
    except Exception as e:
        logr.warning("getMinerLog:|:"+str(e))
        return "error in reading miner log"
    finally:
        miner_socket.close()


def resetMiner():
    miner_socket = socket()
    try:
        miner_socket.connect((miner_ip, miner_port))
        sleep(1)
        miner_socket.sendall("ascset|0,reboot,0".encode())
        return True
    except Exception as e:
        logr.warning("miner shutdown ,"+str(e))
        return False
    finally:
        miner_socket.close()
