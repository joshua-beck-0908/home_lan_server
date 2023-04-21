# Main Flask server file
import os
import sys
import flask
import lifx
import presence
import ruleman

def startup() -> None:
    lifx.init()
    ruleman.init()

startup()
app = flask.Flask(__name__)

@app.route('/lights', methods=['POST'])
def lights():
    data = flask.request.get_json()
    lifx.readData(data)
    return 'OK'

@app.route('/sensor', methods=['POST'])
def sensor():
    print(flask.request.get_data())
    data = flask.request.get_json()
    if 'sensor' in data:
        presence.presenceSensor(data['sensor'])
    elif 'magsensor' in data:
        presence.magneticSensor(data['magsensor'])
    return 'OK'

@app.route('/cmd', methods=['POST'])
def cmd():
    data = flask.request.get_json()
    ruleman.run(data['cmd'])
    return 'OK'

def main():
    startup()
    app.run(debug=True, port=5000, host='0.0.0.0')

if __name__ == '__main__':
    main()