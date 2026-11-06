import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';
import 'gps_location_helper.dart';

class ScholarPickerModal extends StatefulWidget {
  final EttehadRepository repo;
  final String? currentScholarId;
  final ValueChanged<Map<String, dynamic>> onScholarSelected;

  const ScholarPickerModal({
    super.key,
    required this.repo,
    this.currentScholarId,
    required this.onScholarSelected,
  });

  static void show(
    BuildContext context,
    EttehadRepository repo, {
    String? currentScholarId,
    required ValueChanged<Map<String, dynamic>> onScholarSelected,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => ScholarPickerModal(
        repo: repo,
        currentScholarId: currentScholarId,
        onScholarSelected: onScholarSelected,
      ),
    );
  }

  @override
  State<ScholarPickerModal> createState() => _ScholarPickerModalState();
}

class _ScholarPickerModalState extends State<ScholarPickerModal> {
  final TextEditingController _searchCtrl = TextEditingController();

  // GPS User Location State (Step 1)
  String _userGpsCity = 'تهران';
  String _sortMode = 'gps'; // 'gps' | 'speed' | 'answers'

  // Advanced Multi-Facet Filters (Step 2)
  bool _showAdvancedFilters = false;
  String _selectedCity = 'all';
  String _selectedMadhhab = 'all';
  String _selectedSpecialty = 'all';
  bool _onlyWithMosque = false;

  final List<String> _cities = [
    'همه استان‌ها و شهرها',
    ...GpsLocationHelper.availableCities,
  ];

  final List<Map<String, String>> _madhhabs = [
    {'key': 'all', 'label': 'همه مذاهب'},
    {'key': 'shia', 'label': 'شیعه اثناعشری (جعفری)'},
    {'key': 'sunni_shafii', 'label': 'اهل سنت (شافعی)'},
    {'key': 'sunni_hanafi', 'label': 'اهل سنت (حنفی)'},
    {'key': 'taqrib', 'label': 'فقه مقارن و تقریب'},
  ];

  final List<Map<String, String>> _specialties = [
    {'key': 'all', 'label': 'همه حوزه‌های تخصصی'},
    {'key': 'moamelat', 'label': 'فقه معاملات و بورس'},
    {'key': 'ebadat', 'label': 'احکام عبادی و مناسک'},
    {'key': 'kalam', 'label': 'کلام و پاسخ به شبهات'},
    {'key': 'family', 'label': 'خانواده و ازدواج'},
    {'key': 'quran', 'label': 'تفسیر و علوم قرآن'},
    {'key': 'medical', 'label': 'مسائل نوین پزشکی'},
  ];

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  int get _activeFiltersCount {
    int count = 0;
    if (_selectedCity != 'all' && _selectedCity != 'همه استان‌ها و شهرها') count++;
    if (_selectedMadhhab != 'all') count++;
    if (_selectedSpecialty != 'all') count++;
    if (_onlyWithMosque) count++;
    return count;
  }

  void _changeUserGpsCity() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            height: 380,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.my_location_rounded, color: EttehadColors.primary, size: 20),
                    const SizedBox(width: 8),
                    const Text(
                      'انتخاب یا تغییر موقعیت GPS شما',
                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: EttehadColors.navy),
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 20),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const Text(
                  'عالمان و اساتید بر اساس فاصله به شهر انتخابی شما مرتب خواهند شد:',
                  style: TextStyle(fontSize: 11, color: Colors.black54),
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: ListView.separated(
                    itemCount: GpsLocationHelper.availableCities.length,
                    separatorBuilder: (context, index) => const Divider(height: 1),
                    itemBuilder: (context, idx) {
                      final c = GpsLocationHelper.availableCities[idx];
                      final isCurrent = c == _userGpsCity;
                      return ListTile(
                        dense: true,
                        title: Text(
                          c,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                            color: isCurrent ? EttehadColors.primary : EttehadColors.ink,
                          ),
                        ),
                        trailing: isCurrent ? const Icon(Icons.check_circle_rounded, color: EttehadColors.primary, size: 18) : null,
                        onTap: () {
                          setState(() {
                            _userGpsCity = c;
                          });
                          Navigator.pop(ctx);
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  List<Map<String, dynamic>> _getFilteredScholars() {
    final query = _searchCtrl.text.trim().toLowerCase();
    final scholars = widget.repo.scholars;

    final filtered = scholars.where((sc) {
      // 1. Text search focused on Scholar Name (and secondarily on mosque/title)
      final name = (sc['name'] ?? '').toString().toLowerCase();
      final title = (sc['title'] ?? '').toString().toLowerCase();
      final mosque = (sc['mosque'] ?? '').toString().toLowerCase();
      final bio = (sc['bio'] ?? '').toString().toLowerCase();

      final matchesSearch = query.isEmpty ||
          name.contains(query) ||
          title.contains(query) ||
          mosque.contains(query) ||
          bio.contains(query);

      if (!matchesSearch) return false;

      // 2. City filter (Step 2)
      if (_selectedCity != 'all' && _selectedCity != 'همه استان‌ها و شهرها') {
        final city = (sc['city'] ?? '').toString();
        if (!city.contains(_selectedCity)) return false;
      }

      // 3. Madhhab filter (Step 2)
      if (_selectedMadhhab != 'all') {
        final madhhab = (sc['madhhab'] ?? '').toString();
        if (_selectedMadhhab == 'shia' && !madhhab.contains('شیعه')) return false;
        if (_selectedMadhhab == 'sunni_shafii' && !madhhab.contains('شافعی')) return false;
        if (_selectedMadhhab == 'sunni_hanafi' && !madhhab.contains('حنفی')) return false;
        if (_selectedMadhhab == 'taqrib' && !madhhab.contains('تقریب') && !madhhab.contains('مشترک')) return false;
      }

      // 4. Specialty filter (Step 2)
      if (_selectedSpecialty != 'all') {
        final specs = (sc['specialties'] ?? '').toString();
        final scTitle = (sc['title'] ?? '').toString();
        final textToCheck = '$specs $scTitle';
        if (_selectedSpecialty == 'moamelat' && !textToCheck.contains('معاملات') && !textToCheck.contains('بورس') && !textToCheck.contains('اقتصاد')) return false;
        if (_selectedSpecialty == 'ebadat' && !textToCheck.contains('عباد') && !textToCheck.contains('احکام') && !textToCheck.contains('شرعی')) return false;
        if (_selectedSpecialty == 'kalam' && !textToCheck.contains('کلام') && !textToCheck.contains('عقاید') && !textToCheck.contains('حکمت')) return false;
        if (_selectedSpecialty == 'family' && !textToCheck.contains('خانواده') && !textToCheck.contains('ازدواج')) return false;
        if (_selectedSpecialty == 'quran' && !textToCheck.contains('تفسیر') && !textToCheck.contains('قرآن')) return false;
        if (_selectedSpecialty == 'medical' && !textToCheck.contains('پزشکی') && !textToCheck.contains('مستحدثه')) return false;
      }

      // 5. Only with mosque (Step 2)
      if (_onlyWithMosque) {
        final mosque = (sc['mosque'] ?? '').toString().trim();
        if (mosque.isEmpty) return false;
      }

      return true;
    }).toList();

    // Sorting algorithm:
    // A) If searching by scholar name, rank direct name match to absolute top
    if (query.isNotEmpty) {
      filtered.sort((a, b) {
        final aName = (a['name'] ?? '').toString().toLowerCase();
        final bName = (b['name'] ?? '').toString().toLowerCase();
        final aHasName = aName.contains(query);
        final bHasName = bName.contains(query);
        if (aHasName && !bHasName) return -1;
        if (!aHasName && bHasName) return 1;

        final distA = GpsLocationHelper.getScholarDistanceKm(_userGpsCity, a);
        final distB = GpsLocationHelper.getScholarDistanceKm(_userGpsCity, b);
        return distA.compareTo(distB);
      });
      return filtered;
    }

    // B) Step 1: Default sort by GPS distance (Nearest First)
    if (_sortMode == 'gps') {
      filtered.sort((a, b) {
        final distA = GpsLocationHelper.getScholarDistanceKm(_userGpsCity, a);
        final distB = GpsLocationHelper.getScholarDistanceKm(_userGpsCity, b);
        return distA.compareTo(distB);
      });
    } else if (_sortMode == 'speed') {
      filtered.sort((a, b) {
        final tA = (a['response_time_hours'] as num?)?.toInt() ?? 10;
        final tB = (b['response_time_hours'] as num?)?.toInt() ?? 10;
        return tA.compareTo(tB);
      });
    } else if (_sortMode == 'answers') {
      filtered.sort((a, b) {
        final cA = (a['answer_count'] as num?)?.toInt() ?? 0;
        final cB = (b['answer_count'] as num?)?.toInt() ?? 0;
        return cB.compareTo(cA);
      });
    }

    return filtered;
  }

  void _clearFilters() {
    setState(() {
      _searchCtrl.clear();
      _selectedCity = 'all';
      _selectedMadhhab = 'all';
      _selectedSpecialty = 'all';
      _onlyWithMosque = false;
      _sortMode = 'gps';
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _getFilteredScholars();
    final hasActiveFilter = _activeFiltersCount > 0 || _searchCtrl.text.isNotEmpty || _sortMode != 'gps';

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Container(
        height: MediaQuery.of(context).size.height * 0.94,
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          children: [
            // Handle bar
            Container(
              margin: const EdgeInsets.only(top: 10, bottom: 6),
              width: 44,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),

            // Header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: EttehadColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.manage_search_rounded, color: EttehadColors.primary, size: 22),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'جستجو و فیلتر پیشرفته علما و اساتید',
                          style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: EttehadColors.navy),
                        ),
                        Text(
                          'انتخاب از میان بیش از ۶۰۰ عالم برجسته در ۳۲ استان کشور',
                          style: TextStyle(fontSize: 10, color: Colors.grey.shade600),
                        ),
                      ],
                    ),
                  ),
                  if (hasActiveFilter)
                    TextButton(
                      onPressed: _clearFilters,
                      child: const Text('پاک‌کردن فیلترها', style: TextStyle(fontSize: 10.5, color: Colors.red)),
                    ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close_rounded, size: 22),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            // 1. DEDICATED SEARCH BAR (Focused on Scholar Name)
            Container(
              color: Colors.white,
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.person_search_rounded, color: EttehadColors.primary, size: 16),
                      SizedBox(width: 6),
                      Text(
                        'جستجو بر اساس نام عالم دینی',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _searchCtrl,
                    onChanged: (_) => setState(() {}),
                    decoration: InputDecoration(
                      hintText: 'نام یا لقب عالم را بنویسید (مثال: موسوی، مرادی، گرگیج، عابدی...)',
                      hintStyle: const TextStyle(fontSize: 11.5, color: Colors.black45),
                      prefixIcon: const Icon(Icons.search_rounded, color: EttehadColors.primary, size: 20),
                      suffixIcon: _searchCtrl.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear_rounded, size: 18),
                              onPressed: () {
                                _searchCtrl.clear();
                                setState(() {});
                              },
                            )
                          : null,
                      filled: true,
                      fillColor: EttehadColors.surfaceLow,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                    ),
                  ),
                ],
              ),
            ),

            // 2. STEP 1: USER GPS BANNER & PROXIMITY FIRST
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: EttehadColors.emerald.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: EttehadColors.emerald.withValues(alpha: 0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.my_location_rounded, size: 16, color: EttehadColors.emeraldDark),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          'مرحله ۱ (پیش‌فرض): موقعیت GPS شما: $_userGpsCity',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: EttehadColors.emeraldDark),
                        ),
                      ),
                      const SizedBox(width: 6),
                      InkWell(
                        onTap: _changeUserGpsCity,
                        borderRadius: BorderRadius.circular(8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: EttehadColors.emerald),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.edit_location_alt_rounded, size: 13, color: EttehadColors.emeraldDark),
                              SizedBox(width: 3),
                              Text('تغییر شهر GPS', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: EttehadColors.emeraldDark)),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'عالمان و اساتید ابتدا بر اساس کمترین فاصله به موقعیت مکانی شما نمایش داده می‌شوند:',
                    style: TextStyle(fontSize: 10, color: Colors.black87),
                  ),
                  const SizedBox(height: 6),

                  // Sort selector chips
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _sortChip('gps', '📍 نزدیک‌ترین به من (GPS)', Icons.near_me_rounded),
                        const SizedBox(width: 6),
                        _sortChip('speed', '⚡ سریع‌ترین پاسخ', Icons.speed_rounded),
                        const SizedBox(width: 6),
                        _sortChip('answers', '⭐ بیشترین پاسخ', Icons.check_circle_outline_rounded),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // 3. STEP 2: EXPANDABLE ADVANCED FILTERS (مرحله دوم: فیلترهای چندوجهی)
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              decoration: BoxDecoration(
                color: EttehadColors.surfaceLow,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: EttehadColors.border),
              ),
              child: Column(
                children: [
                  InkWell(
                    onTap: () => setState(() => _showAdvancedFilters = !_showAdvancedFilters),
                    borderRadius: BorderRadius.circular(14),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      child: Row(
                        children: [
                          Icon(
                            _showAdvancedFilters ? Icons.tune_rounded : Icons.filter_alt_outlined,
                            size: 16,
                            color: EttehadColors.primary,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Row(
                              children: [
                                const Flexible(
                                  child: Text(
                                    'مرحله ۲: فیلترهای تکمیلی (استان، مذهب، تخصص، مسجد)',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                                  ),
                                ),
                                if (_activeFiltersCount > 0) ...[
                                  const SizedBox(width: 6),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                                    decoration: BoxDecoration(
                                      color: EttehadColors.primary,
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Text(
                                      '${toPersianDigits(_activeFiltersCount)} فیلتر فعال',
                                      style: const TextStyle(fontSize: 9, color: Colors.white, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                          Icon(
                            _showAdvancedFilters ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                            size: 20,
                            color: Colors.black54,
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Collapsible Filters Body
                  if (_showAdvancedFilters) ...[
                    const Divider(height: 1),
                    Padding(
                      padding: const EdgeInsets.all(10),
                      child: Column(
                        children: [
                          // Dropdowns Row: City & Madhhab
                          Row(
                            children: [
                              // City Picker
                              Expanded(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: EttehadColors.border),
                                  ),
                                  child: DropdownButtonHideUnderline(
                                    child: DropdownButton<String>(
                                      value: _selectedCity == 'all' ? _cities.first : _selectedCity,
                                      isExpanded: true,
                                      icon: const Icon(Icons.location_city_rounded, size: 15, color: EttehadColors.primary),
                                      style: const TextStyle(fontSize: 10.5, color: EttehadColors.ink),
                                      items: _cities.map((c) {
                                        return DropdownMenuItem<String>(
                                          value: c,
                                          child: Text(c, style: const TextStyle(fontSize: 10.5)),
                                        );
                                      }).toList(),
                                      onChanged: (v) {
                                        setState(() {
                                          _selectedCity = (v == _cities.first) ? 'all' : (v ?? 'all');
                                        });
                                      },
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),

                              // Madhhab Picker
                              Expanded(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: EttehadColors.border),
                                  ),
                                  child: DropdownButtonHideUnderline(
                                    child: DropdownButton<String>(
                                      value: _selectedMadhhab,
                                      isExpanded: true,
                                      icon: const Icon(Icons.balance_rounded, size: 15, color: EttehadColors.amberDark),
                                      style: const TextStyle(fontSize: 10.5, color: EttehadColors.ink),
                                      items: _madhhabs.map((m) {
                                        return DropdownMenuItem<String>(
                                          value: m['key']!,
                                          child: Text(m['label']!, style: const TextStyle(fontSize: 10.5)),
                                        );
                                      }).toList(),
                                      onChanged: (v) {
                                        setState(() => _selectedMadhhab = v ?? 'all');
                                      },
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),

                          // Specialty Row and Mosque Checkbox
                          Row(
                            children: [
                              // Specialty Picker
                              Expanded(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: EttehadColors.border),
                                  ),
                                  child: DropdownButtonHideUnderline(
                                    child: DropdownButton<String>(
                                      value: _selectedSpecialty,
                                      isExpanded: true,
                                      icon: const Icon(Icons.school_rounded, size: 15, color: EttehadColors.emeraldDark),
                                      style: const TextStyle(fontSize: 10.5, color: EttehadColors.ink),
                                      items: _specialties.map((s) {
                                        return DropdownMenuItem<String>(
                                          value: s['key']!,
                                          child: Text(s['label']!, style: const TextStyle(fontSize: 10.5)),
                                        );
                                      }).toList(),
                                      onChanged: (v) {
                                        setState(() => _selectedSpecialty = v ?? 'all');
                                      },
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),

                              // Only With Mosque Toggle Chip
                              InkWell(
                                onTap: () => setState(() => _onlyWithMosque = !_onlyWithMosque),
                                borderRadius: BorderRadius.circular(10),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
                                  decoration: BoxDecoration(
                                    color: _onlyWithMosque ? EttehadColors.emerald.withValues(alpha: 0.15) : Colors.white,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(
                                      color: _onlyWithMosque ? EttehadColors.emerald : EttehadColors.border,
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        Icons.mosque_rounded,
                                        size: 15,
                                        color: _onlyWithMosque ? EttehadColors.emeraldDark : Colors.black54,
                                      ),
                                      const SizedBox(width: 4),
                                      Text(
                                        'دارای مسجد',
                                        style: TextStyle(
                                          fontSize: 10.5,
                                          fontWeight: _onlyWithMosque ? FontWeight.bold : FontWeight.normal,
                                          color: _onlyWithMosque ? EttehadColors.emeraldDark : EttehadColors.ink,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // Result stats strip
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Flexible(
                    child: Text(
                      'تعداد اساتید: ${toPersianDigits(filtered.length)} عالم',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.inkLight),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      _sortMode == 'gps' ? 'مرتب‌سازی: نزدیک‌ترین (GPS)' : (_sortMode == 'speed' ? 'سریع‌ترین پاسخ' : 'بیشترین پاسخ'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 10, color: EttehadColors.primary, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ),

            // Scholars Result List
            Expanded(
              child: filtered.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.person_off_rounded, size: 48, color: Colors.grey.shade400),
                          const SizedBox(height: 8),
                          const Text(
                            'هیچ عالمی با نام یا مشخصات وارد شده یافت نشد.',
                            style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Colors.black54),
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            'لطفاً نام دیگری را جستجو کرده یا فیلترهای استانی را تغییر دهید.',
                            style: TextStyle(fontSize: 11, color: Colors.black38),
                          ),
                          const SizedBox(height: 12),
                          ElevatedButton.icon(
                            onPressed: _clearFilters,
                            icon: const Icon(Icons.refresh_rounded, size: 16),
                            label: const Text('پاک‌کردن فیلترها و نمایش همه'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: EttehadColors.primary,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                            ),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                      itemCount: filtered.length,
                      itemBuilder: (ctx, idx) {
                        final sc = filtered[idx];
                        final scId = sc['id']?.toString() ?? 'sc_$idx';
                        final isSelected = widget.currentScholarId == scId;
                        final name = (sc['name'] ?? 'استاد').toString();
                        final title = (sc['title'] ?? 'فقه و معارف').toString();
                        final city = (sc['city'] ?? 'قم').toString();
                        final mosque = (sc['mosque'] ?? '').toString().trim();
                        final madhhab = (sc['madhhab'] ?? 'تقریب فریقین').toString();
                        final responseHours = sc['response_time_hours'] ?? (2 + idx);

                        final distanceKm = GpsLocationHelper.getScholarDistanceKm(_userGpsCity, sc);
                        final distanceStr = GpsLocationHelper.formatDistance(distanceKm);
                        final isNearbyInSameCity = distanceKm < 15.0;

                        List<String> specialties = [];
                        final rawSpecs = sc['specialties'];
                        if (rawSpecs is String) {
                          try {
                            final decoded = jsonDecode(rawSpecs);
                            if (decoded is List) specialties = decoded.map((e) => e.toString()).toList();
                          } catch (_) {}
                        } else if (rawSpecs is List) {
                          specialties = rawSpecs.map((e) => e.toString()).toList();
                        }

                        return Container(
                          margin: const EdgeInsets.only(bottom: 10),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: isSelected ? EttehadColors.primary : EttehadColors.border,
                              width: isSelected ? 2 : 1,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.03),
                                blurRadius: 6,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Top row: Avatar + Name + Madhhab
                                Row(
                                  children: [
                                    CircleAvatar(
                                      radius: 20,
                                      backgroundColor: EttehadColors.navy,
                                      child: Text(
                                        name.isNotEmpty ? name.substring(0, min(2, name.length)) : 'عالم',
                                        style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            name,
                                            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: EttehadColors.navy),
                                          ),
                                          Text(
                                            '$title • پاسخ‌گویی حدود $responseHours ساعت',
                                            style: const TextStyle(fontSize: 10, color: Colors.black54),
                                          ),
                                        ],
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFEFF6FF),
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: Text(
                                        madhhab,
                                        style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),

                                // Location, Mosque strip & GPS Distance Badge
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: isNearbyInSameCity
                                        ? EttehadColors.emerald.withValues(alpha: 0.08)
                                        : EttehadColors.surfaceLow,
                                    borderRadius: BorderRadius.circular(8),
                                    border: isNearbyInSameCity
                                        ? Border.all(color: EttehadColors.emerald.withValues(alpha: 0.3))
                                        : null,
                                  ),
                                  child: SingleChildScrollView(
                                    scrollDirection: Axis.horizontal,
                                    child: Row(
                                      children: [
                                        Icon(
                                          Icons.location_on_rounded,
                                          size: 14,
                                          color: isNearbyInSameCity ? EttehadColors.emeraldDark : EttehadColors.primary,
                                        ),
                                        const SizedBox(width: 4),
                                        Text(
                                          'استان/شهر: $city',
                                          style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
                                        ),
                                        const SizedBox(width: 6),
                                        // Proximity Distance Pill
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                                          decoration: BoxDecoration(
                                            color: isNearbyInSameCity ? EttehadColors.emerald : Colors.blue.shade50,
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Text(
                                            isNearbyInSameCity ? '📍 $distanceStr (نزدیک‌ترین به شما)' : '📍 $distanceStr با شما',
                                            style: TextStyle(
                                              fontSize: 9,
                                              fontWeight: FontWeight.bold,
                                              color: isNearbyInSameCity ? Colors.white : EttehadColors.primary,
                                            ),
                                          ),
                                        ),
                                        if (mosque.isNotEmpty) ...[
                                          const SizedBox(width: 6),
                                          const Icon(Icons.mosque_rounded, size: 13, color: EttehadColors.emeraldDark),
                                          const SizedBox(width: 3),
                                          Text(
                                            mosque,
                                            style: const TextStyle(fontSize: 9.5, color: EttehadColors.emeraldDark, fontWeight: FontWeight.bold),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                ),

                                if (specialties.isNotEmpty) ...[
                                  const SizedBox(height: 6),
                                  Wrap(
                                    spacing: 4,
                                    runSpacing: 4,
                                    children: specialties.map((s) {
                                      return Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: Colors.grey.shade100,
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Text(s, style: const TextStyle(fontSize: 9, color: Colors.black87)),
                                      );
                                    }).toList(),
                                  ),
                                ],
                                const SizedBox(height: 10),

                                // Selection button
                                SizedBox(
                                  width: double.infinity,
                                  height: 36,
                                  child: ElevatedButton.icon(
                                    onPressed: () {
                                      widget.onScholarSelected(sc);
                                      Navigator.pop(context);
                                    },
                                    icon: Icon(
                                      isSelected ? Icons.check_circle_rounded : Icons.person_add_alt_1_rounded,
                                      size: 16,
                                    ),
                                    label: Text(
                                      isSelected ? 'عالم دینی انتخاب‌شده شما' : 'انتخاب این عالم جهت ارسال مستقیم استفتاء',
                                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                                    ),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: isSelected ? EttehadColors.emeraldDark : EttehadColors.primary,
                                      foregroundColor: Colors.white,
                                      elevation: 0,
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                    ),
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
    );
  }

  Widget _sortChip(String key, String label, IconData icon) {
    final isSelected = _sortMode == key;
    return InkWell(
      onTap: () => setState(() => _sortMode = key),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
        decoration: BoxDecoration(
          color: isSelected ? EttehadColors.emeraldDark : Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isSelected ? EttehadColors.emeraldDark : Colors.grey.shade300),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 12, color: isSelected ? Colors.white : Colors.black54),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 9.5,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                color: isSelected ? Colors.white : Colors.black87,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
