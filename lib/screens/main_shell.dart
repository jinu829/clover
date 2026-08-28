import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'home_screen.dart';
import 'shopping_screen.dart';
import 'scan_screen.dart';
import 'my_page_screen.dart';

/// 앱의 뼈대(shell). 하단 탭 4개와, 각 탭에 해당하는 화면을 담는다.
/// 어떤 탭이 선택됐는지가 "바뀌는 값"이라 StatefulWidget.
class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _index = 0; // 현재 선택된 탭 번호 (0:홈 1:쇼핑 2:스캔 3:마이)

  // 탭 순서에 맞춘 화면들
  final List<Widget> _screens = const [
    HomeScreen(),
    ShoppingScreen(),
    ScanScreen(),
    MyPageScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // IndexedStack: 탭을 바꿔도 각 화면 상태를 유지해준다
      body: IndexedStack(index: _index, children: _screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        // 탭을 누르면 _index를 바꾸고 -> 화면이 다시 그려짐
        onDestinationSelected: (i) => setState(() => _index = i),
        backgroundColor: Colors.white,
        indicatorColor: AppColors.primarySoft,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home, color: AppColors.primary),
            label: '홈',
          ),
          NavigationDestination(
            icon: Icon(Icons.shopping_bag_outlined),
            selectedIcon: Icon(Icons.shopping_bag, color: AppColors.primary),
            label: '쇼핑',
          ),
          NavigationDestination(
            icon: Icon(Icons.crop_free),
            selectedIcon: Icon(Icons.crop_free, color: AppColors.primary),
            label: '스캔',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person, color: AppColors.primary),
            label: '마이',
          ),
        ],
      ),
    );
  }
}
