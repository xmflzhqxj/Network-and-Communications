import time
import board      
import adafruit_dht

sensor_pin = board.D17 

try:
    
    dht_device = adafruit_dht.DHT11(sensor_pin, use_pulseio=False)
except RuntimeError as init_error:
    print(f"센서 초기화 실패: {init_error.args[0]}")
    print("GPIO 핀이 올바르게 연결되었는지, sudo로 실행해야 하는지 확인하세요.")

    dht_device = None

def temperature_humidity_read():
    
    # 초기화가 실패했으면 함수를 실행하지 않습니다.
    if dht_device is None:
        print("센서가 초기화되지 않아 값을 읽을 수 없습니다.")
        return (None, None)

    try:
        # 센서 값 읽기 시도
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity

        if temperature_c is not None and humidity is not None:
            
            return (temperature_c, humidity)
        else:
            # 센서가 None을 반환한 경우 (일시적 오류)
            return (None, None)

    except RuntimeError as error:
        
        print(f"센서 읽기 오류: {error.args[0]} (잠시 후 재시도)")
        return (None, None)
    except Exception as error:
        # 그 외 예기치 못한 심각한 오류
        print(f"심각한 오류 발생: {error}")
        dht_device.exit() # 이 경우 장치를 정리합니다.
        raise error # 오류를 상위로 전달


if __name__ == "__main__":
    print("온습도 측정을 시작합니다. (Ctrl+C로 종료)")
    
    try:
        while True:
            # 정의한 함수 호출
            temp, hum = temperature_humidity_read()
            
            # 함수가 반환한 값을 확인하고 출력
            if temp is not None and hum is not None:
                print(f" 온도: {temp:.1f}°C  |  습도: {hum:.1f}%")
            else:
                print("센서 읽기 실패! (재시도 중...)")

            # 딜레이는 함수 밖의 루프에서 관리
            time.sleep(2.0)
            
    except KeyboardInterrupt:
        print("\n측정을 종료합니다.")
    finally:
        # 프로그램 종료 시 센서 자원 정리
        if dht_device is not None:
            dht_device.exit()