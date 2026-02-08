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

# MQTT 브로커 주소 설정. 라즈베리 파이 자체에서 서버를 돌리므로 로컬호스트로 설정
MQTT_BROKER = "localhost"

# 공부 및 착석 데이터를 저장할 파일 경로
DATA_FILE = "/home/pi/my_project/habit_data.json"

# 구글 제미나이 API 및 날씨 정보용 API 키 입력
GEMINI_API_KEY = "AIzaSyBVkV0oyoiqe0ImSaSNuGyg39F4YSBHj5c"
WEATHER_API_KEY = "4c4c765a0915abeed982b761bca2bdf1"
CITY_NAME = "Gimpo-si"

# 제미나이 AI 사용을 위한 클라이언트 설정
ai_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.0-flash"

# ==============================================================================
# 2. MQTT 토픽 정의
# ==============================================================================

# 아두이노 코드의 토픽과 정확히 일치해야 통신 가능

# ESP32에서 라즈베리 파이로 보내는 정보
TOPIC_PRESENCE      = "home/livingroom/presence"
TOPIC_LIGHT_LEVEL   = "home/livingroom/light/level"
TOPIC_SITTING_TIME  = "home/livingroom/sitting/time"
TOPIC_MODE_REPORT   = "home/livingroom/mode/report"
TOPIC_EXERCISE_DONE = "home/livingroom/exercise/done"

# 라즈베리 파이에서 ESP32로 명령을 내리는 토픽
TOPIC_LCD_LINE2     = "home/livingroom/lcd/line2"
TOPIC_RGB_SET       = "home/livingroom/rgb/set"
TOPIC_TRAFFIC_SET   = "home/livingroom/traffic/set"

# 기타 기능 및 가상 센서 데이터 토픽
TOPIC_SLEEP_START   = "home/livingroom/sleep/start"
TOPIC_ALARM_STOP    = "home/livingroom/alarm/stop"
TOPIC_FOCUS_END     = "home/livingroom/focus/end"
TOPIC_VIRTUAL_SENSOR = "home/temp_sensor/data"

# ==============================================================================
# 3. 전역 상태 관리
# ==============================================================================

# 현재 시스템의 상태를 저장하는 변수 모음
state = {
    "mode": 0,           # 0: 평상시, 1: 집중, 2: 취침 모드
    "presence": False,   # 재실 여부 확인
    "sitting_minutes": 0, # 착석 지속 시간
    "light_level": 100,  # 조도 센서 값. 100이 가장 밝음
    "is_away_pending": False, # 잠시 자리를 비웠는지 확인하는 플래그
    "away_pending_start": 0,  # 자리 비움 시작 시간 기록
    "needs_exercise": False   # 운동 필요 상태인지 확인
}

# ==============================================================================
# 4. 핵심 제어 로직
# ==============================================================================

def control_smart_lighting(client):
    # 방 밝기에 따라 LED 색상 및 밝기 자동 조절
    level = state["light_level"]
    
    # 방이 충분히 밝으면 LED 소등. 기준값 70
    if level > 70:
        client.publish(TOPIC_RGB_SET, json.dumps({"r": 0, "g": 0, "b": 0}))
        return
    
    # 어두울수록 LED를 밝게 켜기 위해 반비례 계산
    # 70이면 밝기 0, 0이면 밝기 1
    brightness = 1.0 - (level / 70.0)
    
    # 모드에 따른 기본 색상 설정
    if state["mode"] == 1:   base = {"r": 255, "g": 255, "b": 255} # 집중 모드는 백색
    elif state["mode"] == 0: base = {"r": 255, "g": 200, "b": 150} # 평상시 모드는 온백색
    elif state["mode"] == 2: base = {"r": 50, "g": 0, "b": 0}      # 취침 모드는 적색
    else:                    base = {"r": 255, "g": 255, "b": 255}
    
    # 설정된 색상에 계산된 밝기를 적용하여 최종 색상 결정
    color = {
        "r": int(base["r"] * brightness),
        "g": int(base["g"] * brightness),
        "b": int(base["b"] * brightness)
    }
    client.publish(TOPIC_RGB_SET, json.dumps(color))

def update_status_by_time(client):
    # 착석 시간에 따른 신호등 색상 및 LCD 메시지 제어
    mins = state["sitting_minutes"]
    
    # 사람이 없으면 빨간불 대기 상태 유지
    if not state["presence"]:
        client.publish(TOPIC_TRAFFIC_SET, "RED")
        return

    # 30분 미만이면 초록불 점등
    if mins < 30:
        client.publish(TOPIC_TRAFFIC_SET, "GREEN")
        # 시간이 0분으로 리셋된 직후 모드별 안내 메시지 전송
        if mins == 0:
            if state["mode"] == 1:
                client.publish(TOPIC_LCD_LINE2, "Focusing...", retain=True)
            elif state["mode"] == 2:
                # 취침 모드에서는 날씨 대신 터치 안내 문구 표시
                client.publish(TOPIC_LCD_LINE2, "Press Touch!", retain=True)
                
    # 30분에서 40분 사이면 노란불로 경고 표시
    elif mins < 40:
        client.publish(TOPIC_TRAFFIC_SET, "YELLOW")
        
    # 40분 초과 시 빨간불 점등 및 운동 알림 메시지 전송
    else:
        client.publish(TOPIC_TRAFFIC_SET, "RED")
        client.publish(TOPIC_LCD_LINE2, "Need Exercise!", retain=True)

# ==============================================================================
# 5. 유틸리티 함수
# ==============================================================================

def publish_weather_to_lcd(client):
    # 평상시 모드가 아니면 날씨 정보 전송 중단
    # 집중 모드나 취침 모드 메시지 덮어쓰기 방지
    if state["mode"] != 0:
        return

    # API를 통해 김포시 날씨 정보 조회
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": CITY_NAME, "appid": WEATHER_API_KEY, "units": "metric", "lang": "en"}
    try:
        res = requests.get(url, params=params, timeout=5).json()
        if res.get("cod") == 200:
            temp = round(res["main"]["temp"], 1)
            desc = res["weather"][0]["description"].lower()
            keyword = "Cloud"
            if "clear" in desc or "sun" in desc: keyword = "Sunny"
            elif "rain" in desc: keyword = "Rain"
            elif "snow" in desc: keyword = "Snow"
            
            # 운동 알림 상태가 아닐 경우에만 날씨 정보 표시
            if not state["needs_exercise"]:
                client.publish(TOPIC_LCD_LINE2, f"{keyword} {temp}C", retain=True)
                client.publish(TOPIC_VIRTUAL_SENSOR, json.dumps({"temp": temp, "humidity": res["main"]["humidity"]}))
    except: pass

def save_data_to_json(minutes, note="Session"):
    # 착석 시간을 JSON 파일로 저장
    if minutes < 1: return
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = {"date": today, "minutes": minutes, "type": note, "timestamp": datetime.now().isoformat()}
    
    if not os.path.exists(DATA_FILE): data = {"sessions": [], "daily_stats": {}}
    else:
        try: 
            with open(DATA_FILE, "r") as f: data = json.load(f)
        except: data = {"sessions": [], "daily_stats": {}}

    data["sessions"].append(new_entry)
    if today not in data["daily_stats"]: data["daily_stats"][today] = 0
    data["daily_stats"][today] += minutes

    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)
    print(f"[SAVE] Saved {minutes} mins ({note})")

def calculate_wake_up_time(client):
    # 제미나이 AI에게 기상 시간 문의
    print("[AI] Calculating wake-up time...")
    try:
        res = ai_client.models.generate_content(model=GEMINI_MODEL, contents="현재 취침 시작. 기상 시간을 'Wake: HH:MM AM' 형식으로만 답해.")
        client.publish(TOPIC_LCD_LINE2, res.text.strip(), retain=True)
    except: 
        # AI 응답 실패 시 기본값 07:30 AM 표시
        client.publish(TOPIC_LCD_LINE2, "Wake: 07:30 AM", retain=True)

# ==============================================================================
# 6. MQTT 콜백
# ==============================================================================

def on_connect(client, userdata, flags, rc, properties=None):
    print("[MQTT] Connected")
    client.subscribe("home/livingroom/#")
    
    # 서버 접속 즉시 이전 메시지 잔상 제거
    # 평상시 모드라면 날씨 로딩 메시지 표시 후 즉시 날씨 정보 갱신
    if state["mode"] == 0:
        client.publish(TOPIC_LCD_LINE2, "Loading Weather...", retain=True)
        publish_weather_to_lcd(client)

def on_message(client, userdata, msg):
    # ESP32로부터 수신된 메시지 처리
    topic = msg.topic
    payload = msg.payload.decode()

    # 착석 시간 데이터 수신 시
    if topic == TOPIC_SITTING_TIME:
        try:
            val = int(payload)
            state["sitting_minutes"] = val
            # 동기화 로직 적용
            # 라즈베리 파이가 늦게 켜져도 시간이 0분 이상이면 재실 상태로 강제 전환
            if val >= 0 and not state["presence"]:
                print("[SYNC] Time detected. Forcing state to PRESENT.")
                state["presence"] = True
                state["is_away_pending"] = False
            update_status_by_time(client)
        except: pass

    # 운동 완료 및 5회 터치 수신 시
    elif topic == TOPIC_EXERCISE_DONE:
        state["sitting_minutes"] = 0
        state["needs_exercise"] = False
        update_status_by_time(client) # 시간 리셋으로 인한 초록불 전환
        client.publish(TOPIC_LCD_LINE2, "Great Job!", retain=True)

    # 조도 센서 데이터 수신 시
    elif topic == TOPIC_LIGHT_LEVEL:
        try:
            state["light_level"] = int(payload)
            control_smart_lighting(client)
        except: pass

    # 모드 변경 신호 수신 시
    elif topic == TOPIC_MODE_REPORT:
        state["mode"] = int(payload)
        control_smart_lighting(client)
        
        # 모드 변경 즉시 LCD 화면 갱신
        if state["mode"] == 0: 
            client.publish(TOPIC_LCD_LINE2, "Loading Weather...", retain=True)
            publish_weather_to_lcd(client)
        elif state["mode"] == 1:
            client.publish(TOPIC_LCD_LINE2, "Focusing...", retain=True)
        elif state["mode"] == 2:
            client.publish(TOPIC_LCD_LINE2, "Press Touch!", retain=True)

    # 집중 모드 강제 종료 시
    elif topic == TOPIC_FOCUS_END:
        save_data_to_json(state["sitting_minutes"], "Focus Mode")
        state["sitting_minutes"] = 0
        client.publish(TOPIC_LCD_LINE2, "Session Saved!")

    # 수면 모드 시작 시
    elif topic == TOPIC_SLEEP_START:
        calculate_wake_up_time(client)
    
    # 알람 종료 시
    elif topic == TOPIC_ALARM_STOP:
        client.publish(TOPIC_LCD_LINE2, "Alarm Off")

    # 재실 감지 센서 처리
    elif topic == TOPIC_PRESENCE:
        if payload == "PRESENT":
            state["presence"] = True
            state["is_away_pending"] = False
            update_status_by_time(client)
        elif payload == "AWAY":
            # 부재 감지 시 즉시 처리하지 않고 60초 대기
            if state["presence"] and not state["is_away_pending"]:
                state["is_away_pending"] = True
                state["away_pending_start"] = time.time()
                client.publish(TOPIC_TRAFFIC_SET, "RED")

def graceful_shutdown(signum, frame):
    # 프로그램 강제 종료 시 데이터 저장 후 안전하게 종료
    if state["presence"] and state["sitting_minutes"] > 0:
        save_data_to_json(state["sitting_minutes"], f"Interrupted ({state['mode']})")
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_shutdown)

# ==============================================================================
# 7. 메인 실행
# ==============================================================================

if __name__ == "__main__":
    # MQTT 클라이언트 설정 및 연결
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try: client.connect(MQTT_BROKER, 1883, 60)
    except: sys.exit(1)

    client.loop_start()

    last_weather_check = 0
    try:
        while True:
            now = time.time()
            # 60초 이상 부재 시 퇴실 처리 및 데이터 저장
            if state["is_away_pending"] and (now - state["away_pending_start"] > 60):
                save_data_to_json(state["sitting_minutes"], "Normal Session")
                state["presence"] = False
                state["is_away_pending"] = False
                state["sitting_minutes"] = 0
            
            # 날씨는 30분에 한 번씩만 업데이트
            # 평상시 모드일 경우에만 업데이트 수행
            if state["mode"] == 0 and (now - last_weather_check > 1800):
                publish_weather_to_lcd(client)
                last_weather_check = now
                
            time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect()