import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// 스캔 준비 화면: 어두운 카드 안에 촬영 가이드를 보여준다.
class ScanScreen extends StatelessWidget {
  const ScanScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // 촬영 가이드: (이모지, 설명)
    final guides = <(String, String)>[
      ('📍', '밝은 장소에서 촬영해주세요'),
      ('🧍', '전신이 보이도록 2m 거리에서 촬영'),
      ('🔄', '정면, 측면, 후면 순서로 촬영'),
      ('👕', '몸에 맞는 옷을 입어주세요'),
    ];

    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(
              color: AppColors.darkCard,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(height: 10),
                // 카메라 아이콘
                Container(
                  width: 120,
                  height: 120,
                  decoration: const BoxDecoration(color: Color(0xFF0E6B4E), shape: BoxShape.circle),
                  child: const Icon(Icons.camera_alt_outlined, color: AppColors.primary, size: 54),
                ),
                const SizedBox(height: 28),
                const Text(
                  '스캔 준비',
                  style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: Colors.white),
                ),
                const SizedBox(height: 12),
                const Text(
                  '정확한 아바타 생성을 위해\n아래 가이드를 따라주세요',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white70, fontSize: 15, height: 1.4),
                ),
                const SizedBox(height: 28),
                // 가이드 목록 (... 은 리스트를 펼쳐서 넣는 문법)
                ...guides.map(
                  (g) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    child: Row(
                      children: [
                        Text(g.$1, style: const TextStyle(fontSize: 22)),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Text(g.$2, style: const TextStyle(color: Colors.white, fontSize: 15)),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                // 촬영 시작 버튼
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton(
                    onPressed: () {},
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
          ),
        ),
      ),
    );
  }
}
