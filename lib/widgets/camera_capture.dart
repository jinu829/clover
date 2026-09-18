import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:image_picker/image_picker.dart';
import '../theme/app_theme.dart';

/// 카메라(실제 웹캠/폰카메라) 라이브 미리보기 → 촬영, 또는 갤러리 선택.
/// 웹(localhost)·모바일 모두에서 라이브 카메라가 열린다.
/// 사진은 공통으로 bytes(Uint8List)로 다룬다.
class CameraCapture extends StatefulWidget {
  final void Function(Uint8List photo)? onConfirmed;
  const CameraCapture({super.key, this.onConfirmed});

  @override
  State<CameraCapture> createState() => _CameraCaptureState();
}

class _CameraCaptureState extends State<CameraCapture> {
  final ImagePicker _picker = ImagePicker();
  CameraController? _controller; // 라이브 카메라 컨트롤러
  bool _live = false; // 라이브 미리보기 중인지
  bool _busy = false; // 처리 중(로딩)
  Uint8List? _photo; // 찍거나 고른 사진
  String? _error; // 오류 문구

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  // 카메라 켜기 (권한 요청 → 라이브 미리보기)
  Future<void> _openCamera() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final cams = await availableCameras();
      if (cams.isEmpty) {
        setState(() {
          _error = '사용 가능한 카메라가 없어요.';
          _busy = false;
        });
        return;
      }
      final controller = CameraController(cams.first, ResolutionPreset.medium, enableAudio: false);
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() {
        _controller = controller;
        _live = true;
        _busy = false;
      });
    } catch (e) {
      setState(() {
        _error = '카메라를 열 수 없어요. 브라우저에서 카메라 접근을 허용했는지 확인해 주세요.';
        _busy = false;
      });
    }
  }

  // 촬영
  Future<void> _shoot() async {
    final c = _controller;
    if (c == null || !c.value.isInitialized) return;
    setState(() => _busy = true);
    try {
      final file = await c.takePicture();
      final bytes = await file.readAsBytes();
      await c.dispose();
      if (!mounted) return;
      setState(() {
        _photo = bytes;
        _live = false;
        _controller = null;
        _busy = false;
      });
    } catch (e) {
      setState(() {
        _error = '촬영에 실패했어요: $e';
        _busy = false;
      });
    }
  }

  // 카메라 닫기(취소)
  Future<void> _closeCamera() async {
    await _controller?.dispose();
    if (!mounted) return;
    setState(() {
      _controller = null;
      _live = false;
    });
  }

  // 갤러리에서 선택
  Future<void> _pickGallery() async {
    setState(() => _busy = true);
    try {
      final XFile? file = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 1200);
      if (file != null) {
        final bytes = await file.readAsBytes();
        if (mounted) setState(() => _photo = bytes);
      }
    } catch (e) {
      if (mounted) setState(() => _error = '사진을 불러오지 못했어요: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_photo != null) return _takenView(); // 3) 찍은 뒤
    if (_live && _controller != null) return _liveView(); // 2) 라이브 카메라
    return _idleView(); // 1) 시작
  }

  // 1) 시작 화면
  Widget _idleView() {
    return Column(
      children: [
        Container(
          height: 220,
          width: double.infinity,
          decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(16)),
          child: _busy
              ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
              : const Center(child: Icon(Icons.add_a_photo_outlined, size: 56, color: AppColors.primary)),
        ),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Text(_error!, style: const TextStyle(color: Colors.redAccent, fontSize: 13), textAlign: TextAlign.center),
        ],
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: _busy ? null : _openCamera,
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('카메라로 촬영', style: TextStyle(fontWeight: FontWeight.w700)),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
              elevation: 0,
              padding: const EdgeInsets.symmetric(vertical: 15),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: _busy ? null : _pickGallery,
            icon: const Icon(Icons.photo_library_outlined, color: AppColors.textDark),
            label: const Text('갤러리에서 선택', style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w700)),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: AppColors.border),
              padding: const EdgeInsets.symmetric(vertical: 15),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
      ],
    );
  }

  // 2) 라이브 카메라 미리보기
  Widget _liveView() {
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: AspectRatio(
            aspectRatio: _controller!.value.aspectRatio,
            child: CameraPreview(_controller!),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _busy ? null : _closeCamera,
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  side: const BorderSide(color: AppColors.border),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('취소', style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w700)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              flex: 2,
              child: ElevatedButton.icon(
                onPressed: _busy ? null : _shoot,
                icon: const Icon(Icons.camera, size: 20),
                label: const Text('촬영', style: TextStyle(fontWeight: FontWeight.w700)),
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
    );
  }

  // 3) 찍은 사진 미리보기
  Widget _takenView() {
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Image.memory(_photo!, height: 320, width: double.infinity, fit: BoxFit.cover),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () => setState(() => _photo = null),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  side: const BorderSide(color: AppColors.border),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('다시 찍기', style: TextStyle(color: AppColors.textDark, fontWeight: FontWeight.w700)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ElevatedButton(
                onPressed: () => widget.onConfirmed?.call(_photo!),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('사용하기', style: TextStyle(fontWeight: FontWeight.w700)),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
