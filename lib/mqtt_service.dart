// mqtt_service => MQTT 통신을 어떻게 할지
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';
import 'dart:async';

class MqttService {
  // RPi의 MQTT_BROKER IP 주소 (PC IP)
  final String brokerIp = '10.122.26.104'; 
  final int port = 1883;
  final String clientIdentifier = 'flutter_app_${DateTime.now().millisecondsSinceEpoch}';
  
  late MqttServerClient client;
  bool isConnected = false;
  Completer<void>? _connectionCompleter;

  MqttService() {
    client = MqttServerClient(brokerIp, clientIdentifier);
    client.port = port;
    client.logging(on: true); // 디버깅 로그
    client.keepAlivePeriod = 60;
    client.onDisconnected = _onDisconnected;
    client.onConnected = _onConnected;
    client.onAutoReconnect = _onAutoReconnect;
  }

  // 1. 브로커 연결 함수
  Future<void> connect() async {
    try {
      // 새로운 Completer 생성
      _connectionCompleter = Completer<void>();
      
      // 연결 시도
      final connMessage = MqttConnectMessage()
          .withClientIdentifier(clientIdentifier)
          .startClean()
          .withWillQos(MqttQos.atLeastOnce);
      client.connectionMessage = connMessage;
      
      await client.connect();
      
      // 연결 완료 대기 (최대 5초)
      await _connectionCompleter!.future.timeout(
        const Duration(seconds: 5),
        onTimeout: () {
          throw TimeoutException('MQTT 연결 타임아웃');
        },
      );
    } catch (e) {
      isConnected = false;
      if (_connectionCompleter != null && !_connectionCompleter!.isCompleted) {
        _connectionCompleter!.completeError(e);
      }
      rethrow;
    }
  }

  void _onConnected() {
    isConnected = true;
    if (_connectionCompleter != null && !_connectionCompleter!.isCompleted) {
      _connectionCompleter!.complete();
    }
  }

  void _onDisconnected() {
    isConnected = false;
  }

  void _onAutoReconnect() {}

  // 2. 메시지 발행 (Publish) 함수
  void publish(String topic, String message) {
    if (isConnected) {
      try {
        final builder = MqttClientPayloadBuilder();
        builder.addString(message);
        client.publishMessage(topic, MqttQos.atLeastOnce, builder.payload!);
      } catch (_) {}
    }
  }
  
  // 3. 토픽 구독 (Subscribe) 함수 (와일드카드 토픽 지원)
  void subscribe(String topic) {
    if (isConnected) {
      try {
        client.subscribe(topic, MqttQos.atLeastOnce);
      } catch (_) {}
    }
  }

  // 4. 구독 해제 (Unsubscribe) 함수
  void unsubscribe(String topic) {
    if (isConnected) {
      try {
        client.unsubscribe(topic);
      } catch (_) {}
    }
  }

  // 5. 연결 해제 함수
  void disconnect() {
    try {
      if (isConnected) {
        client.disconnect();
      }
    } catch (_) {} finally {
      isConnected = false;
    }
  }

  // 6. 메시지 수신 스트림
  // (StatefulWidget에서 이 스트림을 listen하여 UI를 업데이트)
  Stream<List<MqttReceivedMessage<MqttMessage>>>? get updates => client.updates;
  
  // 7. 연결 상태 확인 (읽기 전용)
  bool get connectionStatus => isConnected;
}


