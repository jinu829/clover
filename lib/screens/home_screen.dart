import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../models/product.dart';
import '../state/app_state.dart';
import 'product_detail_screen.dart';
import 'cart_screen.dart';

/// 홈 화면: 상단바 + 초록 배너 + 카테고리 + 인기 상품.
/// 값이 바뀌는 게 없어서(그냥 보여주기만) StatelessWidget.
class HomeScreen extends StatelessWidget {
  final VoidCallback? onScan; // 스캔 탭으로 이동
  final void Function(String category)? onCategory; // 쇼핑 탭으로 이동(카테고리 지정)
  const HomeScreen({super.key, this.onScan, this.onCategory});

  @override
  Widget build(BuildContext context) {
    // 카테고리 4개: (이름, 이모지)
    final categories = <(String, String)>[
      ('상의', '👕'),
      ('하의', '👖'),
      ('원피스', '👗'),
      ('아우터', '🧥'),
    ];

    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
          children: [
            // ── 상단바: 로고 + 아이콘들 ──
            Row(
              children: [
                const Text(
                  'Clover',
                  style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: AppColors.primary),
                ),
                const Spacer(),
                _topIcon(Icons.search, 0),
                _topIcon(Icons.notifications_none, 2),
                _cartIcon(context),
                _topIcon(Icons.person_outline, 0),
              ],
            ),
            const SizedBox(height: 16),
            // ── 초록 배너 ──
            Container(
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppColors.primary, AppColors.primaryDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '나만의 3D 아바타',
                          style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Colors.white),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          '스캔하고 옷을 입혀보세요',
                          style: TextStyle(color: Colors.white70, fontSize: 14),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: onScan, // 스캔 탭으로 이동
                          icon: const Icon(Icons.camera_alt_outlined, size: 18),
                          label: const Text('스캔 시작', style: TextStyle(fontWeight: FontWeight.w700)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: AppColors.primary,
                            elevation: 0,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: 84,
                    height: 84,
                    decoration: BoxDecoration(
                      color: Colors.white24,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Icon(Icons.crop_free, color: Colors.white, size: 40),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
            // ── 카테고리 ──
            const Text(
              '카테고리',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textDark),
            ),
            const SizedBox(height: 14),
            Row(
              children: categories.map((c) {
                return Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 5),
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: () => onCategory?.call(c.$1), // 이 카테고리로 쇼핑 이동
                      child: Column(
                      children: [
                        Container(
                          height: 72,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.05),
                                blurRadius: 10,
                                offset: const Offset(0, 3),
                              ),
                            ],
                          ),
                          child: Center(child: Text(c.$2, style: const TextStyle(fontSize: 30))),
                        ),
                        const SizedBox(height: 8),
                        Text(c.$1, style: const TextStyle(fontSize: 13, color: AppColors.textDark)),
                      ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 28),
            // ── 인기 상품 헤더 ──
            Row(
              children: const [
                Icon(Icons.trending_up, color: AppColors.primary, size: 22),
                SizedBox(width: 6),
                Text(
                  '인기 상품',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.textDark),
                ),
                Spacer(),
                Text('전체보기', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 14),
            // ── 인기 상품 가로 스크롤 ──
            SizedBox(
              height: 200,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: sampleProducts.length,
                separatorBuilder: (_, _) => const SizedBox(width: 14),
                itemBuilder: (ctx, i) => _popularCard(ctx, sampleProducts[i]),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // 상단 아이콘 (badge > 0 이면 빨간 알림 뱃지 표시)
  Widget _topIcon(IconData icon, int badge) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        IconButton(onPressed: () {}, icon: Icon(icon, color: AppColors.textDark, size: 25)),
        if (badge > 0)
          Positioned(
            right: 4,
            top: 4,
            child: Container(
              padding: const EdgeInsets.all(5),
              decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
              child: Text(
                '$badge',
                style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
              ),
            ),
          ),
      ],
    );
  }

  // 장바구니 아이콘 (담긴 개수 뱃지 + 탭하면 장바구니로)
  Widget _cartIcon(BuildContext context) {
    return ListenableBuilder(
      listenable: AppState.I,
      builder: (context, _) {
        final count = AppState.I.cartCount;
        return Stack(
          clipBehavior: Clip.none,
          children: [
            IconButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const CartScreen()),
              ),
              icon: const Icon(Icons.shopping_bag_outlined, color: AppColors.textDark, size: 25),
            ),
            if (count > 0)
              Positioned(
                right: 4,
                top: 4,
                child: Container(
                  padding: const EdgeInsets.all(5),
                  decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                  child: Text('$count',
                      style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ),
          ],
        );
      },
    );
  }

  // 인기 상품 카드 (가로 스크롤용)
  Widget _popularCard(BuildContext context, Product p) {
    return GestureDetector(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => ProductDetailScreen(product: p)),
      ),
      child: Container(
      width: 150,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10, offset: const Offset(0, 3)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: 120,
            decoration: const BoxDecoration(
              color: AppColors.primarySoft,
              borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            ),
            child: Center(child: Text(p.emoji, style: const TextStyle(fontSize: 48))),
          ),
          Padding(
            padding: const EdgeInsets.all(10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  p.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textDark),
                ),
                const SizedBox(height: 4),
                Text(
                  '${formatPrice(p.price)}원',
                  style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700),
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
