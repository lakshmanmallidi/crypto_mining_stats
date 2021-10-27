from datetime import datetime
from configparser import ConfigParser
from os import path, system
from socket import socket, AF_INET, SOCK_DGRAM, timeout
from time import time, sleep
from json import loads, dumps
from threading import Thread
import paho.mqtt.client as mqtt
from logger import get_logger

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
mqtt_host = config.get('mqtt_broker', 'host')
mqtt_user = config.get('mqtt_broker', 'user')
mqtt_passwd = config.get('mqtt_broker', 'password')
keep_alive_intervel = config.get('mqtt_broker', 'keep_alive_intervel')
sensor_ip = config.get('sensor', 'ip')
sensor_port = int(config.get('sensor', 'port'))
miner_ip = config.get('sensor', 'ip')
miner_port = int(config.get('sensor', 'port'))
sampling_time = int(config.get('sensor', 'sampling_time'))
database_push_time = int(config.get('sensor', 'db_push_wait'))
prev_pwr_state = True
client_socket = socket(AF_INET, SOCK_DGRAM)
client_socket.settimeout(4)
logr = get_logger(__file__)
is_running = True


def relayOn():
    client_socket.sendto("relayOn".encode(), (sensor_ip, sensor_port))
    client_socket.recvfrom(1024)
    client.publish("events", payload=dumps({"event": "relay on"}), qos=1)


def relayOff():
    client_socket.sendto("relayOff".encode(), (sensor_ip, sensor_port))
    client_socket.recvfrom(1024)
    client.publish("events", payload=dumps({"event": "relay off"}), qos=1)


def powerOn():
    global prev_pwr_state
    prev_pwr_state = True
    client.publish("state/power",
                   payload=dumps({"status": "on"}), qos=2, retain=True)
    client.publish("events", payload=dumps({"event": "power on"}), qos=1)


def powerOff():
    global prev_pwr_state
    prev_pwr_state = False
    client.publish("state/power",
                   payload=dumps({"status": "off"}), qos=2, retain=True)
    client.publish("events", payload=dumps({"event": "power off"}), qos=1)


def getSensorData():
    client_socket.sendto("getSensorData".encode(),
                         (sensor_ip, sensor_port))
    message, _ = client_socket.recvfrom(1024)
    return loads(message.decode())


def getMinerLog():
    miner_socket = socket()
    try:
        miner_socket.connect((miner_ip, miner_port))
        sleep(1)
        miner_socket.sendall("estats".encode())
        sleep(2)
        log = miner_socket.recv(10240).decode()
        return log
    except Exception as e:
        return e
    finally:
        miner_socket.close()


def publishData(sensor_data, miner_lg):
    data = {'voltage': sensor_data["voltage"], 'current': sensor_data["current"],
            'power': sensor_data["power"], 'energy': sensor_data["energy"],
            'miner_log': miner_lg}
    client.publish("stats", payload=dumps(data), qos=1)


def resetMiner():
    miner_socket = socket()
    try:
        miner_socket.connect((miner_ip, miner_port))
        sleep(1)
        miner_socket.sendall("ascset|0,reboot,0".encode())
        client.publish("events", payload=dumps(
            {"event": "reset miner"}), qos=1)
        client.publish("reset/status",
                       payload=dumps({"device": "miner", "status": "success"}), qos=2)
    except Exception as e:
        logr.warning(e)
        client.publish("reset/status",
                       payload=dumps({"device": "miner", "status": "failed"}), qos=2)
    finally:
        miner_socket.close()


def resetEnergy():
    client_socket.sendto("resetSensorEnergy".encode(),
                         (sensor_ip, sensor_port))
    message, _ = client_socket.recvfrom(1024)
    if(message.decode() == "reset success"):
        client.publish("events", payload=dumps(
            {"event": "reset energy"}), qos=1)
        client.publish("reset/status",
                       payload=dumps({"device": "energy", "status": "success"}), qos=2)
    else:
        client.publish("reset/status",
                       payload=dumps({"device": "energy", "status": "failed"}), qos=2)


def resetNodeMcu():
    client_socket.sendto("rebootDevice".encode(),
                         (sensor_ip, sensor_port))
    message, _ = client_socket.recvfrom(1024)
    if(message.decode() == "rebooting"):
        client.publish("events", payload=dumps(
            {"event": "reset nodemcu"}), qos=1)
        client.publish("reset/status",
                       payload=dumps({"device": "nodemcu", "status": "success"}), qos=2)
    else:
        client.publish("reset/status",
                       payload=dumps({"device": "nodemcu", "status": "failed"}), qos=2)


def resetPi():
    global is_running
    client.publish("events", payload=dumps(
        {"event": "reset pi"}), qos=1)
    client.publish("reset/status",
                   payload=dumps({"device": "pi", "status": "success"}), qos=2)
    client.publish("pi",
                   payload=dumps({"status": "offline"}), qos=2, retain=True)
    is_running = False
    client.disconnect()
    sleep(10)


def sensorDataProcessing():
    global prev_pwr_state, is_running
    prev_time = time()
    last_push_time = time()
    while is_running:
        if(time()-prev_time > sampling_time):
            try:
                sensor_data = getSensorData()
                if(not prev_pwr_state):
                    powerOn()
                if(time()-last_push_time > database_push_time):
                    miner_lg = getMinerLog()
                    publishData(sensor_data, miner_lg)
                    last_push_time = time()
            except timeout:
                if(prev_pwr_state):
                    powerOff()
            except Exception as e:
                print(e)
            prev_time = time()
        sleep(1)


def on_connect(client, userdata, flags, rc):
    if(rc == 0):
        client.publish("pi",
                       payload=dumps({"status": "online"}), qos=2, retain=True)
        client.subscribe("reset", qos=2)
        client.subscribe("state/relay", qos=2)
        #Thread(target=sensorDataProcessing, args=()).start()
    else:
        logr.warning("unable to connect to mqtt broker")


def on_message(client, userdata, msg):
    if(msg.topic == "reset"):
        payload = loads(msg.payload.decode())
        if(payload["device"] == "energy"):
            resetEnergy()
        elif(payload["device"] == "miner"):
            resetMiner()
        elif(payload["device"] == "nodemcu"):
            resetNodeMcu()
        elif(payload["device"] == "pi"):
            resetPi()
    elif(msg.topic == "state/relay"):
        payload = loads(msg.payload.decode())
        if(payload["status"] == "on"):
            relayOn()
        elif(payload["status"] == "off"):
            relayOff()


try:
    client = mqtt.Client(mqtt_user)
    client.username_pw_set(mqtt_user, mqtt_passwd)
    client.on_connect = on_connect
    client.on_message = on_message
    client.will_set("pi",
                    payload=dumps({"status": "offline"}), qos=2, retain=True)
    client.connect(host=mqtt_host, port=1883,
                   keepalive=int(keep_alive_intervel))
    client.loop_forever()
    if(is_running == False):
        system("reboot")
except Exception as e:
    logr.error(str(e))
