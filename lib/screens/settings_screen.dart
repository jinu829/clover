import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'login_screen.dart';

/// 설정 화면. 알림 토글·다크모드(준비중)·로그아웃.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _noti = true;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: AppColors.textDark,
        title: const Text('설정', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Container(
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
            child: Column(
              children: [
                SwitchListTile(
                  value: _noti,
                  activeThumbColor: AppColors.primary,
                  title: const Text('알림 받기', style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w600)),
                  onChanged: (v) => setState(() => _noti = v),
                ),
                const Divider(height: 1),
                const ListTile(
                  title: Text('다크 모드', style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w600)),
                  trailing: Text('준비 중', style: TextStyle(color: AppColors.textGray, fontSize: 13)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
            child: ListTile(
              leading: const Icon(Icons.logout, color: Colors.redAccent),
              title: const Text('로그아웃', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.w600)),
              onTap: () {
                // 로그인 화면으로 되돌아가고 이전 화면 스택 전부 제거
                Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (_) => const LoginScreen()),
                  (route) => false,
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
