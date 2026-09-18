import 'package:flutter/foundation.dart';
import '../models/product.dart';

/// 장바구니에 담긴 상품 한 줄 (상품 + 선택 사이즈 + 수량).
class CartItem {
  final Product product;
  final String size;
  int qty;
  CartItem({required this.product, required this.size, this.qty = 1});
}

/// 앱 전역 상태 — 찜(좋아요)과 장바구니를 여러 화면이 함께 쓴다.
///
/// ChangeNotifier: 값이 바뀔 때 notifyListeners()를 부르면,
/// 이 상태를 듣고 있는 화면(ListenableBuilder)이 자동으로 다시 그려진다.
/// (setState의 "앱 전역" 버전이라고 보면 됨)
class AppState extends ChangeNotifier {
  AppState._();
  static final AppState I = AppState._(); // 앱 어디서나 AppState.I 로 접근

  // ─── 아바타 ───
  bool _hasAvatar = false; // 아바타 생성 여부 (스캔 완료 시 true)
  bool get hasAvatar => _hasAvatar;
  void createAvatar() {
    _hasAvatar = true;
    notifyListeners();
  }

  // ─── 찜(좋아요) ───
  final Set<String> _liked = {}; // 찜한 상품 id 모음
  bool isLiked(Product p) => _liked.contains(p.id);
  int get likedCount => _liked.length;
  List<Product> get likedProducts =>
      sampleProducts.where((p) => _liked.contains(p.id)).toList();

  void toggleLike(Product p) {
    if (_liked.contains(p.id)) {
      _liked.remove(p.id);
    } else {
      _liked.add(p.id);
    }
    notifyListeners();
  }

  // ─── 장바구니 ───
  final List<CartItem> _cart = [];
  List<CartItem> get cart => List.unmodifiable(_cart);
  int get cartCount => _cart.fold(0, (sum, i) => sum + i.qty); // 총 수량
  int get cartTotal => _cart.fold(0, (sum, i) => sum + i.product.price * i.qty); // 합계 금액

  void addToCart(Product p, String size) {
    // 같은 상품 + 같은 사이즈가 이미 있으면 수량만 +1
    final idx = _cart.indexWhere((i) => i.product.id == p.id && i.size == size);
    if (idx >= 0) {
      _cart[idx].qty++;
    } else {
      _cart.add(CartItem(product: p, size: size));
    }
    notifyListeners();
  }

  void changeQty(CartItem item, int delta) {
    item.qty += delta;
    if (item.qty <= 0) _cart.remove(item); // 0이 되면 삭제
    notifyListeners();
  }

  void removeFromCart(CartItem item) {
    _cart.remove(item);
    notifyListeners();
  }

  void clearCart() {
    _cart.clear();
    notifyListeners();
  }
}
