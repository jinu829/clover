# 클로버(Clover) — 프로젝트 진행 노트

> **Clover: 3D Virtual Try-On Shopping App**
> 옷을 3D 아바타에 입혀보고 핏을 확인하는 가상 피팅 쇼핑 앱.
> 담당: **프론트엔드 (Flutter/Dart)** · 3D 렌더링은 **Unity 연동** 예정 · 서버는 **백엔드 팀**.
> 최종 정리: 2026-09-18

---

## 1. 개발 환경
- Flutter 3.47 (stable), `C:\dev\flutter`
- 프로젝트: `C:\dev\clover`
- 실행(개발): `flutter run -d web-server --web-port 8080 --web-hostname localhost` → http://localhost:8080
- VS Code + Flutter/Dart 확장, 윈도우 개발자 모드 ON(플러그인용)
- GitHub: `github.com/jinu829/clover` (Public), 브랜치 `20260828_front`

## 2. 폴더 구조 (lib/)
```
lib/
├─ main.dart                     앱 시작 · 테마 · 첫 화면
├─ theme/app_theme.dart          색(클로버 초록) · 가격 포맷
├─ models/product.dart           상품 모델(+id, 설명) · 가짜 상품 13개
├─ state/app_state.dart          전역 상태: 찜 · 장바구니 · 아바타 보유
├─ unity/unity_bridge.dart       Flutter↔Unity 통신 다리(현재 Mock)
├─ widgets/
│  ├─ product_card.dart          상품 카드(탭→상세)
│  └─ camera_capture.dart        실제 웹캠 촬영 + 갤러리 선택
└─ screens/
   ├─ login_screen.dart          로그인(입력 검증)
   ├─ signup_screen.dart         회원가입
   ├─ main_shell.dart            하단 탭 4개 뼈대
   ├─ home_screen.dart           홈(배너·카테고리·인기상품)
   ├─ shopping_screen.dart       쇼핑(검색·카테고리 필터·그리드)
   ├─ product_detail_screen.dart 상품 상세(사이즈·찜·장바구니·착용)
   ├─ tryon_result_screen.dart   착용 결과(핏 피드백)
   ├─ scan_screen.dart           스캔(가이드→촬영→완료)
   ├─ fitting_room_screen.dart   피팅룸(Unity 6기능 연동 화면)
   ├─ cart_screen.dart           장바구니
   ├─ wishlist_screen.dart       찜 목록
   ├─ order_history_screen.dart  주문 내역
   └─ settings_screen.dart       설정
```

## 3. 화면 흐름
```
로그인/회원가입
  └─ 메인(하단 탭: 홈 · 쇼핑 · 스캔 · 마이)
       홈 ─ 스캔시작 → 스캔탭 / 카테고리 → 쇼핑탭(해당 카테고리)
       상품카드 → 상품상세 → (착용해보기) → 착용결과
       마이 → 아바타보기 → 피팅룸 / 찜목록 / 장바구니 / 주문내역 / 설정
```

---

## 4. 진행 현황 (체크리스트)

### ✅ 완료 (Flutter)
- [x] 상품 모델 + 설명 13개, 상품 id
- [x] 상품 상세 화면 (사이즈 S/M/L/XL, 찜♡, 공유, 장바구니, 착용해보기)
- [x] 카드/인기상품 → 상세 이동
- [x] 착용 결과 화면 (핏 피드백 카드)
- [x] 쇼핑 검색(TextField) + 카테고리 필터 동시 적용
- [x] 찜 상태관리 + 찜 목록 화면
- [x] 장바구니(수량·합계·주문) + 전역 상태
- [x] 로그인 입력 검증 + 회원가입
- [x] 주문 내역 · 설정(로그아웃)
- [x] 홈 스캔시작→스캔 / 카테고리→쇼핑 연결
- [x] 카메라: **실제 웹캠** 라이브 촬영 + 갤러리 선택
- [x] 아바타 없을 때 "생성해주세요" 안내
- [x] **Unity 연동(Flutter측)**: unity_bridge + 피팅룸 6기능(치수전달·로딩·상의/하의 교체·애니메이션·핏 피드백·신호 로그)
- [x] 공유(클립보드 복사) · 웹 앱 이름/타이틀 "클로버"

### 🔗 백엔드/외부 담당 (자리만 만들어 둠)
- [ ] 실제 로그인 (서버 인증)
- [ ] 착용 이미지·핏 피드백 실제 데이터 (AI 서버)
- [ ] 아바타 생성 처리 (촬영 사진 → 서버)
- [ ] 상품 데이터 서버 연동 (지금은 가짜 13개)

### ⏭️ 남은 Flutter 작업
- [ ] **다크모드** — 색상 211곳(const ~85곳) 리팩터링 필요, 별도 작업
- [ ] **스캔 3각도 흐름** — 정면/측면/후면 순차 촬영 + 생성중 로딩
- [ ] 앱 아이콘/스플래시(네이티브) — 로고 이미지 필요 (웹 타이틀은 완료)
- [ ] 로딩·에러 처리 전 화면 공통화 (백엔드 연동 시)
- [ ] 상태관리: 현재 ChangeNotifier로 충분, 규모 커지면 Provider/Riverpod

---

## 5. Unity 연동 계획 (핵심 다음 과제)
Flutter는 UI·데이터·명령, Unity는 3D 아바타/의류 렌더링 담당. `flutter_unity_widget`로 임베딩.

1. Unity as a Library 프로젝트 생성 + Flutter 임베딩
2. Unity View 활성화 + 데이터 전달(치수, 옷 ID)
3. 3D 아바타·의류 로딩 확인 + 렌더링 결과 수신
4. 상의/하의 교체 → Unity 명령 전달
5. 플랫폼 채널로 핏 피드백 수신·표시
6. 아바타 애니메이션 제어(걷기·포즈)

**실제 연동 시 바꿀 곳 2군데** (`unity/unity_bridge.dart`):
- `_sendToUnity()` → `unityController.postMessage('AvatarManager', method, data)`
- 피팅룸의 "Unity View 자리" → `UnityWidget`

---

## 6. 요약 (한 줄)
Flutter로 구현 가능한 최대치는 거의 완료. 남은 핵심은 **① Unity 3D 연동 ② 백엔드 API**, 그 외 마무리(다크모드·앱아이콘 등).
