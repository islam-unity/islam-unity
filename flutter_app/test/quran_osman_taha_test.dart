import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/features/quran/quran_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late EttehadRepository repo;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    repo = EttehadRepository();
    await repo.initialize();
  });

  group('Quran Osman Taha & 30 Juz Data Structure Tests', () {
    test('Repo initializes 604 Osman Taha pages and 30 Juz', () {
      expect(repo.surahs.length, 114);
      expect(repo.quranPages.length, 604);
      expect(repo.juzList.length, 30);

      // Verify Page 1 (Al-Fatihah 1-7)
      final p1 = repo.getAyahsForPage(1);
      expect(p1.length, 7);
      expect(p1.first['surahId'], 1);
      expect(p1.first['ayahNumber'], 1);
      expect(p1.last['ayahNumber'], 7);

      // Verify Page 2 (Al-Baqarah 1-5)
      final p2 = repo.getAyahsForPage(2);
      expect(p2.length, 5);
      expect(p2.first['surahId'], 2);
      expect(p2.first['ayahNumber'], 1);
      expect(p2.last['ayahNumber'], 5);

      // Verify Page 604 (Surah 112, 113, 114)
      final p604 = repo.getAyahsForPage(604);
      expect(p604.length, 15);
      expect(p604.first['surahId'], 112);
      expect(p604.last['surahId'], 114);

      // Verify Juz 1 (Page 1 to 21)
      final j1 = repo.juzList[0];
      expect(j1['juzNumber'], 1);
      expect(j1['startPage'], 1);
      expect(j1['endPage'], 21);

      // Verify Juz 30 (Page 582 to 604)
      final j30 = repo.juzList[29];
      expect(j30['juzNumber'], 30);
      expect(j30['startPage'], 582);
      expect(j30['endPage'], 604);
    });

    test('Helper functions getStartPageForSurah and getStartPageForJuz work correctly', () {
      expect(repo.getStartPageForSurah(1), 1);
      expect(repo.getStartPageForSurah(2), 2);
      expect(repo.getStartPageForSurah(18), 293); // Al-Kahf
      expect(repo.getStartPageForSurah(114), 604); // An-Nas

      expect(repo.getStartPageForJuz(1), 1);
      expect(repo.getStartPageForJuz(2), 22);
      expect(repo.getStartPageForJuz(30), 582);

      expect(repo.getJuzForPage(1), 1);
      expect(repo.getJuzForPage(22), 2);
      expect(repo.getJuzForPage(582), 30);
      expect(repo.getJuzForPage(604), 30);
    });

    test('getSurahsForJuz returns accurate surahs for Juz 1 and Juz 30', () {
      final sJuz1 = repo.getSurahsForJuz(1);
      expect(sJuz1.any((s) => s['id'] == 1), isTrue); // Al-Fatihah
      expect(sJuz1.any((s) => s['id'] == 2), isTrue); // Al-Baqarah

      final sJuz30 = repo.getSurahsForJuz(30);
      expect(sJuz30.length, greaterThanOrEqualTo(30));
      expect(sJuz30.any((s) => s['id'] == 78), isTrue); // An-Naba
      expect(sJuz30.any((s) => s['id'] == 114), isTrue); // An-Nas
    });
  });

  group('QuranScreen & NativeQuranReaderScreen Widget Tests', () {
    testWidgets('Renders QuranScreen with 2 tabs and Juz filter chip', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Directionality(
            textDirection: TextDirection.rtl,
            child: Scaffold(body: QuranScreen(repo: repo)),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Check tab switchers exist
      expect(find.text('فهرست سوره‌ها (۱۱۴)'), findsOneWidget);
      expect(find.text('۳۰ جزء قرآن مجید'), findsOneWidget);

      // Check Juz filter action chip exists
      expect(find.text('فیلتر جزء (۱ تا ۳۰)'), findsOneWidget);

      // Switch to 30 Juz tab
      await tester.tap(find.text('۳۰ جزء قرآن مجید'));
      await tester.pumpAndSettle();

      // Verify Juz 1 and Juz 2 cards exist
      expect(find.text('جزء ۱ قرآن کریم'), findsOneWidget);
      expect(find.text('مصحف عثمان‌طه (ورق‌زدنی)'), findsWidgets);
    });

    testWidgets('NativeQuranReaderScreen in Osman Taha mode renders PageView and book controls', (tester) async {
      final fatiha = repo.surahs.first;

      await tester.pumpWidget(
        MaterialApp(
          home: Directionality(
            textDirection: TextDirection.rtl,
            child: NativeQuranReaderScreen(
              surah: fatiha,
              repo: repo,
              initialMode: 'uthman',
              initialPage: 1,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Osman Taha horizontal PageView is rendered
      expect(find.byType(PageView), findsOneWidget);

      // Check top header inside page has Surah and Juz indicator
      expect(find.textContaining('الفاتحة'), findsWidgets);
      expect(find.text('الجُزْءُ ۱'), findsWidgets);

      // Check page footer has page number 1
      expect(find.text('— ۱ —'), findsOneWidget);

      // Check bottom navigation HUD has page indicator and jump button
      expect(find.text('صفحه ۱ از ۶۰۴'), findsOneWidget);
      expect(find.text('پرش به جزء'), findsOneWidget);

      // Check turning page works via navigation button
      final nextBtn = find.byTooltip('صفحه بعد');
      expect(nextBtn, findsOneWidget);
      await tester.tap(nextBtn);
      await tester.pumpAndSettle();

      // Now on page 2 (Al-Baqarah)
      expect(find.text('صفحه ۲ از ۶۰۴'), findsOneWidget);
      expect(find.text('— ۲ —'), findsOneWidget);
    });
  });
}
