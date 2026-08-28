import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'main_shell.dart';

/// 로그인 화면 (앱을 켜면 처음 보이는 화면).
/// 비밀번호 가리기, 로그인 유지 체크처럼 "값이 바뀌는" 게 있어서 StatefulWidget.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _obscure = true; // 비밀번호 가리기 상태
  bool _keepLogin = false; // 로그인 유지 체크 상태

  void _goToApp() {
    // 로그인 버튼 -> 메인 화면(4탭)으로 이동.
    // pushReplacement: 로그인 화면을 없애고 교체 (뒤로가기로 로그인으로 안 돌아옴)
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const MainShell()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(
            children: [
              const SizedBox(height: 60),
              // 클로버 로고 (초록 사각형 + 네잎클로버 이모지)
              Container(
                width: 92,
                height: 92,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.primary, AppColors.primaryDark],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(24),
                ),
                child: const Center(child: Text('🍀', style: TextStyle(fontSize: 46))),
              ),
              const SizedBox(height: 20),
              const Text(
                '클로버',
                style: TextStyle(fontSize: 34, fontWeight: FontWeight.w800, color: AppColors.textDark),
              ),
              const SizedBox(height: 8),
              const Text(
                '3D 스캔으로 완벽한 핏을 찾아보세요',
                style: TextStyle(fontSize: 15, color: AppColors.textGray),
              ),
              const SizedBox(height: 44),
              // 이메일 입력
              _label('이메일'),
              const SizedBox(height: 8),
              _inputField(hint: 'example@clover.com', icon: Icons.mail_outline),
              const SizedBox(height: 20),
              // 비밀번호 입력
              _label('비밀번호'),
              const SizedBox(height: 8),
              _inputField(
                hint: '••••••••',
                icon: Icons.lock_outline,
                obscure: _obscure,
                suffix: IconButton(
                  icon: Icon(
                    _obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                    color: AppColors.textGray,
                  ),
                  // 눈 아이콘 누르면 가리기 <-> 보이기 토글
                  onPressed: () => setState(() => _obscure = !_obscure),
                ),
              ),
              const SizedBox(height: 16),
              // 로그인 유지 / 비밀번호 찾기
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      SizedBox(
                        width: 24,
                        height: 24,
                        child: Checkbox(
                          value: _keepLogin,
                          activeColor: AppColors.primary,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                          onChanged: (v) => setState(() => _keepLogin = v ?? false),
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text('로그인 유지', style: TextStyle(color: AppColors.textDark)),
                    ],
                  ),
                  const Text(
                    '비밀번호 찾기',
                    style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              // 로그인 버튼 (가로 꽉 채움)
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _goToApp,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: const Text('로그인', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                ),
              ),
              const SizedBox(height: 24),
              // "또는" 구분선
              Row(
                children: const [
                  Expanded(child: Divider()),
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: 12),
                    child: Text('또는', style: TextStyle(color: AppColors.textGray)),
                  ),
                  Expanded(child: Divider()),
                ],
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  // 입력창 위 라벨 (왼쪽 정렬 텍스트)
  Widget _label(String text) => Align(
        alignment: Alignment.centerLeft,
        child: Text(
          text,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textDark),
        ),
      );

  // 재사용 입력창
  Widget _inputField({
    required String hint,
    required IconData icon,
    bool obscure = false,
    Widget? suffix,
  }) {
    return TextField(
      obscureText: obscure,
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: AppColors.textGray),
        prefixIcon: Icon(icon, color: AppColors.textGray),
        suffixIcon: suffix,
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(vertical: 18),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.6),
        ),
      ),
    );
  }
}
