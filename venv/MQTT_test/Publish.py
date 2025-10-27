import paho.mqtt.client as mqtt
import time
import random

# MQTT 브로커 설정
MQTT_BROKER = "localhost"  # Mosquitto가 실행 중인 PC (현재 PC)
MQTT_PORT = 1883           # 기본 MQTT 포트
MQTT_TOPIC = "home/temp"   # 발행할 토픽

# 클라이언트 생성 및 연결
client = mqtt.Client()
try:
    print(f"Attempting to connect to broker at {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start() # 백그라운드에서 네트워크 루프 시작
 
    print("Publishing messages...")
     
    for i in range(1, 6):
        # 무작위 온도 값 생성
        temperature = 25.0 + round(random.uniform(-1.0, 1.0), 2)
        message = f"Room Temperature is {temperature}°C (Test {i})" 

        # 메시지 발행 (QoS는 기본값 0 사용)
        result = client.publish(MQTT_TOPIC, message)
        
        # 발행 결과 확인
        status = result[0]
        if status == mqtt.MQTT_ERR_SUCCESS:
            print(f"⬆️ Sent: '{message}' to topic '{MQTT_TOPIC}'")
        else:
            print(f"❌ Failed to send message (Status: {status})")

        time.sleep(1) # 1초 대기

finally:
    # 루프와 연결 종료
    client.loop_stop()
    client.disconnect()
    print("✅ Publisher disconnected.")