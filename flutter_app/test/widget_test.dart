import 'package:flutter_test/flutter_test.dart';
import 'package:ettehad_app/main.dart';

void main() {
  testWidgets('EttehadNativeApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const EttehadNativeApp());
    expect(find.textContaining('اتحاد'), findsWidgets);
  });
}
