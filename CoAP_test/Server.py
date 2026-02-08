import asyncio
import datetime
from aiocoap import *
from aiocoap.resource import Resource, Site

# 1. 리소스 클래스 정의 (여기서는 "시간" 리소스)
class TimeResource(Resource):
    """현재 시간을 응답하는 리소스"""

    def __init__(self):
        super().__init__()
        # Content-Format: 텍스트/일반 형식 (50)을 응답할 것임을 지정
        self.content_format = 0 # text/plain

    async def render_get(self, request):
        """GET 요청이 들어왔을 때 실행되는 메서드"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = f"Current Time: {current_time}".encode('utf-8')
        
        # 응답 코드 2.05 Content와 함께 페이로드를 반환
        return Message(code=CONTENT, payload=payload)

# 2. 서버 메인 함수
async def main():
    # CoAP 사이트 (서버) 생성
    root = Site()
    
    # "time" 경로에 TimeResource를 등록
    # 서버 주소는 coap://[서버IP]/time 이 됩니다.
    root.add_resource(['time'], TimeResource())

    # CoAP 프로토콜 컨텍스트를 생성하고, Site를 루트로 설정
    await Context.create_server_context(root, bind=('192.168.35.57', 5683))
    
    print("CoAP 서버 시작. 주소: coap://[로컬IP]:5683/time")
    
    # 서버가 종료되지 않도록 무한 루프 대기
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCoAP 서버 종료.")