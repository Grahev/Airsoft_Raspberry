
import time
import random
import paho.mqtt.client as mqtt

MQTT_HOST = "localhost"  # Change if your broker is elsewhere
MQTT_PORT = 1883

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
    else:
        print(f"Failed to connect, return code {rc}")

def emulate_sensor(sensor_id, client):
    topic = f"airsoft/sensor{sensor_id}/hit"
    payload = {"hit": True, "sensor": sensor_id, "timestamp": time.time()}
    result = client.publish(topic, str(payload))
    status = result[0]
    if status == 0:
        print(f"Sensor {sensor_id} sent hit: {payload}")
    else:
        print(f"Failed to send message from sensor {sensor_id}")

def main():
    client = mqtt.Client()
    client.on_connect = on_connect

    try:
        print(f"Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}...")
        client.connect(MQTT_HOST, MQTT_PORT, 60)
    except Exception as e:
        print(f"Could not connect to MQTT broker: {e}")
        return

    client.loop_start()

    try:
        while True:
            sensor_id = random.choice([1, 2])
            emulate_sensor(sensor_id, client)
            time.sleep(random.uniform(1, 3))
    except KeyboardInterrupt:
        print("Stopped emulation.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()