from datetime import datetime
from configparser import ConfigParser
from os import path, system, remove
from time import time, sleep
from json import loads, dumps
from threading import Thread
import paho.mqtt.client as mqtt
from logger import get_logger
from sensor import relayOff, relayOn, resetEnergy, resetNodeMcu, getSensorData, pingNodeMcu
from miner import resetMiner, getMinerLog, pingMiner
from socket import timeout
from timerThread import RepeatedTimer

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
mqtt_host = config.get('mqtt_broker', 'host')
mqtt_user = config.get('mqtt_broker', 'user')
mqtt_passwd = config.get('mqtt_broker', 'password')
keep_alive_intervel = config.get('mqtt_broker', 'keep_alive_intervel')
sampling_time = int(config.get('sensor', 'sampling_time'))
database_push_time = int(config.get('sensor', 'db_push_wait'))
logr = get_logger(__file__)
is_running = True
sensor_data = {"voltage": 220, "current": 16, "power": 3200, "energy": 100}


def checkPrevPwrState():
    if(path.isfile("power_off.ind")):
        return False
    else:
        return True


def powerOn():
    remove("power_off.ind")
    client.publish("state/power", payload=dumps(
        {"status": "on", "datetime": str(datetime.now().replace(microsecond=0))}),
        qos=2, retain=True)
    client.publish("events", payload=dumps(
        {"event": "power on", "datetime": str(datetime.now().replace(microsecond=0))}),
        qos=2)


def powerOff():
    with open("power_off.ind", "w"):
        pass
    client.publish("state/power", payload=dumps(
        {"status": "off", "datetime": str(datetime.now().replace(microsecond=0))}),
        qos=2, retain=True)
    client.publish("events", payload=dumps(
        {"event": "power off", "datetime": str(datetime.now().replace(microsecond=0))}),
        qos=2)


def publishData(sensor_data, miner_lg):
    data = {'voltage': sensor_data["voltage"], 'current': sensor_data["current"],
            'power': sensor_data["power"], 'energy': sensor_data["energy"],
            'miner_log': miner_lg, "datetime": str(datetime.now().replace(microsecond=0))}
    client.publish("stats", payload=dumps(data), qos=2)


def resetPi():
    global is_running
    client.publish("events", payload=dumps(
        {"event": "reset pi"}), qos=2)
    client.publish("reset/status", payload=dumps(
        {"device": "pi", "status": "success",
         "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
    client.publish("pi",
                   payload=dumps({"status": "offline"}), qos=2, retain=True)
    is_running = False
    sensor_thread.stop()
    pwr_thread.stop()
    client.disconnect()
    sleep(10)


def energyResetCntrl():
    status = resetEnergy()
    if(status == "reset success"):
        client.publish("events", payload=dumps(
            {"event": "reset energy",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
        client.publish("reset/status", payload=dumps(
            {"device": "energy", "status": "success",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
    elif(status == "timeout"):
        client.publish("reset/status", payload=dumps(
            {"device": "energy", "status": "power off",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
    else:
        client.publish("reset/status", payload=dumps(
            {"device": "energy", "status": "failed",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)


def minerResetCntrl():
    status = resetMiner()
    if(status == True):
        client.publish("events", payload=dumps(
            {"event": "reset miner",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
        client.publish("reset/status", payload=dumps(
            {"device": "miner", "status": "success",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
    else:
        client.publish("reset/status", payload=dumps(
            {"device": "miner", "status": "failed",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)


def nodeMcuResetCntrl():
    status = resetNodeMcu()
    if(status == "rebooting"):
        client.publish("events", payload=dumps(
            {"event": "reset nodemcu",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
        client.publish("reset/status", payload=dumps(
            {"device": "nodemcu", "status": "success",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
    elif(status == "timeout"):
        client.publish("reset/status", payload=dumps(
            {"device": "energy", "status": "power off",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)
    else:
        client.publish("reset/status", payload=dumps(
            {"device": "nodemcu", "status": "failed",
                "datetime": str(datetime.now().replace(microsecond=0))}), qos=2)


def relayOnCntrl():
    status = relayOn()
    if(status):
        client.publish("events", payload=dumps(
            {"event": "relay on", "datetime": str(datetime.now())}), qos=2)


def relayOffCntrl():
    status = relayOff()
    if(status):
        client.publish("events", payload=dumps(
            {"event": "relay off", "datetime": str(datetime.now())}), qos=2)


def sensorDataThread():
    try:
        miner_lg = "miner powered off"
        if(checkPrevPwrState()):
            miner_lg = getMinerLog()
            publishData(sensor_data, miner_lg)
    except Exception as e:
        logr.error("sensorDataThread:|:"+str(e))


def powerInfoThread():
    global sensor_data
    try:
        sensor_data = getSensorData()
        if(not checkPrevPwrState()):
            powerOn()
    except timeout:
        if(not (pingNodeMcu() or pingMiner())):
            if(checkPrevPwrState()):
                powerOff()
    except Exception as e:
        logr.error("powerInfoThread:|:"+str(e))


def on_connect(client, userdata, flags, rc):
    if(rc == 0):
        client.publish("pi",
                       payload=dumps({"status": "online"}), qos=2, retain=True)
        client.subscribe("reset", qos=2)
        client.subscribe("state/relay", qos=2)
        pwr_thread.start()
        sensor_thread.start()
    else:
        logr.warning("unable to connect to mqtt broker")


def on_message(client, userdata, msg):
    try:
        if(msg.topic == "reset"):
            payload = loads(msg.payload.decode())
            if(payload["device"] == "energy"):
                energyResetCntrl()
            elif(payload["device"] == "miner"):
                minerResetCntrl()
            elif(payload["device"] == "nodemcu"):
                nodeMcuResetCntrl()
            elif(payload["device"] == "pi"):
                resetPi()
        elif(msg.topic == "state/relay"):
            payload = loads(msg.payload.decode())
            if(payload["status"] == "on"):
                relayOnCntrl()
            elif(payload["status"] == "off"):
                relayOffCntrl()
    except Exception as e:
        logr.error("on_message:|:"+str(e))


try:
    pwr_thread = RepeatedTimer(sampling_time, powerInfoThread)
    sensor_thread = RepeatedTimer(database_push_time, sensorDataThread)
    client = mqtt.Client("raspi")
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
