from datetime import datetime, timedelta
from configparser import ConfigParser
from os import path, stat
from select import select
import paho.mqtt.client as mqtt
from time import sleep, time
import peewee
from threading import Thread

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
host = config.get('mariadb', 'host')
user = config.get('mariadb', 'user')
passwd = config.get('mariadb', 'passwd')
database = config.get('mariadb', 'database')
database_push_time = int(config.get('mariadb', 'db_push_wait'))
stats_push_intervel = int(config.get('avg_stats', 'push_intervel'))
stats_window = int(config.get('avg_stats', 'avg_window'))
mqtt_host = config.get('mqtt_broker', 'host')
mqtt_user = config.get('mqtt_broker', 'user')
mqtt_passwd = config.get('mqtt_broker', 'password')
keep_alive_intervel = config.get('mqtt_broker', 'keep_alive_intervel')
client_user = "avg_stats_pusher"
db = peewee.MySQLDatabase(database, user=user, password=passwd,
                          host=host, port=3306)


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


def pushLastDbInsertTime():
    global database_push_time
    prev_time = time()
    while True:
        if(time()-prev_time > database_push_time):
            try:
                last_insertion_date = stats.select(
                    peewee.fn.MAX(stats.stat_datetime)).scalar()
                client.publish("stats/last_insert_at",
                               payload=str(last_insertion_date), retain=True)
            except Exception as e:
                print("pushLastDbInsertTime:|:"+str(e))
            prev_time = time()
            sleep(database_push_time-5)


def pushAvgStats():
    global stats_push_intervel, stats_window, database_push_time
    prev_time = time()
    while True:
        if(time()-prev_time > stats_push_intervel):
            try:
                windowed = (datetime.now() - timedelta(minutes=stats_window)) \
                    .replace(second=0, microsecond=0)
                avg_voltage = stats.select().where(stats.stat_datetime > windowed) \
                    .select(peewee.fn.AVG(stats.voltage)).scalar()
                avg_current = stats.select().where(stats.stat_datetime > windowed) \
                    .select(peewee.fn.AVG(stats.current)).scalar()
                client.publish("stats/avg_voltage",
                               payload=round(avg_voltage, 2), retain=True)
                client.publish("stats/avg_current",
                               payload=round(avg_current, 2), retain=True)
            except Exception as e:
                print(e)
            prev_time = time()
            sleep(stats_push_intervel-5)


def on_connect(client, userdata, flags, rc):
    if(rc == 0):
        Thread(target=pushAvgStats, args=()).start()
        Thread(target=pushLastDbInsertTime, args=()).start()
    else:
        print("unable to connect to mqtt broker")


try:
    client = mqtt.Client(client_user)
    client.username_pw_set(mqtt_user, mqtt_passwd)
    client.on_connect = on_connect
    client.connect(host=mqtt_host, port=1883,
                   keepalive=int(keep_alive_intervel))
    client.loop_forever()
except Exception as e:
    print(str(e))
