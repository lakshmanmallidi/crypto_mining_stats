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
from threading import Thread

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'db.ini'))
host = config.get('mariadb', 'host')
user = config.get('mariadb', 'user')
passwd = config.get('mariadb', 'passwd')
database = config.get('mariadb', 'database')

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mariadb+mariadbconnector://{}:{}@{}:3306/{}' \
    .format(user, passwd, host, database)
db = SQLAlchemy(app)

power_state = False
relay_state = False
sensor_ip = "192.168.43.107"
sensor_port = 12000
sensor_loop_time = 5
power_on_wait_time = 300  # set later to 300
database_push_time = 60


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


def validateSensorData(sensor_date):
    return {"status": True}


def sensorDataProcessing():
    global power_state, relay_state
    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.settimeout(4)
    prev_time = time()
    last_push_time = time()
    while True:
        if(time()-prev_time > sensor_loop_time):
            client_socket.sendto("getSensorData".encode(),
                                 (sensor_ip, sensor_port))
            try:
                message, _ = client_socket.recvfrom(1024)
                sensor_data = loads(message.decode())
                if(power_state == False):
                    db.session.add(events(event_type="power on",
                                          event_datetime=datetime.now()))
                    db.session.commit()
                    sleep(power_on_wait_time)
                    client_socket.sendto("getSensorData".encode(),
                                         (sensor_ip, sensor_port))
                    client_socket.recvfrom(1024)
                    power_state = True

                if(time()-last_push_time > database_push_time):
                    db.session.add(stats(voltage=sensor_data["voltage"],
                                         current=sensor_data["current"],
                                         power=sensor_data["power"],
                                         energy=sensor_data["energy"],
                                         stat_datetime=datetime.now()))
                    db.session.commit()
                    last_push_time = time()

                sensorValidation = validateSensorData(sensor_data)
                # can add network check here
                if(sensorValidation["status"]):
                    if(relay_state == False):
                        client_socket.sendto(
                            "relayOn".encode(), (sensor_ip, sensor_port))
                        client_socket.recvfrom(1024)
                        relay_state = True
                        db.session.add(events(event_type="relay on",
                                              event_datetime=datetime.now()))
                        db.session.commit()
                else:
                    if(relay_state == True):
                        client_socket.sendto(
                            "relayOff".encode(), (sensor_ip, sensor_port))
                        client_socket.recvfrom(1024)
                        relay_state = False
                        db.session.add(events(event_type=sensorValidation["event_type"],
                                              event_log=sensorValidation["event_log"],
                                              event_datetime=datetime.now()))
                        db.session.commit()

            except timeout:
                if(power_state == True):
                    power_state = False
                    relay_state = False
                    db.session.add(events(event_type="power off",
                                          event_datetime=datetime.now()))
                    db.session.commit()
            prev_time = time()
        sleep(sensor_loop_time-1)


db.create_all()
Thread(target=app.run, args=()).start()
sensorDataProcessing()

'''class triggers(Resource):
    def post(self):
        data = request.get_json()
        try:
            db.session.add(manual_triggers(trigger_type=data["trigger_type"],
                                           trigger_datetime=datetime.now()))
            db.session.commit()
            return {"status": "success"}, 200
        except Exception as e:
            print(e)
            return {"status": "failed"}, 500


class events(Resource):
    def post(self):
        data = request.get_json()
        try:
            db.session.add(power_events(event_type=data["event_type"], event_log=data["event_log"],
                                        event_datetime=datetime.now()))
            db.session.commit()
            return {"status": "success"}, 200
        except Exception:
            return {"status": "failed"}, 500


class statistics(Resource):
    def post(self):
        data = request.get_json()
        try:
            db.session.add(power_stats(voltage=data["voltage"], current=data["current"],
                                       power=data["power"], energy=data["energy"],
                                       stat_datetime=datetime.now()))
            db.session.commit()
            return {"status": "success"}, 200
        except Exception as e:
            print(e)
            return {"status": "failed"}, 500


api.add_resource(powerStatistics, '/power_stat/')
api.add_resource(powerEvents, '/power_event/')
api.add_resource(manualTriggers, '/manual_trigger/')

if __name__ == '__main__':
    app.run(debug=True)
    db.create_all()'''
