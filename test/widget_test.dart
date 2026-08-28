// 기본 스모크 테스트: 앱이 정상적으로 켜지고 로그인 화면이 뜨는지 확인.
import 'package:flutter_test/flutter_test.dart';
import 'package:clover/main.dart';

void main() {
  testWidgets('로그인 화면이 표시된다', (WidgetTester tester) async {
    await tester.pumpWidget(const CloverApp());

    // 로그인 화면의 '클로버' 제목과 '로그인' 버튼이 보이는지 확인
    expect(find.text('클로버'), findsOneWidget);
    expect(find.text('로그인'), findsOneWidget);
  });
}
