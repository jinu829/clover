import 'package:flutter/material.dart';

/// 클로버 앱의 색상 모음.
/// 여기 값만 바꾸면 앱 전체 색이 한 번에 바뀐다. (디자인 시스템의 기본)
class AppColors {
  static const Color primary = Color(0xFF15C57E); // 클로버 메인 초록
  static const Color primaryDark = Color(0xFF0BA968); // 진한 초록 (그라데이션용)
  static const Color primarySoft = Color(0xFFE6F8F0); // 아주 연한 초록 (배경/버튼)
  static const Color scaffold = Color(0xFFF6F7F9); // 페이지 배경(연회색)
  static const Color textDark = Color(0xFF1A1D26); // 진한 제목 글자
  static const Color textGray = Color(0xFF9AA0A6); // 회색 보조 글자
  static const Color chipBg = Color(0xFFEEF0F7); // 비활성 칩 배경
  static const Color darkCard = Color(0xFF1E2A38); // 스캔 화면 어두운 카드
  static const Color border = Color(0xFFE3E5EA); // 입력창/버튼 테두리
}

/// 가격 숫자에 천 단위 콤마를 넣어준다. (29000 -> "29,000")
String formatPrice(int price) {
  return price.toString().replaceAllMapped(
        RegExp(r'\B(?=(\d{3})+(?!\d))'),
        (m) => ',',
      );
}
