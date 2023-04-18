# Interface to the LIFX LAN API
# Used for the home lighting system.
# Currently using LIFX as they can be directly controlled over the LAN.
# Can be used to control LIFX bulbs on the local network.
# See https://lan.developer.lifx.com/docs for documentation.

import time
from typing import Callable
import lifxlan
from presence import getPresence
import json

shortNames = {
    'Bedroom Light': 'bl',
    'Extra Bedroom Light': 'ebl',
    'Bathroom Light': 'bal',
    'Kitchen & WB Light': 'kl',
    'TV & WB Light': 'lrl',
}

bulbs = {}
lifx = lifxlan.LifxLAN()
props = {'kelvin': 5000, 'brightness': 1, 'lightPower': {}}


def init():
    findBulbs()
    for b in bulbs:
        props['lightPower'][b] = runcmd(bulbs[b].get_power) != 0
    if len(bulbs) > 0:
        b = bulbs[list(bulbs)[0]]
        props['kelvin'] = runcmd(b.get_color)[3]
        props['brightness'] = runcmd(b.get_color)[2] / 65535
    
def findBulbs() -> None:
    # Find all bulbs on the network
    global bulbs
    for dev in runcmd(lifx.get_lights):
        if runcmd(dev.get_label) in shortNames:
            bulbs[shortNames[runcmd(dev.get_label)]] = dev


def runcmd(cmd: Callable, *args, **kwargs) -> None:
    # Run a command on a bulb
    for i in range(5):
        try:
            return cmd(*args, **kwargs)
        except lifxlan.errors.WorkflowException:
            time.sleep(0.2)
        
def turnOn(bulb: str) -> None:
    if props['lightPower'][bulb]:
        return
    props['lightPower'][bulb] = True
    # Turn on a bulb
    runcmd(bulbs[bulb].set_power, True)

def turnOff(bulb: str) -> None:
    if props['lightPower'][bulb] == False:
        return
    props['lightPower'][bulb] = False
    # Turn off a bulb
    runcmd(bulbs[bulb].set_power, False)
    
def setMode(brightness, kelvin) -> None:
    if brightness == props['brightness'] and kelvin == props['kelvin']:
        return
    props['brightness'] = brightness
    props['kelvin'] = kelvin
    brightness = int(65535 * brightness)
    # Set the colour of a bulb
    for b in bulbs:
        runcmd(bulbs[b].set_color, [0, 0, brightness, kelvin])
        
def readData(data: dict) -> None:
    # Read data from the server
    print(data)
    print(json.dumps(data, sort_keys=True, indent=4))
    if 'mode' in data:
        setMode(data['mode']['brightness'], data['mode']['kelvin'])
    if 'bulbs' in data:
        for b in data['bulbs']:
            if b['state'] == 'on' or b['state'] == True:
                turnOn(b['name'])
            elif b['state'] == 'off' or b['state'] == False:
                turnOff(b['name'])

def main():
    findBulbs()
    time.sleep(1)
    turnOn('bl')
    turnOn('kl')
    turnOn('lrl')
    setMode(1, 3500)

if __name__ == '__main__':
    main()