import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/features/ai_chat/ai_chat_screen.dart';
import 'package:ettehad_app/ui/features/library/library_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('AiChatScreen renders Markdown for AI responses and eliminates white gap on keyboard open', (WidgetTester tester) async {
    final repo = EttehadRepository();
    repo.initialize();

    await tester.pumpWidget(
      MaterialApp(
        home: Directionality(
          textDirection: TextDirection.rtl,
          child: AiChatScreen(repo: repo),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 1. Verify initial message uses MarkdownBody
    expect(find.byType(MarkdownBody), findsWidgets);

    // 2. Verify no tick checklist accordion ("مراحل تفکر") in message
    expect(find.textContaining('مراحل تفکر و کاوش دستیار'), findsNothing);

    // 3. Verify input bar adapts snugly without white gap
    final outerContainerFinder = find.byWidgetPredicate(
      (w) => w is Container && w.decoration is BoxDecoration && (w.decoration as BoxDecoration).color == const Color(0xFFFBF9F4),
    );
    expect(outerContainerFinder, findsOneWidget);
    final containerWidget = tester.widget<Container>(outerContainerFinder);
    final insetsClosed = containerWidget.padding as EdgeInsets;
    expect(insetsClosed.bottom, equals(8.0)); // Snug 8px padding directly above bottom bar / keyboard

    // Simulate keyboard open by setting viewInsets
    tester.view.viewInsets = const FakeViewPadding(bottom: 300.0);
    await tester.pumpAndSettle();

    final containerWidgetOpen = tester.widget<Container>(outerContainerFinder);
    final insetsOpen = containerWidgetOpen.padding as EdgeInsets;
    expect(insetsOpen.bottom, equals(8.0)); // Snug 8px padding directly on keyboard

    // Reset viewInsets
    tester.view.resetViewInsets();
  });

  testWidgets('AiChatScreen input bar remains visible with snug padding', (WidgetTester tester) async {
    final repo = EttehadRepository();
    repo.initialize();

    await tester.pumpWidget(
      MaterialApp(
        home: Directionality(
          textDirection: TextDirection.rtl,
          child: AiChatScreen(repo: repo),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Verify input TextField exists and is visible
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('سؤال علمی، فقهی، قرآنی یا اخلاقی خود را بنویسید...'), findsOneWidget);

    final outerContainerFinder = find.byWidgetPredicate(
      (w) => w is Container && w.decoration is BoxDecoration && (w.decoration as BoxDecoration).color == const Color(0xFFFBF9F4),
    );
    expect(outerContainerFinder, findsOneWidget);
    final insetsClosed = tester.widget<Container>(outerContainerFinder).padding as EdgeInsets;
    expect(insetsClosed.bottom, equals(8.0));
  });

  testWidgets('Book citation resolves and opens NativeBookReaderScreen without crashing', (WidgetTester tester) async {
    final repo = EttehadRepository();
    repo.initialize();

    await tester.pumpWidget(
      MaterialApp(
        home: Directionality(
          textDirection: TextDirection.rtl,
          child: NativeBookReaderScreen(
            book: const {
              'id': 'source://book/bk_hadith_nawawi40/chapter/ch_001',
              'title': 'الأحاديث النبوية في الأحاديث الصحيحة النبوية - الأربعون النووية',
              'author': 'مشترک مذاهب',
            },
            repo: repo,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Verify it rendered successfully without crash or clamp error
    expect(find.byType(NativeBookReaderScreen), findsOneWidget);
    expect(find.textContaining('الأربعون النووية'), findsWidgets);
  });
}
