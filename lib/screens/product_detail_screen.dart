import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';
import '../models/product.dart';
import '../state/app_state.dart';
import 'tryon_result_screen.dart';

/// 상품 상세 화면. 사이즈 선택·찜 상태가 바뀌므로 StatefulWidget.
class ProductDetailScreen extends StatefulWidget {
  final Product product;
  const ProductDetailScreen({super.key, required this.product});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  final List<String> _sizes = const ['S', 'M', 'L', 'XL'];
  String _selectedSize = 'M';

  @override
  Widget build(BuildContext context) {
    final p = widget.product;
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: AppColors.textDark,
        title: const Text('상품 상세', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
        actions: [
          // 찜(하트) — 전역 상태를 듣고 있다가 바뀌면 아이콘 갱신
          ListenableBuilder(
            listenable: AppState.I,
            builder: (context, _) {
              final liked = AppState.I.isLiked(p);
              return IconButton(
                icon: Icon(liked ? Icons.favorite : Icons.favorite_border,
                    color: liked ? Colors.redAccent : AppColors.textDark),
                onPressed: () => AppState.I.toggleLike(p),
              );
            },
          ),
          IconButton(icon: const Icon(Icons.share_outlined), onPressed: () {
            // 상품 공유 문구를 클립보드에 복사
            Clipboard.setData(ClipboardData(
                text: '클로버 추천 상품: ${p.name} (${formatPrice(p.price)}원) 🍀'));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('공유 문구를 복사했어요 📋'), duration: Duration(seconds: 1)),
            );
          }),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 이미지
            Container(
              width: double.infinity,
              height: 300,
              color: AppColors.primarySoft,
              child: Center(child: Text(p.emoji, style: const TextStyle(fontSize: 120))),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 카테고리 뱃지
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                    decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(20)),
                    child: Text(p.category, style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700, fontSize: 12)),
                  ),
                  const SizedBox(height: 12),
                  Text(p.name, style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w800, color: AppColors.textDark)),
                  const SizedBox(height: 8),
                  Text('${formatPrice(p.price)}원', style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w800, color: AppColors.primary)),
                  const SizedBox(height: 20),
                  const Divider(),
                  const SizedBox(height: 16),
                  // 사이즈 선택
                  const Text('사이즈 선택', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.textDark)),
                  const SizedBox(height: 12),
                  Row(
                    children: _sizes.map((s) {
                      final active = s == _selectedSize;
                      return Padding(
                        padding: const EdgeInsets.only(right: 10),
                        child: GestureDetector(
                          onTap: () => setState(() => _selectedSize = s),
                          child: Container(
                            width: 54,
                            height: 48,
                            alignment: Alignment.center,
                            decoration: BoxDecoration(
                              color: active ? AppColors.primary : Colors.white,
                              border: Border.all(color: active ? AppColors.primary : AppColors.border),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(s, style: TextStyle(color: active ? Colors.white : AppColors.textDark, fontWeight: FontWeight.w700)),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 20),
                  const Divider(),
                  const SizedBox(height: 16),
                  // 설명
                  const Text('상품 설명', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.textDark)),
                  const SizedBox(height: 10),
                  Text(p.description, style: const TextStyle(fontSize: 14.5, color: AppColors.textGray, height: 1.6)),
                  const SizedBox(height: 20),
                  // 착용 안내
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(14)),
                    child: const Row(
                      children: [
                        Icon(Icons.auto_awesome, color: AppColors.primary),
                        SizedBox(width: 12),
                        Expanded(child: Text('아래 "착용해보기"를 누르면 내 아바타에 이 옷을 입혀볼 수 있어요.',
                            style: TextStyle(fontSize: 13.5, color: AppColors.textDark, height: 1.5))),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ],
        ),
      ),
      // 하단 고정 버튼
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
          child: Row(
            children: [
              // 장바구니 담기
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  border: Border.all(color: AppColors.border),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: IconButton(
                  icon: const Icon(Icons.shopping_bag_outlined, color: AppColors.textDark),
                  onPressed: () {
                    AppState.I.addToCart(p, _selectedSize);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('$_selectedSize 사이즈를 장바구니에 담았어요'), duration: const Duration(seconds: 1)),
                    );
                  },
                ),
              ),
              const SizedBox(width: 12),
              // 착용해보기 → 착용 결과 화면
              Expanded(
                child: SizedBox(
                  height: 56,
                  child: ElevatedButton.icon(
                    onPressed: () {
                      // 아바타가 없으면 먼저 생성하라고 안내
                      if (!AppState.I.hasAvatar) {
                        _showNoAvatarDialog(context);
                        return;
                      }
                      Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => TryOnResultScreen(product: p, size: _selectedSize),
                      ));
                    },
                    icon: const Icon(Icons.auto_awesome, size: 18),
                    label: const Text('착용해보기', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // 아바타가 없을 때 안내 다이얼로그
  void _showNoAvatarDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Text('아바타가 없어요', style: TextStyle(fontWeight: FontWeight.w800, color: AppColors.textDark)),
        content: const Text('먼저 아바타를 생성해주세요.\n스캔 탭에서 사진을 촬영하면 아바타를 만들 수 있어요.',
            style: TextStyle(color: AppColors.textDark, height: 1.5)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('확인', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }
}
