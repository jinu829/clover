import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';

/// 장바구니 화면. 담은 상품·수량·합계·주문.
class CartScreen extends StatelessWidget {
  const CartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: AppColors.textDark,
        title: const Text('장바구니', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      ),
      body: ListenableBuilder(
        listenable: AppState.I,
        builder: (context, _) {
          final cart = AppState.I.cart;
          if (cart.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.shopping_bag_outlined, size: 56, color: AppColors.textGray),
                  SizedBox(height: 12),
                  Text('장바구니가 비어있어요', style: TextStyle(color: AppColors.textGray)),
                ],
              ),
            );
          }
          return Column(
            children: [
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.all(20),
                  itemCount: cart.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 12),
                  itemBuilder: (_, i) => _cartRow(context, cart[i]),
                ),
              ),
              _bottomBar(context),
            ],
          );
        },
      ),
    );
  }

  // 장바구니 한 줄
  Widget _cartRow(BuildContext context, CartItem item) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
      child: Row(
        children: [
          // 이미지
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(12)),
            child: Center(child: Text(item.product.emoji, style: const TextStyle(fontSize: 30))),
          ),
          const SizedBox(width: 12),
          // 이름·사이즈·가격
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.product.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
                const SizedBox(height: 2),
                Text('사이즈 ${item.size}', style: const TextStyle(color: AppColors.textGray, fontSize: 12)),
                const SizedBox(height: 6),
                Text('${formatPrice(item.product.price)}원',
                    style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w800)),
              ],
            ),
          ),
          // 수량 조절
          Column(
            children: [
              Row(
                children: [
                  _qtyBtn(Icons.remove, () => AppState.I.changeQty(item, -1)),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    child: Text('${item.qty}', style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textDark)),
                  ),
                  _qtyBtn(Icons.add, () => AppState.I.changeQty(item, 1)),
                ],
              ),
              const SizedBox(height: 4),
              GestureDetector(
                onTap: () => AppState.I.removeFromCart(item),
                child: const Text('삭제', style: TextStyle(color: AppColors.textGray, fontSize: 12)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _qtyBtn(IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 28,
        height: 28,
        decoration: BoxDecoration(
          border: Border.all(color: AppColors.border),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, size: 16, color: AppColors.textDark),
      ),
    );
  }

  // 하단 합계 + 주문 버튼
  Widget _bottomBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      decoration: const BoxDecoration(color: Colors.white),
      child: SafeArea(
        top: false,
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('합계', style: TextStyle(color: AppColors.textGray, fontSize: 15)),
                Text('${formatPrice(AppState.I.cartTotal)}원',
                    style: const TextStyle(color: AppColors.textDark, fontSize: 20, fontWeight: FontWeight.w800)),
              ],
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton(
                onPressed: () {
                  AppState.I.clearCart();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('주문이 완료됐어요! (결제는 준비 중)'), duration: Duration(seconds: 2)),
                  );
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: const Text('주문하기', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
