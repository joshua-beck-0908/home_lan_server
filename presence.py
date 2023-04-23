# Holds the results from PIR sensors.

import time

sensorTime = {}
sensorVariable = {
    '3485186e670': {'var': 'bs1', 'light': 'bl'},
    '34851859cd4': {'var': 'ks1', 'light': 'kl'},
    '348518589a8': {'var': 'lrs1', 'light': 'lrl'},
    'm_3485187428': {'var': 'entrys1', 'light': 'entry'},
}


def magneticSensor(sensor: str) -> None:
    presenceSensor(f'm_{sensor}')
    
def presenceSensor(sensor: str) -> None:
    # Record the time a sensor was triggered.
    sensorTime[sensor] = time.time()
    if sensor in sensorVariable:
        run('SET ' + sensorVariable[sensor]['var'].upper() + ' TO TRUE')
    
def getPresence(sensor: str, timeout=120) -> bool:
    # Check if a sensor has been triggered recently.
    if sensor in sensorTime:
        if time.time() - sensorTime[sensor] < timeout:
            return True
    return False

def getLastTime(sensor) -> float:
    # Get the time a sensor was last triggered.
    if sensor in sensorTime:
        return sensorTime[sensor]
    return 0

from ruleman import run