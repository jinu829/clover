import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'home_screen.dart';
import 'shopping_screen.dart';
import 'scan_screen.dart';
import 'my_page_screen.dart';

/// 앱의 뼈대(shell). 하단 탭 4개와, 각 탭에 해당하는 화면을 담는다.
class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _index = 0; // 현재 선택된 탭 (0:홈 1:쇼핑 2:스캔 3:마이)
  String _shopCategory = '전체'; // 쇼핑 탭에 넘겨줄 카테고리

  /// 탭 이동 (필요하면 쇼핑 카테고리도 함께 지정)
  void _goToTab(int i, {String? category}) {
    setState(() {
      _index = i;
      if (category != null) _shopCategory = category;
    });
  }

  @override
  Widget build(BuildContext context) {
    // 홈에 "스캔 이동"·"카테고리 이동" 통로를 넘겨준다
    final screens = [
      HomeScreen(
        onScan: () => _goToTab(2), // 스캔 탭으로
        onCategory: (c) => _goToTab(1, category: c), // 쇼핑 탭 + 카테고리
      ),
      ShoppingScreen(category: _shopCategory),
      const ScanScreen(),
      const MyPageScreen(),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: screens), // 탭 전환해도 상태 유지
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
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
