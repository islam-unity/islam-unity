import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'data/ettehad_repository.dart';
import 'ui/core/theme.dart';
import 'ui/features/ai_chat/ai_chat_screen.dart';
import 'ui/features/auth/auth_screen.dart';
import 'ui/features/library/library_screen.dart';

import 'ui/features/profile/profile_sheet.dart';
import 'ui/features/qna/qna_screen.dart';
import 'ui/features/quran/quran_screen.dart';
import 'ui/features/tools/tools_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: EttehadColors.navy,
      statusBarIconBrightness: Brightness.light,
    ),
  );
  runApp(const EttehadNativeApp());
}

class EttehadNativeApp extends StatefulWidget {
  const EttehadNativeApp({super.key});

  @override
  State<EttehadNativeApp> createState() => _EttehadNativeAppState();
}

class _EttehadNativeAppState extends State<EttehadNativeApp> {
  final EttehadRepository _repo = EttehadRepository();
  bool _skippedAuthAsGuest = false;

  @override
  void initState() {
    super.initState();
    _repo.initialize();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'کتابخوان اتحاد',
      debugShowCheckedModeBanner: false,
      theme: buildEttehadTheme(),
      builder: (context, child) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: ListenableBuilder(
        listenable: _repo,
        builder: (context, _) {
          if (!_repo.isInitialized) {
            return const _SplashLoadingScreen();
          }
          // If not logged in and hasn't chosen to skip as guest, show the full Auth Screen
          if (!_repo.isLoggedIn && !_skippedAuthAsGuest) {
            return EttehadAuthScreen(
              repo: _repo,
              initialStep: (!_repo.isProfileCompleted && _repo.authToken != null) ? 3 : 0,
              onLoginSuccess: () {
                setState(() {});
              },
              onSkipGuest: () {
                setState(() => _skippedAuthAsGuest = true);
              },
            );
          }
          return EttehadMainShell(repo: _repo);
        },
      ),
    );
  }
}


class _SplashLoadingScreen extends StatelessWidget {
  const _SplashLoadingScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFBF9F4),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 108,
              height: 108,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(28),
                boxShadow: [
                  BoxShadow(
                    color: EttehadColors.primary.withValues(alpha: 0.14),
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Image.asset('assets/images/app_icon.png', fit: BoxFit.contain),
            ),
            const SizedBox(height: 20),
            const Text(
              'سامانه معارفی و کتابخوان «اتحاد»',
              style: TextStyle(color: EttehadColors.navy, fontSize: 18, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            const Text(
              'در حال بارگذاری پایگاه جامع آفلاین قرآن، تفاسیر و کتب مرجع...',
              style: TextStyle(color: Colors.black54, fontSize: 12),
            ),
            const SizedBox(height: 24),
            const CircularProgressIndicator(color: EttehadColors.primary),
          ],
        ),
      ),
    );
  }
}

class EttehadMainShell extends StatefulWidget {
  final EttehadRepository repo;

  const EttehadMainShell({super.key, required this.repo});

  @override
  State<EttehadMainShell> createState() => _EttehadMainShellState();
}

class _EttehadMainShellState extends State<EttehadMainShell> {
  static const double _bottomNavHeight = 60;
  int _selectedIndex = 0; // 0: کتابخانه, 1: قرآن کریم, 2: اتحادیار, 3: اتحاد کده, 4: ابزار کده
  String? _pendingAiPrompt;

  void _showProfileSheet() {
    showEttehadUserProfile(context, widget.repo);
  }

  Future<bool> _showExitConfirmDialog() async {
    final shouldExit = await showDialog<bool>(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          backgroundColor: Colors.white,
          title: const Row(
            children: [
              Icon(Icons.exit_to_app_rounded, color: EttehadColors.primary, size: 24),
              SizedBox(width: 8),
              Text(
                'خروج از برنامه',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: EttehadColors.navy),
              ),
            ],
          ),
          content: const Text(
            'آیا می‌خواهید از سامانه کتابخوان معارفی اتحاد خارج شوید؟',
            style: TextStyle(fontSize: 13, color: Colors.black87, height: 1.5),
          ),
          actionsPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text(
                'انصراف و ماندن',
                style: TextStyle(color: Colors.black54, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFEF4444),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                elevation: 0,
              ),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text(
                'بله، خروج',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
    return shouldExit ?? false;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;

        // If user is on any other tab, first navigate back to Library (tab 0)
        if (_selectedIndex != 0) {
          setState(() => _selectedIndex = 0);
          return;
        }

        // When on the home/library tab, confirm before closing
        final confirmed = await _showExitConfirmDialog();
        if (confirmed) {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        extendBody: false,
        resizeToAvoidBottomInset: false,
        // AppBar removed per requirement 4
        body: Builder(
          builder: (context) {
            final mq = MediaQuery.of(context);
            // ارتفاع نوار پایین را از ارتفاع کیبورد کم می‌کنیم تا فاصله‌ی سفید ایجاد نشود
            final adjustedKeyboard =
                (mq.viewInsets.bottom - _bottomNavHeight).clamp(0.0, double.infinity);
            return MediaQuery(
              data: mq.copyWith(
                viewInsets: mq.viewInsets.copyWith(bottom: adjustedKeyboard),
              ),
              child: SafeArea(
                bottom: false,
                child: IndexedStack(
                  index: _selectedIndex,
                  children: [
                    LibraryScreen(
                      repo: widget.repo,
                      onAskAiAboutBook: (bookId, bookTitle) {
                        setState(() {
                          _pendingAiPrompt = 'لطفاً خلاصه، موضوعات اصلی و دیدگاه‌های کتاب «$bookTitle» را تحلیل کن.';
                          _selectedIndex = 2;
                        });
                      },
                      onOpenProfile: _showProfileSheet,
                    ),
                    QuranScreen(repo: widget.repo),
                    AiChatScreen(
                      repo: widget.repo,
                      initialPrompt: _pendingAiPrompt,
                    ),
                    QnaScreen(repo: widget.repo),
                    ToolsScreen(repo: widget.repo),
                  ],
                ),
              ),
            );
          },
        ),
        bottomNavigationBar: _buildSymmetricalBottomNav(),
      ),
    );
  }

  Widget _buildSymmetricalBottomNav() {
    return Container(
      height: _bottomNavHeight,
      decoration: BoxDecoration(
        color: EttehadColors.paper,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: const Border(top: BorderSide(color: EttehadColors.border)),
        boxShadow: [
          BoxShadow(
            color: EttehadColors.navy.withValues(alpha: 0.12),
            blurRadius: 16,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _navItem(0, 'کتابخانه', Icons.local_library_rounded),
          _navItem(1, 'قرآن کریم', Icons.menu_book_rounded),
          // Center Elevated Ettehad-Yar Button
          GestureDetector(
            onTap: () => setState(() => _selectedIndex = 2),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Transform.translate(
                  offset: const Offset(0, -11),
                  child: Container(
                    width: 56,
                    height: 56,
                    padding: const EdgeInsets.all(2.0),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: const LinearGradient(
                        colors: [EttehadColors.navy, EttehadColors.primary, EttehadColors.mint],
                        begin: Alignment.bottomLeft,
                        end: Alignment.topRight,
                      ),
                      border: Border.all(color: EttehadColors.paper, width: 3.0),
                      boxShadow: [
                        BoxShadow(
                          color: EttehadColors.primary.withValues(alpha: 0.45),
                          blurRadius: 14,
                          offset: const Offset(0, 5),
                        ),
                      ],
                    ),
                    child: Image.asset('assets/images/logo_symbol_white.png', fit: BoxFit.contain),
                  ),
                ),
                Transform.translate(
                  offset: const Offset(0, -9),
                  child: Text(
                    'اتحادیار',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w900,
                      color: _selectedIndex == 2 ? EttehadColors.primary : EttehadColors.navy,
                    ),
                  ),
                ),
              ],
            ),
          ),
          _navItem(3, 'اتحاد کده', Icons.forum_rounded),
          _navItem(4, 'ابزار کده', Icons.explore_rounded),
        ],
      ),
    );
  }

  Widget _navItem(int index, String label, IconData icon) {
    final active = _selectedIndex == index;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _selectedIndex = index),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 23,
              color: active ? EttehadColors.primary : Colors.black54,
            ),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: active ? FontWeight.w900 : FontWeight.w600,
                color: active ? EttehadColors.primary : Colors.black54,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
