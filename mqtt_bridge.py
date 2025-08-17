import os, json
import paho.mqtt.client as mqtt
from typing import Callable
from dotenv import load_dotenv

# Load .env
load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "192.168.4.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))


#MQTT_HOST = os.getenv("MQTT_HOST", "192.168.4.1")
#MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

class MQTTBridge:
    def __init__(self, on_hit: Callable[[str,str,int|None], None], on_announce: Callable[[str,str], None]):
        self.on_hit = on_hit
        self.on_announce = on_announce
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self):
        self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=45)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, c, userdata, flags, rc, props=None):
        c.subscribe("targets/+/+/hit")
        c.subscribe("targets/+/+/announce")

    def _on_message(self, c, userdata, msg):
        topic = msg.topic
        parts = topic.split("/")
        try:
            payload = json.loads(msg.payload.decode())
        except Exception:
            payload = {}
        if len(parts) >= 4 and parts[0] == "targets":
            system_id = parts[1]
            target_id = parts[2]
            if parts[3] == "hit":
                amp = payload.get("amp")
                self.on_hit(system_id, target_id, amp)
            elif parts[3] == "announce":
                self.on_announce(system_id, target_id)

    def send_led_cmd(self, system_id: str, target_id: str, color: str, time_ms: int):
        topic = f"targets/{system_id}/{target_id}/cmd"
        self.client.publish(topic, json.dumps({"led_color": color, "led_time": time_ms}), qos=0)
