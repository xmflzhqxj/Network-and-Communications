import paho.mqtt.client as mqtt

MQTT_BROKER = "10.122.26.104"
MQTT_PORT = 1883
MQTT_TOPIC = "raspberry/transmit"

def on_connect(client, userdata, flags,rc):
    if rc == 0:
        print(f"Mosquitto 브로커({MQTT_BROKER})에 성공적으로 연결 되었습니다.")
        client.subscribe(MQTT_TOPIC)
        print(f"토픽 구독 시작{MQTT_TOPIC}")
    else : 
        print(f"브로커 연결 실패(코드{rc}")

def on_message(client, userdata, msg):
    print(f"received message [topic :{msg.topic}] : {msg.payload.decode('utf-8')}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try :
    print(f"브로커{MQTT_BROKER}:{MQTT_PORT}에 연결을 시도합니다.")
    client.connect(MQTT_BROKER,MQTT_PORT,60)
    client.loop_forever()

except KeyboardInterrupt:
    print("\n구독을 중지합니다.")
    client.disconnect()

except Exception as e:
    print(f"연결 오류:{e}")


