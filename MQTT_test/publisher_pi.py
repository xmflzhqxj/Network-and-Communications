import paho.mqtt.client as mqtt
import time
import dht

MQTT_BROKER ="10.122.26.104"
MQTT_PORT = 1883
MQTT_TOPIC = "raspberry/temp_humidity"

client = mqtt.Client()

try:
    print(f"Attempting to connect to broker at {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER,MQTT_PORT,60)
    client.loop_start()  
    
    print("publishing messages...")
    temp, humi = dht.temperature_humidity_read()
    message =f"Temperature : {temp}°C, Humidity : {humi}%"
    result = client.publish(MQTT_TOPIC,message)
    
    status = result[0]
    
    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Sent: {message} to topic:{MQTT_TOPIC}")
    else:
        print(f"Failed to send message (status : {status})")
    time.sleep(1)
    
finally:
    client.loop_stop()
    client.disconnect()
    print("Publisher disconnected.")    