import 'package:flutter/material.dart';

class EttehadColors {
  static const Color navy = Color(0xFF0A2E6E);
  static const Color midnight = Color(0xFF09152B);
  static const Color primary = Color(0xFF0B72E7);
  static const Color ocean = Color(0xFF1499DE);
  static const Color mint = Color(0xFF22C1D6);
  static const Color sky = Color(0xFF46CCF3);
  static const Color amber = Color(0xFFD97706);
  static const Color amberDark = Color(0xFFB45309);
  static const Color amberLight = Color(0xFFF59E0B);
  static const Color paper = Color(0xFFFBF9F4);
  static const Color surface = Color(0xFFF8FAFC);
  static const Color surfaceLow = Color(0xFFF1F5F9);
  static const Color ink = Color(0xFF0A1B39);
  static const Color border = Color(0xFFE5DEC9);
  static const Color skyCardStart = Color(0xFFE0F2FE);
  static const Color skyCardEnd = Color(0xFFBAE6FD);
  static const Color emerald = Color(0xFF10B981);
  static const Color emeraldDark = Color(0xFF065F46);
  static const Color inkLight = Color(0xFF64748B);
}

String toPersianDigits(dynamic input) {
  if (input == null) return '';
  final str = input.toString();
  const en = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
  const fa = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
  var out = str;
  for (var i = 0; i < 10; i++) {
    out = out.replaceAll(en[i], fa[i]);
  }
  return out;
}

ThemeData buildEttehadTheme() {
  return ThemeData(
    useMaterial3: true,
    fontFamily: 'Vazirmatn',
    scaffoldBackgroundColor: EttehadColors.paper,
    colorScheme: ColorScheme.fromSeed(
      seedColor: EttehadColors.primary,
      primary: EttehadColors.primary,
      secondary: EttehadColors.amber,
      surface: EttehadColors.paper,
      onSurface: EttehadColors.ink,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: EttehadColors.paper,
      foregroundColor: EttehadColors.navy,
      elevation: 0,
      centerTitle: true,
    ),
  );
}
