# Domoticz-ZWavejs2MQTT
Allows a ZWavejs2MQTT instance to connect directly to Domoticz and handles Z-Wave devices 

## Key features

* Domoticz acts as the MQTT broker so only Domoticz and ZWavejs2MQTT instances are required
* Currently supported:
  * Binary switches
  * Multilevel switches (Dimmers)
  * Power meters - kWh, W, A, V
  * Battery level
  * Scenes

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

## ZWavejs2Mqtt Configuration

Under 'Settings'
* 'Zwave'
  * Set serial port for ZWave stick
  * other settings don't matter
* 'Mqtt'
  * Host url - set to IP of Domoticz
  * Port 1883
  * Enable 'Clean'
  * Enable 'Auth' and specify Username/Password  (matching values will be required in Domoticz plugin settings as well)
* 'Gateway'
  *  Topic type: ValueID topics
  *  Payload type: JSON Time-Value
  *  Enable 'Ignore location' ONLY
* 'Home Assistant'
  *  Enable 'MQTT Discovery' ONLY
  *  Discovery prefix: domoticz

## Adding new ZWave nodes

To get the device names to come through automatically:
* Stop Domoticz
* Add the device to the ZWave stick
* Find the new device in ZWavejs2MQTT via the UI
* Set the device name and location
* Start Domoticz and the related new devices will be created with the correct names
If Domoticz is running when the device is added things will still work but the device will be given a default name of 'nodeID_<x>', the name can still be changed in both ZWavejs2MQTT and Domoticz without impacting functionality.
