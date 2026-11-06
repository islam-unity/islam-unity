import 'package:flutter/material.dart';
import '../../../data/ettehad_repository.dart';
import '../../core/theme.dart';
import '../auth/auth_modal.dart';
import '../auth/profile_setup_card.dart';

void showEttehadUserProfile(BuildContext context, EttehadRepository repo) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) => Directionality(
      textDirection: TextDirection.rtl,
      child: _ProfileSheetWidget(repo: repo),
    ),
  );
}

class _ProfileSheetWidget extends StatefulWidget {
  final EttehadRepository repo;
  const _ProfileSheetWidget({required this.repo});

  @override
  State<_ProfileSheetWidget> createState() => _ProfileSheetWidgetState();
}

class _ProfileSheetWidgetState extends State<_ProfileSheetWidget> {
  late bool _isScholarRole;
  bool _darkMode = false;
  bool _adhanNotifications = true;
  late String _selectedMadhhab;
  late int _avatarIndex;
  bool _isEditingProfile = false;

  static const List<IconData> _avatarIcons = [
    Icons.person_rounded,
    Icons.school_rounded,
    Icons.mosque_rounded,
    Icons.menu_book_rounded,
    Icons.history_edu_rounded,
    Icons.account_balance_rounded,
  ];

  @override
  void initState() {
    super.initState();
    _isScholarRole = widget.repo.userRole == 'SCHOLAR';
    _selectedMadhhab = widget.repo.userMadhhab.isNotEmpty ? widget.repo.userMadhhab : 'شیعه اثناعشری';
    _avatarIndex = int.tryParse(widget.repo.userAvatar) ?? 0;
    if (_avatarIndex < 0 || _avatarIndex >= _avatarIcons.length) _avatarIndex = 0;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.92,
      decoration: const BoxDecoration(
        color: EttehadColors.paper,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        children: [
          // Drag Handle
          const SizedBox(height: 10),
          Center(
            child: Container(
              width: 40,
              height: 4.5,
              decoration: BoxDecoration(
                color: Colors.black26,
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),

          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: EttehadColors.primary.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        _isEditingProfile ? Icons.edit_note_rounded : Icons.manage_accounts_rounded,
                        color: EttehadColors.primary,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      _isEditingProfile ? 'ویرایش و شخصی‌سازی پروفایل' : 'پروفایل و شخصی‌سازی',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                    ),
                  ],
                ),
                Row(
                  children: [
                    if (_isEditingProfile)
                      TextButton.icon(
                        onPressed: () => setState(() => _isEditingProfile = false),
                        icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                        label: const Text('انصراف', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, color: Colors.black54),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Body Content
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 30),
              children: [
                if (_isEditingProfile) ...[
                  EttehadProfileSetupCard(
                    repo: widget.repo,
                    isInitialSetup: false,
                    onComplete: () {
                      setState(() {
                        _isEditingProfile = false;
                        _isScholarRole = widget.repo.userRole == 'SCHOLAR';
                        _selectedMadhhab = widget.repo.userMadhhab;
                        _avatarIndex = int.tryParse(widget.repo.userAvatar) ?? 0;
                        if (_avatarIndex < 0 || _avatarIndex >= _avatarIcons.length) _avatarIndex = 0;
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('مشخصات کاربری با موفقیت به‌روزرسانی شد.'),
                          backgroundColor: Color(0xFF10B981),
                          behavior: SnackBarBehavior.floating,
                        ),
                      );
                    },
                    onSkip: () => setState(() => _isEditingProfile = false),
                  ),
                ] else ...[
                  // Pending Scholar Banner (if scholar role is active)
                  if (_isScholarRole)
                    Container(
                      margin: const EdgeInsets.only(bottom: 14),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFEF3C7),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0xFFF59E0B), width: 1.5),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.hourglass_top_rounded, color: Color(0xFFB45309), size: 22),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    const Text(
                                      'درخواست عضویت عالم دینی',
                                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: Color(0xFF78350F)),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFFDE68A),
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: const Text('در انتظار احراز', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: Color(0xFF92400E))),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  widget.repo.mosqueName != null && widget.repo.mosqueName!.isNotEmpty
                                      ? 'مشخصات شما برای فعالیت در ${widget.repo.mosqueName} ثبت شده است. پس از تأیید مدیریت، دسترسی میز پاسخ‌گویی فعال می‌شود.'
                                      : 'مشخصات شما برای فعالیت در مسجد و پاسخ‌گویی به استفتائات ثبت شده است. پس از تأیید در پنل مدیریت، میز کار تخصصی شما فعال خواهد شد.',
                                  style: const TextStyle(fontSize: 10.5, color: Color(0xFF92400E), height: 1.5),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),

                  // User Identity Card
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [EttehadColors.navy, EttehadColors.primary, Color(0xFF09152B)],
                        begin: Alignment.topRight,
                        end: Alignment.bottomLeft,
                      ),
                      borderRadius: BorderRadius.circular(22),
                      boxShadow: [
                        BoxShadow(
                          color: EttehadColors.navy.withValues(alpha: 0.25),
                          blurRadius: 14,
                          offset: const Offset(0, 5),
                        ),
                      ],
                    ),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            GestureDetector(
                              onTap: () {
                                setState(() {
                                  _avatarIndex = (_avatarIndex + 1) % _avatarIcons.length;
                                });
                                widget.repo.updateProfile(avatar: _avatarIndex.toString());
                              },
                              child: Stack(
                                children: [
                                  CircleAvatar(
                                    radius: 28,
                                    backgroundColor: Colors.white.withValues(alpha: 0.2),
                                    child: Icon(_avatarIcons[_avatarIndex], color: Colors.amberAccent, size: 32),
                                  ),
                                  Positioned(
                                    bottom: 0,
                                    right: 0,
                                    child: Container(
                                      padding: const EdgeInsets.all(3),
                                      decoration: const BoxDecoration(
                                        color: EttehadColors.mint,
                                        shape: BoxShape.circle,
                                      ),
                                      child: const Icon(Icons.refresh_rounded, size: 12, color: EttehadColors.navy),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          widget.repo.isLoggedIn ? widget.repo.userFullName : 'مهمان گرامی (وارد نشده)',
                                          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: Colors.white),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      const SizedBox(width: 6),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: EttehadColors.mint,
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Text(
                                          _isScholarRole ? 'عالم دینی' : 'پژوهشگر',
                                          style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    widget.repo.isLoggedIn
                                        ? 'شماره تماس: ${widget.repo.userPhoneNumber ?? "نامشخص"}'
                                        : 'جهت همگام‌سازی یادداشت‌ها و ذخیره کتاب‌ها وارد شوید',
                                    style: const TextStyle(fontSize: 11, color: Colors.white70),
                                  ),
                                  const SizedBox(height: 6),
                                  Wrap(
                                    spacing: 6,
                                    runSpacing: 4,
                                    children: [
                                      _tagPill(_selectedMadhhab),
                                      _tagPill(widget.repo.userKnowledgeLevel == 'SEMINARY'
                                          ? 'سطح حوزوی'
                                          : (widget.repo.userKnowledgeLevel == 'ACADEMIC' ? 'سطح دانشگاهی' : 'سطح عمومی')),
                                      ...widget.repo.userInterests.take(2).map((item) => _tagPill(item)),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),

                        // Action Buttons: Edit Profile and Auth/Logout
                        Row(
                          children: [
                            if (widget.repo.isLoggedIn) ...[
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: () => setState(() => _isEditingProfile = true),
                                  icon: const Icon(Icons.tune_rounded, size: 15, color: Colors.white),
                                  label: const Text(
                                    'ویرایش مشخصات',
                                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
                                  ),
                                  style: OutlinedButton.styleFrom(
                                    side: const BorderSide(color: Colors.white38),
                                    padding: const EdgeInsets.symmetric(vertical: 8),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                            ],
                            Expanded(
                              child: ElevatedButton.icon(
                                onPressed: () {
                                  if (widget.repo.isLoggedIn) {
                                    widget.repo.logout();
                                    setState(() {
                                      _isScholarRole = false;
                                      _avatarIndex = 0;
                                    });
                                  } else {
                                    showEttehadAuthModal(context, widget.repo, onSuccess: () {
                                      setState(() {
                                        _isScholarRole = widget.repo.userRole == 'SCHOLAR';
                                        _selectedMadhhab = widget.repo.userMadhhab;
                                        _avatarIndex = int.tryParse(widget.repo.userAvatar) ?? 0;
                                        if (_avatarIndex < 0 || _avatarIndex >= _avatarIcons.length) _avatarIndex = 0;
                                      });
                                    });
                                  }
                                },
                                icon: Icon(
                                  widget.repo.isLoggedIn ? Icons.logout_rounded : Icons.login_rounded,
                                  size: 15,
                                  color: widget.repo.isLoggedIn ? Colors.redAccent : EttehadColors.navy,
                                ),
                                label: Text(
                                  widget.repo.isLoggedIn ? 'خروج از حساب' : 'ورود / ثبت‌نام با پیامک',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: widget.repo.isLoggedIn ? Colors.redAccent : EttehadColors.navy,
                                  ),
                                ),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.white,
                                  foregroundColor: EttehadColors.navy,
                                  padding: const EdgeInsets.symmetric(vertical: 8),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                  elevation: 0,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const Divider(color: Colors.white24, height: 24),

                        // Role Switcher Bar
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              'نقش فعال در سامانه:',
                              style: TextStyle(color: Colors.white70, fontSize: 11.5),
                            ),
                            Container(
                              padding: const EdgeInsets.all(3),
                              decoration: BoxDecoration(
                                color: Colors.black26,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Row(
                                children: [
                                  _roleOptionBtn('کاربر عادی', !_isScholarRole, () {
                                    setState(() => _isScholarRole = false);
                                    widget.repo.updateProfile(role: 'SEEKER');
                                  }),
                                  _roleOptionBtn('عالم دینی', _isScholarRole, () {
                                    setState(() => _isScholarRole = true);
                                    widget.repo.updateProfile(role: 'SCHOLAR');
                                  }),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // 4 Reading & Activity Stats
                  Builder(
                    builder: (context) {
                      final readBooksCount = widget.repo.readBooksCount;
                      final notesCount = widget.repo.totalBookBookmarksCount;
                      final inquiriesCount = widget.repo.scholarChats.length;
                      final lastAyahNum = widget.repo.lastReadAyah;

                      return Row(
                        children: [
                          _statCard('کتب فعال و نشان', '${toPersianDigits(readBooksCount)} اثر', Icons.local_library_rounded, Colors.blue),
                          const SizedBox(width: 8),
                          _statCard('استفتائات من', '${toPersianDigits(inquiriesCount)} گفتگو', Icons.question_answer_rounded, Colors.amber),
                          const SizedBox(width: 8),
                          _statCard('فیش و نشان‌ها', '${toPersianDigits(notesCount)} مورد', Icons.edit_note_rounded, Colors.teal),
                          const SizedBox(width: 8),
                          _statCard('آخرین آیه مطالعه', 'آیه ${toPersianDigits(lastAyahNum)}', Icons.bookmark_added_rounded, Colors.indigo),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 20),

                  // Madhhab Selector
                  const Text(
                    'رویکرد فقهی و مذهبی پیش‌فرض',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: EttehadColors.border),
                    ),
                    child: Column(
                      children: [
                        _madhhabRadioTile('شیعه اثناعشری'),
                        const Divider(height: 12),
                        _madhhabRadioTile('اهل سنت (حنفی)'),
                        const Divider(height: 12),
                        _madhhabRadioTile('اهل سنت (شافعی)'),
                        const Divider(height: 12),
                        _madhhabRadioTile('تقریب و تطبیق مذاهب اسلامی'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Settings & Preferences
                  const Text(
                    'تنظیمات برنامه و شخصی‌سازی',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: EttehadColors.border),
                    ),
                    child: Column(
                      children: [
                        SwitchListTile(
                          dense: true,
                          secondary: const Icon(Icons.dark_mode_rounded, color: EttehadColors.navy),
                          title: const Text('حالت شب و مطالعه تاریک', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                          subtitle: const Text('کاهش نور صفحه برای آسایش چشم در شب', style: TextStyle(fontSize: 10.5)),
                          value: _darkMode,
                          onChanged: (v) => setState(() => _darkMode = v),
                        ),
                        const Divider(height: 1),
                        SwitchListTile(
                          dense: true,
                          secondary: const Icon(Icons.notifications_active_rounded, color: EttehadColors.navy),
                          title: const Text('اعلان اوقات شرعی و اذان', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                          subtitle: const Text('یادآوری ۵ نوبت نماز یومیه', style: TextStyle(fontSize: 10.5)),
                          value: _adhanNotifications,
                          onChanged: (v) => setState(() => _adhanNotifications = v),
                        ),
                        const Divider(height: 1),
                        ListTile(
                          dense: true,
                          leading: const Icon(Icons.storage_rounded, color: EttehadColors.navy),
                          title: const Text('وضعیت مخزن آفلاین', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold)),
                          subtitle: Text(
                            '${toPersianDigits(widget.repo.surahs.length)} سوره کامل • ${toPersianDigits(widget.repo.books.length)} کتاب مرجع • ۱۰۰٪ آفلاین',
                            style: const TextStyle(fontSize: 10.5, color: Colors.green),
                          ),
                          trailing: const Icon(Icons.check_circle_rounded, color: Colors.green, size: 20),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // App Info & Version
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: EttehadColors.surfaceLow,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Image.asset('assets/images/app_icon.png', width: 26, height: 26),
                            const SizedBox(width: 8),
                            const Text(
                              'سامانه معارفی و کتابخوان «اتحاد»',
                              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.navy),
                            ),
                          ],
                        ),
                        const Text(
                          'نسخه ۲.۰.۰ نیتیو',
                          style: TextStyle(fontSize: 10, color: Colors.black54, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _statCard(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: EttehadColors.border),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 18),
            const SizedBox(height: 4),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 11, color: EttehadColors.navy)),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(fontSize: 8.5, color: Colors.black54), textAlign: TextAlign.center, maxLines: 1),
          ],
        ),
      ),
    );
  }

  Widget _tagPill(String title) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white12),
      ),
      child: Text(title, style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.bold)),
    );
  }

  Widget _roleOptionBtn(String text, bool active, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: active ? Colors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          text,
          style: TextStyle(
            fontSize: 10.5,
            fontWeight: active ? FontWeight.w900 : FontWeight.w600,
            color: active ? EttehadColors.primary : Colors.white70,
          ),
        ),
      ),
    );
  }

  Widget _madhhabRadioTile(String name) {
    final selected = _selectedMadhhab == name;
    return InkWell(
      onTap: () {
        setState(() => _selectedMadhhab = name);
        widget.repo.updateProfile(madhhab: name);
      },
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(name, style: TextStyle(fontSize: 12, fontWeight: selected ? FontWeight.w900 : FontWeight.w500, color: selected ? EttehadColors.primary : EttehadColors.navy)),
          Icon(selected ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded, color: selected ? EttehadColors.primary : Colors.black38, size: 18),
        ],
      ),
    );
  }
}
