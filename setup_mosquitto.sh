#!/bin/bash

# Mosquitto MQTT 브로커 설치 및 설정 스크립트

echo "Mosquitto MQTT 브로커 설치를 시작합니다..."

# 1. 시스템 업데이트
sudo apt update

# 2. Mosquitto 브로커 및 클라이언트 설치
sudo apt install -y mosquitto mosquitto-clients

# 3. Mosquitto 서비스 시작 및 자동 시작 설정
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# 4. Mosquitto 서비스 상태 확인
echo ""
echo "Mosquitto 서비스 상태 확인:"
sudo systemctl status mosquitto --no-pager

# 5. 기본 설정 파일 확인
echo ""
echo "Mosquitto 설정 파일 위치: /etc/mosquitto/mosquitto.conf"
echo ""
echo "설치 완료!"
echo ""
echo "테스트 방법:"
echo "1. 터미널 1에서 구독: mosquitto_sub -h localhost -t 'home/temp_sensor/data'"
echo "2. 터미널 2에서 발행: mosquitto_pub -h localhost -t 'home/temp_sensor/data' -m 'test'"
echo ""
echo "DHT11 센서 스크립트 실행: python3 MQTT_dht11_sensor.py"
