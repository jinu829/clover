import 'package:flutter/foundation.dart';

/// 사용자 체형 치수 (Unity로 넘길 데이터).
class UserMeasurements {
  final double heightCm; // 키
  final double? waistCm; // 허리둘레(추정)
  const UserMeasurements({required this.heightCm, this.waistCm});

  Map<String, dynamic> toJson() => {
        'height': heightCm,
        if (waistCm != null) 'waist': waistCm,
      };
}

/// Flutter ↔ Unity 통신 다리(Bridge).
///
/// ⚠️ 지금은 Unity 프로젝트가 없어서 **가짜(Mock)** 로 동작한다.
/// 실제 연동 시 바꿀 곳은 딱 두 군데:
///   1) [_sendToUnity] → `unityController.postMessage(오브젝트, 메서드, 데이터)`
///   2) 화면의 "Unity View 자리" → `flutter_unity_widget`의 `UnityWidget`
/// 그러면 아래 6개 기능이 그대로 실제 Unity와 연결된다.
class UnityBridge extends ChangeNotifier {
  UnityBridge._();
  static final UnityBridge I = UnityBridge._(); // 앱 어디서나 UnityBridge.I

  // ── Unity에서 받은 상태(렌더링 결과) ──
  bool ready = false; // 아바타·의류 로딩 완료 여부
  String? topId; // 현재 착용 상의 옷 ID
  String? bottomId; // 현재 착용 하의 옷 ID
  String animation = 'idle'; // 현재 애니메이션 (idle/walk/pose)
  String? fitFeedback; // Unity가 보내온 핏 피드백 텍스트
  final List<String> log = []; // 주고받은 신호 기록 (데모용)

  int _fbIndex = 0;

  void _record(String line) {
    log.insert(0, line);
    if (log.length > 15) log.removeLast();
  }

  /// [Flutter → Unity] 신호 보내기.
  /// 실제 연동 시 이 줄이 `unityController.postMessage('AvatarManager', method, data)` 가 된다.
  void _sendToUnity(String method, String data) {
    _record('▶ Unity로: $method("$data")');
    // TODO(unity): unityController?.postMessage('AvatarManager', method, data);
  }

  // ── 기능②: Unity View 활성화 + 기본 데이터(치수) 전달 ──
  void loadAvatar(UserMeasurements m) {
    ready = false;
    _sendToUnity('LoadAvatar', m.toJson().toString());
    notifyListeners();
    // (가짜) 1.2초 뒤 Unity가 "로딩 완료"를 보내온다고 가정 → 기능③ 렌더링 결과 수신
    Future.delayed(const Duration(milliseconds: 1200), () {
      ready = true;
      _record('◀ Unity에서: 아바타·의류 로딩 완료');
      notifyListeners();
    });
  }

  // ── 기능④: 상의/하의 교체 명령 전달 ──
  void changeTop(String clothId) {
    topId = clothId;
    _sendToUnity('ChangeTop', clothId);
    _receiveFitFeedback(); // 교체하면 Unity가 핏 피드백을 계산해 보내옴(가짜)
    notifyListeners();
  }

  void changeBottom(String clothId) {
    bottomId = clothId;
    _sendToUnity('ChangeBottom', clothId);
    _receiveFitFeedback();
    notifyListeners();
  }

  // ── 기능⑥: 아바타 애니메이션 제어 ──
  void playAnimation(String name) {
    animation = name;
    _sendToUnity('PlayAnimation', name);
    notifyListeners();
  }

  // ── 기능⑤: 플랫폼 채널로 핏 피드백 수신 (가짜) ──
  // 실제로는 Unity가 계산해서 Flutter로 보내주는 값이다.
  void _receiveFitFeedback() {
    const samples = [
      '어깨가 잘 맞아요. 전체적으로 편안한 핏이에요.',
      '허리가 약간 여유 있어요. 딱 맞는 핏을 원하면 한 사이즈 아래도 좋아요.',
      '기장이 적당하고 실루엣이 깔끔해요. 잘 어울려요!',
    ];
    fitFeedback = samples[_fbIndex % samples.length];
    _fbIndex++;
    _record('◀ Unity에서: 핏 피드백 수신');
  }

  void reset() {
    ready = false;
    topId = null;
    bottomId = null;
    animation = 'idle';
    fitFeedback = null;
    _fbIndex = 0;
    log.clear();
    notifyListeners();
  }
}
