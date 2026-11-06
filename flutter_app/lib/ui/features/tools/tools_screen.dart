import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../data/ettehad_repository.dart';
import '../../core/theme.dart';
import '../profile/profile_sheet.dart';

class ToolsScreen extends StatefulWidget {
  final EttehadRepository repo;

  const ToolsScreen({super.key, required this.repo});

  @override
  State<ToolsScreen> createState() => _ToolsScreenState();
}

class _ToolsScreenState extends State<ToolsScreen> {
  String _selectedCity = 'تهران';
  int _dhikrCount = 0;
  int _selectedDhikrIdx = 0;
  Map<String, dynamic>? _istikharaResult;
  bool _isIstikharaLoading = false;

  static const Map<String, List<double>> _cityCoordinates = {
    'تهران': [35.6892, 51.3890],
    'مشهد مقدس': [36.2972, 59.6067],
    'مشهد': [36.2972, 59.6067],
    'اصفهان': [32.6546, 51.6680],
    'شیراز': [29.5918, 52.5837],
    'تبریز': [38.0800, 46.2919],
    'قم': [34.6401, 50.8764],
    'قم مقدس': [34.6401, 50.8764],
    'اهواز': [31.3183, 48.6706],
    'ارومیه': [37.5527, 45.0761],
    'کرمانشاه': [34.3277, 47.0778],
    'گرگان': [36.8427, 54.4439],
    'سنندج': [35.3219, 46.9862],
    'زاهدان': [29.4963, 60.8629],
    'رشت': [37.2808, 49.5832],
    'یزد': [31.8974, 54.3569],
    'کرمان': [30.2839, 57.0834],
    'بندرعباس': [27.1832, 56.2666],
    'بوشهر': [28.9234, 50.8203],
    'زنجان': [36.6736, 48.4787],
    'ساری': [36.5633, 53.0601],
    'همدان': [34.7989, 48.5150],
  };

  double get _qiblaAngle {
    final coords = _cityCoordinates[_selectedCity] ?? _cityCoordinates['تهران']!;
    final phi = coords[0] * pi / 180.0;
    final lambda = coords[1] * pi / 180.0;
    const kaabaLat = 21.4225 * pi / 180.0;
    const kaabaLng = 39.8262 * pi / 180.0;
    final deltaLng = kaabaLng - lambda;

    final y = sin(deltaLng);
    final x = cos(phi) * tan(kaabaLat) - sin(phi) * cos(deltaLng);
    double bearing = atan2(y, x) * 180.0 / pi;
    return (bearing + 360.0) % 360.0;
  }

  double get _distanceToKaabaKm {
    final coords = _cityCoordinates[_selectedCity] ?? _cityCoordinates['تهران']!;
    const r = 6371.0;
    final phi1 = coords[0] * pi / 180.0;
    const phi2 = 21.4225 * pi / 180.0;
    final deltaPhi = phi2 - phi1;
    final deltaLambda = (39.8262 - coords[1]) * pi / 180.0;

    final a = sin(deltaPhi / 2) * sin(deltaPhi / 2) +
        cos(phi1) * cos(phi2) * sin(deltaLambda / 2) * sin(deltaLambda / 2);
    final c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return r * c;
  }

  @override
  void initState() {
    super.initState();
    widget.repo.syncDailyDhikrs().then((_) {
      if (mounted) setState(() {});
    });
  }

  final List<Map<String, dynamic>> _weekDhikrs = [
    {'day': 'شنبه', 'dhikr': 'یا رَبَّ الْعالَمین', 'count': 100, 'virtue': 'موجب فزونی مال و برکت'},
    {'day': 'یکشنبه', 'dhikr': 'یا ذَا الْجَلالِ وَ الْاِکْرام', 'count': 100, 'virtue': 'موجب فتح و نصرت'},
    {'day': 'دوشنبه', 'dhikr': 'یا قاضِیَ الْحاجات', 'count': 100, 'virtue': 'موجب کثرت مال و بی‌نیازی'},
    {'day': 'سه‌شنبه', 'dhikr': 'یا اَرْحَمَ الرّاحِمین', 'count': 100, 'virtue': 'موجب برآورده شدن حاجات'},
    {'day': 'چهارشنبه', 'dhikr': 'یا حَیُّ یا قَیّوم', 'count': 100, 'virtue': 'موجب عزت دائمی'},
    {'day': 'پنج‌شنبه', 'dhikr': 'لا اِلهَ اِلَّا اللهُ الْمَلِکُ الْحَقُّ الْمُبین', 'count': 100, 'virtue': 'موجب رزق وسیع و ایمنی از فقر'},
    {'day': 'جمعه', 'dhikr': 'اللّهُمَّ صَلِّ عَلی مُحَمَّدٍ وَ آلِ مُحَمَّدٍ وَ عَجِّلْ فَرَجَهُمْ', 'count': 100, 'virtue': 'موجب عزیز شدن و آمرزش گناهان'},
  ];

  List<Map<String, dynamic>> get _effectiveWeekDhikrs {
    if (widget.repo.dailyDhikrs.isNotEmpty) {
      return widget.repo.dailyDhikrs.map((d) {
        return {
          'day': d['title']?.toString().replaceFirst('ذکر روز ', '') ?? 'روز',
          'dhikr': d['arabic_text'] ?? d['dhikr'] ?? '',
          'count': (d['target_count'] as num?)?.toInt() ?? 100,
          'virtue': d['virtue'] ?? d['translation'] ?? '',
        };
      }).toList();
    }
    return _weekDhikrs;
  }

  String get _currentPersianDateString {
    final now = DateTime.now();
    final gYear = now.year;
    final gMonth = now.month;
    final gDay = now.day;
    final gDays = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    int gy = gYear - 1600;
    int gm = gMonth - 1;
    int gd = gDay - 1;
    int gDayNo = 365 * gy + ((gy + 3) ~/ 4) - ((gy + 99) ~/ 100) + ((gy + 399) ~/ 400);
    for (int i = 0; i < gm; ++i) {
      gDayNo += gDays[i + 1];
    }
    if (gm > 1 && ((gYear % 4 == 0 && gYear % 100 != 0) || (gYear % 400 == 0))) {
      gDayNo++;
    }
    gDayNo += gd;
    int jDayNo = gDayNo - 79;
    int jNp = jDayNo ~/ 12053;
    jDayNo %= 12053;
    int jy = 979 + 33 * jNp + 4 * (jDayNo ~/ 1461);
    jDayNo %= 1461;
    if (jDayNo >= 366) {
      jy += (jDayNo - 1) ~/ 365;
      jDayNo = (jDayNo - 1) % 365;
    }
    int jm;
    int jd;
    if (jDayNo < 186) {
      jm = 1 + (jDayNo ~/ 31);
      jd = 1 + (jDayNo % 31);
    } else {
      jm = 7 + ((jDayNo - 186) ~/ 30);
      jd = 1 + ((jDayNo - 186) % 30);
    }
    const weekDays = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه', 'یکشنبه'];
    const monthNames = [
      '', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
      'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ];
    final dayName = weekDays[(now.weekday - 1) % 7];
    return '$dayName، ${toPersianDigits(jd)} ${monthNames[jm]} ${toPersianDigits(jy)}';
  }

  String get _currentGregorianDateString {
    final now = DateTime.now();
    const months = [
      '', 'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return '${now.day} ${months[now.month]} ${now.year}';
  }

  Map<String, dynamic> _getCurrentCityData() {
    final cities = widget.repo.prayerTimes;
    final city = cities.firstWhere(
      (c) => (c['city_name'] ?? '').toString() == _selectedCity,
      orElse: () => cities.isNotEmpty
          ? cities.first
          : {
              'city_name': 'تهران',
              'fajr': '۰۴:۵۲',
              'sunrise': '۰۶:۱۸',
              'dhuhr': '۱۲:۰۴',
              'asr': '۱۵:۲۵',
              'sunset': '۱۷:۴۹',
              'maghrib': '۱۸:۰۸',
              'isha': '۱۹:۰۲',
              'midnight': '۲۳:۲۴',
            },
    );
    final res = Map<String, dynamic>.from(city);
    if (city['times'] is Map) {
      res.addAll(Map<String, dynamic>.from(city['times'] as Map));
    }
    return res;
  }

  // 1. Qibla Finder Modal
  void _openQiblaDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) => Directionality(
          textDirection: TextDirection.rtl,
          child: Container(
            height: MediaQuery.of(context).size.height * 0.85,
            decoration: const BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            ),
            child: Column(
              children: [
                Container(
                  margin: const EdgeInsets.only(top: 10, bottom: 6),
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: EttehadColors.emerald.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.explore_rounded, color: EttehadColors.emerald, size: 24),
                      ),
                      const SizedBox(width: 10),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('قبله‌نمای هوشمند سه‌بعدی', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                            Text('جهت‌یابی دقیق کعبه معظمه و زاویه انحراف قطب‌نما', style: TextStyle(fontSize: 11, color: Colors.black54)),
                          ],
                        ),
                      ),
                      IconButton(onPressed: () => Navigator.pop(ctx), icon: const Icon(Icons.close)),
                    ],
                  ),
                ),
                const Divider(height: 1),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      children: [
                        // City Selector for Qibla
                        Container(
                          margin: const EdgeInsets.only(bottom: 16),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                          decoration: BoxDecoration(
                            color: EttehadColors.surfaceLow,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: EttehadColors.border),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('افق و موقعیت جهت‌یابی:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                              DropdownButtonHideUnderline(
                                child: DropdownButton<String>(
                                  value: _cityCoordinates.containsKey(_selectedCity) ? _selectedCity : 'تهران',
                                  dropdownColor: Colors.white,
                                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.primary),
                                  onChanged: (v) {
                                    if (v != null) {
                                      setState(() => _selectedCity = v);
                                      setSheetState(() {});
                                    }
                                  },
                                  items: _cityCoordinates.keys.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                                ),
                              ),
                            ],
                          ),
                        ),

                        // Compass Circle
                        Container(
                          width: 250,
                          height: 250,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: const Color(0xFFFBF9F4),
                            border: Border.all(color: const Color(0xFFC8B998), width: 4),
                            boxShadow: [
                              BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 16, spreadRadius: 2),
                            ],
                          ),
                          child: Stack(
                            alignment: Alignment.center,
                            children: [
                              // Dial Markings
                              Transform.rotate(
                                angle: _qiblaAngle * (pi / 180),
                                child: Image.network(
                                  'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=400&q=80',
                                  fit: BoxFit.cover,
                                  opacity: const AlwaysStoppedAnimation(0.0),
                                ),
                              ),
                              // Direction texts
                              const Positioned(top: 8, child: Text('شمال (N)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 10, color: Colors.red))),
                              const Positioned(bottom: 8, child: Text('جنوب (S)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 10, color: Colors.black54))),
                              const Positioned(right: 8, child: Text('شرق (E)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 10, color: Colors.black54))),
                              const Positioned(left: 8, child: Text('غرب (W)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 10, color: Colors.black54))),

                              // Needle pointing to Qibla
                              Transform.rotate(
                                angle: (_qiblaAngle - 180) * (pi / 180),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(6),
                                      decoration: const BoxDecoration(
                                        color: EttehadColors.emerald,
                                        shape: BoxShape.circle,
                                        boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 4)],
                                      ),
                                      child: const Icon(Icons.mosque_rounded, color: Colors.white, size: 20),
                                    ),
                                    Container(
                                      width: 4,
                                      height: 70,
                                      decoration: BoxDecoration(
                                        color: EttehadColors.emeraldDark,
                                        borderRadius: BorderRadius.circular(2),
                                      ),
                                    ),
                                    const SizedBox(height: 70),
                                  ],
                                ),
                              ),

                              // Center Pin
                              Container(
                                width: 14,
                                height: 14,
                                decoration: const BoxDecoration(color: EttehadColors.navy, shape: BoxShape.circle),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),

                        // Info cards
                        Row(
                          children: [
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: EttehadColors.surfaceLow,
                                  borderRadius: BorderRadius.circular(14),
                                  border: Border.all(color: EttehadColors.border),
                                ),
                                child: Column(
                                  children: [
                                    const Text('زاویه قبله از شمال', style: TextStyle(fontSize: 10.5, color: Colors.black54)),
                                    const SizedBox(height: 4),
                                    Text('${toPersianDigits(_qiblaAngle.toStringAsFixed(1))}° جنوب غربی', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.primary)),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: EttehadColors.surfaceLow,
                                  borderRadius: BorderRadius.circular(14),
                                  border: Border.all(color: EttehadColors.border),
                                ),
                                child: Column(
                                  children: [
                                    const Text('فاصله تا مکه مکرمه', style: TextStyle(fontSize: 10.5, color: Colors.black54)),
                                    const SizedBox(height: 4),
                                    Text('${toPersianDigits(_distanceToKaabaKm.round().toString())} کیلومتر', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.emerald)),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),

                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: EttehadColors.emerald.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: EttehadColors.emerald.withValues(alpha: 0.25)),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.check_circle_rounded, color: EttehadColors.emerald, size: 20),
                              SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'سنسور مغناطیسی گوشی فعال و کالیبره است. دستگاه را به‌صورت افقی نگاه دارید.',
                                  style: TextStyle(fontSize: 11, color: Colors.black87),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // 2. Prayer Times Modal
  void _openPrayerDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) {
          final data = _getCurrentCityData();
          final cities = widget.repo.prayerTimes;

          return Directionality(
            textDirection: TextDirection.rtl,
            child: Container(
              height: MediaQuery.of(context).size.height * 0.85,
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              child: Column(
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 10, bottom: 6),
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.teal.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.schedule_rounded, color: Colors.teal, size: 24),
                        ),
                        const SizedBox(width: 10),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('اوقات شرعی و اذان‌گو', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                              Text('محاسبه دقیق اوقات بر اساس افق شهرهای ایران و وقت فضیلت', style: TextStyle(fontSize: 11, color: Colors.black54)),
                            ],
                          ),
                        ),
                        IconButton(onPressed: () => Navigator.pop(ctx), icon: const Icon(Icons.close)),
                      ],
                    ),
                  ),
                  const Divider(height: 1),
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        // City selector
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                          decoration: BoxDecoration(
                            color: EttehadColors.surfaceLow,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: EttehadColors.border),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('انتخاب شهر و افق شرعی:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                              DropdownButtonHideUnderline(
                                child: DropdownButton<String>(
                                  value: cities.any((c) => c['city_name'] == _selectedCity) ? _selectedCity : cities.first['city_name'].toString(),
                                  dropdownColor: Colors.white,
                                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.primary),
                                  onChanged: (v) {
                                    if (v != null) {
                                      setState(() => _selectedCity = v);
                                      setSheetState(() {});
                                    }
                                  },
                                  items: cities.map((c) => DropdownMenuItem(value: c['city_name'].toString(), child: Text(c['city_name'].toString()))).toList(),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 14),

                        // Upcoming prayer badge
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [EttehadColors.navy, EttehadColors.primary],
                            ),
                            borderRadius: BorderRadius.circular(18),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('فریضه بعدی در افق شما', style: TextStyle(color: Colors.white70, fontSize: 11)),
                                  SizedBox(height: 4),
                                  Text('اذان مغرب', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  const Text('زمان اذان', style: TextStyle(color: Colors.white70, fontSize: 11)),
                                  const SizedBox(height: 4),
                                  Text(data['maghrib'] ?? '۱۸:۰۸', style: const TextStyle(color: Colors.amberAccent, fontSize: 18, fontWeight: FontWeight.w900)),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),

                        // Prayer Table
                        _buildPrayerRow('اذان صبح', data['fajr'] ?? '۰۴:۵۲', Icons.wb_twilight_rounded, false),
                        _buildPrayerRow('طلوع آفتاب', data['sunrise'] ?? '۰۶:۱۸', Icons.wb_sunny_rounded, false),
                        _buildPrayerRow('اذان ظهر', data['dhuhr'] ?? '۱۲:۰۴', Icons.light_mode_rounded, false),
                        _buildPrayerRow('اذان عصر', data['asr'] ?? '۱۵:۲۵', Icons.wb_sunny_outlined, false),
                        _buildPrayerRow('غروب آفتاب', data['sunset'] ?? '۱۷:۴۹', Icons.bedtime_outlined, false),
                        _buildPrayerRow('اذان مغرب', data['maghrib'] ?? '۱۸:۰۸', Icons.nights_stay_rounded, true),
                        _buildPrayerRow('نیمه‌شب شرعی', data['midnight'] ?? '۲۳:۲۴', Icons.bedtime_rounded, false),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildPrayerRow(String title, String time, IconData icon, bool highlight) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: highlight ? EttehadColors.primary.withValues(alpha: 0.1) : EttehadColors.surfaceLow,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: highlight ? EttehadColors.primary : EttehadColors.border),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: highlight ? EttehadColors.primary : Colors.black54),
          const SizedBox(width: 10),
          Text(title, style: TextStyle(fontWeight: highlight ? FontWeight.w900 : FontWeight.bold, fontSize: 13, color: highlight ? EttehadColors.primary : Colors.black87)),
          const Spacer(),
          Text(time, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: highlight ? EttehadColors.primary : Colors.black87)),
        ],
      ),
    );
  }

  // 3. Dhikr Counter Modal
  void _openDhikrDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) {
          final dhikrList = widget.repo.dhikrs.isNotEmpty
              ? widget.repo.dhikrs
              : [
                  {'title': 'صلوات بر محمد و آل محمد', 'arabic_text': 'اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَآلِ مُحَمَّدٍ', 'target_count': 100},
                  {'title': 'تسبیحات حضرت زهرا (س)', 'arabic_text': 'الله اکبر (۳۴) • الحمدلله (۳۳) • سبحان الله (۳۳)', 'target_count': 100},
                  {'title': 'استغفار', 'arabic_text': 'اَسْتَغْفِرُ اللهَ رَبّی وَ اَتُوبُ اِلَیْهِ', 'target_count': 70},
                  {'title': 'ذکر لا اله الا الله', 'arabic_text': 'لا اِلهَ اِلَّا اللهُ الْمَلِکُ الْحَقُّ الْمُبین', 'target_count': 100},
                ];
          final current = dhikrList[_selectedDhikrIdx % dhikrList.length];
          final target = (current['target_count'] as num?)?.toInt() ?? 100;

          return Directionality(
            textDirection: TextDirection.rtl,
            child: Container(
              height: MediaQuery.of(context).size.height * 0.85,
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              child: Column(
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 10, bottom: 6),
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.amber.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.touch_app_rounded, color: EttehadColors.amberDark, size: 24),
                        ),
                        const SizedBox(width: 10),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('صلوات‌شمار و تسبیحات هوشمند', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                              Text('شمارنده تمام‌صفحه با ویبره لمسی و ثبت اذکار روزانه', style: TextStyle(fontSize: 11, color: Colors.black54)),
                            ],
                          ),
                        ),
                        IconButton(onPressed: () => Navigator.pop(ctx), icon: const Icon(Icons.close)),
                      ],
                    ),
                  ),
                  const Divider(height: 1),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        children: [
                          // Dhikr Selector Chips
                          SizedBox(
                            height: 38,
                            child: ListView.separated(
                              scrollDirection: Axis.horizontal,
                              itemCount: dhikrList.length,
                              separatorBuilder: (_, _) => const SizedBox(width: 8),
                              itemBuilder: (c, i) {
                                final isSel = _selectedDhikrIdx == i;
                                return ChoiceChip(
                                  label: Text(dhikrList[i]['title'].toString()),
                                  selected: isSel,
                                  onSelected: (v) {
                                    if (v) {
                                      setSheetState(() {
                                        _selectedDhikrIdx = i;
                                        _dhikrCount = 0;
                                      });
                                      setState(() {});
                                    }
                                  },
                                  selectedColor: EttehadColors.amberDark,
                                  labelStyle: TextStyle(
                                    color: isSel ? Colors.white : Colors.black87,
                                    fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
                                    fontSize: 11,
                                  ),
                                );
                              },
                            ),
                          ),
                          const SizedBox(height: 14),

                          // Dhikr text
                          Text(
                            current['arabic_text'].toString(),
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontFamily: 'QuranFont',
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: EttehadColors.navy,
                              height: 1.6,
                            ),
                          ),
                          const Spacer(),

                          // Giant Counter Button
                          GestureDetector(
                            onTap: () {
                              HapticFeedback.lightImpact();
                              setSheetState(() {
                                _dhikrCount++;
                              });
                              setState(() {});
                            },
                            child: Container(
                              width: 180,
                              height: 180,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFEF3C7), Color(0xFFFDE68A), Color(0xFFF59E0B)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.amber.withValues(alpha: 0.35),
                                    blurRadius: 20,
                                    spreadRadius: 4,
                                    offset: const Offset(0, 8),
                                  ),
                                ],
                                border: Border.all(color: Colors.white, width: 4),
                              ),
                              child: Center(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      toPersianDigits(_dhikrCount),
                                      style: const TextStyle(
                                        fontSize: 44,
                                        fontWeight: FontWeight.w900,
                                        color: EttehadColors.navy,
                                      ),
                                    ),
                                    Text(
                                      'هدف: ${toPersianDigits(target)}',
                                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.amberDark),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          const Spacer(),

                          // Controls: Reset & Save
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              OutlinedButton.icon(
                                onPressed: () {
                                  setSheetState(() => _dhikrCount = 0);
                                  setState(() {});
                                },
                                icon: const Icon(Icons.refresh_rounded, size: 16),
                                label: const Text('صفر کردن شمارنده', style: TextStyle(fontSize: 12)),
                              ),
                              const SizedBox(width: 14),
                              ElevatedButton.icon(
                                onPressed: () {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('شمارش ذکر در دفتر اعمال شما ذخیره شد.'), backgroundColor: EttehadColors.emerald),
                                  );
                                },
                                icon: const Icon(Icons.save_rounded, size: 16),
                                label: const Text('ثبت در سوابق', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: EttehadColors.amberDark,
                                  foregroundColor: Colors.white,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // 4. Quran Istikhara Modal
  void _openIstikharaDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) {
          return Directionality(
            textDirection: TextDirection.rtl,
            child: Container(
              height: MediaQuery.of(context).size.height * 0.85,
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              child: Column(
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 10, bottom: 6),
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.purple.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.auto_stories_rounded, color: Colors.purple, size: 24),
                        ),
                        const SizedBox(width: 10),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('استخاره با قرآن مجید', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                              Text('آداب شرعی نیت، تفأل به کلام‌الله و استخراج فرجام کار', style: TextStyle(fontSize: 11, color: Colors.black54)),
                            ],
                          ),
                        ),
                        IconButton(onPressed: () => Navigator.pop(ctx), icon: const Icon(Icons.close)),
                      ],
                    ),
                  ),
                  const Divider(height: 1),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Etiquette card
                          Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF3E8FF),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFD8B4FE)),
                            ),
                            child: const Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('آداب و شرایط استخاره:', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: Color(0xFF581C87))),
                                SizedBox(height: 6),
                                Text(
                                  '۱. با طهارت و وضو باشید.\n۲. سه مرتبه صلوات و سوره اخلاص (توحید) را قرائت فرمایید.\n۳. نیت قلبی خود را در پیشگاه خداوند متعال متمرکز سازید.',
                                  style: TextStyle(fontSize: 11, height: 1.6, color: Color(0xFF3B0764)),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 16),

                          if (_istikharaResult == null) ...[
                            SizedBox(
                              width: double.infinity,
                              height: 48,
                              child: ElevatedButton.icon(
                                onPressed: _isIstikharaLoading
                                    ? null
                                    : () {
                                        setSheetState(() => _isIstikharaLoading = true);
                                        Future.delayed(const Duration(milliseconds: 700), () {
                                          _performIstikhara();
                                          setSheetState(() => _isIstikharaLoading = false);
                                          setState(() {});
                                        });
                                      },
                                icon: _isIstikharaLoading
                                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                    : const Icon(Icons.touch_app_rounded),
                                label: Text(
                                  _isIstikharaLoading ? 'در حال گشودن مصحف شریف...' : 'انجام استخاره با قرآن مجید',
                                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13),
                                ),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF7E22CE),
                                  foregroundColor: Colors.white,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                ),
                              ),
                            ),
                          ] else ...[
                            // Result presentation
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(18),
                                border: Border.all(color: _istikharaResult!['verdictColor'] as Color, width: 2),
                                boxShadow: const [BoxShadow(color: Color(0x0F000000), blurRadius: 12)],
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: (_istikharaResult!['verdictColor'] as Color).withValues(alpha: 0.15),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Text(
                                          _istikharaResult!['verdictTitle'].toString(),
                                          style: TextStyle(
                                            color: _istikharaResult!['verdictColor'] as Color,
                                            fontWeight: FontWeight.w900,
                                            fontSize: 13,
                                          ),
                                        ),
                                      ),
                                      Text(
                                        'سوره ${_istikharaResult!['surahName']} • آیه ${_istikharaResult!['ayahNumber']}',
                                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.navy),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  Text(
                                    _istikharaResult!['arabic'].toString(),
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(fontFamily: 'QuranFont', fontSize: 16, height: 1.8, color: EttehadColors.navy),
                                  ),
                                  const SizedBox(height: 10),
                                  Text(
                                    _istikharaResult!['persian'].toString(),
                                    style: const TextStyle(fontSize: 11.5, height: 1.6, color: Colors.black87),
                                  ),
                                  const Divider(height: 20),
                                  Text(
                                    'تحلیل و فرجام کار:\n${_istikharaResult!['verdictDesc']}',
                                    style: const TextStyle(fontSize: 11, height: 1.5, color: Colors.black54),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 14),
                            SizedBox(
                              width: double.infinity,
                              child: OutlinedButton.icon(
                                onPressed: () {
                                  setSheetState(() => _istikharaResult = null);
                                  setState(() => _istikharaResult = null);
                                },
                                icon: const Icon(Icons.refresh_rounded),
                                label: const Text('انجام استخاره دیگر'),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  void _performIstikhara() {
    if (widget.repo.surahs.isEmpty) return;
    final rnd = Random();
    final surah = widget.repo.surahs[rnd.nextInt(widget.repo.surahs.length)];
    final ayahs = List<Map<String, dynamic>>.from(surah['ayahs'] ?? []);
    if (ayahs.isEmpty) return;
    final ayah = ayahs[rnd.nextInt(ayahs.length)];
    final verdicts = [
      {'title': 'بسیار نیک و مبارک (خوب)', 'desc': 'با توکل بر خداوند متعال اقدام فرمایید؛ عاقبت این کار خیر و برکت است.', 'color': Colors.green.shade700},
      {'title': 'میانه (مشورت و احتیاط)', 'desc': 'پس از مشورت با اهل فن و رعایت جوانب احتیاط اقدام نمایید.', 'color': EttehadColors.amberDark},
      {'title': 'ترک آن اولی است', 'desc': 'صلاح در صبر، تأمل بیشتر و پرهیز از شتاب‌زدگی در این امر است.', 'color': Colors.red.shade700},
    ];
    final v = verdicts[rnd.nextInt(verdicts.length)];
    _istikharaResult = {
      'surahName': surah['nameArabic'] ?? surah['name'] ?? '',
      'ayahNumber': ayah['number'] ?? ayah['ayahNumber'] ?? 1,
      'arabic': ayah['text'] ?? ayah['textArabic'] ?? '',
      'persian': ayah['translation'] ?? ayah['textPersian'] ?? '',
      'verdictTitle': v['title'],
      'verdictDesc': v['desc'],
      'verdictColor': v['color'],
    };
  }

  // 5. Calendar & Duas Modal
  void _openCalendarDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: Container(
          height: MediaQuery.of(context).size.height * 0.85,
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              Container(
                margin: const EdgeInsets.only(top: 10, bottom: 6),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.cyan.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.calendar_month_rounded, color: Colors.cyan, size: 24),
                    ),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('تقویم، مناسبت‌ها و اذکار ایام هفته', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                          Text('تقویم تطبیقی شمسی، قمری و میلادی به همراه ادعیه روزانه', style: TextStyle(fontSize: 11, color: Colors.black54)),
                        ],
                      ),
                    ),
                    IconButton(onPressed: () => Navigator.pop(ctx), icon: const Icon(Icons.close)),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    // Date card
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF0A2E6E), Color(0xFF0B72E7)],
                        ),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        children: [
                          const Text('امروز در یک نگاه', style: TextStyle(color: Colors.white70, fontSize: 11)),
                          const SizedBox(height: 4),
                          Text(_currentPersianDateString, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
                          const SizedBox(height: 2),
                          Text('تقویم بین‌المللی: $_currentGregorianDateString', style: const TextStyle(color: Colors.amberAccent, fontSize: 11)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),

                    const Text('اذکار اختصاصی روزهای هفته (۱۰۰ مرتبه):', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.primary)),
                    const SizedBox(height: 10),

                    ..._effectiveWeekDhikrs.map((item) {
                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: EttehadColors.surfaceLow,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: EttehadColors.border),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: EttehadColors.primary.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(item['day'].toString(), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: EttehadColors.primary)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(item['dhikr'].toString(), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: EttehadColors.navy)),
                                  Text(item['virtue'].toString(), style: const TextStyle(fontSize: 10, color: Colors.black54)),
                                ],
                              ),
                            ),
                            Text('۱۰۰×', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: Colors.grey.shade600)),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final currentCityData = _getCurrentCityData();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 100),
      children: [
        // 1. Header Bar
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [EttehadColors.primary, Color(0xFF06B6D4)],
                    ),
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [
                      BoxShadow(
                        color: EttehadColors.primary.withValues(alpha: 0.25),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      )
                    ],
                  ),
                  child: const Icon(Icons.explore_rounded, color: Colors.white, size: 24),
                ),
                const SizedBox(width: 10),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'ابزار کده',
                          style: TextStyle(
                            fontWeight: FontWeight.w900,
                            fontSize: 17,
                            color: EttehadColors.primary,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: EttehadColors.amberDark.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: EttehadColors.amberDark.withValues(alpha: 0.3)),
                          ),
                          child: const Text(
                            'ابزارهای مذهبی',
                            style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: EttehadColors.amberDark),
                          ),
                        ),
                      ],
                    ),
                    const Text(
                      'خدمات کاربردی، فرایض و ادعیه روزمره مسلمانان',
                      style: TextStyle(fontSize: 10, color: EttehadColors.inkLight),
                    ),
                  ],
                ),
              ],
            ),
            InkWell(
              onTap: () => showEttehadUserProfile(context, widget.repo),
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: EttehadColors.border),
                  boxShadow: [
                    BoxShadow(
                      color: EttehadColors.navy.withValues(alpha: 0.05),
                      blurRadius: 6,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    Icon(
                      widget.repo.isLoggedIn ? Icons.manage_accounts_rounded : Icons.account_circle_outlined,
                      size: 18,
                      color: EttehadColors.primary,
                    ),
                    const SizedBox(width: 5),
                    const Text(
                      'پروفایل',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.navy),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),

        // 2. Daily Status & Prayer Overview Banner
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0A2E6E), Color(0xFF0B72E7), Color(0xFF1499DE)],
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
            ),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0B72E7).withValues(alpha: 0.25),
                blurRadius: 16,
                offset: const Offset(0, 4),
              )
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.calendar_today_rounded, color: Colors.amberAccent, size: 16),
                      SizedBox(width: 6),
                      Text(
                        'پنج‌شنبه، ۱ آبان ۱۴۰۵ • ۲۳ ربیع‌الثانی',
                        style: TextStyle(color: Color(0xFFCFFAFE), fontSize: 11, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text(
                      '۱۲:۳۰',
                      style: TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold, fontSize: 11),
                    ),
                  ),
                ],
              ),
              const Divider(color: Colors.white24, height: 18),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('فریضه بعدی:', style: TextStyle(color: Color(0xFF99F6E4), fontSize: 11)),
                      const SizedBox(height: 2),
                      Text(
                        'اذان ظهر (${currentCityData['dhuhr'] ?? '۱۲:۰۴'})',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14),
                      ),
                      const SizedBox(height: 2),
                      const Text(
                        'ذکر امروز: لا اِلهَ اِلَّا اللهُ الْمَلِکُ الْحَقُّ الْمُبین',
                        style: TextStyle(color: Color(0xFF5EEAD4), fontSize: 9.5),
                      ),
                    ],
                  ),
                  InkWell(
                    onTap: _openPrayerDialog,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFBBF24),
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
                      ),
                      child: const Row(
                        children: [
                          Text('جدول اوقات', style: TextStyle(color: Color(0xFF0F172A), fontWeight: FontWeight.w900, fontSize: 11.5)),
                          SizedBox(width: 4),
                          Icon(Icons.chevron_left_rounded, size: 16, color: Color(0xFF0F172A)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),

        // 3. Section Title
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Container(width: 4, height: 16, decoration: BoxDecoration(color: EttehadColors.primary, borderRadius: BorderRadius.circular(2))),
                const SizedBox(width: 6),
                const Text(
                  'ابزارهای تخصصی و کاربردی',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Colors.black87),
                ),
              ],
            ),
            const Text('۵ بخش مستقل', style: TextStyle(fontSize: 10.5, color: Colors.black45, fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 12),

        // 4. Five Dedicated Tool Cards
        _buildDedicatedToolCard(
          title: 'قبله‌نمای هوشمند',
          badge: 'سنسور قطب‌نما',
          badgeColor: EttehadColors.emerald,
          subtitle: 'جهت‌یابی زنده کعبه معظمه، چرخش ۳۶۰ درجه و فاصله تا مکه مکرمه',
          icon: Icons.explore_rounded,
          iconColor: EttehadColors.emerald,
          iconBg: const Color(0xFFECFDF5),
          onTap: _openQiblaDialog,
        ),
        const SizedBox(height: 10),

        _buildDedicatedToolCard(
          title: 'اوقات شرعی و اذان',
          badge: 'شمارش معکوس',
          badgeColor: Colors.teal,
          subtitle: 'اوقات دقیق شرعی، تقویم اذان ۱۲ شهر ایران و هشدار وقت فضیلت',
          icon: Icons.schedule_rounded,
          iconColor: Colors.teal,
          iconBg: const Color(0xFFF0FDFA),
          onTap: _openPrayerDialog,
        ),
        const SizedBox(height: 10),

        _buildDedicatedToolCard(
          title: 'صلوات‌شمار و تسبیحات',
          badge: 'ویبره لمسی',
          badgeColor: EttehadColors.amberDark,
          subtitle: 'شمارنده تمام‌صفحه اذکار و حالت اختصاصی تسبیحات حضرت زهرا (س)',
          icon: Icons.touch_app_rounded,
          iconColor: EttehadColors.amberDark,
          iconBg: const Color(0xFFFFFBEB),
          onTap: _openDhikrDialog,
        ),
        const SizedBox(height: 10),

        _buildDedicatedToolCard(
          title: 'استخاره با قرآن مجید',
          badge: 'با تفسیر آیه',
          badgeColor: Colors.purple,
          subtitle: 'آداب نیت، استخراج برخط آیه قرآن و تحلیل فرجام کار (خوب، میانه، بد)',
          icon: Icons.auto_stories_rounded,
          iconColor: Colors.purple,
          iconBg: const Color(0xFFFAF5FF),
          onTap: _openIstikharaDialog,
        ),
        const SizedBox(height: 10),

        _buildDedicatedToolCard(
          title: 'تقویم و ادعیه روز',
          badge: 'اذکار هفته',
          badgeColor: Colors.cyan,
          subtitle: 'تقویم همزمان شمسی، قمری و میلادی به همراه اذکار اختصاصی هر روز هفته',
          icon: Icons.calendar_month_rounded,
          iconColor: Colors.cyan,
          iconBg: const Color(0xFFECFEFF),
          onTap: _openCalendarDialog,
        ),
        const SizedBox(height: 16),

        // 5. Quick Knowledge Tips Card
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                Colors.amber.withValues(alpha: 0.12),
                Colors.orange.withValues(alpha: 0.05),
                Colors.transparent,
              ],
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
          ),
          child: const Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.lightbulb_rounded, color: EttehadColors.amberDark, size: 22),
              SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('نکته فقهی روز:', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5, color: Color(0xFF78350F))),
                    SizedBox(height: 2),
                    Text(
                      'وقت فضیلت نماز ظهر از زوال خورشید تا زمانی است که سایه شاخص به اندازه خودش شود و اقامه نماز اول وقت موجب برکت و گشایش در رزق است.',
                      style: TextStyle(fontSize: 11, height: 1.5, color: Colors.black87),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDedicatedToolCard({
    required String title,
    required String badge,
    required Color badgeColor,
    required String subtitle,
    required IconData icon,
    required Color iconColor,
    required Color iconBg,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFFE5DEC9)),
          boxShadow: const [
            BoxShadow(color: Color(0x080F5257), blurRadius: 8, offset: Offset(0, 2)),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: iconBg,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: iconColor.withValues(alpha: 0.3)),
              ),
              child: Icon(icon, color: iconColor, size: 26),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: Colors.black87)),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                        decoration: BoxDecoration(
                          color: badgeColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          badge,
                          style: TextStyle(color: badgeColor, fontSize: 9.5, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10.5, color: Colors.black54, height: 1.4),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: const Color(0xFFF9FAFB),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.chevron_left_rounded, size: 18, color: Colors.black38),
            ),
          ],
        ),
      ),
    );
  }
}
