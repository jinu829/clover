import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../widgets/product_card.dart';

/// 찜한 상품만 모아 보여주는 화면.
class WishlistScreen extends StatelessWidget {
  const WishlistScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: AppColors.textDark,
        title: const Text('찜한 상품', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      ),
      // 전역 상태(찜)를 듣고 있다가 바뀌면 목록 갱신
      body: ListenableBuilder(
        listenable: AppState.I,
        builder: (context, _) {
          final items = AppState.I.likedProducts;
          if (items.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.favorite_border, size: 56, color: AppColors.textGray),
                  SizedBox(height: 12),
                  Text('찜한 상품이 없어요', style: TextStyle(color: AppColors.textGray)),
                ],
              ),
            );
          }
          return GridView.builder(
            padding: const EdgeInsets.all(20),
            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
              maxCrossAxisExtent: 220,
              crossAxisSpacing: 14,
              mainAxisSpacing: 14,
              childAspectRatio: 0.68,
            ),
            itemCount: items.length,
            itemBuilder: (_, i) => ProductCard(product: items[i]),
          );
        },
      ),
    );
  }
}
