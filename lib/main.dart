import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'screens/login_screen.dart';

void main() {
  runApp(const CloverApp()); // 앱 시작점 (C의 main과 같은 역할)
}

/// 앱 전체를 감싸는 최상위 위젯. 테마(색·폰트)와 첫 화면을 정한다.
class CloverApp extends StatelessWidget {
  const CloverApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '클로버',
      debugShowCheckedModeBanner: false, // 오른쪽 위 'DEBUG' 띠 숨김
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.primary,
          primary: AppColors.primary,
        ),
        scaffoldBackgroundColor: Colors.white,
        useMaterial3: true,
      ),
      home: const LoginScreen(), // 앱을 켜면 로그인 화면부터
    );
  }
}
