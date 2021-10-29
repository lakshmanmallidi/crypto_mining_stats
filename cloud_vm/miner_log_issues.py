from datetime import datetime
from configparser import ConfigParser
from os import path
from json import loads, dumps
import paho.mqtt.client as mqtt
from time import sleep

config = ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
mqtt_host = config.get('mqtt_broker', 'host')
mqtt_user = config.get('mqtt_broker', 'user')
mqtt_passwd = config.get('mqtt_broker', 'password')
keep_alive_intervel = config.get('mqtt_broker', 'keep_alive_intervel')
client_user = "issue_identifier"
echu_issue = False


def check_echu_issue(log):
    global echu_issue
    if(log != "error in reading miner log"):
        if(log[log.find("ECHU["):(log.find("ECMM[")-1)] != "ECHU[0 0 131073]"):
            if(echu_issue == False):
                client.publish("issues/ECHU",
                               payload=dumps({"status": True, "datetime": str(datetime.now())}), qos=2)
                echu_issue = True
        else:
            if(echu_issue == True):
                client.publish("issues/ECHU",
                               payload=dumps({"status": False, "datetime": str(datetime.now())}), qos=2)
                echu_issue = False


def on_connect(client, userdata, flags, rc):
    if(rc == 0):
        client.subscribe("stats", qos=2)
    else:
        print("unable to connect to mqtt broker")


def on_message(client, userdata, msg):
    try:
        log = loads(msg.payload.decode())['miner_log']
        check_echu_issue(log)
    except Exception as e:
        print(str(e))
    sleep(2)


try:
    client = mqtt.Client(client_user)
    client.username_pw_set(mqtt_user, mqtt_passwd)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host=mqtt_host, port=1883,
                   keepalive=int(keep_alive_intervel))
    client.loop_forever()
except Exception as e:
    print(str(e))
