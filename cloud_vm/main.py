from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from configparser import ConfigParser
from os import path
from json import loads
import paho.mqtt.client as mqtt

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
host = config.get('mariadb', 'host')
user = config.get('mariadb', 'user')
passwd = config.get('mariadb', 'passwd')
database = config.get('mariadb', 'database')
mqtt_host = config.get('mqtt_broker', 'host')
mqtt_user = config.get('mqtt_broker', 'user')
mqtt_passwd = config.get('mqtt_broker', 'password')
keep_alive_intervel = config.get('mqtt_broker', 'keep_alive_intervel')
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mariadb+mariadbconnector://{}:{}@{}:3306/{}' \
    .format(user, passwd, host, database)
client_user = "cloud_vm"
db = SQLAlchemy(app)


class stats(db.Model):
    voltage = db.Column(db.Float)
    current = db.Column(db.Float)
    power = db.Column(db.Float)
    energy = db.Column(db.Float)
    miner_log = db.Column(db.Text)
    stat_datetime = db.Column(db.DateTime, primary_key=True)


class events(db.Model):
    event_sequence = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(15), nullable=False)
    event_log = db.Column(db.String(30))
    event_datetime = db.Column(db.DateTime, nullable=False)


def on_connect(client, userdata, flags, rc):
    if(rc == 0):
        client.subscribe("events", qos=2)
        client.subscribe("stats", qos=2)
    else:
        print("unable to connect to mqtt broker")


def on_message(client, userdata, msg):
    try:
        if(msg.topic == "events"):
            payload = loads(msg.payload.decode())
            db.session.add(events(event_type=payload["event"],
                                  event_datetime=datetime.now()))
            db.session.commit()
        elif(msg.topic == "stats"):
            sensor_data = loads(msg.payload.decode())
            db.session.add(stats(voltage=sensor_data["voltage"],
                                 current=sensor_data["current"],
                                 power=sensor_data["power"],
                                 energy=sensor_data["energy"],
                                 miner_log=sensor_data["miner_log"],
                                 stat_datetime=datetime.now()))
            db.session.commit()
    except Exception as e:
        print(str(e))


try:
    db.create_all()
    client = mqtt.Client(client_user)
    client.username_pw_set(mqtt_user, mqtt_passwd)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host=mqtt_host, port=1883,
                   keepalive=int(keep_alive_intervel))
    client.loop_forever()
except Exception as e:
    print(str(e))
