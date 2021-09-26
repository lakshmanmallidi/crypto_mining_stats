from flask import Flask, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db.ini'))
host = config.get('mariadb', 'host')
user = config.get('mariadb', 'user')
passwd = config.get('mariadb', 'passwd')
database = config.get('mariadb', 'database')

app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mariadb+mariadbconnector://{}:{}@{}:3306/{}' \
    .format(user, passwd, host, database)
db = SQLAlchemy(app)


class power_stats(db.Model):
    stat_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    voltage = db.Column(db.Float)
    current = db.Column(db.Float)
    power = db.Column(db.Float)
    energy = db.Column(db.Float)
    stat_datetime = db.Column(db.DateTime, nullable=False)


class power_events(db.Model):
    event_sequence = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(15), nullable=False)
    event_log = db.Column(db.String(30))
    event_datetime = db.Column(db.DateTime, nullable=False)


class manual_triggers(db.Model):
    trigger_sequence = db.Column(
        db.Integer, primary_key=True, autoincrement=True)
    trigger_type = db.Column(db.String(10), nullable=False)
    trigger_datetime = db.Column(db.DateTime, nullable=False)


class manualTriggers(Resource):
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


class powerEvents(Resource):
    def post(self):
        data = request.get_json()
        try:
            db.session.add(power_events(event_type=data["event_type"], event_log=data["event_log"],
                                        event_datetime=datetime.now()))
            db.session.commit()
            return {"status": "success"}, 200
        except Exception:
            return {"status": "failed"}, 500


class powerStatistics(Resource):
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
    db.create_all()
