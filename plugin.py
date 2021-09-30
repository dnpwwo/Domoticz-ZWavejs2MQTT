# Python Plugin Zwavejs2Mqtt integration
#
# Author: Dnpwwo, 2021
#
"""
<plugin key="Zwavejs2Mqtt" name="ZWavejs2Mqtt Direct Integration" author="dnpwwo" version="1.0.0" externallink="https://zwave-js.github.io/zwavejs2mqtt/#/">
    <description>
        <h2>ZWavejs2Mqtt Direct Integration</h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Allows ZWavejs2Mqtt to connect directly to Domoticz without an intermediate broker</li>
            <li>Exposes all published endpoint in Domoticz devices and units</li>
            <li>Values for hardware devices logically grouped by name</li>
        </ul>
        <h3>Zwavejs2Mqtt Configuration - Zwave</h3>
        <ul style="list-style-type:square">
            <li>Name: zwavejs2mqtt</li>
            <li>Host url: &lt;domoticz host&gt;</li>
            <li>Port: 1883</li>
            <li>QoS: 1</li>
            <li>Retain: Off</li>
            <li>Auth: True. Enter same username/password as below</li>
        </ul>
        <h3>Zwavejs2Mqtt Configuration - Gateway</h3>
        <ul style="list-style-type:square">
            <li>Topic type: ValueID topics</li>
            <li>Payload type: JSON Time-Value</li>
            <li>Use node names: False</li>
            <li>Ignore location: True</li>
            <li>Send Zwave events: False</li>
            <li>Ignore status updates: False</li>
            <li>Include Node info: False</li>
            <li>Publish node details: False</li>
        </ul>
        <h3>Zwavejs2Mqtt Configuration - Home Assistant</h3>
        <ul style="list-style-type:square">
            <li>WS Server: False</li>
            <li>MQTT Discovery: True</li>
            <li>Discovery prefix: domoticz</li>
            <li>Retained discovery: False</li>
            <li>Manual discovery: False</li>
        </ul>
    </description>
    <params>
        <param field="Port" label="Connection" required="true" width="200px">
            <options>
                <option label="Unencrypted" value="1883" default="true" />
                <option label="Encrypted" value="8883" />
                <option label="Encrypted (Client Certificate)" value="8884" />
            </options>
        </param>
        <param field="Username" label="Username" width="200px"/>
        <param field="Password" label="Password" width="200px" password=true/>
        <param field="Mode5" label="Write to file" width="75px">
            <options>
                <option label="True" value="True"/>
                <option label="False" value="False"  default="true" />
            </options>
        </param>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import DomoticzEx as Domoticz
import json
import os,sys
from datetime import datetime

class BasePlugin:
    
    def __init__(self):
        self.enabled = False
        self.mqttListener = None
        self.mqttClients = {}
        self.mqttLogFile = None
        self.counter = 0

        # Configuration structure:
        #    {
	    #        "devices":
	    #        {
		#            "zwavejs2mqtt_0xe0779f52_node3":
		#            {
		#	            "units":
		#	            {
		#		            1:
		#		            {
		#			            "mapped_type": "scene_state_scene_001",
		#           			"reported_type": "sensor",
		#			            "state_topic": "zwave/5/38/0/currentValue",
		#			            "command_topic": "zwave/5/38/0/targetValue/set",
		#			            "on_command_type": "brightness"
		#			            "payload_on": true,
		#			            "payload_off": false
		#		            }
        #                   2:
        #                   {
        #                       ...
        #                   }
		#	            }
		#	            "battery":
		#	            {
		#		            "state_topic": "zwave/5/38/0/level",
        #                   "reported_type": "sensor",
		#               	"mapped_type": "battery_level"
		#	            }
		#            }
	    #        }
        #   	"topics": 
        #   	{
		#           "zwave/3/91/0/scene/001": 
		#           {
		#	            "deviceID": "zwavejs2mqtt_0xe0779f52_node3",
		#	            "unit": "1"
		#           },
		#           "zwave/3/128/0/level":
		#           {
		#	            "deviceID": "zwavejs2mqtt_0xe0779f52_node3",
		#	            "mapped_type": "battery_level"
		#           },
        #       }
        #    }
        #
        self.pluginConfig = None

        #   Type mapping:
        self.typeMapping = {
                    "any":                      {"type": "Contact", "update": self.updateContact },
                    "dimmer":                   {"type": "Dimmer", "update": self.updateDimmer, "command": self.commandDimmer },
                    "electric_a_value":         {"type": "Current/Ampere", "update": self.updateCurrent },
                    "electric_v_value":         {"type": "Voltage", "update": self.updateVoltage },
                    "electric_w_value":         {"type": "Usage", "update": self.updateUsage },
                    "electric_kwh_value":       {"type": (113,0,0), "update": self.updatekWh },
                    "home_security":            {"type": "Contact", "update": self.updateContact },
                    "rgb_dimmer":               {"type": (241,2,7), "update": self.updateColor, "command": self.commandColor },
                    "scene_state_scene_001":    {"type": "Push On", "update": self.updateScene },
                    "scene_state_scene_002":    {"type": "Push On", "update": self.updateScene },
                    "scene_state_scene_003":    {"type": "Push On", "update": self.updateScene },
                    "scene_state_scene_004":    {"type": "Push On", "update": self.updateScene },
                    "scene_state_scene_005":    {"type": "Push On", "update": self.updateScene },
                    "scene_state_scene_006":    {"type": "Push On", "update": self.updateScene },
                    "scene_state_scene_007":    {"type": "Push On", "update": self.updateScene },
                    "scene_state_scene_008":    {"type": "Push On", "update": self.updateScene },
                    "switch":                   {"type": "Switch", "update": self.updateBinarySwitch, "command": self.commandBinarySwitch }
                    }

        #   Special handling (device level)
        self.specialHandling = {
            "battery_level": { "update": self.updateBattery }
            }

    def commandColor(self, cmdUnit, Command, Level, Hue):
        # commandColor called: Lava Lamp_rgb_dimmer, Command: Set Color, Level: 1, Hue: {"b":113,"cw":0,"g":255,"m":3,"r":192,"t":0,"ww":0}
        # commandColor called: Lava Lamp_rgb_dimmer, Command: Set Level, Level: 29, Hue:
        # commandColor called: Lava Lamp_rgb_dimmer, Command: Set Color, Level: 45, Hue: {"b":113,"cw":0,"g":255,"m":3,"r":192,"t":0,"ww":0}
        Domoticz.Log("commandColor called: "+cmdUnit.Name+", Command: "+Command+", Level: "+str(Level)+", Hue: "+str(Hue))

    def commandDimmer(self, cmdUnit, Command, Level, Hue):
        # commandDimmer called: Office Dimmer, Command: On, Level: 0, Hue:          <-- turn on
        # commandDimmer called: Office Dimmer, Command: Off, Level: 99, Hue:        <-- Turn off
        # commandDimmer called: Office Dimmer, Command: Set Level, Level: 47, Hue:  <-- Change slider
        # Appears that there is a single 'set' topic for both on/off and brightness
        Domoticz.Log("commandDimmer called: "+cmdUnit.Name+", Command: "+Command+", Level: "+str(Level)+", Hue: "+str(Hue))

        # Read the configuration for the detaila
        unitConfig = self.unitConfiguration(cmdUnit.Parent.DeviceID, cmdUnit.Unit)
        if (unitConfig == None): 
            Domoticz.Error("Dimmer command failed for "+cmdUnit.Name+", unable to find configuration.")
            return

        if (not "command_topic" in unitConfig): 
            Domoticz.Error("Dimmer command failed for "+cmdUnit.Name+", No command topic mapped.")
            return
        theTopic = unitConfig["command_topic"]

        # Create the payload based on the command
        if (Command == "Set Level"):
            maxBrightness = unitConfig["brightness_scale"] if ("brightness_scale" in unitConfig) else 99
            theBrightness = Level * (maxBrightness/99) if (Level * (maxBrightness/99) <= maxBrightness) else maxBrightness
            thePayload = str(int(theBrightness))
        else:
            thePayload = Command

        # Tell everyone!
        for mqttConn in self.mqttClients:
            if (self.mqttClients[mqttConn].Connected()):
                messageDict = {"Verb":"PUBLISH", "QoS":1, "Topic":theTopic, "PacketIdentifier":1234, "Payload":thePayload}
                Domoticz.Log("commandDimmer Publishing: "+str(messageDict))
                self.mqttClients[mqttConn].Send(messageDict)
            else:
                Domoticz.Error("Client is not connected: "+mqttConn)

    def commandBinarySwitch(self, cmdUnit, Command, Level, Hue):
        # commandBinarySwitch called: Bedside Lamp_switch, Command: Off, Level: 0
        Domoticz.Debug("commandBinarySwitch called: "+cmdUnit.Name+", Command: "+Command+", Level: "+str(Level))

        # Read the configuration for the detaila
        unitConfig = self.unitConfiguration(cmdUnit.Parent.DeviceID, cmdUnit.Unit)
        if (unitConfig == None): 
            Domoticz.Error("Switch command failed for "+cmdUnit.Name+", unable to find configuration.")
            return

        if (not "command_topic" in unitConfig): 
            Domoticz.Error("Switch command failed for "+cmdUnit.Name+", No command topic mapped.")
            return
        theTopic = unitConfig["command_topic"]

        if Command == "On":
            thePayload = "{'value':"+str(unitConfig["payload_on"])+"}" if "payload_on" in unitConfig else "{'value':True}"
        else:
            thePayload = "{'value':"+str(unitConfig["payload_off"])+"}" if "payload_on" in unitConfig else "{'value':False}"
        Domoticz.Debug("commandBinarySwitch: Found topic: "+theTopic+", Payload is: "+thePayload)
        # Tell everyone!
        for mqttConn in self.mqttClients:
            if (self.mqttClients[mqttConn].Connected()):
                messageDict = {"Verb":"PUBLISH", "QoS":1, "Topic":theTopic, "PacketIdentifier":1234, "Payload":thePayload}
                Domoticz.Log("commandBinarySwitch Publishing: "+str(messageDict))
                self.mqttClients[mqttConn].Send(messageDict)
            else:
                Domoticz.Error("Client is not connected: "+mqttConn)

    def updateBattery(self, unitObj, jsonDict):
        if ('value' in jsonDict):
            if (unitObj.BatteryLevel != jsonDict['value']):
                unitObj.BatteryLevel = jsonDict['value']
                unitObj.Update()
            Domoticz.Debug("updateBattery: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updateCurrent(self, unitObj, jsonDict):
        # Complicated, sValue only '0.0;0.0;0.0'
        if ('value' in jsonDict):
            oldValue = unitObj.sValue
            unitObj.sValue = str(jsonDict['value'])+';0.0;0.0'
            if (unitObj.sValue != oldValue):
                unitObj.Update()
            else:
                unitObj.Touch()
            Domoticz.Debug("updateCurrent: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updateVoltage(self, unitObj, jsonDict):
        # Simply stored in sValue
        if ('value' in jsonDict):
            oldValue = unitObj.sValue
            unitObj.sValue = str(jsonDict['value'])
            if (unitObj.sValue != oldValue):
                unitObj.Update()
            else:
                unitObj.Touch()
            Domoticz.Debug("updateVoltage: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updateUsage(self, unitObj, jsonDict):
        # Simply stored in sValue
        if ('value' in jsonDict):
            oldValue = unitObj.sValue
            unitObj.sValue = "{:.3f}".format(jsonDict['value'])
            if (unitObj.sValue != oldValue):
                unitObj.Update()
            else:
                unitObj.Touch()
            Domoticz.Debug("updateUsage: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updatekWh(self, unitObj, jsonDict):
        # sValue only.  '10180123'  KwH -> '10180.123'
        # Note: Number of decimal places provided can vary
        if ('value' in jsonDict):
            oldValue = unitObj.sValue
            jsonDict['value'] = "{:.3f}".format(jsonDict['value'])  # Force 3 trailing decimal places
            unitObj.sValue = str(jsonDict['value']).replace(".","") # Remove the decimal place (Domoticz will put it back in)
            if (unitObj.sValue != oldValue):
                unitObj.Update()
            else:
                unitObj.Touch()
            Domoticz.Debug("updatekWh: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updateDimmer(self, unitObj, jsonDict):
        # nValue maps to:
        #       0 - Off
        #       1 - On (When dimmer is at max, shows 'On')
        #       2 - When dimmer is not at min or max.
        #       Unit 'LastLevel' is what controls the slider 
        unitConfig = self.unitConfiguration(unitObj.Parent.DeviceID, unitObj.Unit)
        if (unitConfig == None): 
            Domoticz.Error("updateDimmer: Failed for "+unitObj.Name+", unable to find configuration.")
            return

        if ('value' in jsonDict):
            maxBrightness = unitConfig["brightness_scale"] if ("brightness_scale" in unitConfig) else 99
            oldnValue = unitObj.nValue
            oldsValue = unitObj.sValue
            oldlValue = unitObj.LastLevel
            unitObj.nValue = 2 if (jsonDict['value'] > 0) else 0
            if (jsonDict['value'] == maxBrightness):
                unitObj.nValue = 1
            unitObj.sValue = str(jsonDict['value'])
            if (jsonDict['value'] > 0):
                unitObj.LastLevel = jsonDict['value']

            if (unitObj.nValue != oldnValue) or (unitObj.sValue != oldsValue) or (unitObj.LastLevel != oldlValue):
                unitObj.Update(Log=True)
            else:
                unitObj.Touch()
            Domoticz.Log("updateDimmer: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updateBinarySwitch(self, unitObj, jsonDict):
        # nValue 0 - Off, 1 = On.  sValue can be updated but is ignored
        # Read the configuration for the details
        unitConfig = self.unitConfiguration(unitObj.Parent.DeviceID, unitObj.Unit)
        if (unitConfig == None): 
            Domoticz.Error("updateBinarySwitch: Failed for "+unitObj.Name+", unable to find configuration.")
            return

        if ('value' in jsonDict):
            oldValue = unitObj.nValue
            unitObj.sValue = "On" if (jsonDict['value'] == unitConfig["payload_on"]) else "Off"
            unitObj.nValue = 1 if (jsonDict['value'] == unitConfig["payload_on"]) else 0
            if (unitObj.nValue != oldValue):
                unitObj.Update(Log=True)
            else:
                unitObj.Touch()
            Domoticz.Debug("updateBinarySwitch: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updateScene(self, unitObj, jsonDict):
        # Scenes are mapped to PushOn but this may be wrong because commands can't be triggered from Domoticz
        # Event flow looks like this for brief touch:
        #    2021-09-23 15:44:28.384: '{'time': 1632375583399, 'value': 0}'
        #    2021-09-23 15:44:28.446: '{'time': 1632375584401}'
        # Event flow looks like this for long touch:
        #    2021-09-23 15:48:05.152: '{'time': 1632376083125, 'value': 2}'
        #    2021-09-23 15:48:05.399: '{'time': 1632376083330, 'value': 2}'
        #    2021-09-23 15:48:05.585: '{'time': 1632376083529, 'value': 1}'
        #    2021-09-23 15:48:06.581: '{'time': 1632376084530}'
        Domoticz.Log("updateScene: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updateColor(self, unitObj, jsonDict):
        # updateColor: Bedside Lamp_rgb_dimmer, Payload: {'time': 1632621863751, 'value': {'red': 62, 'green': 67, 'blue': 165}}
        # updateColor: Bedside Lamp_rgb_dimmer, Payload: {'time': 1632622088122, 'value': 75}
        Domoticz.Log("updateColor: "+unitObj.Name+", Payload: "+str(jsonDict))

        if (not 'value' in jsonDict): return

        theValue = jsonDict['value']
        if (isinstance(theValue, dict)):
            # Color update
            Domoticz.Log("updateColor: "+unitObj.Name+", Payload: "+str(jsonDict))
        else:
            # Brightness update
            oldValue = unitObj.sValue
            unitObj.sValue = str(theValue)
            unitObj.nValue = int(15 * (theValue / 100))
            if (unitObj.sValue != oldValue):
                unitObj.Update(Log=True)
            else:
                unitObj.Touch()
            Domoticz.Log("updateColor: "+unitObj.Name+", Payload: "+str(jsonDict))


    def updateContact(self, unitObj, jsonDict):
        # zwave/7/113/0/Home_Security/Sensor_status: b'{"time":1632470645111,"value":2}'
        # zwave/7/48/0/Any: b'{"time":1632470726665,"value":false}'
        Domoticz.Log("updateContact: "+unitObj.Name+", Payload: "+str(jsonDict))

        # Read the configuration for the detaila
        unitConfig = self.unitConfiguration(unitObj.Parent.DeviceID, unitObj.Unit)
        if (unitConfig == None): 
            Domoticz.Error("updateContact: Failed for "+unitObj.Name+", unable to find configuration.")
            return

        if ('value' in jsonDict):
            oldValue = unitObj.nValue
            unitObj.sValue = "On" if (jsonDict['value'] == unitConfig["payload_on"]) else "Off"
            unitObj.nValue = 1 if (jsonDict['value'] == unitConfig["payload_on"]) else 0
            if (unitObj.nValue != oldValue):
                unitObj.Update(Log=True)
            else:
                unitObj.Touch()
            Domoticz.Debug("updateContact: "+unitObj.Name+", Payload: "+str(jsonDict))

    def updateNothing(self, unitObj, jsonDict):
        Domoticz.Log("updateNothing: "+unitObj.Name+", Payload: "+str(jsonDict))


    def unitConfiguration(self, deviceID, unitNum):
        # Sanity check data
        if (not deviceID in self.pluginConfig["devices"]):
            Domoticz.Error(deviceID+" not found in plugin configuration.")
            return None
        if (not str(unitNum) in self.pluginConfig["devices"][deviceID]["units"]):
            Domoticz.Error(str(unitNum)+" not found in "+deviceID+" plugin configuration.")
            return None
        return self.pluginConfig["devices"][deviceID]["units"][str(unitNum)]

    def typeFromConfiguration(self, deviceID, unitNum):
        unitConfig = self.unitConfiguration(deviceID, unitNum)
        if (unitConfig == None) or (not "mapped_type" in unitConfig):
            Domoticz.Error(deviceID+"\\"+str(unitNum)+" not mapped in plugin configuration.")
            return None
        return unitConfig["mapped_type"]

    def synchroniseData(self, Topic, Payload):
        try:
            # No devices yet so just exit
            if (not "devices" in self.pluginConfig):
                return

            jsonDict = json.loads(Payload)

            if (not Topic in self.pluginConfig["topics"]):
                Domoticz.Log(Topic+" not found in Topics configuration.")
                return

            # Short cut to the actual device details
            theTopic = self.pluginConfig["topics"][Topic]
            deviceID = theTopic["deviceID"]
            if (not deviceID in Devices):
                Domoticz.Error(deviceID+" not found in plugin Devices dictionary.")
                return

            # if a unit is available then this is a normal topic
            if ("unit" in theTopic):
                unitNum = theTopic["unit"]

                # Get type from config
                theType = self.typeFromConfiguration(deviceID, unitNum)
                if (theType == None): return

                # Ignore events in the past
                if ("time" in jsonDict):
                    eventDT = datetime.fromtimestamp(int(jsonDict["time"])/1000).strftime("%Y-%m-%d %H:%M:%S")
                    if (not int(unitNum) in Devices[deviceID].Units):
                        Domoticz.Error(unitNum+" not found in "+deviceID+" plugin Units dictionary.")
                        return
                    theUnit = Devices[deviceID].Units[int(unitNum)]
                    if (eventDT >= str(theUnit.LastUpdate)):
                        # Find updater
                        Domoticz.Debug(theUnit.Name+" ("+str(theUnit.nValue)+","+theUnit.sValue+") with payload: '"+str(jsonDict)+"'")
                        if (theType in self.typeMapping):
                            self.typeMapping[theType]["update"](theUnit, jsonDict)
                        else:
                            Domoticz.Log("Unmapped message: "+theUnit.Name+" '"+str(jsonDict)+"'")
                    else:
                        Domoticz.Debug("Discarding out of date event. Event: "+eventDT+", Unit:"+str(theUnit.LastUpdate))
            else:
                # Device level topic (such as battery)
                theType = theTopic["mapped_type"]
                Domoticz.Log("Device level topic: "+theType)
                if (not theType in self.specialHandling):
                    Domoticz.Log("Unmapped message: "+theType+" '"+str(jsonDict)+"'")
                    return
                for unit in Devices[deviceID].Units:
                    self.specialHandling[theType]["update"](Devices[deviceID].Units[unit], jsonDict)

        except:
            exc_type, exc_obj, tb = sys.exc_info()
            Domoticz.Error("Unexpected error: " + str(sys.exc_info()[0])+" at line: "+str(tb.tb_lineno))
            Domoticz.Dump()

    def synchroniseDevice(self, Topic, Payload):
        try:
            jsonDict = json.loads(Payload)
            mqttDict = jsonDict["device"]
            deviceID = mqttDict["identifiers"][0]

            #Domoticz.Log("Topic: "+str(jsonDict["state_topic"] ))
            if (not "devices" in self.pluginConfig):
                self.pluginConfig["devices"] = {}
                self.pluginConfig["topics"] = {}

            # if the device is already known then exit
            if (not deviceID in self.pluginConfig["devices"]):
                self.pluginConfig["devices"][deviceID] = {"units":{}}
            unitsDict = self.pluginConfig["devices"][deviceID]["units"]

            # Cycle through any existing units to see if the topic is already handled
            for unit in unitsDict:
                if ("state_topic" in unitsDict[unit]) and (unitsDict[unit]["state_topic"] == jsonDict["state_topic"]):
                    Domoticz.Debug(jsonDict["state_topic"]+" is already mapped against "+deviceID+"\\"+unit)
                    return

            # Device type is in the topc name
            # domoticz/sensor/Bedside_Lamp/electric_kwh_value/config
            topicList = Topic.split('/')
            if (len(topicList) != 5):
                Domoticz.Error("Incorrect topic strcture, device not created: "+Topic)
                return
            typeName = self.typeMapping[topicList[3]]["type"] if topicList[3] in self.typeMapping else None

            # This is new so consider:
            #   1.  Should this be a new Unit?
            #   2.  Is this of Device level interest?
            #   3.  Otherwise ignore it
            if (typeName == None) and (not topicList[3] in self.specialHandling):
                Domoticz.Debug(jsonDict["state_topic"]+" ignored")
                return

            valueDict=None
            #   1.  Should this be a new Unit?
            unitNum = "0"
            if (typeName != None):
                # Unit number doesn't matter so determine the next available
                for unit in unitsDict:
                    if (unit > unitNum):
                        unitNum = unit
                unitNum = str(int(unitNum)+1)
                unitsDict[unitNum] = {}
                valueDict = unitsDict[unitNum]

            #   2.  Is this of Device level interest?
            if (topicList[3] in self.specialHandling):
                self.pluginConfig["devices"][deviceID][topicList[3]] = {}
                valueDict = self.pluginConfig["devices"][deviceID][topicList[3]]

            # Add known details
            valueDict["mapped_type"] = topicList[3]
            valueDict["reported_type"] = topicList[1]

            # Retain all state and command topics for later use
            for entry in jsonDict:
                if (entry.find("_topic") != -1):
                    valueDict[entry] = jsonDict[entry]
                    if (entry.find("state_topic") != -1):
                        # Store state topics in the secondary structure for quick lookup 
                        if (unitNum == "0"):
                            self.pluginConfig["topics"][jsonDict[entry]] = { "deviceID":deviceID, "mapped_type":topicList[3] }
                        else:
                            self.pluginConfig["topics"][jsonDict[entry]] = { "deviceID":deviceID, "unit":unitNum }

            # Look for specific attributes that may be useful later
            if ("payload_on" in jsonDict): valueDict["payload_on"] = jsonDict["payload_on"]
            if ("payload_off" in jsonDict): valueDict["payload_off"] = jsonDict["payload_off"]
            if ("on_command_type" in jsonDict): valueDict["on_command_type"] = jsonDict["on_command_type"]
            if ("brightness_scale" in jsonDict): valueDict["brightness_scale"] = jsonDict["brightness_scale"]

            # Update the persistent configuration
            Domoticz.Configuration(self.pluginConfig)

            # Create the matching Domoticz DeviceStatus entries if it has been mapped to a type
            if (typeName == None):
                Domoticz.Debug("'"+topicList[3]+"' is not a mapped type, device not created: "+Topic)
                return

            name = jsonDict["name"]
            description = mqttDict["manufacturer"]+" - "+mqttDict["model"]

            if (not isinstance(typeName, tuple)): 
                # New device: 'Lava Lamp_electric_kwh_value', DeviceID: 'zwavejs2mqtt_0xe0779f52_node6', Description: 'AEON Labs - Smart Switch 6 (ZW096)'
                newUnit = Domoticz.Unit(Name=name, DeviceID=deviceID, Unit=int(unitNum), TypeName=typeName, Description=description)
            else:
                mainType, subType, switchType = typeName
                newUnit = Domoticz.Unit(Name=name, DeviceID=deviceID, Unit=int(unitNum), Type=mainType, Subtype=subType, Switchtype=switchType , Description=description)
            newUnit.Create()

            Domoticz.Log("New created device: '"+name+"', DeviceID: '"+deviceID+"', Description: '"+description+"'")
        except:
            exc_type, exc_obj, tb = sys.exc_info()
            Domoticz.Error("Unexpected error: " + str(sys.exc_info()[0])+" at line: "+str(tb.tb_lineno))
            Domoticz.Dump()

    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
        if Parameters["Mode5"] == "True":
            self.mqttLogFile = open(Parameters["HomeFolder"]+"MQTT Messages.log","a")
        DumpConfigToLog()

        # load the existing configuration
        self.pluginConfig = Domoticz.Configuration()

        # set up the listener
        Protocol = "MQTT"
        if (Parameters["Port"] == "8883"): Protocol = "MQTTS"
        self.mqttListener = Domoticz.Connection(Name="ZWave2MQTT", Transport="TCP/IP", Protocol=Protocol, Address=Parameters["Address"], Port=Parameters["Port"])
        self.mqttListener.Listen()

    def onStop(self):
        if (self.mqttLogFile != None):
            self.mqttLogFile.close()

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("MQTT connected successfully.")
            self.mqttClients[Connection.Address+":"+Connection.Port] = Connection
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+Parameters["Port"]+" with error: "+Description)

    def onMessage(self, Connection, Data):
        if (isinstance(Data, dict)) and ("Verb" in Data):
            Domoticz.Debug("onMessage called with: "+Data["Verb"])
            #DumpDictionaryToLog(Data)
            if (Data["Verb"] == "CONNECT"):
                reasonCode = 0  # Success
                reasonString = "Success"
                sessionPresent = True
                if (Data["Version"] > 4):
                    Domoticz.Error("MQTT Client is using an unacceptable protocol version")
                    reasonCode = 1  # Success
                    reasonString = "Connection Refused, unacceptable protocol version"
                    sessionPresent = False
                elif (len(Parameters["Username"]) > 0) and (len(Parameters["Password"]) > 0) and \
                        ((not "Username" in Data) or (not "Password" in Data) or \
                         (Parameters["Username"] != Data["Username"]) or (Parameters["Password"] != Data["Password"])):
                    Domoticz.Error("MQTT Client Authentication fail, bad user name or password")
                    reasonCode = 4  # Authentication fail
                    reasonString = "Connection Refused, bad user name or password"
                    sessionPresent = False
                Connection.Send({"Verb":"CONNACK",
                                 "SessionPresent":sessionPresent, 
                                 "ReasonCode":reasonCode,     # https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901079
                                 #"SessionExpiryInterval":3600,
                                 "MaximumQoS":1,
                                 "RetainAvailable":False,
                                 "MaximumPacketSize":4096,
                                 #"AssignedClientID":None,
                                 "ReasonString":reasonString,
                                 "ResponseInformation":"Domoticz"})
                if (reasonCode == 0):
                    Domoticz.Log("MQTT Connection: "+reasonString)
                else:
                    if (Connection.Address+":"+Connection.Port in self.mqttClients):
                        self.mqttClients.pop(Connection.Address+":"+Connection.Port,None)
            elif (Data["Verb"] == "PUBLISH"):
                node = None
                try:
                    if (Data["QoS"] == 1):
                        Connection.Send({"Verb":"PUBACK", "ReasonCode":  0, "PacketIdentifier":Data["PacketIdentifier"], "ReasonString":"Success"})
                    
                    if (self.mqttLogFile != None):
                        self.mqttLogFile.write(Data["Topic"]+": "+str(Data["Payload"])+"\n")

                    if (Data["Topic"][:8] == "domoticz"):
                        self.synchroniseDevice(Data["Topic"], Data["Payload"])

                    if (Data["Topic"][:5] == "zwave"):
                        self.synchroniseData(Data["Topic"], Data["Payload"])

                except json.JSONDecodeError:
                    if (Data["QoS"] == 1):
                        Connection.Send({"Verb":"PUBACK", "ReasonCode":153, "PacketIdentifier":Data["PacketIdentifier"], "ReasonString":"JSON Error"})
                except KeyError:
                    Domoticz.Error("Key error: " + str(node))
                except:
                    exc_type, exc_obj, tb = sys.exc_info()
                    Domoticz.Error("Unexpected error: " + str(sys.exc_info()[0])+" at line: "+str(tb.tb_lineno))
                    Domoticz.Dump()
                    if (Connection.Address+":"+Connection.Port in self.mqttClients):
                        self.mqttClients.pop(Connection.Address+":"+Connection.Port,None)
            elif (Data["Verb"] == "SUBSCRIBE"):
                # MQTT2ZWave Subscription, Payload: 
                # {
                # 'Verb': 'SUBSCRIBE', 
                # 'PacketIdentifier': 48228, 
                # 'Topics': [
                #       {'Topic': 'zwave/+/+/+/+/set', 'QoS': 0}, 
                #       {'Topic': 'zwave/+/+/+/+/+/set', 'QoS': 0}, 
                #       {'Topic': 'homeassistant/status', 'QoS': 0}, 
                #       {'Topic': 'zwave/_CLIENTS/ZWAVE_GATEWAY-zwavejs2mqtt/broadcast/#', 'QoS': 0}, 
                #       {'Topic': 'zwave/_CLIENTS/ZWAVE_GATEWAY-zwavejs2mqtt/api/#', 'QoS': 0}, 
                #       {'Topic': 'zwave/_CLIENTS/ZWAVE_GATEWAY-zwavejs2mqtt/multicast/#', 'QoS': 0}
                #       ]
                # }
                #Domoticz.Log("MQTT2ZWave Subscription, Payload: "+str(Data))
                Connection.Send({"Verb":"SUBACK", "PacketIdentifier":Data["PacketIdentifier"], "QoS":0 })
            elif (Data["Verb"] == "PINGREQ"):
                Connection.Send({"Verb":"PINGRESP"})
                Domoticz.Debug("Responded to PING: "+Data["Verb"])
            elif (Data["Verb"] == "PUBACK"):
                Domoticz.Debug("PUBACK received: "+str(Data))
            else:
                Domoticz.Error("Unhandled message type: "+str(Data))
        else:
            Domoticz.Error("onMessage: '"+Connection.Address+":"+Connection.Port+"' send data that was not a dictionary or no Verb was present")
            if (Connection.Address+":"+Connection.Port in self.mqttClients):
                self.mqttClients.pop(Connection.Address+":"+Connection.Port,None)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called for:"+Connection.Address+":"+Connection.Port)
        if (Connection.Address+":"+Connection.Port in self.mqttClients):
            self.mqttClients.pop(Connection.Address+":"+Connection.Port,None)

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called: "+str(self.counter))

    def onCommand(self, DeviceID, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called: "+DeviceID+"\\"+str(Unit)+", Command: "+Command)

        theType = self.typeFromConfiguration(DeviceID, Unit)
        if (theType == None): return

        theFunc = None
        if (theType in self.typeMapping):
            theEntry = self.typeMapping[theType]
            if (not "command" in theEntry):
                Domoticz.Error("Command sent for device type that does not support it.")
            else:
                theFunc = theEntry["command"]

        if (theFunc != None):
            if (not DeviceID in Devices):
                Domoticz.Error(DeviceID+" not found in plugin Devices dictionary.")
                return
            if (not Unit in Devices[DeviceID].Units):
                Domoticz.Error(str(Unit)+" not found in "+DeviceID+" plugin Units dictionary.")
                return
            theFunc(Devices[DeviceID].Units[Unit], Command, Level, Hue)

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def onCommand(DeviceID, Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(DeviceID, Unit, Command, Level, Hue)

def onStop():
    global _plugin
    _plugin.onStop()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    return

def DumpDictionaryToLog(theDict, Depth=""):
    if isinstance(theDict, dict):
        for x in theDict:
            if isinstance(theDict[x], dict):
                Domoticz.Log(Depth+"> Dict '"+x+"' ("+str(len(theDict[x]))+"):")
                DumpDictionaryToLog(theDict[x], Depth+"---")
            elif isinstance(theDict[x], list):
                Domoticz.Log(Depth+"> List '"+x+"' ("+str(len(theDict[x]))+"):")
                DumpListToLog(theDict[x], Depth+"---")
            elif isinstance(theDict[x], str):
                Domoticz.Log(Depth+">'" + x + "':'" + str(theDict[x]) + "'")
            else:
                Domoticz.Log(Depth+">'" + x + "': " + str(theDict[x]))

def DumpListToLog(theList, Depth):
    if isinstance(theList, list):
        for x in theList:
            if isinstance(x, dict):
                Domoticz.Log(Depth+"> Dict ("+str(len(x))+"):")
                DumpDictionaryToLog(x, Depth+"---")
            elif isinstance(x, list):
                Domoticz.Log(Depth+"> List ("+str(len(theList))+"):")
                DumpListToLog(x, Depth+"---")
            elif isinstance(x, str):
                Domoticz.Log(Depth+">'" + x + "':'" + str(theList[x]) + "'")
            else:
                Domoticz.Log(Depth+">'" + x + "': " + str(theList[x]))

                