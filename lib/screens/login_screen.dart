import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'main_shell.dart';
import 'signup_screen.dart';

/// 로그인 화면. 입력 검증·비밀번호 토글이 있어 StatefulWidget.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController();
  final _pwCtrl = TextEditingController();
  bool _obscure = true;
  bool _keepLogin = false;
  String? _emailError; // 이메일 오류 문구 (null이면 정상)
  String? _pwError; // 비밀번호 오류 문구

  @override
  void dispose() {
    _emailCtrl.dispose();
    _pwCtrl.dispose();
    super.dispose();
  }

  void _login() {
    final email = _emailCtrl.text.trim();
    final pw = _pwCtrl.text;
    setState(() {
      // 이메일 검증
      if (email.isEmpty) {
        _emailError = '이메일을 입력하세요';
      } else if (!email.contains('@') || !email.contains('.')) {
        _emailError = '올바른 이메일 형식이 아니에요';
      } else {
        _emailError = null;
      }
      // 비밀번호 검증
      _pwError = pw.isEmpty ? '비밀번호를 입력하세요' : null;
    });

    // 둘 다 통과하면 메인으로
    if (_emailError == null && _pwError == null) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const MainShell()),
      );
    }
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
              const SizedBox(height: 56),
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
              const Text('클로버', style: TextStyle(fontSize: 34, fontWeight: FontWeight.w800, color: AppColors.textDark)),
              const SizedBox(height: 8),
              const Text('3D 스캔으로 완벽한 핏을 찾아보세요', style: TextStyle(fontSize: 15, color: AppColors.textGray)),
              const SizedBox(height: 40),
              // 이메일
              _label('이메일'),
              const SizedBox(height: 8),
              _inputField(
                controller: _emailCtrl,
                hint: 'example@clover.com',
                icon: Icons.mail_outline,
                errorText: _emailError,
              ),
              const SizedBox(height: 16),
              // 비밀번호
              _label('비밀번호'),
              const SizedBox(height: 8),
              _inputField(
                controller: _pwCtrl,
                hint: '••••••••',
                icon: Icons.lock_outline,
                obscure: _obscure,
                errorText: _pwError,
                suffix: IconButton(
                  icon: Icon(_obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: AppColors.textGray),
                  onPressed: () => setState(() => _obscure = !_obscure),
                ),
              ),
              const SizedBox(height: 12),
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
                  const Text('비밀번호 찾기', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w600)),
                ],
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _login,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: const Text('로그인', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                ),
              ),
              const SizedBox(height: 20),
              Row(
                children: const [
                  Expanded(child: Divider()),
                  Padding(padding: EdgeInsets.symmetric(horizontal: 12), child: Text('또는', style: TextStyle(color: AppColors.textGray))),
                  Expanded(child: Divider()),
                ],
              ),
              const SizedBox(height: 20),
              // 회원가입 링크
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text('아직 회원이 아니신가요?', style: TextStyle(color: AppColors.textGray)),
                  const SizedBox(width: 6),
                  GestureDetector(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const SignupScreen()),
                    ),
                    child: const Text('회원가입', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
                  ),
                ],
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _label(String text) => Align(
        alignment: Alignment.centerLeft,
        child: Text(text, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textDark)),
      );

  Widget _inputField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    bool obscure = false,
    Widget? suffix,
    String? errorText,
  }) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: AppColors.textGray),
        prefixIcon: Icon(icon, color: AppColors.textGray),
        suffixIcon: suffix,
        errorText: errorText,
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
