import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../models/product.dart';
import '../unity/unity_bridge.dart';

/// 피팅룸(라커룸) — Unity 3D 아바타 뷰가 들어갈 화면.
/// 지금은 UnityBridge(가짜)로 6개 연동 기능을 모두 동작시킨다.
/// 실제 연동 시: 아래 _unityView 자리에 flutter_unity_widget의 UnityWidget을 넣는다.
class FittingRoomScreen extends StatefulWidget {
  const FittingRoomScreen({super.key});

  @override
  State<FittingRoomScreen> createState() => _FittingRoomScreenState();
}

class _FittingRoomScreenState extends State<FittingRoomScreen> {
  @override
  void initState() {
    super.initState();
    // 기능②: 화면이 열리면 치수를 넘겨 아바타 로드 (예시 치수)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      UnityBridge.I.reset();
      UnityBridge.I.loadAvatar(const UserMeasurements(heightCm: 170, waistCm: 78));
    });
  }

  String _emojiOf(String? id) {
    if (id == null) return '·';
    final list = sampleProducts.where((e) => e.id == id);
    return list.isEmpty ? '·' : list.first.emoji;
  }

  String _nameOf(String? id) {
    if (id == null) return '없음';
    final list = sampleProducts.where((e) => e.id == id);
    return list.isEmpty ? '없음' : list.first.name;
  }

  @override
  Widget build(BuildContext context) {
    final tops = sampleProducts.where((p) => p.category == '상의').toList();
    final bottoms = sampleProducts.where((p) => p.category == '하의').toList();

    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: AppColors.textDark,
        title: const Text('피팅룸', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      ),
      body: ListenableBuilder(
        listenable: UnityBridge.I,
        builder: (context, _) {
          final b = UnityBridge.I;
          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _unityView(b), // 기능①③: Unity View 자리 + 렌더링 상태
                if (b.fitFeedback != null) ...[
                  const SizedBox(height: 16),
                  _feedbackCard(b.fitFeedback!), // 기능⑤: 핏 피드백 표시
                ],
                const SizedBox(height: 24),
                _sectionTitle('상의 교체'),
                const SizedBox(height: 10),
                _clothRow(tops, b.topId, (id) => b.changeTop(id)), // 기능④
                const SizedBox(height: 20),
                _sectionTitle('하의 교체'),
                const SizedBox(height: 10),
                _clothRow(bottoms, b.bottomId, (id) => b.changeBottom(id)), // 기능④
                const SizedBox(height: 24),
                _sectionTitle('아바타 동작'),
                const SizedBox(height: 10),
                _animControls(b), // 기능⑥
                const SizedBox(height: 24),
                _sectionTitle('신호 로그 (Flutter ↔ Unity)'),
                const SizedBox(height: 10),
                _logView(b),
                const SizedBox(height: 20),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _sectionTitle(String t) =>
      Text(t, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textDark));

  // 기능①③: Unity 3D View 자리 (실제로는 UnityWidget)
  Widget _unityView(UnityBridge b) {
    return Container(
      width: double.infinity,
      height: 320,
      decoration: BoxDecoration(color: AppColors.darkCard, borderRadius: BorderRadius.circular(20)),
      child: !b.ready
          ? const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(color: AppColors.primary),
                  SizedBox(height: 16),
                  Text('3D 아바타 로딩 중...', style: TextStyle(color: Colors.white70)),
                ],
              ),
            )
          : Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(_emojiOf(b.topId), style: const TextStyle(fontSize: 34)), // 상의
                const Text('🧍', style: TextStyle(fontSize: 72)), // 아바타
                Text(_emojiOf(b.bottomId), style: const TextStyle(fontSize: 34)), // 하의
                const SizedBox(height: 10),
                Text('상의: ${_nameOf(b.topId)}  ·  하의: ${_nameOf(b.bottomId)}',
                    style: const TextStyle(color: Colors.white70, fontSize: 12)),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                  decoration: BoxDecoration(color: Colors.white12, borderRadius: BorderRadius.circular(20)),
                  child: Text('애니메이션: ${_animLabel(b.animation)}',
                      style: const TextStyle(color: Colors.white, fontSize: 12)),
                ),
                const SizedBox(height: 8),
                const Text('Unity 3D View 자리 (연동 예정)', style: TextStyle(color: Colors.white38, fontSize: 11)),
              ],
            ),
    );
  }

  Widget _feedbackCard(String text) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(14)),
      child: Row(
        children: [
          const Icon(Icons.thumb_up_alt_outlined, color: AppColors.primary),
          const SizedBox(width: 12),
          Expanded(child: Text(text, style: const TextStyle(color: AppColors.textDark, height: 1.5, fontSize: 13.5))),
        ],
      ),
    );
  }

  // 기능④: 옷 목록 → 탭하면 Unity로 교체 명령
  Widget _clothRow(List<Product> items, String? selectedId, void Function(String id) onSelect) {
    return SizedBox(
      height: 92,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (_, i) {
          final p = items[i];
          final active = p.id == selectedId;
          return GestureDetector(
            onTap: () => onSelect(p.id),
            child: Container(
              width: 72,
              decoration: BoxDecoration(
                color: active ? AppColors.primarySoft : Colors.white,
                border: Border.all(color: active ? AppColors.primary : AppColors.border),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(p.emoji, style: const TextStyle(fontSize: 28)),
                  const SizedBox(height: 4),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: Text(p.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 10, color: active ? AppColors.primary : AppColors.textGray)),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // 기능⑥: 애니메이션 버튼
  Widget _animControls(UnityBridge b) {
    Widget btn(String name, String label, IconData icon) {
      final active = b.animation == name;
      return Expanded(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: GestureDetector(
            onTap: () => b.playAnimation(name),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                color: active ? AppColors.primary : Colors.white,
                border: Border.all(color: active ? AppColors.primary : AppColors.border),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Icon(icon, color: active ? Colors.white : AppColors.textDark, size: 22),
                  const SizedBox(height: 4),
                  Text(label,
                      style: TextStyle(
                          color: active ? Colors.white : AppColors.textDark,
                          fontSize: 12,
                          fontWeight: FontWeight.w600)),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return Row(
      children: [
        btn('idle', '정지', Icons.accessibility_new),
        btn('walk', '걷기', Icons.directions_walk),
        btn('pose', '포즈', Icons.self_improvement),
      ],
    );
  }

  String _animLabel(String a) => switch (a) {
        'walk' => '걷기',
        'pose' => '포즈',
        _ => '정지',
      };

  // 신호 로그 (데모용 — 실제 주고받는 메시지 확인)
  Widget _logView(UnityBridge b) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
      child: b.log.isEmpty
          ? const Text('아직 주고받은 신호가 없어요.', style: TextStyle(color: AppColors.textGray, fontSize: 12))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: b.log
                  .map((line) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Text(
                          line,
                          style: TextStyle(
                            fontSize: 12,
                            color: line.startsWith('▶') ? AppColors.primary : AppColors.textGray,
                          ),
                        ),
                      ))
                  .toList(),
            ),
    );
  }
}
