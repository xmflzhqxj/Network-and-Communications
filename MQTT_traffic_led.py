import paho.mqtt.client as mqtt

# 설정
MQTT_BROKER = "localhost"  # 라즈베리파이 자신
MQTT_TOPIC_PUB = "home/livingroom/traffic/set" # 신호등 제어 명령 토픽

# 센서 상태 저장소 (초기값: 모두 비활성)
sensor_states = {
    "pir": False,   # 인체감지
    "touch": False, # 터치
    "dark": False   # 어두움 (조도)
}

# 브로커 연결 시 실행되는 함수
def on_connect(client, userdata, flags, rc):
    print("Traffic Manager Connected")
    # 모든 센서 데이터 구독
    client.subscribe("home/livingroom/pir/state")
    client.subscribe("home/livingroom/touch/state")
    client.subscribe("home/livingroom/light/level")

# 메시지 수신 시 실행되는 함수
def on_message(client, userdata, msg):
    global sensor_states
    topic = msg.topic
    payload = msg.payload.decode()
    
    # 1. 데이터 업데이트 (센서 상태 판단)
    if "pir/state" in topic:
        sensor_states["pir"] = (payload == "DETECTED")
        print(f"PIR State: {sensor_states['pir']}")
        
    elif "touch/state" in topic:
        sensor_states["touch"] = (payload == "TOUCHED")
        print(f"Touch State: {sensor_states['touch']}")

    elif "light/level" in topic:
        # 조도 값(숫자)을 받아서 '어두움' 여부 판단
        try:
            lux = float(payload)
            # 기준값 1000 이상이면 어두움으로 판단 (환경에 맞게 수정 가능)
            is_dark = lux > 1000 
            if sensor_states["dark"] != is_dark: # 상태가 바뀔 때만 로그 출력
                sensor_states["dark"] = is_dark
                print(f"Dark Detected: {is_dark} (Value: {lux})")
        except:
            pass

    # 2. 트래픽 계산 및 명령 발행 (결정 내리기)
    decide_traffic_light(client)

# 신호등 색상 결정 함수
def decide_traffic_light(client):
    # 활성화된(True인) 센서 개수 세기
    active_count = sum(sensor_states.values())
    
    command = "GREEN"
    
    if active_count >= 3:
        command = "RED"    # 3개 이상 활성 -> 혼잡 (빨강)
    elif active_count == 2:
        command = "YELLOW" # 2개 활성 -> 주의 (노랑)
    else:
        command = "GREEN"  # 0~1개 활성 -> 원활 (초록)
        
    # 결정된 명령을 ESP32에게 전송 (Publish)
    print(f"Traffic Judge: Active {active_count} -> Command: {command}")
    client.publish(MQTT_TOPIC_PUB, command)

# 메인 실행 부분
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# 브로커 연결 및 루프 시작
try:
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nTraffic Manager Stopped")
    client.disconnect()