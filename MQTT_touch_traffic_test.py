import paho.mqtt.client as mqtt

# 설정
MQTT_BROKER = "localhost" 
MQTT_TOPIC_PUB = "home/livingroom/traffic/set" # 신호등 제어

# 현재 신호등 상태 (0: OFF, 1: GREEN, 2: YELLOW, 3: RED)
current_step = 0 
step_commands = ["OFF", "GREEN", "YELLOW", "RED"]

def on_connect(client, userdata, flags, rc):
    print("✅ Manual Traffic Controller Connected")
    # 터치 센서만 구독
    client.subscribe("home/livingroom/touch/state")
    
    # 시작 시 끄기 명령 전송
    client.publish(MQTT_TOPIC_PUB, "OFF")

def on_message(client, userdata, msg):
    global current_step
    topic = msg.topic
    payload = msg.payload.decode()
    
    # 터치 센서가 'TOUCHED' 될 때만 반응 (눌렀을 때만)
    if topic == "home/livingroom/touch/state" and payload == "TOUCHED":
        
        # 1. 단계 증가 (0 -> 1 -> 2 -> 3 -> 0 ...)
        current_step += 1
        if current_step >= len(step_commands):
            current_step = 0 # 다시 처음으로
            
        # 2. 현재 단계에 맞는 명령 찾기
        next_command = step_commands[current_step]
        
        # 3. 명령 발행 (Publish)
        print(f"👆 터치 감지! 다음 단계: {next_command} (Step: {current_step})")
        client.publish(MQTT_TOPIC_PUB, next_command)

# 메인 실행
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopped")
    client.disconnect()