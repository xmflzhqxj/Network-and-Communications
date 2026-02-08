import asyncio
from aiocoap import *

# 1. 클라이언트 메인 함수
async def main():
    # CoAP 컨텍스트 생성
    protocol = await Context.create_client_context()

    # CoAP 서버 주소 및 리소스 경로
    # 서버가 실행 중인 PC의 IP 주소를 입력하세요. (여기서는 로컬호스트 가정)
    server_address = "192.168.35.57" 
    uri = f"coap://{server_address}/time" 

    print(f"--- CoAP 서버에 GET 요청: {uri} ---")

    # 2. GET 요청 메시지 생성
    request = Message(code=GET, uri=uri)

    try:
        # 3. 요청 전송 및 응답 수신
        response = await protocol.request(request).response
        
        # 4. 결과 출력
        print("Response Code:", response.code)
        print("Response Payload:", response.payload.decode('utf-8'))

    except Exception as e:
        print("Error:", e)
    finally:
        # 5. 프로토콜 컨텍스트 닫기 (비연결형 통신의 이점)
        await protocol.shutdown()

if __name__ == "__main__":
    asyncio.run(main())