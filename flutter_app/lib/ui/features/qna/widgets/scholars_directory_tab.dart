import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';
import 'new_inquiry_modal.dart';
import 'scholar_chat_screen.dart';
import 'gps_location_helper.dart';

class ScholarsDirectoryTab extends StatefulWidget {
  final EttehadRepository repo;

  const ScholarsDirectoryTab({super.key, required this.repo});

  @override
  State<ScholarsDirectoryTab> createState() => _ScholarsDirectoryTabState();
}

class _ScholarsDirectoryTabState extends State<ScholarsDirectoryTab> {
  final TextEditingController _searchCtrl = TextEditingController();

  // GPS User Location State (Step 1)
  String _userGpsCity = 'تهران';
  String _sortMode = 'gps'; // 'gps' | 'speed' | 'answers'

  // Advanced Multi-Facet Filters (Step 2)
  bool _showAdvancedFilters = false;
  String _selectedCity = 'all';
  String _selectedMadhhabFilter = 'all';
  String _selectedSpecialty = 'all';
  bool _onlyWithMosque = false;

  final List<String> _cities = [
    'همه استان‌ها و شهرها',
    ...GpsLocationHelper.availableCities,
  ];

  final List<Map<String, String>> _madhhabFilters = [
    {'key': 'all', 'label': 'همه مذاهب'},
    {'key': 'shia', 'label': 'شیعه (جعفری)'},
    {'key': 'sunni_shafii', 'label': 'اهل سنت (شافعی)'},
    {'key': 'sunni_hanafi', 'label': 'اهل سنت (حنفی)'},
    {'key': 'taqrib', 'label': 'تقریب و فقه مقارن'},
  ];

  final List<Map<String, String>> _specialties = [
    {'key': 'all', 'label': 'همه تخصص‌ها'},
    {'key': 'moamelat', 'label': 'معاملات و بورس'},
    {'key': 'ebadat', 'label': 'احکام عبادات'},
    {'key': 'kalam', 'label': 'کلام و عقاید'},
    {'key': 'family', 'label': 'خانواده'},
    {'key': 'quran', 'label': 'تفسیر قرآن'},
    {'key': 'medical', 'label': 'مسائل پزشکی'},
  ];

  @override
  void initState() {
    super.initState();
    widget.repo.syncScholarsFromBackend().then((_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  int get _activeFiltersCount {
    int count = 0;
    if (_selectedCity != 'all' && _selectedCity != 'همه استان‌ها و شهرها') count++;
    if (_selectedMadhhabFilter != 'all') count++;
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
                      'تغییر موقعیت GPS کاربر',
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
                  'فاصله علمای دینی بر اساس شهر انتخاب‌شده شما محاسبه می‌گردد:',
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

  void _openScholarChat(Map<String, dynamic> scholar) {
    final res = widget.repo.startOrOpenScholarChat(scholar);
    if (res == 'LIMIT_REACHED') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('حداکثر ۵ گفتگوی همزمان با اساتید فعال است.'),
          backgroundColor: EttehadColors.amberDark,
        ),
      );
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: ScholarChatRoomScreen(scholar: scholar, repo: widget.repo),
        ),
      ),
    );
  }

  void _openInquiryModal(Map<String, dynamic> scholar) {
    NewInquiryModal.show(
      context,
      widget.repo,
      targetScholar: scholar,
    );
  }

  List<Map<String, dynamic>> _getFilteredScholars() {
    final query = _searchCtrl.text.trim().toLowerCase();
    final scholars = widget.repo.scholars;

    final filtered = scholars.where((sc) {
      final name = (sc['name'] ?? '').toString().toLowerCase();
      final title = (sc['title'] ?? '').toString().toLowerCase();
      final mosque = (sc['mosque'] ?? '').toString().toLowerCase();
      final city = (sc['city'] ?? '').toString();
      final madhhab = (sc['madhhab'] ?? '').toString();

      // Search focused on name + mosque/title
      if (query.isNotEmpty) {
        if (!name.contains(query) && !title.contains(query) && !mosque.contains(query) && !city.contains(query)) {
          return false;
        }
      }

      // City filter (Step 2)
      if (_selectedCity != 'all' && _selectedCity != 'همه استان‌ها و شهرها') {
        if (!city.contains(_selectedCity)) return false;
      }

      // Madhhab filter (Step 2)
      if (_selectedMadhhabFilter == 'shia' && !madhhab.contains('شیعه')) return false;
      if (_selectedMadhhabFilter == 'sunni_shafii' && !madhhab.contains('شافعی')) return false;
      if (_selectedMadhhabFilter == 'sunni_hanafi' && !madhhab.contains('حنفی')) return false;
      if (_selectedMadhhabFilter == 'taqrib' && !madhhab.contains('تقریب') && !madhhab.contains('مشترک')) return false;

      // Specialty filter (Step 2)
      if (_selectedSpecialty != 'all') {
        final specs = (sc['specialties'] ?? '').toString();
        final scTitle = title;
        final textToCheck = '$specs $scTitle';
        if (_selectedSpecialty == 'moamelat' && !textToCheck.contains('معاملات') && !textToCheck.contains('بورس')) return false;
        if (_selectedSpecialty == 'ebadat' && !textToCheck.contains('عباد') && !textToCheck.contains('احکام')) return false;
        if (_selectedSpecialty == 'kalam' && !textToCheck.contains('کلام') && !textToCheck.contains('عقاید')) return false;
        if (_selectedSpecialty == 'family' && !textToCheck.contains('خانواده')) return false;
        if (_selectedSpecialty == 'quran' && !textToCheck.contains('تفسیر') && !textToCheck.contains('قرآن')) return false;
        if (_selectedSpecialty == 'medical' && !textToCheck.contains('پزشکی')) return false;
      }

      // Mosque filter (Step 2)
      if (_onlyWithMosque && mosque.trim().isEmpty) return false;

      return true;
    }).toList();

    // Sort order:
    // A) If searching by name, prioritize direct name matches at top
    if (query.isNotEmpty) {
      filtered.sort((a, b) {
        final aName = (a['name'] ?? '').toString().toLowerCase();
        final bName = (b['name'] ?? '').toString().toLowerCase();
        final aHas = aName.contains(query);
        final bHas = bName.contains(query);
        if (aHas && !bHas) return -1;
        if (!aHas && bHas) return 1;

        final distA = GpsLocationHelper.getScholarDistanceKm(_userGpsCity, a);
        final distB = GpsLocationHelper.getScholarDistanceKm(_userGpsCity, b);
        return distA.compareTo(distB);
      });
      return filtered;
    }

    // B) Step 1: Default sort by GPS Distance (Nearest First)
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
      _selectedMadhhabFilter = 'all';
      _selectedSpecialty = 'all';
      _onlyWithMosque = false;
      _sortMode = 'gps';
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _getFilteredScholars();

    return Column(
      children: [
        // 1. DEDICATED SEARCH BAR (Focused on Scholar Name)
        Container(
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.person_search_rounded, color: EttehadColors.primary, size: 16),
                  SizedBox(width: 6),
                  Text(
                    'جستجو بر اساس نام عالم دینی',
                    style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              TextField(
                controller: _searchCtrl,
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  hintText: 'نام یا لقب عالم را وارد کنید (مانند: موسوی، مرادی، گرگیج، عابدی...)',
                  hintStyle: const TextStyle(fontSize: 11, color: Colors.black45),
                  prefixIcon: const Icon(Icons.search_rounded, color: EttehadColors.primary, size: 18),
                  suffixIcon: _searchCtrl.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear_rounded, size: 16),
                          onPressed: () {
                            _searchCtrl.clear();
                            setState(() {});
                          },
                        )
                      : null,
                  filled: true,
                  fillColor: EttehadColors.surfaceLow,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
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
                  const Icon(Icons.my_location_rounded, size: 15, color: EttehadColors.emeraldDark),
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
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: EttehadColors.emerald),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.edit_location_alt_rounded, size: 12, color: EttehadColors.emeraldDark),
                          SizedBox(width: 3),
                          Text('تغییر شهر', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: EttehadColors.emeraldDark)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              const Text(
                'عالمان و اساتید ابتدا بر اساس کمترین فاصله به موقعیت شما نمایش داده می‌شوند:',
                style: TextStyle(fontSize: 10, color: Colors.black87),
              ),
              const SizedBox(height: 6),

              // Proximity Sort Chips
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

        // 3. STEP 2: EXPANDABLE ADVANCED FILTERS (مرحله دوم: فیلترهای تکمیلی)
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

              // Collapsible Filter Body
              if (_showAdvancedFilters) ...[
                const Divider(height: 1),
                Padding(
                  padding: const EdgeInsets.all(10),
                  child: Column(
                    children: [
                      // City and Mosque row
                      Row(
                        children: [
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
                                  style: const TextStyle(fontSize: 11, color: EttehadColors.ink),
                                  items: _cities.map((c) {
                                    return DropdownMenuItem<String>(
                                      value: c,
                                      child: Text(c, style: const TextStyle(fontSize: 11)),
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
                          InkWell(
                            onTap: () => setState(() => _onlyWithMosque = !_onlyWithMosque),
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                              decoration: BoxDecoration(
                                color: _onlyWithMosque ? EttehadColors.emerald.withValues(alpha: 0.15) : Colors.white,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: _onlyWithMosque ? EttehadColors.emerald : EttehadColors.border),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.mosque_rounded, size: 15, color: _onlyWithMosque ? EttehadColors.emeraldDark : Colors.black54),
                                  const SizedBox(width: 4),
                                  Text('دارای مسجد', style: TextStyle(fontSize: 10.5, fontWeight: _onlyWithMosque ? FontWeight.bold : FontWeight.normal)),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),

                      // Madhhab Filter Chips
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: _madhhabFilters.map((f) {
                            final isSelected = _selectedMadhhabFilter == f['key'];
                            return Padding(
                              padding: const EdgeInsets.only(left: 6),
                              child: InkWell(
                                onTap: () => setState(() => _selectedMadhhabFilter = f['key']!),
                                borderRadius: BorderRadius.circular(10),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4.5),
                                  decoration: BoxDecoration(
                                    color: isSelected ? EttehadColors.primary : Colors.white,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: isSelected ? EttehadColors.primary : EttehadColors.border),
                                  ),
                                  child: Text(
                                    f['label']!,
                                    style: TextStyle(
                                      fontSize: 10.5,
                                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                      color: isSelected ? Colors.white : EttehadColors.ink,
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                      const SizedBox(height: 6),

                      // Specialty Filter Chips
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: _specialties.map((s) {
                            final isSelected = _selectedSpecialty == s['key'];
                            return Padding(
                              padding: const EdgeInsets.only(left: 6),
                              child: InkWell(
                                onTap: () => setState(() => _selectedSpecialty = s['key']!),
                                borderRadius: BorderRadius.circular(10),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: isSelected ? EttehadColors.amberDark : Colors.white,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: isSelected ? EttehadColors.amberDark : EttehadColors.border),
                                  ),
                                  child: Text(
                                    s['label']!,
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                      color: isSelected ? Colors.white : EttehadColors.inkLight,
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),

        // Result count strip
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  'اساتید پاسخ‌گو: ${toPersianDigits(filtered.length)} عالم',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.inkLight),
                ),
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  _sortMode == 'gps' ? 'مرتب‌سازی: نزدیک‌ترین به موقعیت شما' : (_sortMode == 'speed' ? 'مرتب‌سازی: سریع‌ترین پاسخ' : 'مرتب‌سازی: بیشترین پاسخ'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10, color: EttehadColors.primary, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),

        // Scholars List
        Expanded(
          child: filtered.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.search_off_rounded, size: 48, color: Colors.grey.shade400),
                      const SizedBox(height: 8),
                      const Text(
                        'عالمی با نام یا مشخصات وارد شده یافت نشد.',
                        style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Colors.black54),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'لطفاً نام یا فیلترهای انتخابی را تغییر دهید.',
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
              : RefreshIndicator(
                  color: EttehadColors.primary,
                  onRefresh: () async {
                    await widget.repo.syncScholarsFromBackend();
                    if (mounted) setState(() {});
                  },
                  child: ListView.builder(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
                    itemCount: filtered.length,
                    itemBuilder: (ctx, idx) {
                      final sc = filtered[idx];
                      final name = (sc['name'] ?? 'عالم دینی').toString();
                      final title = (sc['title'] ?? 'استاد و پژوهشگر حوزه').toString();
                      final city = (sc['city'] ?? 'قم').toString();
                      final mosque = (sc['mosque'] ?? '').toString().trim();
                    final madhhab = (sc['madhhab'] ?? 'شیعه اثناعشری').toString();
                    final bio = (sc['bio'] ?? '').toString();
                    final answerCount = sc['answer_count'] ?? (120 + idx * 35);
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
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: EttehadColors.border),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.04),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Top Row: Avatar + Name + Response Time
                            Row(
                              children: [
                                CircleAvatar(
                                  radius: 22,
                                  backgroundColor: EttehadColors.navy,
                                  child: Text(
                                    name.isNotEmpty ? name.substring(0, min(2, name.length)) : 'عالم',
                                    style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        name,
                                        style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.navy),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        title,
                                        style: const TextStyle(fontSize: 10.5, color: Colors.black54),
                                      ),
                                    ],
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: Colors.amber.shade50,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: Colors.amber.shade200),
                                  ),
                                  child: Text(
                                    'پاسخ در ${toPersianDigits(responseHours)} ساعت',
                                    style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: Colors.amber.shade900),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),

                            // Location, Mosque & GPS Proximity Distance Pill
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
                                      style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold),
                                    ),
                                    const SizedBox(width: 6),
                                    // Proximity badge
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                                      decoration: BoxDecoration(
                                        color: isNearbyInSameCity ? EttehadColors.emerald : Colors.blue.shade50,
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: Text(
                                        isNearbyInSameCity ? '📍 $distanceStr (نزدیک‌ترین به شما)' : '📍 $distanceStr با شما',
                                        style: TextStyle(
                                          fontSize: 9.5,
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

                            // Madhhab & stats row
                            const SizedBox(height: 8),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2.5),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFEFF6FF),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    madhhab,
                                    style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                                  ),
                                ),
                                Text(
                                  '${toPersianDigits(answerCount)} پاسخ مستند',
                                  style: const TextStyle(fontSize: 10, color: Colors.black54),
                                ),
                              ],
                            ),

                            // Specialties tags
                            if (specialties.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Wrap(
                                spacing: 4,
                                runSpacing: 4,
                                children: specialties.map((s) {
                                  return Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                                    decoration: BoxDecoration(
                                      color: Colors.grey.shade100,
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(s, style: const TextStyle(fontSize: 9.5, color: Colors.black87)),
                                  );
                                }).toList(),
                              ),
                            ],

                            // Bio preview
                            if (bio.isNotEmpty) ...[
                              const SizedBox(height: 6),
                              Text(
                                bio,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 10, color: Colors.black54, height: 1.4),
                              ),
                            ],

                            // Action buttons
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: () => _openInquiryModal(sc),
                                    icon: const Icon(Icons.help_outline_rounded, size: 15),
                                    label: const Text('طرح استفتاء', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                                    style: OutlinedButton.styleFrom(
                                      foregroundColor: EttehadColors.primary,
                                      side: const BorderSide(color: EttehadColors.primary),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                      padding: const EdgeInsets.symmetric(vertical: 8),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: ElevatedButton.icon(
                                    onPressed: () => _openScholarChat(sc),
                                    icon: const Icon(Icons.chat_bubble_outline_rounded, size: 15),
                                    label: const Text('گفتگوی مستقیم', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: EttehadColors.navy,
                                      foregroundColor: Colors.white,
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                      padding: const EdgeInsets.symmetric(vertical: 8),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
        ),
      ],
    );
  }

  Widget _sortChip(String key, String label, IconData icon) {
    final isSelected = _sortMode == key;
    return InkWell(
      onTap: () => setState(() => _sortMode = key),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: isSelected ? EttehadColors.emeraldDark : Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isSelected ? EttehadColors.emeraldDark : Colors.grey.shade300),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 11, color: isSelected ? Colors.white : Colors.black54),
            const SizedBox(width: 3),
            Text(
              label,
              style: TextStyle(
                fontSize: 9,
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
