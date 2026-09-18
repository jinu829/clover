import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';
import '../models/product.dart';

/// 착용 결과 화면.
///
/// ⚠️ 이 화면의 "결과 이미지 영역"이 나중에 Unity View(3D 아바타)가 들어갈 자리다.
/// 지금은 placeholder 박스 + 가짜 핏 피드백으로 UI만 완성해둔다.
/// (Unity 연동 시: 여기에 UnityWidget을 넣고, 사용자 치수·옷 ID를 전달)
class TryOnResultScreen extends StatefulWidget {
  final Product product;
  final String size;
  const TryOnResultScreen({super.key, required this.product, required this.size});

  @override
  State<TryOnResultScreen> createState() => _TryOnResultScreenState();
}

class _TryOnResultScreenState extends State<TryOnResultScreen> {
  bool _loading = true; // 착용 처리 중 (실제로는 Unity/서버가 처리)

  @override
  void initState() {
    super.initState();
    // 착용 처리하는 척 1.5초 로딩 (실제 렌더링은 Unity/서버 담당)
    Future.delayed(const Duration(milliseconds: 1500), () {
      if (mounted) setState(() => _loading = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.product;
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: AppColors.textDark,
        title: const Text('착용 결과', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      ),
      body: _loading ? _loadingView() : _resultView(p),
    );
  }

  // 로딩 화면
  Widget _loadingView() {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(color: AppColors.primary),
          SizedBox(height: 20),
          Text('아바타에 착용 중...', style: TextStyle(color: AppColors.textGray, fontSize: 15)),
        ],
      ),
    );
  }

  // 결과 화면
  Widget _resultView(Product p) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── 3D 착용 미리보기 자리 (⚠️ Unity View 들어갈 곳) ──
          Container(
            width: double.infinity,
            height: 360,
            color: AppColors.darkCard,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.view_in_ar, color: AppColors.primary, size: 64),
                const SizedBox(height: 14),
                Text('${p.emoji}  ${p.name}', style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                const Text('3D 착용 미리보기', style: TextStyle(color: Colors.white70, fontSize: 13)),
                const SizedBox(height: 4),
                const Text('(Unity 3D 아바타 연동 예정)', style: TextStyle(color: Colors.white38, fontSize: 11)),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 상품 요약
                Text(p.name, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.textDark)),
                const SizedBox(height: 4),
                Text('선택 사이즈: ${widget.size}  ·  ${formatPrice(p.price)}원',
                    style: const TextStyle(color: AppColors.textGray)),
                const SizedBox(height: 24),
                // 핏 피드백 (가짜 데이터 — 나중에 서버/AI가 계산)
                const Text('핏 피드백', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textDark)),
                const SizedBox(height: 12),
                _feedbackRow('📏', '어깨', '잘 맞음'),
                _feedbackRow('👕', '가슴', '약간 여유 있음'),
                _feedbackRow('📐', '기장', '적당함'),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(14)),
                  child: const Row(
                    children: [
                      Icon(Icons.thumb_up_alt_outlined, color: AppColors.primary),
                      SizedBox(width: 12),
                      Expanded(child: Text('전체적으로 잘 어울려요! 편안한 핏을 원하면 한 사이즈 업도 좋아요.',
                          style: TextStyle(color: AppColors.textDark, fontSize: 13.5, height: 1.5))),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                const Text('※ 핏 피드백은 예시입니다. 실제 분석은 서버 연동 예정.',
                    style: TextStyle(color: AppColors.textGray, fontSize: 11)),
                const SizedBox(height: 24),
                // 버튼
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.of(context).pop(),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          side: const BorderSide(color: AppColors.border),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        child: const Text('다시 고르기', style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w700)),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () {
                          // 착용 결과 공유 문구를 클립보드에 복사 (링크 공유 대체)
                          Clipboard.setData(ClipboardData(
                              text: '클로버에서 "${p.name}"을(를) ${widget.size} 사이즈로 착용해봤어요! 🍀'));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('공유 문구를 복사했어요 📋'), duration: Duration(seconds: 1)),
                          );
                        },
                        icon: const Icon(Icons.share_outlined, size: 18),
                        label: const Text('공유하기', style: TextStyle(fontWeight: FontWeight.w700)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _feedbackRow(String icon, String part, String result) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Text(icon, style: const TextStyle(fontSize: 18)),
          const SizedBox(width: 12),
          SizedBox(width: 50, child: Text(part, style: const TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w600))),
          Text(result, style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
