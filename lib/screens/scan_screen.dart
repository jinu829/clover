import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../widgets/camera_capture.dart';

/// 스캔 화면: 가이드 → 촬영/선택 → 완료. 단계가 바뀌므로 StatefulWidget.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  bool _capturing = false; // 촬영 화면 표시 중
  Uint8List? _captured; // 완료된(선택된) 사진

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          // 상태에 따라 3가지 화면 중 하나
          child: _captured != null
              ? _doneView()
              : _capturing
                  ? _captureView()
                  : _guideView(),
        ),
      ),
    );
  }

  // 1) 가이드 화면 (어두운 카드)
  Widget _guideView() {
    final guides = <(String, String)>[
      ('📍', '밝은 장소에서 촬영해주세요'),
      ('🧍', '전신이 보이도록 2m 거리에서 촬영'),
      ('🔄', '정면, 측면, 후면 순서로 촬영'),
      ('👕', '몸에 맞는 옷을 입어주세요'),
    ];
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(color: AppColors.darkCard, borderRadius: BorderRadius.circular(24)),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: 10),
          Container(
            width: 120,
            height: 120,
            decoration: const BoxDecoration(color: Color(0xFF0E6B4E), shape: BoxShape.circle),
            child: const Icon(Icons.camera_alt_outlined, color: AppColors.primary, size: 54),
          ),
          const SizedBox(height: 28),
          const Text('스캔 준비', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: Colors.white)),
          const SizedBox(height: 12),
          const Text('정확한 아바타 생성을 위해\n아래 가이드를 따라주세요',
              textAlign: TextAlign.center, style: TextStyle(color: Colors.white70, fontSize: 15, height: 1.4)),
          const SizedBox(height: 28),
          ...guides.map(
            (g) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(
                children: [
                  Text(g.$1, style: const TextStyle(fontSize: 22)),
                  const SizedBox(width: 16),
                  Expanded(child: Text(g.$2, style: const TextStyle(color: Colors.white, fontSize: 15))),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 54,
            child: ElevatedButton(
              onPressed: () => setState(() => _capturing = true), // 촬영 화면으로
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              child: const Text('촬영 시작', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            ),
          ),
        ],
      ),
    );
  }

  // 2) 촬영 화면 (카메라/갤러리)
  Widget _captureView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            IconButton(
              onPressed: () => setState(() => _capturing = false), // 가이드로 되돌아감
              icon: const Icon(Icons.arrow_back, color: AppColors.textDark),
            ),
            const Text('사진 촬영', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.textDark)),
          ],
        ),
        const SizedBox(height: 4),
        const Padding(
          padding: EdgeInsets.only(left: 4),
          child: Text('전신이 잘 보이는 사진을 찍거나 골라주세요.', style: TextStyle(color: AppColors.textGray)),
        ),
        const SizedBox(height: 24),
        // 재사용 카메라 위젯 — 사용하기 누르면 완료 화면으로
        CameraCapture(
          onConfirmed: (photo) => setState(() {
            _captured = photo;
            _capturing = false;
          }),
        ),
      ],
    );
  }

  // 3) 완료 화면 (선택된 사진 미리보기)
  Widget _doneView() {
    return Column(
      children: [
        const SizedBox(height: 6),
        const Align(
          alignment: Alignment.centerLeft,
          child: Text('촬영 완료', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.textDark)),
        ),
        const SizedBox(height: 16),
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Image.memory(_captured!, height: 320, width: double.infinity, fit: BoxFit.cover),
        ),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(14)),
          child: const Row(
            children: [
              Icon(Icons.auto_awesome, color: AppColors.primary),
              SizedBox(width: 12),
              Expanded(
                child: Text('이 사진으로 아바타를 만들 준비가 됐어요! (실제 생성은 서버 연동 예정)',
                    style: TextStyle(color: AppColors.textDark, fontSize: 13.5, height: 1.5)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () => setState(() {
                  _captured = null;
                  _capturing = true; // 다시 촬영 화면으로
                }),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  side: const BorderSide(color: AppColors.border),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('다시 촬영', style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w700)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ElevatedButton(
                onPressed: () {
                  AppState.I.createAvatar(); // 아바타 생성됨으로 표시
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('아바타가 생성됐어요! 이제 옷을 입혀볼 수 있어요 ✨'), duration: Duration(seconds: 2)),
                  );
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('아바타 만들기', style: TextStyle(fontWeight: FontWeight.w700)),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
