import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// 마이페이지: 프로필 + 통계(주문/찜/포인트) + 내 아바타 카드.
class MyPageScreen extends StatelessWidget {
  const MyPageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffold,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // ── 상단 제목 ──
            Row(
              children: const [
                Text(
                  '마이페이지',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: AppColors.textDark),
                ),
                Spacer(),
                Icon(Icons.home_outlined, color: AppColors.textDark, size: 26),
                SizedBox(width: 16),
                Icon(Icons.settings_outlined, color: AppColors.textDark, size: 26),
              ],
            ),
            const SizedBox(height: 24),
            // ── 프로필 ──
            Row(
              children: [
                Container(
                  width: 76,
                  height: 76,
                  decoration: const BoxDecoration(color: AppColors.primary, shape: BoxShape.circle),
                  child: const Icon(Icons.person, color: Colors.white, size: 40),
                ),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Row(
                      children: [
                        Text(
                          '홍길동',
                          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.textDark),
                        ),
                        SizedBox(width: 6),
                        Icon(Icons.keyboard_arrow_down, color: AppColors.textDark),
                      ],
                    ),
                    SizedBox(height: 4),
                    Text('clover@example.com', style: TextStyle(color: AppColors.textGray)),
                  ],
                ),
                const Spacer(),
                const Icon(Icons.edit_outlined, color: AppColors.textGray),
              ],
            ),
            const SizedBox(height: 28),
            // ── 통계 3개 ──
            Row(
              children: const [
                _StatItem(value: '12', label: '주문'),
                _StatItem(value: '24', label: '찜'),
                _StatItem(value: '3,500', label: '포인트'),
              ],
            ),
            const SizedBox(height: 28),
            // ── 내 아바타 헤더 ──
            Row(
              children: const [
                Text(
                  '내 아바타',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textDark),
                ),
                Spacer(),
                Text('관리', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 14),
            // ── 아바타 카드 ──
            Container(
              padding: const EdgeInsets.symmetric(vertical: 30, horizontal: 20),
              decoration: BoxDecoration(
                color: AppColors.primarySoft,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                children: [
                  Container(
                    width: 110,
                    height: 110,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.15),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.person, color: AppColors.primary, size: 60),
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    '3D 아바타가 준비되었습니다',
                    style: TextStyle(fontSize: 15, color: AppColors.textDark, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      // 아바타 보기 (초록 채운 버튼)
                      Expanded(
                        child: SizedBox(
                          height: 48,
                          child: ElevatedButton(
                            onPressed: () {},
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.primary,
                              foregroundColor: Colors.white,
                              elevation: 0,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                            child: const Text('아바타 보기', style: TextStyle(fontWeight: FontWeight.w700)),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      // 재스캔 (흰 배경 테두리 버튼)
                      Expanded(
                        child: SizedBox(
                          height: 48,
                          child: OutlinedButton(
                            onPressed: () {},
                            style: OutlinedButton.styleFrom(
                              backgroundColor: Colors.white,
                              foregroundColor: AppColors.textDark,
                              side: const BorderSide(color: AppColors.border),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                            child: const Text('재스캔', style: TextStyle(fontWeight: FontWeight.w700)),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 통계 항목 하나 (숫자 + 라벨). 예: 12 / 주문
class _StatItem extends StatelessWidget {
  final String value;
  final String label;
  const _StatItem({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: AppColors.primary),
          ),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: AppColors.textGray)),
        ],
      ),
    );
  }
}
