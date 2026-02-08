import json
import os
import time
import signal
import sys
import requests
from datetime import datetime
import paho.mqtt.client as mqtt
from google import genai

# ==============================================================================
# 1. 설정 및 API 키
# ==============================================================================
MQTT_BROKER = "localhost"
DATA_FILE = "/home/pi/my_project/habit_data.json"

GEMINI_API_KEY = "AIzaSyBVkV0oyoiqe0ImSaSNuGyg39F4YSBHj5c"
WEATHER_API_KEY = "4c4c765a0915abeed982b761bca2bdf1"
CITY_NAME = "Gimpo-si"

ai_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.0-flash"

# ==============================================================================
# 2. MQTT 토픽 정의 
# ==============================================================================
TOPIC_PRESENCE      = "home/livingroom/presence"
TOPIC_LIGHT_LEVEL   = "home/livingroom/light/level"
TOPIC_SITTING_TIME  = "home/livingroom/sitting/time"
TOPIC_MODE_REPORT   = "home/livingroom/mode/report"
TOPIC_SLEEP_START   = "home/livingroom/sleep/start"  
TOPIC_ALARM_STOP    = "home/livingroom/alarm/stop"
TOPIC_FOCUS_END     = "home/livingroom/focus/end"
TOPIC_EXERCISE_DONE = "home/livingroom/exercise/done"

TOPIC_LCD_LINE2     = "home/livingroom/lcd/line2"
TOPIC_RGB_SET       = "home/livingroom/rgb/set"
TOPIC_TRAFFIC_SET   = "home/livingroom/traffic/set"
TOPIC_VIRTUAL_SENSOR = "home/temp_sensor/data"

# ==============================================================================
# 3. 전역 상태 관리
# ==============================================================================
state = {
    "mode": 0,
    "presence": False,
    "sitting_minutes": 0,
    "light_level": 100,
    "is_away_pending": False,
    "away_pending_start": 0,
    "needs_exercise": False  # 운동 필요 상태 플래그
}

# ==============================================================================
# 4. 핵심 제어 로직
# ==============================================================================

def update_status_by_time(client):
    """앉은 시간과 운동 여부에 따라 신호등과 LCD 결정"""
    mins = state["sitting_minutes"]
    
    if not state["presence"]:
        client.publish(TOPIC_TRAFFIC_SET, "RED")
        return

    # [신호등 단계별 제어]
    if mins < 30:
        state["needs_exercise"] = False
        client.publish(TOPIC_TRAFFIC_SET, "GREEN")
    elif mins < 40:
        client.publish(TOPIC_TRAFFIC_SET, "YELLOW")
    else:
        # 40분 이상 앉아 있을 때
        state["needs_exercise"] = True
        client.publish(TOPIC_TRAFFIC_SET, "RED")
        # ESP32 LCD에 운동하라는 메시지 강제 전송
        client.publish(TOPIC_LCD_LINE2, "Need Exercise!", retain=True)

def control_smart_lighting(client):
    """조도 기반 RGB 조명 제어"""
    if state["light_level"] > 30:
        client.publish(TOPIC_RGB_SET, json.dumps({"r": 0, "g": 0, "b": 0}))
        return
    
    color = {"r": 0, "g": 0, "b": 0}
    if state["mode"] == 1: color = {"r": 255, "g": 255, "b": 255} # 집중: 백색
    elif state["mode"] == 0: color = {"r": 100, "g": 100, "b": 100} # 평상시: 흐린 백색
    elif state["mode"] == 2: color = {"r": 50, "g": 0, "b": 0}    # 취침: 적색
    client.publish(TOPIC_RGB_SET, json.dumps(color))

# ==============================================================================
# 5. 유틸리티 함수
# ==============================================================================

def publish_weather_to_lcd(client):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": CITY_NAME, "appid": WEATHER_API_KEY, "units": "metric", "lang": "en"}
    try:
        res = requests.get(url, params=params, timeout=5).json()
        if res.get("cod") == 200:
            temp = round(res["main"]["temp"], 1)
            desc = res["weather"][0]["description"].lower()
            keyword = "Sunny" if "clear" in desc else "Cloudy"
            # 운동 메시지 상태가 아닐 때만 날씨 표시
            if not state["needs_exercise"]:
                client.publish(TOPIC_LCD_LINE2, f"{keyword} {temp}C", retain=True)
    except: pass

def save_data_to_json(minutes, note="Session"):
    if minutes < 1: return
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = {"date": today, "minutes": minutes, "type": note, "timestamp": datetime.now().isoformat()}
    # (파일 저장 로직 생략 - 기존과 동일)
    print(f"[SAVE] {minutes} mins saved.")

# ==============================================================================
# 6. MQTT 콜백
# ==============================================================================

def on_connect(client, userdata, flags, rc, properties=None):
    print("[MQTT] Connected successfully")
    client.subscribe("home/livingroom/#")
    publish_weather_to_lcd(client)

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()

    # [A] 시간 데이터 수신 -> 신호등 업데이트
    if topic == TOPIC_SITTING_TIME:
        try:
            state["sitting_minutes"] = int(payload)
            update_status_by_time(client)
        except: pass

    # [B] 운동 완료 신호 (ESP32에서 5번 터치)
    elif topic == TOPIC_EXERCISE_DONE:
        print("[EXERCISE] User completed exercise! Resetting...")
        state["sitting_minutes"] = 0
        state["needs_exercise"] = False
        client.publish(TOPIC_TRAFFIC_SET, "GREEN")
        client.publish(TOPIC_LCD_LINE2, "Great Job!", retain=True)

    # [C] 조도 센서 -> RGB 제어
    elif topic == TOPIC_LIGHT_LEVEL:
        try:
            state["light_level"] = int(payload)
            control_smart_lighting(client)
        except: pass

    # [D] 모드 변경 보고
    elif topic == TOPIC_MODE_REPORT:
        state["mode"] = int(payload)
        control_smart_lighting(client)
        if state["mode"] == 0: publish_weather_to_lcd(client)

    # [E] 수면 및 기타
    elif topic == TOPIC_SLEEP_START:
        prompt = "현재 취침 시작. 기상 시간을 'Wake: HH:MM AM' 형식으로만 답해."
        try:
            res = ai_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            client.publish(TOPIC_LCD_LINE2, res.text.strip(), retain=True)
        except: pass

    elif topic == TOPIC_PRESENCE:
        if payload == "PRESENT":
            state["presence"] = True
            state["is_away_pending"] = False
        elif payload == "AWAY":
            state["is_away_pending"] = True
            state["away_pending_start"] = time.time()
            client.publish(TOPIC_TRAFFIC_SET, "RED")

# ==============================================================================
# 7. 메인 루프
# ==============================================================================

if __name__ == "__main__":
    # [수정] 최신 Paho-MQTT v2 API 버전 적용
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, 1883, 60)
    except:
        print("[ERROR] MQTT Broker connection failed")
        sys.exit(1)

    client.loop_start()

    try:
        while True:
            now = time.time()
            # 쿨다운 자동 저장
            if state["is_away_pending"] and (now - state["away_pending_start"] > 60):
                save_data_to_json(state["sitting_minutes"], "Normal Session")
                state["presence"] = False
                state["is_away_pending"] = False
                state["sitting_minutes"] = 0
            time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect()