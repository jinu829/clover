/// 상품 하나를 표현하는 데이터 틀(모델).
/// C의 struct랑 비슷한 개념 — 상품이 가진 정보를 묶어둔 것.
class Product {
  final String id; // 상품 고유 번호 (나중에 Unity로 "옷 ID" 넘길 때 사용)
  final String name; // 상품 이름
  final int price; // 가격(원)
  final String category; // 카테고리: 상의 / 하의 / 원피스 / 아우터
  final String emoji; // 임시 이미지(이모지) — 나중에 진짜 사진으로 교체
  final String description; // 상품 설명
  final bool wearing; // 지금 아바타가 착용 중인지

  const Product({
    required this.id,
    required this.name,
    required this.price,
    required this.category,
    required this.emoji,
    this.description = '',
    this.wearing = false,
  });
}

/// 가짜(예시) 상품 목록.
/// 프론트에서는 이렇게 먼저 화면을 완성하고,
/// 나중에 백엔드 팀원이 서버 데이터로 이 부분만 갈아끼운다.
const List<Product> sampleProducts = [
  Product(id: 'p01', name: '베이직 화이트 티셔츠', price: 29000, category: '상의', emoji: '👕', description: '어디에나 잘 어울리는 필수 기본 티셔츠. 부드러운 순면 소재로 사계절 편하게 입기 좋아요.', wearing: true),
  Product(id: 'p02', name: '스트레이트 데님', price: 59000, category: '하의', emoji: '👖', description: '군더더기 없는 일자 핏 데님 팬츠. 어떤 상의와도 매치하기 쉬운 데일리 아이템.', wearing: true),
  Product(id: 'p03', name: '플로럴 원피스', price: 79000, category: '원피스', emoji: '👗', description: '화사한 플로럴 패턴의 여름 원피스. 가볍고 시원한 소재로 나들이룩에 제격.'),
  Product(id: 'p04', name: '오버핏 트렌치 코트', price: 129000, category: '아우터', emoji: '🧥', description: '넉넉한 오버핏 실루엣의 트렌치 코트. 간절기 아우터로 세련된 무드를 완성.'),
  Product(id: 'p05', name: '스트라이프 셔츠', price: 39000, category: '상의', emoji: '👔', description: '깔끔한 스트라이프 셔츠. 오피스룩과 캐주얼룩 모두 소화하는 만능템.'),
  Product(id: 'p06', name: '슬림핏 슬랙스', price: 49000, category: '하의', emoji: '👖', description: '다리를 길어 보이게 하는 슬림핏 슬랙스. 단정한 자리에 잘 어울려요.'),
  Product(id: 'p07', name: '라운드 니트', price: 45000, category: '상의', emoji: '🧶', description: '포근한 라운드넥 니트. 부드러운 감촉으로 가을·겨울 데일리 필수템.'),
  Product(id: 'p08', name: '데님 자켓', price: 69000, category: '아우터', emoji: '🧥', description: '빈티지한 무드의 데님 자켓. 레이어드하기 좋아 활용도가 높아요.'),
  Product(id: 'p09', name: '롱 셔츠 원피스', price: 89000, category: '원피스', emoji: '👗', description: '편안하게 걸치는 롱 셔츠 원피스. 벨트로 포인트를 주기도 좋아요.'),
  Product(id: 'p10', name: '후드 집업', price: 55000, category: '아우터', emoji: '🧥', description: '데일리 후드 집업. 활동적인 캐주얼 룩에 편하게 매치하세요.'),
  Product(id: 'p11', name: '크롭 티셔츠', price: 25000, category: '상의', emoji: '👕', description: '짧은 기장의 크롭 티셔츠. 하이웨스트 하의와 잘 어울려요.'),
  Product(id: 'p12', name: '와이드 팬츠', price: 52000, category: '하의', emoji: '👖', description: '편안한 와이드 실루엣 팬츠. 트렌디하면서 활동성도 좋아요.'),
  Product(id: 'p13', name: '플리츠 원피스', price: 72000, category: '원피스', emoji: '👗', description: '우아한 플리츠(주름) 원피스. 여성스러운 실루엣을 완성해줘요.'),
];
