from datetime import datetime
from configparser import ConfigParser
from os import path, replace, statvfs_result
from json import loads
import paho.mqtt.client as mqtt
from time import sleep
import peewee

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
host = config.get('mariadb', 'host')
user = config.get('mariadb', 'user')
passwd = config.get('mariadb', 'passwd')
database = config.get('mariadb', 'database')
database_push_time = int(config.get('mariadb', 'db_push_wait'))-5
mqtt_host = config.get('mqtt_broker', 'host')
mqtt_user = config.get('mqtt_broker', 'user')
mqtt_passwd = config.get('mqtt_broker', 'password')
keep_alive_intervel = config.get('mqtt_broker', 'keep_alive_intervel')
client_user = "cloud_vm"
db = peewee.MySQLDatabase(database, user=user, password=passwd,
                          host=host, port=3306,autoconnect=False)


class stats(peewee.Model):
    voltage = peewee.FloatField()
    current = peewee.FloatField()
    power = peewee.FloatField()
    energy = peewee.FloatField()
    miner_log = peewee.TextField()
    stat_datetime = peewee.DateTimeField(primary_key=True)

    class Meta:
        database = db
        db_table = 'stats'


class events(peewee.Model):
    event_sequence = peewee.BigAutoField(primary_key=True)
    event_type = peewee.TextField()
    event_log = peewee.TextField(null=True)
    event_datetime = peewee.DateTimeField()

    class Meta:
        database = db
        db_table = 'events'


def checkRecordExistsUnderTime(date_time):
    try:
        last_insertion_date = stats.select().order_by(
            stats.stat_datetime.desc()).get().stat_datetime
        if((date_time-last_insertion_date).total_seconds() > database_push_time):
            return False
        else:
            return True
    except peewee.DoesNotExist as e:
        return False


def on_connect(client, userdata, flags, rc):
    if(rc == 0):
        client.subscribe("events", qos=2)
        client.subscribe("stats", qos=2)
    else:
        print("unable to connect to mqtt broker")


def on_message(client, userdata, msg):
    db.connect(reuse_if_open=True)
    try:
        if(msg.topic == "events"):
            payload = loads(msg.payload.decode())
            events.create(event_type=payload["event"],
                          event_datetime=datetime.strptime(payload['datetime'], "%Y-%m-%d %H:%M:%S")).save()
        elif(msg.topic == "stats"):
            sensor_data = loads(msg.payload.decode())
            date_time = datetime.strptime(
                sensor_data['datetime'], "%Y-%m-%d %H:%M:%S") \
                .replace(second=0, microsecond=0)
            if(not checkRecordExistsUnderTime(date_time)):
                stats.create(voltage=sensor_data["voltage"],
                             current=sensor_data["current"],
                             power=sensor_data["power"],
                             energy=sensor_data["energy"],
                             miner_log=sensor_data["miner_log"],
                             stat_datetime=date_time).save()
    except Exception as e:
        print(str(e))
    finally:
        db.close()
    sleep(2)


try:
    with db:
        db.connect(reuse_if_open=True)
        stats.create_table()
        events.create_table()
    client = mqtt.Client(client_user)
    client.username_pw_set(mqtt_user, mqtt_passwd)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host=mqtt_host, port=1883,
                   keepalive=int(keep_alive_intervel))
    client.loop_forever()
except Exception as e:
    print(str(e))
