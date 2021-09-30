# Domoticz-ZWavejs2MQTT
Allows a ZWavejs2MQTT instance to connect directly to Domoticz and handles Z-Wave devices 

## Installation

Python version 3.4 or higher required & Domoticz version that supports the Extended Python Framework.

To install:
* Go in your Domoticz directory using a command line and open the plugins directory.
* Run: ```git clone https://github.com/dnpwwo/Domoticz-ZWavejs2MQTT.git```
* Restart Domoticz.

In the web UI, navigate to the Hardware page.  In the hardware dropdown there will be an entry called "ZWavejs2Mqtt Direct Integration".

## Updating

To update:
* Go in your Domoticz directory using a command line and open the plugins directory then the Domoticz-ZWavejs2MQTT directory.
* Run: ```git pull```
* Restart Domoticz.

## Adding new ZWave nodes

To get the device names to come through automatically:
* Stop Domoticz
* Add the device to the ZWave stick
* Find the new device in ZWavejs2MQTT via the UI
* Set the device name and location
* Start Domoticz and the related new devices will be created with the correct names
If Domoticz is running when the device is added things will still work but the device will be given a default name of 'nodeID_<x>', the name can still be changed in both ZWavejs2MQTT and Domoticz without impacting functionality.
