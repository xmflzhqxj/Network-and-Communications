import paho.mqtt.client as mqtt

# MQTT 브로커 설정
MQTT_BROKER = "localhost"  # Mosquitto가 실행 중인 PC (현재 PC)
MQTT_PORT = 1883           # 기본 MQTT 포트
MQTT_TOPIC = "home/temp"   # 구독할 토픽
   
# 브로커 연결 성공 시 호출되는 콜백 함수
def on_connect(client, userdata, flags, rc):
    # rc=0이면 연결 성공을 의미
    print(f"✅ Broker connected! Result code: {rc}")
    # 연결 성공 시, 토픽을 구독합니다.
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribing to topic: {MQTT_TOPIC}")

# 메시지를 수신했을 때 호출되는 콜백 함수
def on_message(client, userdata, msg):
    # 수신된 메시지를 디코딩하여 출력합니다.
    print(f"➡️ Received Message - Topic: {msg.topic}, Payload: {msg.payload.decode()}")

# 클라이언트 생성 및 설정
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# 브로커 연결 시도 및 루프 시작
try:
    print(f"Attempting to connect to broker at {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    # 루프를 영원히 실행하여 네트워크 트래픽을 처리하고 콜백 함수를 대기합니다.
    client.loop_forever()
except Exception as e:
    print(f"❌ Connection error: {e}")