// lib/main.dart
import 'package:flutter/material.dart';
import 'mqtt_service.dart';
import 'dart:async';
import 'dart:convert';
import 'package:mqtt_client/mqtt_client.dart';

void main() {
  runApp(const MyApp());
}

// --- 1. 앱 루트 ---
class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '나만의 IoT 앱',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const MyHomePage(title: '나만의 IoT 시스템'),
    );
  }
}

// --- 2. 홈 페이지 (대시보드) ---
class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  // MQTT 서비스 인스턴스
  final MqttService mqttService = MqttService();
  StreamSubscription? _mqttSubscription;
  String connectionStatus = '연결 중...';
  
  // 기기 목록 데이터 (동적으로 추가 가능하도록 변경)
  List<Map<String, String>> devices = [
    {'id': 'living_room_light', 'name': '거실 조명', 'icon': 'lightbulb'},
    {'id': 'bedroom_fan', 'name': '침실 선풍기', 'icon': 'air'},
    {'id': 'temp_sensor', 'name': '온습도 센서', 'icon': 'thermostat'},
  ];
  
  // 이미 추가된 장치 ID를 추적 (중복 방지)
  final Set<String> _discoveredDeviceIds = {};

  @override
  void initState() {
    super.initState();
    // 초기 장치들을 발견된 장치 목록에 추가
    for (var device in devices) {
      _discoveredDeviceIds.add(device['id']!);
    }
    _connectMqtt();
  }

  // MQTT 연결 및 메시지 수신 설정
  Future<void> _connectMqtt() async {
    try {
      await mqttService.connect();
      setState(() {
        connectionStatus = mqttService.isConnected ? '연결됨' : '연결 실패';
      });
      
      // 모든 장치의 상태와 알림을 받기 위한 와일드카드 토픽 구독
      if (mqttService.isConnected) {
        // home/{device_id}/status - 장치 상태 메시지
        mqttService.subscribe('home/+/status');
        // home/{device_id}/announce - 장치 등록/알림 메시지
        mqttService.subscribe('home/+/announce');
        // home/{device_id}/data - 센서 데이터 메시지
        mqttService.subscribe('home/+/data');
      }
      
      // MQTT 메시지 수신 스트림 구독
      _mqttSubscription = mqttService.updates?.listen((messages) {
        for (var message in messages) {
          final topic = message.topic;
          final payload = message.payload as MqttPublishMessage;
          final messageString = MqttPublishPayload.bytesToStringAsString(payload.payload.message);
          
          // 토픽에서 장치 ID 추출 및 새 장치 감지
          _handleMqttMessage(topic, messageString);
        }
      });
    } catch (e) {
      setState(() {
        connectionStatus = '연결 실패: $e';
      });
    }
  }

  // MQTT 메시지를 처리하고 새 장치를 자동으로 추가하는 함수
  void _handleMqttMessage(String topic, String payload) {
    // 토픽 패턴: home/{device_id}/status 또는 home/{device_id}/announce 등
    final topicParts = topic.split('/');
    if (topicParts.length >= 2 && topicParts[0] == 'home') {
      final deviceId = topicParts[1];
      
      // 이미 발견된 장치가 아니면 새로 추가
      if (!_discoveredDeviceIds.contains(deviceId)) {
        _discoveredDeviceIds.add(deviceId);
        _addNewDevice(deviceId, payload, topicParts.length > 2 ? topicParts[2] : '');
      }
    }
  }

  // 새 장치를 목록에 추가하는 함수
  void _addNewDevice(String deviceId, String payload, String topicType) {
    // 장치 이름과 아이콘을 자동으로 결정
    String deviceName = deviceId.replaceAll('_', ' '); // 기본 이름 (device_id에서 _를 공백으로)
    String iconType = 'settings'; // 기본 아이콘
    
    // payload가 JSON 형식이면 파싱 시도
    try {
      final jsonData = jsonDecode(payload);
      if (jsonData is Map<String, dynamic>) {
        // JSON에서 장치 정보 추출
        if (jsonData.containsKey('name')) {
          deviceName = jsonData['name'].toString();
        }
        if (jsonData.containsKey('icon')) {
          iconType = jsonData['icon'].toString();
        } else if (jsonData.containsKey('type')) {
          // type으로부터 icon 추론
          final type = jsonData['type'].toString().toLowerCase();
          if (type.contains('light') || type.contains('lamp')) {
            iconType = 'lightbulb';
          } else if (type.contains('fan') || type.contains('vent')) {
            iconType = 'air';
          } else if (type.contains('sensor') || type.contains('temp')) {
            iconType = 'thermostat';
          } else if (type.contains('lock')) {
            iconType = 'lock';
          }
        }
      }
    } catch (_) {
      // JSON 파싱 실패 시 device_id로부터 추론
      final lowerId = deviceId.toLowerCase();
      if (lowerId.contains('light') || lowerId.contains('lamp') || lowerId.contains('led')) {
        iconType = 'lightbulb';
        deviceName = deviceId.contains('living') ? '거실 조명' : 
                     deviceId.contains('bedroom') ? '침실 조명' : 
                     deviceId.contains('kitchen') ? '주방 조명' : '조명';
      } else if (lowerId.contains('fan') || lowerId.contains('vent')) {
        iconType = 'air';
        deviceName = deviceId.contains('bedroom') ? '침실 선풍기' : '선풍기';
      } else if (lowerId.contains('temp') || lowerId.contains('sensor') || lowerId.contains('humidity')) {
        iconType = 'thermostat';
        deviceName = '온습도 센서';
      } else if (lowerId.contains('motor')) {
        iconType = 'settings';
        deviceName = '모터';
      } else if (lowerId.contains('lock') || lowerId.contains('door')) {
        iconType = 'lock';
        deviceName = '도어락';
      }
    }
    
    // 새 장치 추가
    setState(() {
      devices.add({
        'id': deviceId,
        'name': deviceName,
        'icon': iconType,
      });
    });
  }

  @override
  void dispose() {
    _mqttSubscription?.cancel();
    mqttService.disconnect();
    super.dispose();
  }

  // 기기를 클릭했을 때 상세 페이지로 이동하는 함수
  void _navigateToDevicePage(Map<String, String> device) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => DeviceDetailPage(
          device: device,
          mqttService: mqttService,
        ),
      ),
    );
  }

  // "작은 네모" 하나를 그리는 함수
  Widget _buildDeviceCard(Map<String, String> device) {
    // 아이콘 이름에 맞는 실제 아이콘을 매핑
    IconData iconData;
    switch (device['icon']) {
      case 'lightbulb':
        iconData = Icons.lightbulb_outline;
        break;
      case 'air':
        iconData = Icons.air_outlined;
        break;
      case 'thermostat':
        iconData = Icons.thermostat_outlined;
        break;
      case 'lock':
        iconData = Icons.lock_outline;
        break;
      default:
        iconData = Icons.settings_outlined;
    }

    return InkWell(
      onTap: () {
        _navigateToDevicePage(device); // 클릭 시 페이지 이동
      },
      borderRadius: BorderRadius.circular(12.0),
      child: Card(
        elevation: 4.0, // 카드에 그림자 효과
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12.0),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              iconData,
              size: 48.0,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 16.0), // 아이콘과 텍스트 사이 간격
            Text(
              device['name']!,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16.0, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title), // '나만의 IoT 시스템'
        actions: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Center(
              child: Text(
                connectionStatus,
                style: TextStyle(
                  fontSize: 12.0,
                  color: mqttService.isConnected ? Colors.green : Colors.red,
                ),
              ),
            ),
          ),
        ],
      ),
      // body를 GridView로 변경
      body: GridView.builder(
        padding: const EdgeInsets.all(16.0), // 그리드 전체의 바깥쪽 여백
        // 그리드 레이아웃 설정
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,    // 한 줄에 2개의 네모
          crossAxisSpacing: 16.0, // 네모 사이의 가로 간격
          mainAxisSpacing: 16.0,  // 네모 사이의 세로 간격
        ),
        itemCount: devices.length, // 기기 목록의 개수만큼 만듦
        itemBuilder: (context, index) {
          // _buildDeviceCard 함수를 호출하여 네모 하나를 그림
          return _buildDeviceCard(devices[index]);
        },
      ),
    );
  }
}

// --- 3. 상세 제어 페이지 ---
class DeviceDetailPage extends StatefulWidget {
  // 홈 페이지에서 전달받은 기기 정보를 저장할 변수
  final Map<String, String> device;
  final MqttService mqttService;

  const DeviceDetailPage({
    super.key,
    required this.device,
    required this.mqttService,
  });

  @override
  State<DeviceDetailPage> createState() => _DeviceDetailPageState();
}

class _DeviceDetailPageState extends State<DeviceDetailPage> {
  // 이 페이지의 상태 (예: 스위치가 켜졌는지)
  bool _isSwitchedOn = false;
  String _sensorData = '데이터 수신 대기 중...';
  StreamSubscription? _mqttSubscription;

  @override
  void initState() {
    super.initState();
    _setupMqttSubscription();
  }

  // MQTT 구독 설정
  void _setupMqttSubscription() {
    // 센서 데이터를 받기 위한 토픽 구독
    if (widget.device['id'] == 'temp_sensor') {
      final topic = 'home/${widget.device['id']}/status';
      widget.mqttService.subscribe(topic);
      
      // 메시지 수신 스트림 구독
      _mqttSubscription = widget.mqttService.updates?.listen((messages) {
        for (var message in messages) {
          final topic = message.topic;
          if (topic.contains(widget.device['id']!)) {
            final payload = message.payload as MqttPublishMessage;
            final messageString = MqttPublishPayload.bytesToStringAsString(
              payload.payload.message,
            );
            setState(() {
              _sensorData = messageString;
            });
          }
        }
      });
    }
  }

  @override
  void dispose() {
    _mqttSubscription?.cancel();
    super.dispose();
  }

  // MQTT로 제어 명령을 보내는 함수
  void _controlDevice(bool value) {
    setState(() {
      _isSwitchedOn = value;
    });
    
    // MQTT 발행(Publish) 로직
    if (widget.mqttService.isConnected) {
      String topic = 'home/${widget.device['id']}/set';
      String payload = value ? "ON" : "OFF";
      
      widget.mqttService.publish(topic, payload);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('MQTT 연결이 되어있지 않습니다.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    // 아이콘 데이터 (홈페이지와 동일)
    IconData iconData;
    switch (widget.device['icon']) {
      case 'lightbulb':
        iconData = Icons.lightbulb;
        break;
      case 'air':
        iconData = Icons.air;
        break;
      case 'thermostat':
        iconData = Icons.thermostat;
        break;
      case 'lock':
        iconData = Icons.lock;
        break;
      default:
        iconData = Icons.settings;
    }

    return Scaffold(
      appBar: AppBar(
        // 전달받은 기기 이름으로 AppBar 제목 설정
        title: Text(widget.device['name']!),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              iconData,
              size: 100.0,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 24.0),
            Text(
              '${widget.device['name']!}의 제어판',
              style: const TextStyle(fontSize: 20.0, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 24.0),
            
            // 제어 위젯(스위치, 슬라이더 등)
            if (widget.device['id'] == 'living_room_light' ||
                widget.device['id'] == 'bedroom_fan' ||
                widget.device['id'] == 'pi_motor')
              SwitchListTile(
                title: const Text('기기 전원'),
                value: _isSwitchedOn,
                onChanged: (bool value) {
                  _controlDevice(value); // 스위치를 누르면 MQTT 제어 함수 호출
                },
              ),

            if (widget.device['id'] == 'temp_sensor')
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Text(
                      '현재 센서 데이터:',
                      style: TextStyle(fontSize: 18.0, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8.0),
                    Text(
                      _sensorData,
                      style: const TextStyle(fontSize: 18.0),
                    ),
                  ],
                ),
              ),
            
            const SizedBox(height: 24.0),
            Text(
              'MQTT 상태: ${widget.mqttService.isConnected ? "연결됨" : "연결 안됨"}',
              style: TextStyle(
                fontSize: 14.0,
                color: widget.mqttService.isConnected ? Colors.green : Colors.red,
              ),
            ),
          ],
        ),
      ),
    );
  }
}


