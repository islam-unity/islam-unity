import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../data/ettehad_repository.dart';
import '../../core/theme.dart';
import '../profile/profile_sheet.dart';

class QuranScreen extends StatefulWidget {
  final EttehadRepository repo;

  const QuranScreen({super.key, required this.repo});

  @override
  State<QuranScreen> createState() => _QuranScreenState();
}

class _QuranScreenState extends State<QuranScreen> {
  String _activeTab = 'SURAHS'; // 'SURAHS' | 'JUZ'
  String _searchQuery = '';
  String _revelationFilter = 'ALL'; // 'ALL' | 'MAKKI' | 'MADANI'
  int? _selectedJuz; // null = all, 1..30

  List<Map<String, dynamic>> get _filteredSurahs {
    List<Map<String, dynamic>> list = widget.repo.surahs;

    if (_selectedJuz != null) {
      final juzSurahs = widget.repo.getSurahsForJuz(_selectedJuz!);
      final juzSurahIds = juzSurahs.map((s) => s['id']).toSet();
      list = list.where((s) => juzSurahIds.contains(s['id'])).toList();
    }

    return list.where((s) {
      final nameAr = (s['nameArabic'] ?? s['name'] ?? '').toString();
      final nameFa = (s['namePersian'] ?? s['meaning'] ?? '').toString();
      final rev = (s['revelationType'] ?? 'MAKKI').toString().toUpperCase();
      if (_revelationFilter != 'ALL' && rev != _revelationFilter) {
        return false;
      }
      if (_searchQuery.trim().isNotEmpty) {
        final q = _searchQuery.trim();
        if (!nameAr.contains(q) && !nameFa.contains(q) && s['id'].toString() != q) {
          return false;
        }
      }
      return true;
    }).toList();
  }

  List<Map<String, dynamic>> get _filteredJuzList {
    return widget.repo.juzList.where((j) {
      if (_searchQuery.trim().isEmpty) return true;
      final q = _searchQuery.trim();
      final jNum = j['juzNumber'].toString();
      final sName = (j['startSurahName'] ?? '').toString();
      final eName = (j['endSurahName'] ?? '').toString();
      return jNum.contains(q) || sName.contains(q) || eName.contains(q);
    }).toList();
  }

  void _openSurahReader(
    Map<String, dynamic> surah, {
    String initialMode = 'translation',
    int? initialPage,
    int? initialJuz,
  }) {
    final page = initialPage ?? widget.repo.getStartPageForSurah((surah['id'] as num?)?.toInt() ?? 1);
    final juz = initialJuz ?? widget.repo.getJuzForPage(page);
    widget.repo.updateLastReadQuran(
      (surah['id'] as num?)?.toInt() ?? 1,
      (surah['nameArabic'] ?? surah['name'] ?? 'الفاتحة').toString(),
      1,
      page: page,
      juz: juz,
    );
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: NativeQuranReaderScreen(
            surah: surah,
            repo: widget.repo,
            initialMode: initialMode,
            initialPage: page,
            initialJuz: juz,
          ),
        ),
      ),
    );
  }

  void _openJuzReader(Map<String, dynamic> juzItem, {String mode = 'uthman'}) {
    final startSurahId = (juzItem['startSurahId'] as num?)?.toInt() ?? 1;
    final startPage = (juzItem['startPage'] as num?)?.toInt() ?? 1;
    final juzNum = (juzItem['juzNumber'] as num?)?.toInt() ?? 1;

    final targetSurah = widget.repo.surahs.firstWhere(
      (s) => s['id'] == startSurahId,
      orElse: () => widget.repo.surahs.isNotEmpty ? widget.repo.surahs.first : {},
    );

    if (targetSurah.isNotEmpty) {
      _openSurahReader(
        targetSurah,
        initialMode: mode,
        initialPage: startPage,
        initialJuz: juzNum,
      );
    }
  }

  void _showJuzPickerModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: Container(
          height: MediaQuery.of(context).size.height * 0.75,
          padding: const EdgeInsets.all(18),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(10)),
                ),
              ),
              const SizedBox(height: 14),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.filter_list_rounded, color: EttehadColors.primary, size: 22),
                      SizedBox(width: 8),
                      Text(
                        'انتخاب جزء قرآن کریم (۱ تا ۳۰)',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                      ),
                    ],
                  ),
                  if (_selectedJuz != null)
                    TextButton.icon(
                      onPressed: () {
                        setState(() => _selectedJuz = null);
                        Navigator.pop(ctx);
                      },
                      icon: const Icon(Icons.clear_rounded, size: 16),
                      label: const Text('حذف فیلتر', style: TextStyle(fontSize: 12)),
                    ),
                ],
              ),
              const SizedBox(height: 6),
              const Text(
                'با انتخاب هر جزء، سوره‌های آن فیلتر شده یا مستقیماً وارد مصحف عثمان‌طه می‌شوید:',
                style: TextStyle(fontSize: 11.5, color: Colors.black54),
              ),
              const Divider(height: 18),
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                    childAspectRatio: 2.0,
                    crossAxisSpacing: 8,
                    mainAxisSpacing: 8,
                  ),
                  itemCount: 30,
                  itemBuilder: (ctx, idx) {
                    final jNum = idx + 1;
                    final isSelected = _selectedJuz == jNum;
                    final startPage = widget.repo.getStartPageForJuz(jNum);

                    return InkWell(
                      onTap: () {
                        setState(() {
                          _selectedJuz = jNum;
                        });
                        Navigator.pop(ctx);
                      },
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        decoration: BoxDecoration(
                          color: isSelected ? EttehadColors.primary : const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: isSelected ? EttehadColors.primary : EttehadColors.border,
                            width: isSelected ? 1.8 : 1.0,
                          ),
                        ),
                        alignment: Alignment.center,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'جزء ${toPersianDigits(jNum)}',
                              style: TextStyle(
                                fontWeight: FontWeight.w900,
                                fontSize: 13,
                                color: isSelected ? Colors.white : EttehadColors.navy,
                              ),
                            ),
                            Text(
                              'صفحه ${toPersianDigits(startPage)}',
                              style: TextStyle(
                                fontSize: 9.5,
                                color: isSelected ? Colors.white70 : Colors.black45,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openTajweedAcademyScreen() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: TajweedAcademyScreen(
            repo: widget.repo,
            onOpenSurah: (surah) => _openSurahReader(surah, initialMode: 'tajweed'),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final surahs = _filteredSurahs;
    final juzList = _filteredJuzList;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
      children: [
        // Top Header
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: EttehadColors.border),
                      boxShadow: [
                        BoxShadow(
                          color: EttehadColors.primary.withValues(alpha: 0.1),
                          blurRadius: 10,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: const Icon(Icons.menu_book_rounded, color: EttehadColors.primary, size: 24),
                  ),
                  const SizedBox(width: 10),
                  const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'قرآن کریم و مصحف شریف',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                      ),
                      Text(
                        'مصحف عثمان‌طه (ورق‌زدنی)، ترجمه و ۳۰ جزء',
                        style: TextStyle(fontSize: 10.5, color: Colors.black54),
                      ),
                    ],
                  ),
                ],
              ),
              Row(
                children: [
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: EttehadColors.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: _openTajweedAcademyScreen,
                    icon: const Icon(Icons.school_rounded, size: 16),
                    label: const Text('آکادمی تجوید', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(width: 6),
                  InkWell(
                    onTap: () => showEttehadUserProfile(context, widget.repo),
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: EttehadColors.border),
                      ),
                      child: const Icon(Icons.person_rounded, size: 18, color: EttehadColors.primary),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        // 2-View Segmented Switcher (سوره‌ها vs ۳۰ جزء)
        Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: EttehadColors.border),
          ),
          child: Row(
            children: [
              _tabSwitchBtn('SURAHS', 'فهرست سوره‌ها (۱۱۴)', Icons.format_list_bulleted_rounded),
              _tabSwitchBtn('JUZ', '۳۰ جزء قرآن مجید', Icons.auto_stories_rounded),
            ],
          ),
        ),

        // Search Bar
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: EttehadColors.border),
          ),
          child: TextField(
            onChanged: (v) => setState(() => _searchQuery = v),
            decoration: InputDecoration(
              hintText: _activeTab == 'SURAHS'
                  ? 'جستجوی سوره، شماره سوره یا نام فارسی...'
                  : 'جستجوی جزء، نام سوره شروع یا پایان...',
              hintStyle: const TextStyle(fontSize: 12.5, color: Colors.black45),
              prefixIcon: const Icon(Icons.search_rounded, color: EttehadColors.primary),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            ),
          ),
        ),
        const SizedBox(height: 10),

        // Filter Chips Row
        if (_activeTab == 'SURAHS')
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _filterChip('ALL', 'همه سوره‌ها (۱۱۴)', Icons.all_inclusive_rounded),
                const SizedBox(width: 8),
                _filterChip('MAKKI', 'مکی (۸۶)', Icons.location_on_rounded),
                const SizedBox(width: 8),
                _filterChip('MADANI', 'مدنی (۲۸)', Icons.mosque_rounded),
                const SizedBox(width: 8),
                _juzFilterChip(),
              ],
            ),
          ),

        if (_selectedJuz != null && _activeTab == 'SURAHS') ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFFFEF3C7),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.amber.shade600),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.filter_alt_rounded, color: Color(0xFF92400E), size: 18),
                    const SizedBox(width: 6),
                    Text(
                      'فیلتر جزء ${toPersianDigits(_selectedJuz!)} (صفحه ${toPersianDigits(widget.repo.getStartPageForJuz(_selectedJuz!))})',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF92400E)),
                    ),
                  ],
                ),
                Row(
                  children: [
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF92400E),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: () {
                        final juzData = widget.repo.juzList.firstWhere(
                          (j) => j['juzNumber'] == _selectedJuz,
                          orElse: () => {},
                        );
                        if (juzData.isNotEmpty) {
                          _openJuzReader(juzData, mode: 'uthman');
                        }
                      },
                      child: const Text('مصحف عثمان‌طه', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(width: 6),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 18, color: Color(0xFF92400E)),
                      onPressed: () => setState(() => _selectedJuz = null),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],

        const SizedBox(height: 14),

        // Interactive Tajweed Academy Banner
        GestureDetector(
          onTap: _openTajweedAcademyScreen,
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [EttehadColors.navy, EttehadColors.primary, EttehadColors.ocean],
              ),
              borderRadius: BorderRadius.circular(18),
              boxShadow: [
                BoxShadow(
                  color: EttehadColors.primary.withValues(alpha: 0.2),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.graphic_eq_rounded, color: Colors.amberAccent, size: 26),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            'آکادمی جامع آموزش تجوید قرآن',
                            style: TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w900),
                          ),
                          SizedBox(width: 6),
                          Icon(Icons.verified_rounded, color: Colors.amberAccent, size: 14),
                        ],
                      ),
                      SizedBox(height: 3),
                      Text(
                        'مخارج ۱۷گانه حروف، احکام نون و میم ساکن، مدها و قلقله با تفکیک رنگی کلمات',
                        style: TextStyle(color: Colors.white70, fontSize: 10.5),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.arrow_forward_ios_rounded, color: Colors.amberAccent, size: 16),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),

        // Last Read Resume Card
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF0F5257), Color(0xFF003A3E)],
            ),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0F5257).withValues(alpha: 0.25),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.bookmark_added_rounded, color: Colors.amberAccent, size: 28),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'آخرین قرائت ذخیره‌شده',
                        style: TextStyle(color: Colors.white70, fontSize: 11),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'سوره ${widget.repo.lastReadSurahName} (صفحه ${toPersianDigits(widget.repo.lastReadPage)} • جزء ${toPersianDigits(widget.repo.lastReadJuz)})',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5),
                      ),
                    ],
                  ),
                ],
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.amberAccent,
                  foregroundColor: const Color(0xFF082628),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () {
                  final target = widget.repo.surahs.firstWhere(
                    (s) => s['id'] == widget.repo.lastReadSurahId,
                    orElse: () => widget.repo.surahs.isNotEmpty ? widget.repo.surahs.first : {},
                  );
                  if (target.isNotEmpty) {
                    _openSurahReader(
                      target,
                      initialMode: 'uthman',
                      initialPage: widget.repo.lastReadPage,
                      initialJuz: widget.repo.lastReadJuz,
                    );
                  }
                },
                child: const Text('ادامه قرائت', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        if (_activeTab == 'SURAHS') ...[
          // Surah List Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _selectedJuz != null
                    ? 'سوره‌های جزء ${toPersianDigits(_selectedJuz!)}'
                    : 'فهرست سوره‌های قرآن مجید',
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: EttehadColors.navy),
              ),
              Text(
                '${toPersianDigits(surahs.length)} سوره',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.primary),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Surahs List
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: surahs.length,
            separatorBuilder: (_, _) => const SizedBox(height: 6),
            itemBuilder: (ctx, idx) {
              final s = surahs[idx];
              final id = (s['id'] as num?)?.toInt() ?? (idx + 1);
              final nameAr = (s['nameArabic'] ?? s['name'] ?? '').toString();
              final nameFa = (s['namePersian'] ?? s['meaning'] ?? '').toString();
              final rev = (s['revelationType'] ?? 'MAKKI').toString().toUpperCase() == 'MAKKI' ? 'مکی' : 'مدنی';
              final ayahCount = (s['ayahsCount'] ?? s['ayahCount'] ?? (s['ayahs'] as List?)?.length ?? 7);
              final startPage = (s['startPage'] as num?)?.toInt() ?? 1;

              return Material(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: EttehadColors.border),
                  ),
                  child: ListTile(
                  onTap: () => _openSurahReader(s, initialMode: 'translation'),
                  leading: Container(
                    width: 40,
                    height: 40,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [EttehadColors.skyCardStart, EttehadColors.skyCardEnd],
                      ),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFF7DD3FC)),
                    ),
                    child: Text(
                      toPersianDigits(id),
                      style: const TextStyle(fontWeight: FontWeight.w900, color: EttehadColors.navy),
                    ),
                  ),
                  title: Row(
                    children: [
                      Text(
                        'سوره $nameAr',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: EttehadColors.navy),
                      ),
                      if (nameFa.isNotEmpty) ...[
                        const SizedBox(width: 6),
                        Text('($nameFa)', style: const TextStyle(fontSize: 11, color: Colors.black45)),
                      ],
                    ],
                  ),
                  subtitle: Text(
                    '$rev • ${toPersianDigits(ayahCount)} آیه • ص ${toPersianDigits(startPage)} • جزء ${toPersianDigits(s['juzNumber'] ?? 1)}',
                    style: const TextStyle(fontSize: 11.5, color: Colors.black54),
                  ),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFFFFFBEB),
                          foregroundColor: const Color(0xFFB45309),
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          side: const BorderSide(color: Color(0xFFFDE68A)),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        onPressed: () => _openSurahReader(s, initialMode: 'uthman', initialPage: startPage),
                        child: const Text('عثمان‌طه', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold)),
                      ),
                      const SizedBox(width: 4),
                      const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: EttehadColors.primary),
                    ],
                  ),
                ),
              ),);
            },
          ),
        ] else ...[
          // 30 Juz List Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'فهرست ۳۰ جزء قرآن کریم (مصحف شریف)',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: EttehadColors.navy),
              ),
              Text(
                '${toPersianDigits(juzList.length)} جزء',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.primary),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // 30 Juz List
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: juzList.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (ctx, idx) {
              final j = juzList[idx];
              final jNum = j['juzNumber'] as int;
              final startP = j['startPage'] as int;
              final endP = j['endPage'] as int;
              final startS = j['startSurahName'] as String;
              final startA = j['startAyah'] as int;
              final endS = j['endSurahName'] as String;
              final endA = j['endAyah'] as int;
              final ayahCnt = j['ayahCount'] as int;

              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: EttehadColors.border),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.03),
                      blurRadius: 6,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 38,
                              height: 38,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFEF3C7), Color(0xFFFDE68A)],
                                ),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFFD97706)),
                              ),
                              child: Text(
                                toPersianDigits(jNum),
                                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Color(0xFF92400E)),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'جزء ${toPersianDigits(jNum)} قرآن کریم',
                                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: EttehadColors.navy),
                                ),
                                Text(
                                  'از ص ${toPersianDigits(startP)} تا ${toPersianDigits(endP)} • ${toPersianDigits(ayahCnt)} آیه',
                                  style: const TextStyle(fontSize: 11, color: Colors.black54),
                                ),
                              ],
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: EttehadColors.primary.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            'صفحه ${toPersianDigits(startP)}',
                            style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF8FAFC),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.arrow_right_alt_rounded, size: 16, color: EttehadColors.navy),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              'آغاز: سوره $startS (آیه ${toPersianDigits(startA)}) • پایان: سوره $endS (آیه ${toPersianDigits(endA)})',
                              style: const TextStyle(fontSize: 11, color: Colors.black87),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFFB45309),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            onPressed: () => _openJuzReader(j, mode: 'uthman'),
                            icon: const Icon(Icons.menu_book_rounded, size: 16),
                            label: const Text(
                              'مصحف عثمان‌طه (ورق‌زدنی)',
                              style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                            foregroundColor: EttehadColors.navy,
                            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 10),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            side: const BorderSide(color: EttehadColors.border),
                          ),
                          onPressed: () => _openJuzReader(j, mode: 'translation'),
                          icon: const Icon(Icons.translate_rounded, size: 16),
                          label: const Text('با ترجمه', style: TextStyle(fontSize: 11.5)),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ],
    );
  }

  Widget _tabSwitchBtn(String tab, String title, IconData icon) {
    final active = _activeTab == tab;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _activeTab = tab),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: active ? EttehadColors.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
          ),
          alignment: Alignment.center,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 16, color: active ? Colors.white : EttehadColors.navy),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: active ? FontWeight.w900 : FontWeight.w600,
                  color: active ? Colors.white : EttehadColors.navy,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _filterChip(String id, String label, IconData icon) {
    final selected = _revelationFilter == id;
    return ChoiceChip(
      selected: selected,
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: selected ? Colors.white : EttehadColors.navy),
          const SizedBox(width: 5),
          Text(label, style: TextStyle(color: selected ? Colors.white : EttehadColors.navy, fontSize: 11.5)),
        ],
      ),
      selectedColor: EttehadColors.primary,
      backgroundColor: Colors.white,
      onSelected: (_) => setState(() => _revelationFilter = id),
    );
  }

  Widget _juzFilterChip() {
    final hasJuz = _selectedJuz != null;
    return ActionChip(
      avatar: Icon(
        hasJuz ? Icons.check_circle_rounded : Icons.filter_list_rounded,
        size: 15,
        color: hasJuz ? Colors.white : EttehadColors.navy,
      ),
      label: Text(
        hasJuz ? 'جزء ${toPersianDigits(_selectedJuz!)} (تغییر)' : 'فیلتر جزء (۱ تا ۳۰)',
        style: TextStyle(
          color: hasJuz ? Colors.white : EttehadColors.navy,
          fontSize: 11.5,
          fontWeight: hasJuz ? FontWeight.bold : FontWeight.normal,
        ),
      ),
      backgroundColor: hasJuz ? const Color(0xFFD97706) : Colors.white,
      onPressed: _showJuzPickerModal,
    );
  }
}

// -----------------------------------------------------------------------------
// DEDICATED TAJWEED ACADEMY SCREEN (آموزش تجوید مطابق فایل تستی)
// -----------------------------------------------------------------------------
class TajweedAcademyScreen extends StatefulWidget {
  final EttehadRepository repo;
  final void Function(Map<String, dynamic> surah)? onOpenSurah;

  const TajweedAcademyScreen({
    super.key,
    required this.repo,
    this.onOpenSurah,
  });

  @override
  State<TajweedAcademyScreen> createState() => _TajweedAcademyScreenState();
}

class _TajweedAcademyScreenState extends State<TajweedAcademyScreen> {
  int _activeRuleIndex = 0;

  static const List<Map<String, dynamic>> _tajweedRules = [
    {
      'title': 'احکام مدّ (کشش صوتی)',
      'color': Color(0xFFE11D48),
      'desc': 'کشش حروف مدی (الف، واو، یاء) از ۲ تا ۶ حرکت در موارد مد متصل، منفصل و لازم.',
      'examples': '«جَآءَ» (۴-۵ حرکت)، «الضَّآلِّینَ» (۶ حرکت لازمه)',
    },
    {
      'title': 'احکام اخفاء و غنّه',
      'color': Color(0xFF059669),
      'desc': 'تلفظ حرف از خیشوم (بینی) به اندازه ۲ حرکت در ۱۵ حرف اخفاء یا نون و میم مشدد.',
      'examples': '«مِن قَبْلِ»، «إِنَّ»، «عَمَّ»',
    },
    {
      'title': 'احکام قلقله (تکانش حروف)',
      'color': Color(0xFF2563EB),
      'desc': 'ارتعاش و تکانش صدای حروف قطب جد (ق، ط، ب، ج، د) در حالت سکون.',
      'examples': '«قُلْ هُوَ اللَّهُ أَحَدْ»، «الْفَلَقْ»',
    },
    {
      'title': 'احکام ادغام (یرملون)',
      'color': Color(0xFF7C3AED),
      'desc': 'وارد کردن حرف ساکن در حرف بعد با غنه (ی، ن، م، و) یا بدون غنه (ل، ر).',
      'examples': '«مَن یَقُولُ» (ادغام با غنه)، «مِن رَّبِّهِمْ» (بدون غنه)',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFBF9F4),
      appBar: AppBar(
        backgroundColor: EttehadColors.navy,
        foregroundColor: Colors.white,
        title: const Text('آکادمی آموزش تجوید قرآن کریم', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Hero Banner
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF0F5257), Color(0xFF0A3B3E), Color(0xFF042426)],
              ),
              borderRadius: BorderRadius.circular(22),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF0F5257).withValues(alpha: 0.3),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.white12,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.school_rounded, color: Colors.amberAccent, size: 14),
                          SizedBox(width: 4),
                          Text('تمرین تعاملی تجوید', style: TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                    const Text('سطح: جامع (مبتدی تا پیشرفته)', style: TextStyle(color: Colors.amberAccent, fontSize: 10)),
                  ],
                ),
                const SizedBox(height: 10),
                const Text(
                  'تجوید را با گوش دادن، رنگ‌ها و تکرار صوتی بیاموزید',
                  style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 6),
                const Text(
                  '«وَرَتِّلِ الْقُرْآنَ تَرْتِيلًا» — زیبایی قرآن در ادای صحیح مخارج حروف، رعایت مدها و غنه‌های گوش‌نواز است.',
                  style: TextStyle(color: Colors.white70, fontSize: 11, height: 1.6),
                ),
                const SizedBox(height: 14),
                // Color Codes Strip
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _TajweedLegend(color: Color(0xFFE11D48), label: 'مدّ'),
                      _TajweedLegend(color: Color(0xFF059669), label: 'اخفاء و غنّه'),
                      _TajweedLegend(color: Color(0xFF2563EB), label: 'قلقله'),
                      _TajweedLegend(color: Color(0xFF7C3AED), label: 'ادغام'),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),

          // 3-Step Simple Learning Journey
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: EttehadColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.lightbulb_rounded, color: Colors.amber, size: 18),
                    SizedBox(width: 6),
                    Text('راهنمای ۳ گام یادگیری آسان تجوید', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: EttehadColors.navy)),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    _stepCard('۱. گوش دادن', 'صوت استاد منشاوی و حصری', '۱', EttehadColors.primary),
                    const SizedBox(width: 8),
                    _stepCard('۲. لمس کلمات', 'رنگ کلمه = قاعده تجویدی', '۲', Colors.amber.shade700),
                    const SizedBox(width: 8),
                    _stepCard('۳. تمرین هوشمند', 'تکرار و ارزیابی صوت', '۳', Colors.teal),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),

          // Core Tajweed Rules List
          const Text('۴ قاعده بنیادین تجویدی', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: EttehadColors.navy)),
          const SizedBox(height: 10),
          ..._tajweedRules.asMap().entries.map((entry) {
            final idx = entry.key;
            final r = entry.value;
            final isSelected = _activeRuleIndex == idx;

            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: isSelected ? (r['color'] as Color) : EttehadColors.border, width: isSelected ? 1.8 : 1.0),
              ),
              child: ExpansionTile(
                initiallyExpanded: idx == 0,
                onExpansionChanged: (exp) {
                  if (exp) setState(() => _activeRuleIndex = idx);
                },
                leading: CircleAvatar(
                  backgroundColor: (r['color'] as Color).withValues(alpha: 0.15),
                  child: Icon(Icons.circle, color: r['color'] as Color, size: 14),
                ),
                title: Text(r['title'] as String, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.navy)),
                childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
                children: [
                  Text(r['desc'] as String, style: const TextStyle(fontSize: 11.5, height: 1.6, color: Colors.black87)),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFBF9F4),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: EttehadColors.border),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.auto_awesome, size: 14, color: EttehadColors.primary),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'نمونه قرآنی: ${r['examples']}',
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }),
          const SizedBox(height: 16),

          // Practice with Surah Al-Fatiha
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: EttehadColors.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 13),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            onPressed: () {
              if (widget.repo.surahs.isNotEmpty) {
                Navigator.pop(context);
                widget.onOpenSurah?.call(widget.repo.surahs.first);
              }
            },
            icon: const Icon(Icons.play_circle_fill_rounded, size: 20),
            label: const Text('آغاز تمرین تجویدی روی سوره حمد', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _stepCard(String title, String desc, String num, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFFFBF9F4),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: EttehadColors.border),
        ),
        child: Column(
          children: [
            CircleAvatar(
              radius: 13,
              backgroundColor: color.withValues(alpha: 0.15),
              child: Text(toPersianDigits(num), style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 11)),
            ),
            const SizedBox(height: 6),
            Text(title, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: EttehadColors.navy), textAlign: TextAlign.center),
            const SizedBox(height: 2),
            Text(desc, style: const TextStyle(fontSize: 8.5, color: Colors.black54), textAlign: TextAlign.center, maxLines: 2),
          ],
        ),
      ),
    );
  }
}

// -----------------------------------------------------------------------------
// NATIVE QURAN READER SCREEN (WITH AUTHENTIC OSMAN TAHA HORIZONTAL BOOK VIEW)
// -----------------------------------------------------------------------------
class NativeQuranReaderScreen extends StatefulWidget {
  final Map<String, dynamic> surah;
  final EttehadRepository repo;
  final String initialMode;
  final int? initialPage;
  final int? initialJuz;

  const NativeQuranReaderScreen({
    super.key,
    required this.surah,
    required this.repo,
    this.initialMode = 'translation',
    this.initialPage,
    this.initialJuz,
  });

  @override
  State<NativeQuranReaderScreen> createState() => _NativeQuranReaderScreenState();
}

class _NativeQuranReaderScreenState extends State<NativeQuranReaderScreen> {
  late String _mode; // 'translation' | 'uthman' | 'tajweed'
  late int _currentPage;
  late PageController _pageController;
  late Map<String, dynamic> _currentSurah;

  String _selectedReciter = 'شهریار پرهیزگار (ترتیل آموزشی)';
  String _selectedTranslator = 'حسین انصاریان (روان و شیوا)';
  bool _showTranslation = true;
  double _arabicFontSize = 20.0;
  double _translationFontSize = 13.0;
  bool _isPlayingAudio = false;
  int _currentPlayingAyah = 1;
  bool _nightMode = false;
  String? _currentAudioUrl;
  bool _isLoadingAudio = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _currentSurah = widget.surah;
    final sStartPage = widget.repo.getStartPageForSurah((widget.surah['id'] as num?)?.toInt() ?? 1);
    _currentPage = widget.initialPage ?? sStartPage;
    _pageController = PageController(initialPage: (_currentPage - 1).clamp(0, 603));
    widget.repo.fetchReciters().then((_) {
      if (mounted) setState(() {});
    });
  }

  void _toggleAudioPlayback({int? targetAyah}) async {
    final sId = (_currentSurah['id'] as num?)?.toInt() ?? 1;
    if (_isPlayingAudio && targetAyah == null) {
      setState(() => _isPlayingAudio = false);
      return;
    }

    if (targetAyah != null) {
      _currentPlayingAyah = targetAyah;
    }

    setState(() {
      _isLoadingAudio = true;
      _isPlayingAudio = true;
    });

    String rId = 'parhizgar';
    if (_selectedReciter.contains('منشاوی')) {
      rId = 'menshawi';
    } else if (_selectedReciter.contains('عبدالباسط')) {
      rId = 'abdulbasit';
    } else if (_selectedReciter.contains('حصری')) {
      rId = 'hussary';
    }

    final audioData = await widget.repo.fetchSurahAudio(sId, reciterId: rId);
    if (!mounted) return;

    setState(() {
      _isLoadingAudio = false;
      if (audioData != null) {
        _currentAudioUrl = audioData['audioUrl']?.toString();
      }
    });

    if (_currentAudioUrl != null) {
      ScaffoldMessenger.of(context).hideCurrentSnackBar();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('در حال پخش استریم تلاوت سوره ${_currentSurah['nameArabic'] ?? ''} از CDN معارفی'),
          duration: const Duration(seconds: 2),
          backgroundColor: EttehadColors.primary,
        ),
      );
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Color get _readerBgColor {
    return _nightMode ? const Color(0xFF0F172A) : EttehadColors.paper;
  }

  Color get _readerTextColor {
    return _nightMode ? const Color(0xFFF1F5F9) : EttehadColors.ink;
  }

  void _onModeChanged(String newMode) {
    setState(() {
      _mode = newMode;
      if (newMode == 'uthman') {
        final targetPage = widget.repo.getStartPageForSurah((_currentSurah['id'] as num?)?.toInt() ?? 1);
        _currentPage = targetPage;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_pageController.hasClients) {
            _pageController.jumpToPage((_currentPage - 1).clamp(0, 603));
          }
        });
      }
    });
  }

  void _openQuickJumpSheet() {
    int jumpTab = 0; // 0: Juz (1-30), 1: Surah (1-114), 2: Page (1-604)
    String surahSearch = '';
    final pageTextController = TextEditingController(text: _currentPage.toString());

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setJumpState) => Directionality(
          textDirection: TextDirection.rtl,
          child: Container(
            height: MediaQuery.of(context).size.height * 0.82,
            padding: const EdgeInsets.all(18),
            decoration: const BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(10)),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.travel_explore_rounded, color: EttehadColors.primary, size: 22),
                        SizedBox(width: 8),
                        Text(
                          'پرش سریع در مصحف شریف',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 20),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const SizedBox(height: 10),

                // 3-way Jump Tabs
                Container(
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      _jumpSubTab('۳۰ جزء قرآن', 0, jumpTab, () => setJumpState(() => jumpTab = 0)),
                      _jumpSubTab('۱۱۴ سوره', 1, jumpTab, () => setJumpState(() => jumpTab = 1)),
                      _jumpSubTab('شماره صفحه (۱-۶۰۴)', 2, jumpTab, () => setJumpState(() => jumpTab = 2)),
                    ],
                  ),
                ),
                const Divider(height: 18),

                // Tab Content
                Expanded(
                  child: jumpTab == 0
                      ? GridView.builder(
                          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 3,
                            childAspectRatio: 2.1,
                            crossAxisSpacing: 8,
                            mainAxisSpacing: 8,
                          ),
                          itemCount: 30,
                          itemBuilder: (ctx, idx) {
                            final jNum = idx + 1;
                            final startPage = widget.repo.getStartPageForJuz(jNum);
                            final isCur = widget.repo.getJuzForPage(_currentPage) == jNum;

                            return InkWell(
                              onTap: () {
                                Navigator.pop(ctx);
                                _jumpToPage(startPage);
                              },
                              borderRadius: BorderRadius.circular(12),
                              child: Container(
                                decoration: BoxDecoration(
                                  color: isCur ? const Color(0xFFFEF3C7) : const Color(0xFFF8FAFC),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: isCur ? Colors.amber.shade700 : EttehadColors.border,
                                    width: isCur ? 1.8 : 1.0,
                                  ),
                                ),
                                alignment: Alignment.center,
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text(
                                      'جزء ${toPersianDigits(jNum)}',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w900,
                                        fontSize: 13,
                                        color: isCur ? const Color(0xFF92400E) : EttehadColors.navy,
                                      ),
                                    ),
                                    Text(
                                      'صفحه ${toPersianDigits(startPage)}',
                                      style: TextStyle(
                                        fontSize: 9.5,
                                        color: isCur ? const Color(0xFFB45309) : Colors.black45,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        )
                      : jumpTab == 1
                          ? Column(
                              children: [
                                Container(
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFF8FAFC),
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: EttehadColors.border),
                                  ),
                                  child: TextField(
                                    onChanged: (v) => setJumpState(() => surahSearch = v),
                                    decoration: const InputDecoration(
                                      hintText: 'جستجوی سوره یا شماره...',
                                      hintStyle: TextStyle(fontSize: 11.5),
                                      prefixIcon: Icon(Icons.search_rounded, size: 18),
                                      border: InputBorder.none,
                                      contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Expanded(
                                  child: ListView(
                                    children: widget.repo.surahs.where((s) {
                                      if (surahSearch.trim().isEmpty) return true;
                                      final q = surahSearch.trim();
                                      final nameAr = (s['nameArabic'] ?? s['name'] ?? '').toString();
                                      final nameFa = (s['namePersian'] ?? s['meaning'] ?? '').toString();
                                      return nameAr.contains(q) || nameFa.contains(q) || s['id'].toString() == q;
                                    }).map((s) {
                                      final sId = s['id'];
                                      final sPage = (s['startPage'] as num?)?.toInt() ?? 1;
                                      final sName = (s['nameArabic'] ?? s['name'] ?? '').toString();
                                      final isCur = _currentSurah['id'] == sId;

                                      return ListTile(
                                        dense: true,
                                        onTap: () {
                                          Navigator.pop(ctx);
                                          setState(() => _currentSurah = s);
                                          _jumpToPage(sPage);
                                        },
                                        leading: CircleAvatar(
                                          radius: 14,
                                          backgroundColor: isCur ? EttehadColors.primary : const Color(0xFFE2E8F0),
                                          child: Text(
                                            toPersianDigits(sId),
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: FontWeight.bold,
                                              color: isCur ? Colors.white : EttehadColors.navy,
                                            ),
                                          ),
                                        ),
                                        title: Text(
                                          'سوره $sName',
                                          style: TextStyle(
                                            fontWeight: isCur ? FontWeight.w900 : FontWeight.w700,
                                            fontSize: 13,
                                            color: isCur ? EttehadColors.primary : EttehadColors.navy,
                                          ),
                                        ),
                                        subtitle: Text(
                                          'صفحه ${toPersianDigits(sPage)} • جزء ${toPersianDigits(s['juzNumber'] ?? 1)}',
                                          style: const TextStyle(fontSize: 10.5, color: Colors.black54),
                                        ),
                                        trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 12),
                                      );
                                    }).toList(),
                                  ),
                                ),
                              ],
                            )
                          : Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  'صفحه فعلی: ${toPersianDigits(_currentPage)} از ۶۰۴',
                                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                                ),
                                const SizedBox(height: 16),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Text('شماره صفحه:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                                    const SizedBox(width: 10),
                                    SizedBox(
                                      width: 90,
                                      child: TextField(
                                        controller: pageTextController,
                                        keyboardType: TextInputType.number,
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                        decoration: InputDecoration(
                                          contentPadding: const EdgeInsets.symmetric(vertical: 8),
                                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: EttehadColors.primary,
                                        foregroundColor: Colors.white,
                                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                      ),
                                      onPressed: () {
                                        final p = int.tryParse(pageTextController.text);
                                        if (p != null && p >= 1 && p <= 604) {
                                          Navigator.pop(ctx);
                                          _jumpToPage(p);
                                        }
                                      },
                                      child: const Text('برو به صفحه', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 20),
                                Slider(
                                  value: _currentPage.toDouble(),
                                  min: 1.0,
                                  max: 604.0,
                                  activeColor: EttehadColors.primary,
                                  onChanged: (v) {
                                    setJumpState(() {
                                      pageTextController.text = v.toInt().toString();
                                    });
                                  },
                                ),
                              ],
                            ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _jumpSubTab(String title, int idx, int cur, VoidCallback onTap) {
    final active = idx == cur;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 7),
          decoration: BoxDecoration(
            color: active ? Colors.white : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            boxShadow: active ? const [BoxShadow(color: Colors.black12, blurRadius: 4)] : null,
          ),
          alignment: Alignment.center,
          child: Text(
            title,
            style: TextStyle(
              fontSize: 11,
              fontWeight: active ? FontWeight.bold : FontWeight.normal,
              color: active ? EttehadColors.primary : Colors.black87,
            ),
          ),
        ),
      ),
    );
  }

  void _jumpToPage(int pageNum) {
    final safePage = pageNum.clamp(1, 604);
    setState(() {
      _currentPage = safePage;
      final pageAyahs = widget.repo.getAyahsForPage(safePage);
      if (pageAyahs.isNotEmpty) {
        final sId = pageAyahs.first['surahId'];
        final s = widget.repo.surahs.firstWhere((x) => x['id'] == sId, orElse: () => _currentSurah);
        _currentSurah = s;
      }
    });

    widget.repo.updateLastReadQuran(
      _currentSurah['id'] as int,
      (_currentSurah['nameArabic'] ?? _currentSurah['name'] ?? '').toString(),
      1,
      page: safePage,
      juz: widget.repo.getJuzForPage(safePage),
    );

    if (_mode == 'uthman') {
      if (_pageController.hasClients) {
        _pageController.jumpToPage(safePage - 1);
      }
    }
  }

  void _showAyahDetailsModal(Map<String, dynamic> ayah) {
    final surahName = (ayah['surahNameArabic'] ?? _currentSurah['nameArabic'] ?? '').toString();
    final ayahNum = (ayah['ayahNumber'] ?? ayah['number'] ?? 1) as int;
    final arText = (ayah['textArabic'] ?? ayah['text'] ?? '').toString();
    final faText = (ayah['textPersian'] ?? ayah['translation'] ?? '').toString();

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: _nightMode ? const Color(0xFF1E293B) : const Color(0xFFFFFDF7),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            border: Border.all(color: EttehadColors.border),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(10)),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: EttehadColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      'سوره مبارکه $surahName • آیه ${toPersianDigits(ayahNum)}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: EttehadColors.primary),
                    ),
                  ),
                  Row(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.copy_rounded, size: 18),
                        tooltip: 'کپی آیه و ترجمه',
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: '$arText\n\n$faText'));
                          Navigator.pop(ctx);
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('متن آیه و ترجمه در کلیپ‌بورد کپی شد')),
                          );
                        },
                      ),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, size: 20),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                ],
              ),
              const Divider(height: 16),
              // Arabic text in authentic Uthmanic font
              Text(
                arText,
                textAlign: TextAlign.right,
                style: TextStyle(
                  fontFamily: 'UthmanicHafs',
                  fontSize: 21,
                  height: 2.1,
                  fontWeight: FontWeight.w700,
                  color: _readerTextColor,
                ),
              ),
              if (faText.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(
                  faText,
                  textAlign: TextAlign.right,
                  style: TextStyle(
                    fontSize: 13,
                    height: 1.8,
                    color: _nightMode ? Colors.white70 : Colors.black87,
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: EttehadColors.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: () {
                        Navigator.pop(ctx);
                        _toggleAudioPlayback(targetAyah: ayahNum);
                      },
                      icon: const Icon(Icons.play_arrow_rounded, size: 20),
                      label: const Text('پخش تلاوت آیه', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: EttehadColors.amber,
                      side: const BorderSide(color: EttehadColors.amber),
                      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: () {
                      Navigator.pop(ctx);
                      _openTadabburSheet(ayah);
                    },
                    icon: const Icon(Icons.auto_stories_rounded, size: 18),
                    label: const Text('تدبر و تفسیر', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openQuranSettingsSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) => Directionality(
          textDirection: TextDirection.rtl,
          child: Container(
            height: MediaQuery.of(context).size.height * 0.82,
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              color: EttehadColors.paper,
              borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
            ),
            child: ListView(
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(10)),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.tune_rounded, color: EttehadColors.primary, size: 22),
                        SizedBox(width: 8),
                        Text('تنظیمات صوت، قرائت و قلم', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: EttehadColors.navy)),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 20),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const Divider(height: 20),

                // Reciter Selection
                const Text('انتخاب قاری و صوت قرائت:', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: EttehadColors.border),
                  ),
                  child: DropdownButton<String>(
                    isExpanded: true,
                    value: _selectedReciter,
                    underline: const SizedBox.shrink(),
                    items: (widget.repo.reciters.isNotEmpty
                            ? widget.repo.reciters.map((r) => '${r['nameFa'] ?? r['nameAr']} (${r['style'] ?? 'ترتیل'})').toList()
                            : [
                                'شهریار پرهیزگار (ترتیل آموزشی)',
                                'محمدصدیق منشاوی (تحقیق و تجوید)',
                                'عبدالباسط عبدالصمد (تلاوت مجلسی)',
                                'محمود خلیل الحصری (تجوید شمرده)',
                              ])
                        .map((r) => DropdownMenuItem(value: r, child: Text(r, style: const TextStyle(fontSize: 12))))
                        .toList(),
                    onChanged: (v) {
                      if (v != null) {
                        setState(() => _selectedReciter = v);
                        setSheetState(() {});
                      }
                    },
                  ),
                ),
                const SizedBox(height: 16),

                // Translator Selection
                const Text('انتخاب مترجم قرآن:', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: EttehadColors.border),
                  ),
                  child: DropdownButton<String>(
                    isExpanded: true,
                    value: _selectedTranslator,
                    underline: const SizedBox.shrink(),
                    items: [
                      'حسین انصاریان (روان و شیوا)',
                      'ناصر مکارم شیرازی (روان و تفسیری)',
                      'محمد مهدی فولادوند (دقیق و ساختاری)',
                      'مهدی الهی قمشه‌ای (ادبی و منظوم)',
                    ].map((t) => DropdownMenuItem(value: t, child: Text(t, style: const TextStyle(fontSize: 12)))).toList(),
                    onChanged: (v) {
                      if (v != null) {
                        setState(() => _selectedTranslator = v);
                        setSheetState(() {});
                      }
                    },
                  ),
                ),
                const SizedBox(height: 16),

                // Show/Hide Translation Switch
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('نمایش ترجمه فارسی زیر آیات', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                  value: _showTranslation,
                  onChanged: (v) {
                    setState(() => _showTranslation = v);
                    setSheetState(() {});
                  },
                ),
                const Divider(height: 16),

                // Arabic Font Size
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('اندازه قلم متن عربی آیات (عثمان‌طه):', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                    Text('${toPersianDigits(_arabicFontSize.toInt())} پیکسل', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.primary)),
                  ],
                ),
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.remove_circle_outline, size: 20),
                      onPressed: () {
                        setState(() => _arabicFontSize = (_arabicFontSize - 1).clamp(16.0, 36.0));
                        setSheetState(() {});
                      },
                    ),
                    Expanded(
                      child: Slider(
                        value: _arabicFontSize,
                        min: 16.0,
                        max: 36.0,
                        activeColor: EttehadColors.primary,
                        onChanged: (v) {
                          setState(() => _arabicFontSize = v);
                          setSheetState(() {});
                        },
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.add_circle_outline, size: 20),
                      onPressed: () {
                        setState(() => _arabicFontSize = (_arabicFontSize + 1).clamp(16.0, 36.0));
                        setSheetState(() {});
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Translation Font Size
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('اندازه قلم ترجمه فارسی:', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                    Text('${toPersianDigits(_translationFontSize.toInt())} پیکسل', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.primary)),
                  ],
                ),
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.remove_circle_outline, size: 20),
                      onPressed: () {
                        setState(() => _translationFontSize = (_translationFontSize - 1).clamp(11.0, 22.0));
                        setSheetState(() {});
                      },
                    ),
                    Expanded(
                      child: Slider(
                        value: _translationFontSize,
                        min: 11.0,
                        max: 22.0,
                        activeColor: EttehadColors.primary,
                        onChanged: (v) {
                          setState(() => _translationFontSize = v);
                          setSheetState(() {});
                        },
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.add_circle_outline, size: 20),
                      onPressed: () {
                        setState(() => _translationFontSize = (_translationFontSize + 1).clamp(11.0, 22.0));
                        setSheetState(() {});
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Night Mode Toggle
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('حالت تاریک و شب', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                  value: _nightMode,
                  onChanged: (v) {
                    setState(() => _nightMode = v);
                    setSheetState(() {});
                  },
                ),
                const SizedBox(height: 16),

                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: EttehadColors.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('تأیید و بازگشت به قرائت', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _openTadabburSheet(Map<String, dynamic> ayah) {
    final surahId = (ayah['surahId'] ?? _currentSurah['id']) as int;
    final ayahNum = (ayah['number'] ?? ayah['ayahNumber'] ?? 1) as int;
    final matched = widget.repo.tadabburList.firstWhere(
      (t) => t['surah_id'] == surahId && t['ayah_number'] == ayahNum,
      orElse: () => {},
    );
    final toolsFuture = widget.repo.fetchAyahTools(surahId, ayahNum);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: EttehadColors.paper,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: Container(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height * 0.82,
          ),
          padding: const EdgeInsets.all(20),
          child: ListView(
            shrinkWrap: true,
            children: [
              Row(
                children: [
                  const Icon(Icons.auto_stories_rounded, color: EttehadColors.amber),
                  const SizedBox(width: 8),
                  Text(
                    'تفسیر و تدبر تطبیقی • سوره ${toPersianDigits(surahId)} آیه ${toPersianDigits(ayahNum)}',
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                  ),
                ],
              ),
              const Divider(height: 24),
              Text(
                (ayah['text'] ?? ayah['textArabic'] ?? '').toString(),
                style: const TextStyle(
                  fontFamily: 'UthmanicHafs',
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: EttehadColors.navy,
                ),
              ),
              const SizedBox(height: 12),
              FutureBuilder<Map<String, dynamic>?>(
                future: toolsFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: Row(
                        children: [
                          SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: EttehadColors.primary)),
                          SizedBox(width: 10),
                          Text('در حال دریافت بسته پژوهشی و تفسیری از سرور (api.unitysi.ir)...', style: TextStyle(fontSize: 11, color: Colors.black54)),
                        ],
                      ),
                    );
                  }

                  final data = snapshot.data;
                  final tafsirText = data?['briefTafsir'] ??
                      matched['reflection_text'] ??
                      matched['tafsir_summary'] ??
                      'در تفاسیر معتبر فریقین (المیزان، نمونه، فی ظلال القرآن و تفسیر فخر رازی)، این آیه کریمه دعوت به تعقل، تقوا و همبستگی مؤمنان بر محور حق و عدل الهی دارد.';

                  final aiTadabbur = data?['aiTadabbur']?.toString();
                  final reflectionQ = data?['reflectionQuestion']?.toString();
                  final keywords = (data?['keywords'] is List) ? List<String>.from(data!['keywords']) : <String>[];

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: EttehadColors.border),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(
                              children: [
                                Icon(Icons.menu_book_rounded, size: 16, color: EttehadColors.primary),
                                SizedBox(width: 6),
                                Text('عصاره تفسیر فریقین:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(
                              tafsirText.toString(),
                              style: const TextStyle(fontSize: 12.5, height: 1.8),
                            ),
                          ],
                        ),
                      ),
                      if (aiTadabbur != null && aiTadabbur.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF0FDF4),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: const Color(0xFFBBF7D0)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.psychology_rounded, size: 16, color: Color(0xFF16A34A)),
                                  SizedBox(width: 6),
                                  Text('تدبر معرفتی و زیست مؤمنانه:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF15803D))),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                aiTadabbur,
                                style: const TextStyle(fontSize: 12, height: 1.8, color: Color(0xFF14532D)),
                              ),
                            ],
                          ),
                        ),
                      ],
                      if (reflectionQ != null && reflectionQ.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFEF3C7),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: const Color(0xFFFDE68A)),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.help_outline_rounded, size: 18, color: Color(0xFFB45309)),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'پرسش تدبر: $reflectionQ',
                                  style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: Color(0xFF92400E), height: 1.6),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                      if (keywords.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: keywords.map((k) => Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: EttehadColors.primary.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text('# $k', style: const TextStyle(fontSize: 10.5, color: EttehadColors.primary, fontWeight: FontWeight.bold)),
                          )).toList(),
                        ),
                      ],
                    ],
                  );
                },
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final nameAr = (_currentSurah['nameArabic'] ?? _currentSurah['name'] ?? '').toString();
    final ayahs = List<Map<String, dynamic>>.from(_currentSurah['ayahs'] ?? []);

    return Scaffold(
      backgroundColor: _readerBgColor,
      appBar: AppBar(
        backgroundColor: EttehadColors.navy,
        foregroundColor: Colors.white,
        title: Text(
          _mode == 'uthman'
              ? 'مصحف عثمان‌طه • صفحه ${toPersianDigits(_currentPage)} (جزء ${toPersianDigits(widget.repo.getJuzForPage(_currentPage))})'
              : 'سوره مبارکه $nameAr',
          style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900),
        ),
        actions: [
          IconButton(
            tooltip: 'پرش به جزء یا صفحه',
            icon: const Icon(Icons.travel_explore_rounded),
            onPressed: _openQuickJumpSheet,
          ),
          IconButton(
            tooltip: 'تنظیمات صوت، ترجمه و قلم',
            icon: const Icon(Icons.tune_rounded),
            onPressed: _openQuranSettingsSheet,
          ),
        ],
      ),
      body: Column(
        children: [
          // 3-Mode Quran Switcher
          Container(
            margin: const EdgeInsets.fromLTRB(12, 10, 12, 6),
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: _nightMode ? const Color(0xFF1E293B) : Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: EttehadColors.border),
            ),
            child: Row(
              children: [
                _modeBtn('translation', 'مصحف با ترجمه'),
                _modeBtn('uthman', 'مصحف عثمان‌طه (ورق‌زدنی)'),
                _modeBtn('tajweed', 'آموزش تجوید'),
              ],
            ),
          ),

          if (_mode == 'tajweed')
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.amber.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.amber.shade300),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _TajweedLegend(color: Color(0xFFE11D48), label: 'مدّ'),
                  _TajweedLegend(color: Color(0xFF059669), label: 'اخفاء و غنّه'),
                  _TajweedLegend(color: Color(0xFF2563EB), label: 'قلقله'),
                  _TajweedLegend(color: Color(0xFF7C3AED), label: 'ادغام'),
                ],
              ),
            ),

          Expanded(
            child: _mode == 'uthman'
                ? Column(
                    children: [
                      // The authentic horizontal PageView (book turning left/right)
                      Expanded(
                        child: PageView.builder(
                          controller: _pageController,
                          itemCount: 604,
                          onPageChanged: (index) {
                            final pageNum = index + 1;
                            setState(() {
                              _currentPage = pageNum;
                              final pageAyahs = widget.repo.getAyahsForPage(pageNum);
                              if (pageAyahs.isNotEmpty) {
                                final sId = pageAyahs.first['surahId'];
                                final s = widget.repo.surahs.firstWhere(
                                  (x) => x['id'] == sId,
                                  orElse: () => _currentSurah,
                                );
                                _currentSurah = s;
                              }
                            });
                            widget.repo.updateLastReadQuran(
                              _currentSurah['id'] as int,
                              (_currentSurah['nameArabic'] ?? _currentSurah['name'] ?? '').toString(),
                              1,
                              page: pageNum,
                              juz: widget.repo.getJuzForPage(pageNum),
                            );
                          },
                          itemBuilder: (ctx, index) {
                            final pageNum = index + 1;
                            return _buildOsmanTahaPage(pageNum);
                          },
                        ),
                      ),
                      // Osman Taha Bottom Book Navigation HUD
                      _buildOsmanTahaNavBar(),
                    ],
                  )
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(12, 6, 12, 90),
                    itemCount: ayahs.length,
                    itemBuilder: (ctx, i) {
                      final a = ayahs[i];
                      final ayahNum = (a['number'] ?? a['ayahNumber'] ?? (i + 1)) as int;
                      final ar = (a['text'] ?? a['textArabic'] ?? '').toString();
                      final fa = (a['translation'] ?? a['textPersian'] ?? '').toString();
                      final isPlaying = _isPlayingAudio && _currentPlayingAyah == ayahNum;

                      return Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: isPlaying
                              ? const Color(0xFFFEF3C7)
                              : (_nightMode ? const Color(0xFF1E293B) : Colors.white),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: isPlaying ? Colors.amber.shade600 : EttehadColors.border,
                            width: isPlaying ? 2 : 1,
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: EttehadColors.primary.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: Text(
                                    'آیه ${toPersianDigits(ayahNum)}',
                                    style: const TextStyle(
                                      fontSize: 11.5,
                                      fontWeight: FontWeight.bold,
                                      color: EttehadColors.primary,
                                    ),
                                  ),
                                ),
                                Row(
                                  children: [
                                    IconButton(
                                      icon: Icon(
                                        isPlaying ? Icons.pause_circle_rounded : Icons.play_circle_outline_rounded,
                                        color: isPlaying ? Colors.amber.shade900 : EttehadColors.primary,
                                        size: 20,
                                      ),
                                      onPressed: () {
                                        setState(() {
                                          if (isPlaying) {
                                            _isPlayingAudio = false;
                                          } else {
                                            _isPlayingAudio = true;
                                            _currentPlayingAyah = ayahNum;
                                          }
                                        });
                                      },
                                    ),
                                    TextButton.icon(
                                      onPressed: () => _openTadabburSheet(a),
                                      icon: const Icon(Icons.auto_stories_rounded, size: 16, color: EttehadColors.amber),
                                      label: const Text(
                                        'تدبر',
                                        style: TextStyle(fontSize: 11.5, color: EttehadColors.amber, fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              ar,
                              textAlign: TextAlign.right,
                              style: TextStyle(
                                fontFamily: 'UthmanicHafs',
                                fontSize: _arabicFontSize,
                                height: 2.1,
                                fontWeight: FontWeight.w700,
                                color: _mode == 'tajweed'
                                    ? const Color(0xFF0F5257)
                                    : _readerTextColor,
                              ),
                            ),
                            if (_showTranslation && fa.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Text(
                                fa,
                                style: TextStyle(
                                  fontSize: _translationFontSize,
                                  height: 1.75,
                                  color: _nightMode ? Colors.white70 : Colors.black87,
                                ),
                              ),
                            ],
                          ],
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),

      // Bottom Audio Player Bar
      bottomNavigationBar: Container(
        height: 62,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: _nightMode ? const Color(0xFF1E293B) : Colors.white,
          border: const Border(top: BorderSide(color: EttehadColors.border)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.08),
              blurRadius: 10,
              offset: const Offset(0, -3),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                IconButton(
                  icon: _isLoadingAudio
                      ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: EttehadColors.primary))
                      : Icon(
                          _isPlayingAudio ? Icons.pause_circle_filled_rounded : Icons.play_circle_filled_rounded,
                          color: EttehadColors.primary,
                          size: 34,
                        ),
                  onPressed: () => _toggleAudioPlayback(),
                ),
                const SizedBox(width: 6),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _isPlayingAudio
                          ? 'در حال پخش آیه ${toPersianDigits(_currentPlayingAyah)} (${_currentAudioUrl != null ? 'آنلاین CDN' : 'آماده'})'
                          : 'پخش صوت تلاوت',
                      style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900, color: _readerTextColor),
                    ),
                    Text(
                      _selectedReciter.split('(')[0],
                      style: const TextStyle(fontSize: 10, color: Colors.black54),
                    ),
                  ],
                ),
              ],
            ),
            Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.skip_previous_rounded, size: 22, color: EttehadColors.navy),
                  onPressed: _currentPlayingAyah > 1
                      ? () => setState(() => _currentPlayingAyah--)
                      : null,
                ),
                IconButton(
                  icon: const Icon(Icons.skip_next_rounded, size: 22, color: EttehadColors.navy),
                  onPressed: _currentPlayingAyah < ayahs.length
                      ? () => setState(() => _currentPlayingAyah++)
                      : null,
                ),
                IconButton(
                  tooltip: 'تنظیمات صوت',
                  icon: const Icon(Icons.tune_rounded, size: 20, color: EttehadColors.primary),
                  onPressed: _openQuranSettingsSheet,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // AUTHENTIC OSMAN TAHA MUS'HAF PAGE BUILDER
  // ---------------------------------------------------------------------------
  Widget _buildOsmanTahaPage(int pageNum) {
    final pageAyahs = widget.repo.getAyahsForPage(pageNum);

    if (pageAyahs.isEmpty) {
      return Center(
        child: Text(
          'صفحه ${toPersianDigits(pageNum)} در دسترس نیست',
          style: TextStyle(color: _readerTextColor),
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: _nightMode ? const Color(0xFF131D2E) : const Color(0xFFFFFDF5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: _nightMode ? const Color(0xFF334155) : const Color(0xFFD4AF37),
          width: 2.0,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: _nightMode ? 0.35 : 0.08),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Container(
        margin: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _nightMode ? const Color(0xFF1E293B) : const Color(0xFFC5A059),
            width: 1.0,
          ),
        ),
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 8),
        child: Column(
          children: [
            // 1. Top Mus'haf Header (سورة - حزب - جزء)
            _buildPageTopHeader(pageNum, pageAyahs),
            const SizedBox(height: 4),
            Container(
              height: 1,
              color: _nightMode ? const Color(0xFF334155) : const Color(0xFFD4AF37).withValues(alpha: 0.5),
            ),
            const SizedBox(height: 6),

            // 2. Exact Ayahs of that specific page in Uthmanic font
            Expanded(
              child: SingleChildScrollView(
                physics: const ClampingScrollPhysics(),
                child: _buildPageBody(pageNum, pageAyahs),
              ),
            ),

            const SizedBox(height: 4),
            Container(
              height: 1,
              color: _nightMode ? const Color(0xFF334155) : const Color(0xFFD4AF37).withValues(alpha: 0.5),
            ),
            const SizedBox(height: 4),

            // 3. Footer (Page Number)
            _buildPageFooter(pageNum),
          ],
        ),
      ),
    );
  }

  Widget _buildPageTopHeader(int pageNum, List<Map<String, dynamic>> pageAyahs) {
    final first = pageAyahs.first;
    final surahName = first['surahNameArabic'] ?? _currentSurah['nameArabic'] ?? '';
    final juzNum = first['juz'] ?? widget.repo.getJuzForPage(pageNum);
    final hizbNum = first['hizb'] ?? 1;

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          'سُورَةُ $surahName',
          style: TextStyle(
            fontFamily: 'UthmanicHafs',
            fontSize: 12.5,
            fontWeight: FontWeight.bold,
            color: _nightMode ? Colors.amberAccent : const Color(0xFF8C6D23),
          ),
        ),
        Row(
          children: [
            const Icon(Icons.star_rounded, size: 10, color: Color(0xFFD4AF37)),
            const SizedBox(width: 4),
            Text(
              'حِزْبُ ${toPersianDigits(hizbNum)}',
              style: TextStyle(
                fontFamily: 'UthmanicHafs',
                fontSize: 11,
                color: _nightMode ? Colors.white70 : const Color(0xFF7A591A),
              ),
            ),
            const SizedBox(width: 4),
            const Icon(Icons.star_rounded, size: 10, color: Color(0xFFD4AF37)),
          ],
        ),
        Text(
          'الجُزْءُ ${toPersianDigits(juzNum)}',
          style: TextStyle(
            fontFamily: 'UthmanicHafs',
            fontSize: 12.5,
            fontWeight: FontWeight.bold,
            color: _nightMode ? Colors.amberAccent : const Color(0xFF8C6D23),
          ),
        ),
      ],
    );
  }

  Widget _buildPageBody(int pageNum, List<Map<String, dynamic>> pageAyahs) {
    final List<Widget> sections = [];
    int curSurahId = -1;
    List<Map<String, dynamic>> curSurahAyahs = [];

    void flushSurah() {
      if (curSurahAyahs.isEmpty) return;
      final firstA = curSurahAyahs.first;
      final sId = firstA['surahId'] as int;
      final isSurahStart = firstA['ayahNumber'] == 1;

      // If a surah starts on this page, render the authentic decorative Surah Plaque
      if (isSurahStart) {
        sections.add(_buildSurahTitlePlaque(firstA));
        // Basmalah (except Surah 1 & Surah 9)
        if (sId != 1 && sId != 9) {
          sections.add(_buildBasmalah());
        }
      }

      // Continuous flowing text of ayahs in Uthmanic font
      sections.add(_buildAyahsContinuousText(curSurahAyahs));
      curSurahAyahs = [];
    }

    for (final a in pageAyahs) {
      final sId = a['surahId'] as int;
      if (sId != curSurahId) {
        flushSurah();
        curSurahId = sId;
      }
      curSurahAyahs.add(a);
    }
    flushSurah();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: sections,
    );
  }

  Widget _buildSurahTitlePlaque(Map<String, dynamic> ayah) {
    final sName = (ayah['surahNameArabic'] ?? '').toString();
    final rev = ayah['revelationType'] == 'MAKKI' ? 'مَكِّيَّةٌ' : 'مَدَنِيَّةٌ';
    final count = toPersianDigits(ayah['ayahCount'] ?? 7);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: _nightMode
              ? [const Color(0xFF1E293B), const Color(0xFF334155), const Color(0xFF1E293B)]
              : [const Color(0xFFFBF4DC), const Color(0xFFEAD8A6), const Color(0xFFFBF4DC)],
        ),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: _nightMode ? Colors.amberAccent.withValues(alpha: 0.5) : const Color(0xFFB8860B),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.amber.withValues(alpha: 0.12),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            rev,
            style: TextStyle(
              fontFamily: 'UthmanicHafs',
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: _nightMode ? Colors.white70 : const Color(0xFF7A591A),
            ),
          ),
          Text(
            'سُورَةُ $sName',
            style: TextStyle(
              fontFamily: 'UthmanicHafs',
              fontSize: 16,
              fontWeight: FontWeight.w900,
              color: _nightMode ? Colors.amberAccent : const Color(0xFF4A3207),
            ),
          ),
          Text(
            'آيَاتُهَا $count',
            style: TextStyle(
              fontFamily: 'UthmanicHafs',
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: _nightMode ? Colors.white70 : const Color(0xFF7A591A),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBasmalah() {
    return Padding(
      padding: const EdgeInsets.only(top: 2, bottom: 8),
      child: Center(
        child: Text(
          '۝ بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ ۝',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: 'UthmanicHafs',
            fontSize: _arabicFontSize * 0.95,
            fontWeight: FontWeight.bold,
            color: _nightMode ? const Color(0xFF38BDF8) : const Color(0xFF0F5257),
          ),
        ),
      ),
    );
  }

  Widget _buildAyahsContinuousText(List<Map<String, dynamic>> currentAyahs) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Text.rich(
        TextSpan(
          children: currentAyahs.expand((a) {
            final ayahNum = (a['ayahNumber'] ?? a['number'] ?? 1) as int;
            final arText = (a['textArabic'] ?? a['text'] ?? '').toString();
            final isPlaying = _isPlayingAudio && _currentPlayingAyah == ayahNum;

            return [
              TextSpan(
                text: '$arText ',
                style: TextStyle(
                  fontFamily: 'UthmanicHafs',
                  fontSize: _arabicFontSize,
                  height: 2.15,
                  letterSpacing: 0.2,
                  color: isPlaying ? Colors.amber.shade900 : _readerTextColor,
                  backgroundColor: isPlaying ? Colors.amber.withValues(alpha: 0.25) : Colors.transparent,
                  fontWeight: FontWeight.w600,
                ),
                recognizer: TapGestureRecognizer()..onTap = () => _showAyahDetailsModal(a),
              ),
              TextSpan(
                text: ' ﴿${toPersianDigits(ayahNum)}﴾ ',
                style: TextStyle(
                  fontFamily: 'UthmanicHafs',
                  fontSize: _arabicFontSize * 0.92,
                  fontWeight: FontWeight.bold,
                  color: _nightMode ? Colors.amberAccent : const Color(0xFFB8860B),
                ),
                recognizer: TapGestureRecognizer()..onTap = () => _showAyahDetailsModal(a),
              ),
            ];
          }).toList(),
        ),
        textAlign: TextAlign.justify,
        textDirection: TextDirection.rtl,
      ),
    );
  }

  Widget _buildPageFooter(int pageNum) {
    return Center(
      child: Text(
        '— ${toPersianDigits(pageNum)} —',
        style: TextStyle(
          fontFamily: 'UthmanicHafs',
          fontSize: 12.5,
          fontWeight: FontWeight.bold,
          color: _nightMode ? Colors.white60 : const Color(0xFF8C6D23),
        ),
      ),
    );
  }

  Widget _buildOsmanTahaNavBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: _nightMode ? const Color(0xFF1E293B) : Colors.white,
        border: const Border(top: BorderSide(color: EttehadColors.border)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 6,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Next Page (in RTL, swiping left turns to next page)
          IconButton(
            icon: const Icon(Icons.arrow_back_ios_rounded, size: 18),
            tooltip: 'صفحه بعد',
            onPressed: _currentPage < 604
                ? () {
                    _pageController.nextPage(
                      duration: const Duration(milliseconds: 300),
                      curve: Curves.easeInOut,
                    );
                  }
                : null,
          ),

          // Page Slider & Info
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'صفحه ${toPersianDigits(_currentPage)} از ۶۰۴',
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5),
                    ),
                    Text(
                      'جزء ${toPersianDigits(widget.repo.getJuzForPage(_currentPage))}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: EttehadColors.primary),
                    ),
                  ],
                ),
                SliderTheme(
                  data: SliderTheme.of(context).copyWith(
                    trackHeight: 2.5,
                    thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                  ),
                  child: Slider(
                    value: _currentPage.toDouble(),
                    min: 1.0,
                    max: 604.0,
                    activeColor: EttehadColors.primary,
                    onChanged: (v) {
                      final p = v.toInt();
                      if (p != _currentPage) {
                        _jumpToPage(p);
                      }
                    },
                  ),
                ),
              ],
            ),
          ),

          // Previous Page
          IconButton(
            icon: const Icon(Icons.arrow_forward_ios_rounded, size: 18),
            tooltip: 'صفحه قبل',
            onPressed: _currentPage > 1
                ? () {
                    _pageController.previousPage(
                      duration: const Duration(milliseconds: 300),
                      curve: Curves.easeInOut,
                    );
                  }
                : null,
          ),

          const SizedBox(width: 4),
          // Quick Jump Button
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: EttehadColors.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onPressed: _openQuickJumpSheet,
            icon: const Icon(Icons.filter_list_rounded, size: 15),
            label: const Text('پرش به جزء', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _modeBtn(String id, String title) {
    final active = _mode == id;
    return Expanded(
      child: GestureDetector(
        onTap: () => _onModeChanged(id),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 9),
          decoration: BoxDecoration(
            color: active ? EttehadColors.primary.withValues(alpha: 0.12) : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
          ),
          alignment: Alignment.center,
          child: Text(
            title,
            style: TextStyle(
              fontSize: 11.5,
              fontWeight: active ? FontWeight.w900 : FontWeight.w600,
              color: active ? EttehadColors.primary : Colors.black54,
            ),
          ),
        ),
      ),
    );
  }
}

class _TajweedLegend extends StatelessWidget {
  final Color color;
  final String label;
  const _TajweedLegend({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(width: 9, height: 9, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
