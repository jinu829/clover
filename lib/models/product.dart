/// 상품 하나를 표현하는 데이터 틀(모델).
/// C의 struct랑 비슷한 개념 — 상품이 가진 정보를 묶어둔 것.
class Product {
  final String name; // 상품 이름
  final int price; // 가격(원)
  final String category; // 카테고리: 상의 / 하의 / 원피스 / 아우터
  final String emoji; // 임시 이미지(이모지) — 나중에 진짜 사진으로 교체
  final bool wearing; // 지금 아바타가 착용 중인지

  const Product({
    required this.name,
    required this.price,
    required this.category,
    required this.emoji,
    this.wearing = false,
  });
}

/// 가짜(예시) 상품 목록.
/// 프론트에서는 이렇게 먼저 화면을 완성하고,
/// 나중에 백엔드 팀원이 서버 데이터로 이 부분만 갈아끼운다.
const List<Product> sampleProducts = [
  Product(name: '베이직 화이트 티셔츠', price: 29000, category: '상의', emoji: '👕', wearing: true),
  Product(name: '스트레이트 데님', price: 59000, category: '하의', emoji: '👖', wearing: true),
  Product(name: '플로럴 원피스', price: 79000, category: '원피스', emoji: '👗'),
  Product(name: '오버핏 트렌치 코트', price: 129000, category: '아우터', emoji: '🧥'),
  Product(name: '스트라이프 셔츠', price: 39000, category: '상의', emoji: '👔'),
  Product(name: '슬림핏 슬랙스', price: 49000, category: '하의', emoji: '👖'),
  Product(name: '라운드 니트', price: 45000, category: '상의', emoji: '🧶'),
  Product(name: '데님 자켓', price: 69000, category: '아우터', emoji: '🧥'),
  Product(name: '롱 셔츠 원피스', price: 89000, category: '원피스', emoji: '👗'),
  Product(name: '후드 집업', price: 55000, category: '아우터', emoji: '🧥'),
  Product(name: '크롭 티셔츠', price: 25000, category: '상의', emoji: '👕'),
  Product(name: '와이드 팬츠', price: 52000, category: '하의', emoji: '👖'),
  Product(name: '플리츠 원피스', price: 72000, category: '원피스', emoji: '👗'),
];
