import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../models/product.dart';
import '../widgets/product_card.dart';

/// 쇼핑 화면: 검색바 + 카테고리 칩 + 상품 그리드.
/// 선택된 카테고리가 바뀌면 목록이 바뀌므로 StatefulWidget.
class ShoppingScreen extends StatefulWidget {
  const ShoppingScreen({super.key});

  @override
  State<ShoppingScreen> createState() => _ShoppingScreenState();
}

class _ShoppingScreenState extends State<ShoppingScreen> {
  final List<String> _categories = const ['전체', '상의', '하의', '원피스', '아우터'];
  String _selected = '전체'; // 현재 선택된 카테고리

  @override
  Widget build(BuildContext context) {
    // 선택된 카테고리에 맞게 상품 걸러내기
    final products = _selected == '전체'
        ? sampleProducts
        : sampleProducts.where((p) => p.category == _selected).toList();

    return Scaffold(
      backgroundColor: AppColors.scaffold,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── 헤더 ──
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'CLOVER FITTING ROOM',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primary,
                          letterSpacing: 1,
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        '쇼핑',
                        style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: AppColors.textDark),
                      ),
                    ],
                  ),
                  const Spacer(),
                  Container(
                    width: 44,
                    height: 44,
                    decoration: const BoxDecoration(color: AppColors.primarySoft, shape: BoxShape.circle),
                    child: const Icon(Icons.checkroom, color: AppColors.primary),
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.home_outlined, color: AppColors.textDark, size: 28),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // ── 검색바 ──
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                child: Row(
                  children: const [
                    Icon(Icons.search, color: AppColors.textGray),
                    SizedBox(width: 10),
                    Text('상품을 검색하세요', style: TextStyle(color: AppColors.textGray)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            // ── 카테고리 칩 (가로 스크롤) ──
            SizedBox(
              height: 40,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 20),
                itemCount: _categories.length,
                separatorBuilder: (_, _) => const SizedBox(width: 8),
                itemBuilder: (_, i) {
                  final cat = _categories[i];
                  final active = cat == _selected;
                  return GestureDetector(
                    // 칩을 누르면 선택 카테고리를 바꾸고 -> 목록이 다시 그려짐
                    onTap: () => setState(() => _selected = cat),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: active ? AppColors.primary : AppColors.chipBg,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        cat,
                        style: TextStyle(
                          color: active ? Colors.white : AppColors.textDark,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 16),
            // ── 개수 + 필터/정렬 ──
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(
                children: [
                  Text(
                    '총 ${products.length}개 상품',
                    style: const TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w600),
                  ),
                  const Spacer(),
                  _smallButton(Icons.tune, '필터'),
                  const SizedBox(width: 8),
                  _smallButton(Icons.filter_list, '추천순'),
                ],
              ),
            ),
            const SizedBox(height: 12),
            // ── 상품 그리드 ──
            Expanded(
              child: GridView.builder(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                // maxCrossAxisExtent: 카드 한 개 최대 너비. 화면이 넓으면 열이 자동으로 늘어난다.
                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                  maxCrossAxisExtent: 220,
                  crossAxisSpacing: 14,
                  mainAxisSpacing: 14,
                  childAspectRatio: 0.68,
                ),
                itemCount: products.length,
                itemBuilder: (_, i) => ProductCard(product: products[i]),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // 필터 / 추천순 같은 작은 버튼
  Widget _smallButton(IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppColors.textDark),
          const SizedBox(width: 5),
          Text(label, style: const TextStyle(fontSize: 13, color: AppColors.textDark)),
        ],
      ),
    );
  }
}
