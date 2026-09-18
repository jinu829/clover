import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import 'wishlist_screen.dart';
import 'cart_screen.dart';
import 'order_history_screen.dart';
import 'settings_screen.dart';
import 'fitting_room_screen.dart';

/// 마이페이지: 프로필 + 통계(주문/찜/포인트) + 내 아바타 + 메뉴.
class MyPageScreen extends StatelessWidget {
  const MyPageScreen({super.key});

  void _go(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffold,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // 상단 제목
            Row(
              children: [
                const Text('마이페이지', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: AppColors.textDark)),
                const Spacer(),
                const Icon(Icons.home_outlined, color: AppColors.textDark, size: 26),
                const SizedBox(width: 16),
                GestureDetector(
                  onTap: () => _go(context, const SettingsScreen()),
                  child: const Icon(Icons.settings_outlined, color: AppColors.textDark, size: 26),
                ),
              ],
            ),
            const SizedBox(height: 24),
            // 프로필
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
                        Text('홍길동', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.textDark)),
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
            // 통계 3개 (찜은 실제 개수, 탭 시 이동)
            ListenableBuilder(
              listenable: AppState.I,
              builder: (context, _) {
                return Row(
                  children: [
                    _stat(context, '12', '주문', () => _go(context, const OrderHistoryScreen())),
                    _stat(context, '${AppState.I.likedCount}', '찜', () => _go(context, const WishlistScreen())),
                    _stat(context, '3,500', '포인트', null),
                  ],
                );
              },
            ),
            const SizedBox(height: 28),
            // 내 아바타
            Row(
              children: const [
                Text('내 아바타', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textDark)),
                Spacer(),
                Text('관리', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.symmetric(vertical: 30, horizontal: 20),
              decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(20)),
              child: Column(
                children: [
                  Container(
                    width: 110,
                    height: 110,
                    decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: 0.15), shape: BoxShape.circle),
                    child: const Icon(Icons.person, color: AppColors.primary, size: 60),
                  ),
                  const SizedBox(height: 18),
                  const Text('3D 아바타가 준비되었습니다',
                      style: TextStyle(fontSize: 15, color: AppColors.textDark, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: SizedBox(
                          height: 48,
                          child: ElevatedButton(
                            onPressed: () => _go(context, const FittingRoomScreen()),
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
            const SizedBox(height: 28),
            // 메뉴
            Container(
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
              child: Column(
                children: [
                  _menu(context, Icons.shopping_bag_outlined, '장바구니', () => _go(context, const CartScreen())),
                  const Divider(height: 1),
                  _menu(context, Icons.receipt_long_outlined, '주문 내역', () => _go(context, const OrderHistoryScreen())),
                  const Divider(height: 1),
                  _menu(context, Icons.favorite_border, '찜한 상품', () => _go(context, const WishlistScreen())),
                  const Divider(height: 1),
                  _menu(context, Icons.settings_outlined, '설정', () => _go(context, const SettingsScreen())),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _stat(BuildContext context, String value, String label, VoidCallback? onTap) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Column(
          children: [
            Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: AppColors.primary)),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(color: AppColors.textGray)),
          ],
        ),
      ),
    );
  }

  Widget _menu(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    return ListTile(
      leading: Icon(icon, color: AppColors.textDark),
      title: Text(label, style: const TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w600)),
      trailing: const Icon(Icons.chevron_right, color: AppColors.textGray),
      onTap: onTap,
    );
  }
}
