import 'package:flutter/material.dart';
import '../../../data/ettehad_repository.dart';
import '../../core/theme.dart';

class EttehadProfileSetupCard extends StatefulWidget {
  final EttehadRepository repo;
  final VoidCallback onComplete;
  final VoidCallback? onSkip;
  final bool isInitialSetup;

  const EttehadProfileSetupCard({
    super.key,
    required this.repo,
    required this.onComplete,
    this.onSkip,
    this.isInitialSetup = true,
  });

  @override
  State<EttehadProfileSetupCard> createState() => _EttehadProfileSetupCardState();
}

class _EttehadProfileSetupCardState extends State<EttehadProfileSetupCard> {
  late final TextEditingController _fullNameCtrl;
  late final TextEditingController _mosqueNameCtrl;
  late final TextEditingController _mosqueAddressCtrl;

  late int _avatarIndex;
  late String _selectedMadhhab;
  late String _selectedKnowledgeLevel;
  late String _selectedEducation;
  late bool _isScholarRole;
  late final Set<String> _selectedInterests;

  bool _isLoading = false;
  String? _errorMessage;

  static const List<Map<String, dynamic>> _avatarList = [
    {'icon': Icons.person_rounded, 'label': 'پژوهشگر'},
    {'icon': Icons.school_rounded, 'label': 'دانش‌پژوه'},
    {'icon': Icons.mosque_rounded, 'label': 'عالم دینی'},
    {'icon': Icons.menu_book_rounded, 'label': 'قرآن‌پژوه'},
    {'icon': Icons.history_edu_rounded, 'label': 'حدیث‌شناس'},
    {'icon': Icons.account_balance_rounded, 'label': 'استاد'},
  ];

  static const List<String> _madhhabOptions = [
    'شیعه اثناعشری',
    'اهل سنت (حنفی)',
    'اهل سنت (شافعی)',
    'تقریب و تطبیق مذاهب اسلامی',
  ];

  static const List<Map<String, String>> _knowledgeLevels = [
    {'key': 'GENERAL', 'label': 'عمومی و آزاد'},
    {'key': 'ACADEMIC', 'label': 'دانشگاهی'},
    {'key': 'SEMINARY', 'label': 'حوزوی و طلبگی'},
  ];

  static const List<Map<String, dynamic>> _defaultInterests = [
    {'id': 'tafsir', 'title': 'تفسیر و علوم قرآن', 'icon': Icons.menu_book_rounded},
    {'id': 'fiqh', 'title': 'فقه مقارن و احکام', 'icon': Icons.balance_rounded},
    {'id': 'akhlaq', 'title': 'اخلاق و خودسازی', 'icon': Icons.spa_rounded},
    {'id': 'hadith', 'title': 'حدیث و روایات نبوی', 'icon': Icons.format_quote_rounded},
    {'id': 'kalam', 'title': 'کلام و عقاید اسلامی', 'icon': Icons.psychology_rounded},
    {'id': 'history', 'title': 'تاریخ اسلام و سیره', 'icon': Icons.history_edu_rounded},
    {'id': 'wahdat', 'title': 'تقریب و وحدت اسلامی', 'icon': Icons.handshake_rounded},
    {'id': 'shobahat', 'title': 'پاسخ به شبهات و گفتگو', 'icon': Icons.help_outline_rounded},
  ];

  late List<Map<String, dynamic>> _allInterests;

  @override
  void initState() {
    super.initState();
    _allInterests = List<Map<String, dynamic>>.from(_defaultInterests);
    _loadDynamicPresets();

    final currentName = widget.repo.userFullName;
    _fullNameCtrl = TextEditingController(
      text: (currentName.startsWith('کاربر ') || currentName == 'پژوهشگر گرامی اتحاد') ? '' : currentName,
    );
    _mosqueNameCtrl = TextEditingController(text: widget.repo.mosqueName ?? '');
    _mosqueAddressCtrl = TextEditingController(text: widget.repo.mosqueAddress ?? '');

    _avatarIndex = int.tryParse(widget.repo.userAvatar) ?? 0;
    if (_avatarIndex < 0 || _avatarIndex >= _avatarList.length) _avatarIndex = 0;

    _selectedMadhhab = widget.repo.userMadhhab.isNotEmpty ? widget.repo.userMadhhab : 'شیعه اثناعشری';
    _selectedKnowledgeLevel = widget.repo.userKnowledgeLevel.isNotEmpty ? widget.repo.userKnowledgeLevel : 'GENERAL';
    _selectedEducation = widget.repo.userEducation.isNotEmpty ? widget.repo.userEducation : 'دانشگاهی';
    _isScholarRole = widget.repo.userRole == 'SCHOLAR';

    _selectedInterests = Set<String>.from(widget.repo.userInterests);
    if (_selectedInterests.isEmpty) {
      _selectedInterests.addAll(['تفسیر و علوم قرآن', 'فقه مقارن و احکام', 'اخلاق و خودسازی']);
    }
  }

  Future<void> _loadDynamicPresets() async {
    final data = await widget.repo.fetchInterestsAndPresets();
    if (data != null && mounted) {
      final cats = data['interestCategories'];
      if (cats is List && cats.isNotEmpty) {
        final List<Map<String, dynamic>> serverList = [];
        for (final item in cats) {
          if (item is Map) {
            final title = (item['title'] ?? item['name'] ?? '').toString();
            if (title.isNotEmpty) {
              final iconName = (item['iconName'] ?? item['icon'] ?? '').toString();
              IconData icon = Icons.bookmark_border_rounded;
              if (iconName.contains('book')) {
                icon = Icons.menu_book_rounded;
              } else if (iconName.contains('self_improvement') || iconName.contains('spa')) {
                icon = Icons.spa_rounded;
              } else if (iconName.contains('gavel') || iconName.contains('balance')) {
                icon = Icons.balance_rounded;
              } else if (iconName.contains('psychology')) {
                icon = Icons.psychology_rounded;
              } else if (iconName.contains('history')) {
                icon = Icons.history_edu_rounded;
              } else if (iconName.contains('family')) {
                icon = Icons.family_restroom_rounded;
              } else if (iconName.contains('quote') || iconName.contains('hadith')) {
                icon = Icons.format_quote_rounded;
              }

              serverList.add({
                'id': (item['id'] ?? title).toString(),
                'title': title,
                'icon': icon,
              });
            }
          }
        }
        if (serverList.isNotEmpty) {
          setState(() {
            _allInterests = serverList;
          });
        }
      }
    }
  }

  @override
  void dispose() {
    _fullNameCtrl.dispose();
    _mosqueNameCtrl.dispose();
    _mosqueAddressCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleSave() async {
    final name = _fullNameCtrl.text.trim();
    if (name.isEmpty) {
      setState(() => _errorMessage = 'لطفاً نام و نام‌خانوادگی خود را وارد فرمایید.');
      return;
    }

    if (_isScholarRole && _mosqueNameCtrl.text.trim().isEmpty) {
      setState(() => _errorMessage = 'لطفاً نام مسجد یا مرکز دینی خود را وارد فرمایید.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    await widget.repo.updateProfile(
      fullName: name,
      madhhab: _selectedMadhhab,
      knowledgeLevel: _selectedKnowledgeLevel,
      education: _selectedEducation,
      interests: _selectedInterests.toList(),
      avatar: _avatarIndex.toString(),
      role: _isScholarRole ? 'SCHOLAR' : 'SEEKER',
      mosqueName: _isScholarRole ? _mosqueNameCtrl.text.trim() : null,
      mosqueAddress: _isScholarRole ? _mosqueAddressCtrl.text.trim() : null,
    );

    if (!mounted) return;
    setState(() => _isLoading = false);
    widget.onComplete();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Card Header Banner
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [EttehadColors.navy, EttehadColors.primary],
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
            ),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: EttehadColors.navy.withValues(alpha: 0.2),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.manage_accounts_rounded, color: Colors.amberAccent, size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.isInitialSetup ? 'تکمیل و شخصی‌سازی پروفایل' : 'ویرایش اطلاعات و شخصی‌سازی',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15),
                    ),
                    const SizedBox(height: 3),
                    const Text(
                      'سامانه معارفی اتحاد مطابق گرایش، علایق و سطح علمی شما تطبیق می‌یابد.',
                      style: TextStyle(color: Colors.white70, fontSize: 11, height: 1.4),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),

        // Error message if any
        if (_errorMessage != null)
          Container(
            margin: const EdgeInsets.only(bottom: 14),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFFEE2E2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFEF4444)),
            ),
            child: Row(
              children: [
                const Icon(Icons.error_outline_rounded, color: Color(0xFFB91C1C), size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _errorMessage!,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF991B1B)),
                  ),
                ),
              ],
            ),
          ),

        // Section 1: Choose Avatar
        const Text(
          'انتخاب نمایه و تصویر کاربری',
          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 72,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: _avatarList.length,
            separatorBuilder: (_, _) => const SizedBox(width: 10),
            itemBuilder: (ctx, index) {
              final item = _avatarList[index];
              final isSelected = _avatarIndex == index;
              return GestureDetector(
                onTap: () => setState(() => _avatarIndex = index),
                child: Column(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isSelected ? EttehadColors.primary : EttehadColors.surfaceLow,
                        border: Border.all(
                          color: isSelected ? EttehadColors.navy : EttehadColors.border,
                          width: isSelected ? 2.5 : 1.0,
                        ),
                        boxShadow: isSelected
                            ? [
                                BoxShadow(
                                  color: EttehadColors.primary.withValues(alpha: 0.3),
                                  blurRadius: 8,
                                  offset: const Offset(0, 3),
                                )
                              ]
                            : null,
                      ),
                      child: Icon(
                        item['icon'] as IconData,
                        color: isSelected ? Colors.white : EttehadColors.navy,
                        size: 24,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item['label'] as String,
                      style: TextStyle(
                        fontSize: 9.5,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        color: isSelected ? EttehadColors.primary : Colors.black54,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 16),

        // Section 2: Full Name
        const Text(
          'نام و نام‌خانوادگی',
          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: _fullNameCtrl,
          textDirection: TextDirection.rtl,
          decoration: InputDecoration(
            hintText: 'مثال: علی رضایی یا دکتر مصطفوی',
            prefixIcon: const Icon(Icons.badge_outlined, color: EttehadColors.primary),
            filled: true,
            fillColor: EttehadColors.surfaceLow,
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: EttehadColors.primary, width: 2),
            ),
          ),
        ),
        const SizedBox(height: 16),

        // Section 3: User Role
        const Text(
          'نقش و سطح فعالیت در سامانه اتحاد',
          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _roleCard(
                title: 'پژوهشگر معارفی',
                subtitle: 'مطالعه کتب، قرآن و طرح پرسش',
                icon: Icons.person_search_rounded,
                selected: !_isScholarRole,
                onTap: () => setState(() => _isScholarRole = false),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _roleCard(
                title: 'عالم دینی / امام جماعت',
                subtitle: 'پاسخ‌گویی به استفتائات مساجد',
                icon: Icons.mosque_rounded,
                selected: _isScholarRole,
                onTap: () => setState(() => _isScholarRole = true),
              ),
            ),
          ],
        ),

        // Mosque fields if scholar
        if (_isScholarRole) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFFEF3C7),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFFF59E0B)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.info_outline_rounded, size: 16, color: Color(0xFFB45309)),
                    SizedBox(width: 6),
                    Text(
                      'مشخصات مسجد / مرکز تبلیغی جهت ارتباط با مؤمنین:',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF92400E)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _mosqueNameCtrl,
                  decoration: InputDecoration(
                    hintText: 'نام مسجد (مثال: مسجد جامع النبی)',
                    prefixIcon: const Icon(Icons.location_city_rounded, color: EttehadColors.primary, size: 20),
                    filled: true,
                    fillColor: Colors.white,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _mosqueAddressCtrl,
                  decoration: InputDecoration(
                    hintText: 'آدرس، شهر یا منطقه مسجد',
                    prefixIcon: const Icon(Icons.place_rounded, color: EttehadColors.primary, size: 20),
                    filled: true,
                    fillColor: Colors.white,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  ),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 16),

        // Section 4: Madhhab and Fiqh Approach
        const Text(
          'رویکرد و مذهب فقهی پیش‌فرض',
          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _madhhabOptions.map((m) {
            final isSelected = _selectedMadhhab == m;
            return ChoiceChip(
              label: Text(m),
              selected: isSelected,
              selectedColor: EttehadColors.primary,
              backgroundColor: Colors.white,
              labelStyle: TextStyle(
                fontSize: 11.5,
                fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                color: isSelected ? Colors.white : EttehadColors.navy,
              ),
              side: BorderSide(color: isSelected ? EttehadColors.primary : EttehadColors.border),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              onSelected: (_) => setState(() => _selectedMadhhab = m),
            );
          }).toList(),
        ),
        const SizedBox(height: 16),

        // Section 5: Knowledge Level
        const Text(
          'سطح علمی و تحصیلی',
          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
        ),
        const SizedBox(height: 8),
        Row(
          children: _knowledgeLevels.map((lvl) {
            final isSelected = _selectedKnowledgeLevel == lvl['key'];
            return Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: ChoiceChip(
                  label: Center(child: Text(lvl['label']!)),
                  selected: isSelected,
                  selectedColor: EttehadColors.primary,
                  backgroundColor: Colors.white,
                  labelStyle: TextStyle(
                    fontSize: 11,
                    fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                    color: isSelected ? Colors.white : EttehadColors.navy,
                  ),
                  side: BorderSide(color: isSelected ? EttehadColors.primary : EttehadColors.border),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  onSelected: (_) => setState(() => _selectedKnowledgeLevel = lvl['key']!),
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 16),

        // Section 6: Subject Interests (Multi-Select)
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'علایق موضوعی و پژوهشی معارفی',
              style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
            ),
            Text(
              '${_selectedInterests.length} مورد انتخاب شده',
              style: const TextStyle(fontSize: 10.5, color: EttehadColors.primary, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 7,
          runSpacing: 7,
          children: _allInterests.map((interest) {
            final title = interest['title'] as String;
            final isSelected = _selectedInterests.contains(title);
            return FilterChip(
              avatar: Icon(
                interest['icon'] as IconData,
                size: 15,
                color: isSelected ? Colors.white : EttehadColors.primary,
              ),
              label: Text(title),
              selected: isSelected,
              showCheckmark: false,
              selectedColor: EttehadColors.primary,
              backgroundColor: Colors.white,
              labelStyle: TextStyle(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w900 : FontWeight.w500,
                color: isSelected ? Colors.white : EttehadColors.navy,
              ),
              side: BorderSide(color: isSelected ? EttehadColors.primary : EttehadColors.border),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              onSelected: (selected) {
                setState(() {
                  if (selected) {
                    _selectedInterests.add(title);
                  } else {
                    if (_selectedInterests.length > 1) {
                      _selectedInterests.remove(title);
                    }
                  }
                });
              },
            );
          }).toList(),
        ),
        const SizedBox(height: 24),

        // Submit Button
        ElevatedButton(
          onPressed: _isLoading ? null : _handleSave,
          style: ElevatedButton.styleFrom(
            backgroundColor: EttehadColors.primary,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            elevation: 2,
          ),
          child: _isLoading
              ? const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                )
              : Text(
                  widget.isInitialSetup ? 'ذخیره مشخصات و ورود به کتابخوان اتحاد' : 'ذخیره و به‌روزرسانی مشخصات',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5),
                ),
        ),

        // Skip Button (if initial onboarding)
        if (widget.isInitialSetup && widget.onSkip != null) ...[
          const SizedBox(height: 8),
          Center(
            child: TextButton(
              onPressed: widget.onSkip,
              child: const Text(
                'تکمیل در آینده و ورود مستقیم به برنامه',
                style: TextStyle(fontSize: 12, color: Colors.black54, fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _roleCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: selected ? EttehadColors.primary.withValues(alpha: 0.08) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected ? EttehadColors.primary : EttehadColors.border,
            width: selected ? 2.0 : 1.0,
          ),
        ),
        child: Column(
          children: [
            Icon(icon, color: selected ? EttehadColors.primary : Colors.black45, size: 24),
            const SizedBox(height: 6),
            Text(
              title,
              style: TextStyle(
                fontSize: 11,
                fontWeight: selected ? FontWeight.w900 : FontWeight.bold,
                color: selected ? EttehadColors.primary : EttehadColors.navy,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: const TextStyle(fontSize: 9, color: Colors.black54),
              textAlign: TextAlign.center,
              maxLines: 1,
            ),
          ],
        ),
      ),
    );
  }
}
