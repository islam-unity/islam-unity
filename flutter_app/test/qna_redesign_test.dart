import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/features/qna/qna_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('QnaScreen Redesign Visual & Functional Tests', () {
    late EttehadRepository repo;

    setUp(() async {
      repo = EttehadRepository();
      // Initialize with test data
      repo.scholars = [
        {
          'id': 'scholar_1',
          'name': 'آیت‌الله دکتر موسوی',
          'title': 'استاد سطوح عالی حوزه علمیه',
          'city': 'قم',
          'madhhab': 'شیعه اثناعشری',
          'answer_count': 540,
          'response_time_hours': 2,
          'specialties': '["فقه مقارن", "حکمت متعالیه"]',
        },
        {
          'id': 'scholar_2',
          'name': 'ماموستا عبدالرحمن مرادی',
          'title': 'امام جمعه اهل سنت و استاد فقه شافعی',
          'city': 'سنندج',
          'madhhab': 'اهل سنت (شافعی)',
          'answer_count': 320,
          'response_time_hours': 3,
          'specialties': '["فقه شافعی", "تقریب مذاهب"]',
        },
      ];

      repo.posts = [
        {
          'id': 'post_1',
          'scholar_id': 'scholar_1',
          'title': 'حکم معاملات رمزارزها از منظر فقه معاصر',
          'content': 'در این تحلیل به شروط صحت بیع و پرهیز از غرر در ارزهای دیجیتال پرداخته‌ام.',
          'category': 'FIQH',
          'madhhab': 'مشترک',
          'likes_count': 142,
          'views_count': 1850,
        },
      ];

      repo.books = [
        {
          'id': 'book_nahj',
          'title': 'نهج‌البلاغه شریف',
          'author': 'سید رضی (ره)',
          'category_id': 'HADITH',
          'pages_count': 640,
        },
        {
          'id': 'tafsir_mizan',
          'title': 'تفسیر المیزان',
          'author': 'علامه طباطبایی',
          'category_id': 'TAFSIR',
          'pages_count': 520,
        },
      ];

      repo.scholarChats.clear();
      repo.scholarChats.addAll([
        {
          'scholar': repo.scholars.first,
          'tracking_code': 'ETH-Q-84920',
          'status': 'WAITING_SCHOLAR',
          'lastMessage': 'سلام علیکم، پاسخ استفتاء شما در حال بررسی است.',
          'messages': [
            {'sender': 'user', 'text': 'سلام علیکم، آیا خمس به سهام تعلق می‌گیرد؟', 'time': '۱۰:۰۰'},
            {'sender': 'scholar', 'text': 'پاسخ مستند ارسال خواهد شد.', 'time': '۱۰:۰۵'},
          ],
        }
      ]);
      repo.isInitialized = true;
    });

    Widget createTestApp() {
      return MaterialApp(
        home: Directionality(
          textDirection: TextDirection.rtl,
          child: Scaffold(
            body: QnaScreen(repo: repo),
          ),
        ),
      );
    }

    testWidgets('Renders QnaScreen with top bar, tracker hero and 4 tabs', (tester) async {
      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Top title and subtitles
      expect(find.text('اتحادکده'), findsOneWidget);
      expect(find.text('میز استفتائات، فقه مقارن و مطالب اساتید'), findsOneWidget);

      // Hero banner buttons
      expect(find.text('نقشه مساجد (GPS)'), findsOneWidget);
      expect(find.text('طرح سوال و استفتاء جدید (متنی یا صوتی)'), findsOneWidget);

      // 4 Navigation Tabs
      expect(find.text('استفتائات من'), findsOneWidget);
      expect(find.text('مطالب اساتید'), findsOneWidget);
      expect(find.text('بانک پاسخ‌ها'), findsOneWidget);
      expect(find.text('معرفی اساتید'), findsOneWidget);
    });

    testWidgets('Shows active inquiry in My Inquiries tab', (tester) async {
      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Check active chat card
      expect(find.textContaining('ETH-Q'), findsWidgets);
      expect(find.text('در حال بررسی استاد'), findsOneWidget);
      expect(find.text('آیت‌الله دکتر موسوی'), findsWidgets);
    });

    testWidgets('Can switch to Scholar Insights tab and view posts', (tester) async {
      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Tap on 'مطالب اساتید'
      await tester.tap(find.text('مطالب اساتید'));
      await tester.pumpAndSettle();

      // Verify post content
      expect(find.text('حکم معاملات رمزارزها از منظر فقه معاصر'), findsOneWidget);
      expect(find.text('طرح سوال از استاد'), findsOneWidget);
      expect(find.text('فقه و احکام نوین'), findsOneWidget);
    });

    testWidgets('Can open Mosques Map modal and view mosque cards', (tester) async {
      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Tap Mosques button
      await tester.tap(find.text('مساجد'));
      await tester.pumpAndSettle();

      // Check modal content
      expect(find.text('نشانی مساجد و مراکز معارفی (GPS)'), findsOneWidget);
      expect(find.textContaining('مسجد جامع'), findsWidgets);
      expect(find.text('مسیریابی روی نقشه'), findsWidgets);
    });

    testWidgets('Can open New Inquiry modal with voice recording and anonymous options', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Tap FAB
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Check modal fields
      expect(find.text('طرح سوال و استفتاء اختصاصی'), findsOneWidget);
      expect(find.text('انتخاب عالم دینی جهت ارسال مستقیم سوال'), findsOneWidget);
      expect(find.text('ضبط پیام صوتی (Voice Memo)'), findsOneWidget);
      expect(find.text('ارسال کاملاً ناشناس بدون ذکر نام و مشخصات'), findsOneWidget);
      expect(find.text('ثبت نهایی سوال و ارسال به استاد منتخب'), findsOneWidget);
    });

    testWidgets('Can open ScholarPickerModal with GPS proximity, scholar name search and step 2 filters', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Tap FAB to open NewInquiryModal
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Tap 'فیلتر پیشرفته بر اساس استان، شهر، مذهب، تخصص و مسجد'
      final filterBtn = find.textContaining('فیلتر پیشرفته بر اساس استان');
      expect(filterBtn, findsOneWidget);
      await tester.tap(filterBtn);
      await tester.pumpAndSettle();

      // Verify ScholarPickerModal is displayed with GPS-first & Name Search
      expect(find.text('جستجو و فیلتر پیشرفته علما و اساتید'), findsOneWidget);
      expect(find.textContaining('۶۰۰ عالم برجسته در ۳۲ استان'), findsOneWidget);
      expect(find.text('جستجو بر اساس نام عالم دینی'), findsOneWidget);
      expect(find.textContaining('مرحله ۱ (پیش‌فرض): موقعیت GPS شما'), findsOneWidget);
      expect(find.textContaining('مرحله ۲: فیلترهای تکمیلی'), findsOneWidget);

      // Expand Step 2 Filters
      await tester.tap(find.textContaining('مرحله ۲: فیلترهای تکمیلی'));
      await tester.pumpAndSettle();

      expect(find.text('دارای مسجد'), findsWidgets);
    });

    testWidgets('Scholar search filters specifically by scholar name', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Tap on Scholars Directory tab
      await tester.tap(find.text('معرفی اساتید'));
      await tester.pumpAndSettle();

      expect(find.text('جستجو بر اساس نام عالم دینی'), findsOneWidget);
      expect(find.textContaining('موقعیت GPS شما'), findsOneWidget);

      // Enter scholar name in search
      await tester.enterText(find.byType(TextField).first, 'مرتضی');
      await tester.pumpAndSettle();

      // Verify the matching scholar is shown
      expect(find.textContaining('مرتضی'), findsWidgets);
    });

    testWidgets('Can attach book or AI excerpt to new inquiry and see badge in My Inquiries', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Tap FAB to open NewInquiryModal
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Find and tap book attachment section
      final attachBtn = find.textContaining('پیوست کتاب یا گزیده متن');
      expect(attachBtn, findsOneWidget);
      await tester.tap(attachBtn);
      await tester.pumpAndSettle();

      // Check BookExcerptPickerModal appears with both tabs
      expect(find.text('پیوست کتاب یا فراز متن به عالم دینی'), findsOneWidget);
      expect(find.text('انتخاب از کتب کتابخانه'), findsOneWidget);
      expect(find.text('فرازهای تحلیل هوش مصنوعی'), findsOneWidget);

      // Switch to AI analysis tab
      await tester.tap(find.text('فرازهای تحلیل هوش مصنوعی'));
      await tester.pumpAndSettle();

      // Tap 'پیوست این تحلیل هوش به استفتاء'
      final attachAiBtn = find.text('پیوست این تحلیل هوش به استفتاء').first;
      await tester.tap(attachAiBtn);
      await tester.pumpAndSettle();

      // Verify preview card appears in NewInquiryModal
      expect(find.textContaining('کتاب پیوست‌شده:'), findsOneWidget);
      expect(find.textContaining('تحلیل هوش مصنوعی'), findsOneWidget);

      // Fill in title
      await tester.enterText(find.byType(TextField).at(0), 'سوال فقهی پیرامون فراز پیوست‌شده');
      await tester.pumpAndSettle();

      // Submit
      await tester.tap(find.text('ثبت نهایی سوال و ارسال به استاد منتخب'));
      await tester.pumpAndSettle();

      // Check inquiry was added and book badge is visible in My Inquiries tab
      expect(find.textContaining('کتاب:'), findsWidgets);
    });

    testWidgets('Can attach book excerpt in ScholarChatRoomScreen', (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Tap on the first chat in My Inquiries tab to open ScholarChatRoomScreen
      await tester.tap(find.text('آیت‌الله دکتر موسوی').first);
      await tester.pumpAndSettle();

      // Verify chat screen is open
      expect(find.textContaining('دفتر استفتائات آیت‌الله دکتر موسوی'), findsOneWidget);

      // Find attachment button in input bar
      final attachIcon = find.byTooltip('پیوست کتاب یا گزیده متن (کتابخانه / هوش مصنوعی)');
      expect(attachIcon, findsOneWidget);
      await tester.tap(attachIcon);
      await tester.pumpAndSettle();

      // Modal opens
      expect(find.text('پیوست کتاب یا فراز متن به عالم دینی'), findsOneWidget);

      // Select book from Library tab
      await tester.tap(find.textContaining('تأیید و پیوست'));
      await tester.pumpAndSettle();

      // Verify book reference message is now in chat
      expect(find.textContaining('ارجاع به کتاب:'), findsWidgets);
    });

    testWidgets('Hides orange FAB when user has no inquiries and shows blue button; shows orange FAB when inquiries exist', (tester) async {
      // 1. When inquiries are empty
      repo.scholarChats.clear();
      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Orange FAB should be hidden (null)
      expect(find.byType(FloatingActionButton), findsNothing);
      // Blue button in empty state should be visible
      expect(find.text('طرح اولین سوال و استفتاء'), findsOneWidget);

      // 2. When user submits or has at least 1 inquiry
      repo.scholarChats.add({
        'scholar': repo.scholars.first,
        'tracking_code': 'ETH-Q-99999',
        'status': 'WAITING_SCHOLAR',
        'lastMessage': 'در حال بررسی',
      });
      await tester.pumpWidget(createTestApp());
      await tester.pumpAndSettle();

      // Orange FAB should now appear
      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.text('طرح سوال و استفتاء جدید'), findsOneWidget);
    });
  });
}
