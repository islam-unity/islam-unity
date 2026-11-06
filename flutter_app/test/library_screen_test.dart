import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/features/library/library_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late EttehadRepository repo;

  setUp(() {
    repo = EttehadRepository();
    repo.books = [
      {
        'id': 'book_nahj',
        'title': 'نهج‌البلاغه (ترجمه و شرح برگزیده)',
        'author': 'امام علی بن ابی‌طالب (ع)',
        'category_id': 'hadith',
        'description': 'خطبه‌ها، نامه‌ها و حکمت‌های امیرالمؤمنین',
        'publisher': 'دارالکتب الاسلامیه',
        'rating': 4.9,
      },
      {
        'id': 'book_forty_hadith',
        'title': 'چهل حدیث اخلاقی و معنوی',
        'author': 'امام خمینی (ره)',
        'category_id': 'hadith',
        'description': 'شرح چهل حدیث معتبر اخلاقی و عرفانی',
        'publisher': 'دارالعرفان',
        'rating': 4.8,
      },
      {
        'id': 'tafsir_mizan',
        'title': 'المیزان فی تفسیر القرآن',
        'author': 'علامه طباطبایی',
        'category_id': 'tafsir',
        'description': 'تفسیر قرآن به قرآن علامه طباطبایی',
        'publisher': 'دارالکتب الاسلامیه',
        'rating': 5.0,
      },
    ];
    repo.shelves = [
      {
        'id': 'shelf_reading',
        'name': 'در حال مطالعه',
        'icon': 'auto_stories',
        'bookIds': ['book_nahj'],
      },
      {
        'id': 'shelf_favorites',
        'name': 'کتاب‌های برگزیده تقریب',
        'icon': 'bookmark_star',
        'bookIds': ['book_forty_hadith', 'tafsir_mizan'],
      },
    ];
    repo.categories = [
      {'id': 'tafsir', 'name': 'تفسیر قرآن', 'icon': 'menu_book'},
      {'id': 'hadith', 'name': 'حدیث و روایات', 'icon': 'format_quote'},
    ];
  });

  testWidgets('LibraryScreen full flow test: switcher, categories, details modal & reader', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(
      MaterialApp(
        home: Directionality(
          textDirection: TextDirection.rtl,
          child: Scaffold(
            body: LibraryScreen(repo: repo),
          ),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // 1. Verify storefront renders with books
    expect(find.byType(LibraryScreen), findsOneWidget);
    expect(find.textContaining('نهج'), findsWidgets);

    // 2. Switch to Shelves view
    final shelvesTab = find.text('قفسه‌های من');
    expect(shelvesTab, findsOneWidget);
    await tester.tap(shelvesTab);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify shelves view
    expect(find.text('در حال مطالعه'), findsOneWidget);
    expect(find.text('کتاب‌های برگزیده تقریب'), findsOneWidget);

    // 3. Switch back to Storefront
    final storeTab = find.text('ویترین و کاوش');
    expect(storeTab, findsOneWidget);
    await tester.tap(storeTab);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 4. Test Category Filter chip
    final tafsirChip = find.text('تفسیر قرآن').first;
    await tester.tap(tafsirChip);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.textContaining('المیزان'), findsWidgets);

    // 5. Open Book Details Modal
    final mizanBook = find.textContaining('المیزان').first;
    await tester.tap(mizanBook);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    // Verify modal elements (start reading button)
    final startReadingBtn = find.text('مطالعه اثر در کتابخوان');
    expect(startReadingBtn, findsOneWidget);

    // 6. Tap Start Reading to open NativeBookReaderScreen
    await tester.tap(startReadingBtn);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byType(NativeBookReaderScreen), findsOneWidget);
    expect(find.textContaining('المیزان'), findsWidgets);

    // Test reader interaction (TOC button)
    final tocButton = find.byIcon(Icons.format_list_bulleted_rounded);
    expect(tocButton, findsOneWidget);
    await tester.tap(tocButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // All LibraryScreen full-flow interactions succeeded!
  });
}
