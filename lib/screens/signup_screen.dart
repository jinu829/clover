import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// 회원가입 화면. 입력 검증 후 완료되면 로그인 화면으로 돌아간다.
class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _emailCtrl = TextEditingController();
  final _pwCtrl = TextEditingController();
  final _pw2Ctrl = TextEditingController();
  final _nickCtrl = TextEditingController();
  String? _emailError, _pwError, _pw2Error, _nickError;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _pwCtrl.dispose();
    _pw2Ctrl.dispose();
    _nickCtrl.dispose();
    super.dispose();
  }

  void _signup() {
    final email = _emailCtrl.text.trim();
    final pw = _pwCtrl.text;
    final pw2 = _pw2Ctrl.text;
    final nick = _nickCtrl.text.trim();
    setState(() {
      _emailError = email.isEmpty
          ? '이메일을 입력하세요'
          : (!email.contains('@') || !email.contains('.') ? '올바른 이메일 형식이 아니에요' : null);
      _pwError = pw.length < 6 ? '비밀번호는 6자 이상이에요' : null;
      _pw2Error = pw2 != pw ? '비밀번호가 일치하지 않아요' : null;
      _nickError = nick.isEmpty ? '닉네임을 입력하세요' : null;
    });

    if (_emailError == null && _pwError == null && _pw2Error == null && _nickError == null) {
      Navigator.of(context).pop(); // 로그인 화면으로 복귀
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('회원가입 완료! 로그인해 주세요 🍀'), duration: Duration(seconds: 2)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: AppColors.textDark,
        title: const Text('회원가입', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _field('이메일', _emailCtrl, 'example@clover.com', Icons.mail_outline, error: _emailError),
            _field('비밀번호', _pwCtrl, '6자 이상', Icons.lock_outline, error: _pwError, obscure: true),
            _field('비밀번호 확인', _pw2Ctrl, '다시 입력', Icons.lock_outline, error: _pw2Error, obscure: true),
            _field('닉네임', _nickCtrl, '사용할 닉네임', Icons.person_outline, error: _nickError),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton(
                onPressed: _signup,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: const Text('가입하기', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _field(String label, TextEditingController ctrl, String hint, IconData icon,
      {String? error, bool obscure = false}) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textDark)),
          const SizedBox(height: 8),
          TextField(
            controller: ctrl,
            obscureText: obscure,
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: const TextStyle(color: AppColors.textGray),
              prefixIcon: Icon(icon, color: AppColors.textGray),
              errorText: error,
              filled: true,
              fillColor: Colors.white,
              contentPadding: const EdgeInsets.symmetric(vertical: 16),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: AppColors.border),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: AppColors.primary, width: 1.6),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
