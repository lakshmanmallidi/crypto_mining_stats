from logging import debug
from flask import Flask, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from configparser import ConfigParser
from os import path
from socket import socket, AF_INET, SOCK_DGRAM, timeout
from time import time, sleep
from json import loads
from threading import Thread, Timer

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
host = config.get('mariadb', 'host')
user = config.get('mariadb', 'user')
passwd = config.get('mariadb', 'passwd')
database = config.get('mariadb', 'database')
sensor_ip = config.get('sensor', 'ip')
sensor_port = int(config.get('sensor', 'port'))
sampling_time = int(config.get('sensor', 'sampling_time'))
power_on_wait_time = int(config.get('sensor', 'power_on_wait'))
database_push_time = int(config.get('sensor', 'db_push_wait'))
max_voltage = int(config.get('power_validations', 'max_voltage'))
min_voltage = int(config.get('power_validations', 'min_voltage'))
max_current = int(config.get('power_validations', 'max_current'))

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mariadb+mariadbconnector://{}:{}@{}:3306/{}' \
    .format(user, passwd, host, database)
db = SQLAlchemy(app)
client_socket = socket(AF_INET, SOCK_DGRAM)
client_socket.settimeout(4)
last_push_time = time()


class stats(db.Model):
    voltage = db.Column(db.Float)
    current = db.Column(db.Float)
    power = db.Column(db.Float)
    energy = db.Column(db.Float)
    stat_datetime = db.Column(db.DateTime, primary_key=True)


class events(db.Model):
    event_sequence = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(15), nullable=False)
    event_log = db.Column(db.String(30))
    event_datetime = db.Column(db.DateTime, nullable=False)


def relayOn():
    client_socket.sendto("relayOn".encode(), (sensor_ip, sensor_port))
    client_socket.recvfrom(1024)
    db.session.add(events(event_type="relay on",
                          event_datetime=datetime.now()))
    db.session.commit()


def relayOff():
    client_socket.sendto("relayOff".encode(), (sensor_ip, sensor_port))
    client_socket.recvfrom(1024)
    db.session.add(events(event_type="relay off",
                          event_datetime=datetime.now()))
    db.session.commit()


def getRelayState():
    client_socket.sendto("getRelayState".encode(), (sensor_ip, sensor_port))
    message, _ = client_socket.recvfrom(1024)
    if(message.decode() == "1"):
        return False
    else:
        return True


def softSwitchOn():
    client_socket.sendto("relayOn".encode(), (sensor_ip, sensor_port))
    client_socket.recvfrom(1024)
    db.session.add(events(event_type="soft switch on",
                          event_datetime=datetime.now()))
    db.session.commit()


def softSwitchOff():
    client_socket.sendto("relayOff".encode(), (sensor_ip, sensor_port))
    client_socket.recvfrom(1024)
    db.session.add(events(event_type="soft switch off",
                          event_datetime=datetime.now()))
    db.session.commit()


def getPrevSftSwitchState():
    evnt = events.query.filter(events.event_type.startswith("soft switch")).order_by(
        events.event_datetime.desc()).first()
    if(evnt != None):
        if evnt.event_type == "soft switch on":
            return True
    return False


def getPrevPwrState():
    evnt = events.query.filter(events.event_type.startswith("power")).order_by(
        events.event_datetime.desc()).first()
    if(evnt != None):
        if evnt.event_type == "power on":
            return True
    return False


def powerOn():
    db.session.add(events(event_type="power on",
                   event_datetime=datetime.now()))
    db.session.commit()


def powerOff():
    db.session.add(events(event_type="power off",
                   event_datetime=datetime.now()))
    db.session.commit()


def getSensorData():
    client_socket.sendto("getSensorData".encode(),
                         (sensor_ip, sensor_port))
    message, _ = client_socket.recvfrom(1024)
    return loads(message.decode())


def storeSensorData(sensor_data):
    global last_push_time
    if(time()-last_push_time > database_push_time):
        db.session.add(stats(voltage=sensor_data["voltage"],
                             current=sensor_data["current"],
                             power=sensor_data["power"],
                             energy=sensor_data["energy"],
                             stat_datetime=datetime.now()))
        db.session.commit()
        last_push_time = time()


def validateSensorData(sensor_data):
    if(sensor_data["voltage"] > min_voltage and sensor_data["voltage"] < max_voltage):
        if(sensor_data["current"] < max_current):
            return {"status": True}
        else:
            return {"status": False, "event_type": "over current", "event_log": "current: "+str(sensor_data["current"])}
    else:
        if(sensor_data["voltage"] < min_voltage):
            return {"status": False, "event_type": "low voltage", "event_log": "voltage: "+str(sensor_data["voltage"])}
        else:
            return {"status": False, "event_type": "high voltage", "event_log": "voltage: "+str(sensor_data["voltage"])}


def energyReset():
    client_socket.sendto("resetSensorEnergy".encode(),
                         (sensor_ip, sensor_port))
    message, _ = client_socket.recvfrom(1024)
    db.session.add(events(event_type="energy reset",
                          event_datetime=datetime.now()))
    db.session.commit()
    return message.decode()


def sensorDataProcessing():
    prev_time = time()
    while True:
        if(time()-prev_time > sampling_time):
            try:
                sensor_data = getSensorData()
                if(not getPrevPwrState()):
                    powerOn()
                    sleep(power_on_wait_time)
                storeSensorData(sensor_data)
                sensorValidation = validateSensorData(sensor_data)
                if((not sensorValidation["status"]) and getRelayState()):
                    db.session.add(events(event_type=sensorValidation["event_type"],
                                          event_log=sensorValidation["event_log"],
                                          event_datetime=datetime.now()))
                    db.session.commit()
                    relayOff()

                if(sensorValidation["status"] and (not getRelayState())
                   and getPrevSftSwitchState()):
                    relayOn()

            except timeout:
                if(getPrevPwrState()):
                    powerOff()
            except Exception as e:
                print(e)
            prev_time = time()
        sleep(1)


class softSwitchController(Resource):
    def get(self, state):
        try:
            if(state == "on"):
                softSwitchOn()
            else:
                softSwitchOff()
            return {"status": "success"}, 200
        except timeout:
            return {"status": "device power off"}, 500
        except Exception:
            return {"status": "failed"}, 500


class getStateController(Resource):
    def get(self, type):
        try:
            if(type == "power"):
                return {"status": "success", "state": str(getPrevPwrState())}, 200
            elif(type == "relay"):
                return {"status": "success", "state": str(getRelayState())}, 200
            elif(type == "soft-switch"):
                return {"status": "success", "state": str(getPrevSftSwitchState())}, 200
            else:
                return {"status": "failed"}, 404
        except Exception:
            return {"status": "failed"}, 500


class energyResetController(Resource):
    def get(self):
        try:
            msg = energyReset()
            if(msg == "reset success"):
                return {"status": "success"}, 200
            else:
                return {"status": "error during reset"}, 500
        except timeout:
            return {"status": "device power off"}, 500
        except Exception:
            return {"status": "failed"}, 500


db.create_all()
api.add_resource(softSwitchController, '/soft-switch/<state>')
api.add_resource(getStateController, '/state/<type>')
api.add_resource(energyResetController, '/energy-reset')
Thread(target=app.run, args=()).start()
sensorDataProcessing()
