import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';
import 'scholar_picker_modal.dart';
import 'book_excerpt_picker_modal.dart';

class NewInquiryModal extends StatefulWidget {
  final EttehadRepository repo;
  final Map<String, dynamic>? initialScholar;
  final VoidCallback? onInquiryCreated;

  const NewInquiryModal({
    super.key,
    required this.repo,
    this.initialScholar,
    this.onInquiryCreated,
  });

  static void show(
    BuildContext context,
    EttehadRepository repo, {
    Map<String, dynamic>? targetScholar,
    VoidCallback? onInquiryCreated,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => NewInquiryModal(
        repo: repo,
        initialScholar: targetScholar,
        onInquiryCreated: onInquiryCreated,
      ),
    );
  }

  @override
  State<NewInquiryModal> createState() => _NewInquiryModalState();
}

class _NewInquiryModalState extends State<NewInquiryModal> {
  final TextEditingController _titleCtrl = TextEditingController();
  final TextEditingController _bodyCtrl = TextEditingController();

  String _selectedMadhhab = 'تطبیقی و مشترک (رویکرد تقریب فریقین)';
  String? _selectedScholarId;
  bool _isAnonymous = false;
  Map<String, dynamic>? _attachedBookExcerpt;

  // Audio recording state simulation
  bool _isRecording = false;
  bool _hasRecordedAudio = false;
  bool _isPlayingAudio = false;
  int _recordSeconds = 0;
  Timer? _recordTimer;

  final List<String> _madhhabOptions = [
    'تطبیقی و مشترک (رویکرد تقریب فریقین)',
    'شیعه اثناعشری (فقه جعفری)',
    'اهل سنت (فقه حنفی)',
    'اهل سنت (فقه شافعی)',
  ];

  @override
  void initState() {
    super.initState();
    if (widget.initialScholar != null) {
      _selectedScholarId = widget.initialScholar!['id']?.toString();
      _syncMadhhabFromScholar(widget.initialScholar!);
    } else if (widget.repo.scholars.isNotEmpty) {
      _selectedScholarId = widget.repo.scholars.first['id']?.toString();
      _syncMadhhabFromScholar(widget.repo.scholars.first);
    }
  }

  void _syncMadhhabFromScholar(Map<String, dynamic> sc) {
    final m = (sc['madhhab'] ?? '').toString();
    if (m.contains('شیعه')) {
      _selectedMadhhab = 'شیعه اثناعشری (فقه جعفری)';
    } else if (m.contains('حنفی')) {
      _selectedMadhhab = 'اهل سنت (فقه حنفی)';
    } else if (m.contains('شافعی')) {
      _selectedMadhhab = 'اهل سنت (فقه شافعی)';
    } else {
      _selectedMadhhab = 'تطبیقی و مشترک (رویکرد تقریب فریقین)';
    }
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _bodyCtrl.dispose();
    _recordTimer?.cancel();
    super.dispose();
  }

  void _toggleRecording() {
    if (_isRecording) {
      // Stop recording
      _recordTimer?.cancel();
      setState(() {
        _isRecording = false;
        _hasRecordedAudio = true;
      });
    } else {
      // Start recording
      setState(() {
        _isRecording = true;
        _hasRecordedAudio = false;
        _isPlayingAudio = false;
        _recordSeconds = 0;
      });
      _recordTimer?.cancel();
      _recordTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (!mounted) return;
        setState(() {
          _recordSeconds++;
          if (_recordSeconds >= 120) {
            _toggleRecording();
          }
        });
      });
    }
  }

  void _deleteAudio() {
    setState(() {
      _hasRecordedAudio = false;
      _isPlayingAudio = false;
      _recordSeconds = 0;
    });
  }

  Future<void> _submitInquiry() async {
    final title = _titleCtrl.text.trim();
    final body = _bodyCtrl.text.trim();

    if (_selectedScholarId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('لطفاً عالم مورد نظر خود را جهت ارسال مستقیم سوال انتخاب فرمایید.'),
          backgroundColor: EttehadColors.amberDark,
        ),
      );
      return;
    }

    if (title.isEmpty && !_hasRecordedAudio) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('لطفاً عنوان سوال را وارد کرده یا پیام صوتی ضبط نمایید.'),
          backgroundColor: EttehadColors.amberDark,
        ),
      );
      return;
    }

    final targetScholar = widget.repo.scholars.firstWhere(
      (s) => s['id']?.toString() == _selectedScholarId,
      orElse: () => widget.repo.scholars.isNotEmpty
          ? widget.repo.scholars.first
          : {'id': 'scholar_1', 'name': 'استاد منتخب میز استفتائات'},
    );

    final textContent = body.isNotEmpty
        ? body
        : (_hasRecordedAudio ? '«پرسش به همراه صوت ضمیمه ارسال شد»' : title);

    final attachedBook = _attachedBookExcerpt;

    // Send real consultation thread request to Backend API (api.unitysi.ir)
    final serverRes = await widget.repo.createConsultationThread(
      title: title.isNotEmpty ? title : 'پرسش و استفتاء معارفی',
      body: textContent,
      category: _selectedMadhhab,
      targetScholarId: _selectedScholarId,
      isAnonymous: _isAnonymous,
      bookReference: attachedBook,
    );

    final trackingCode = serverRes['trackingCode']?.toString() ?? 'ETH-Q-${10000 + Random().nextInt(89999)}';
    final threadId = serverRes['threadId']?.toString();

    final newChat = {
      'thread_id': threadId,
      'scholar': targetScholar,
      'tracking_code': trackingCode,
      'madhhab': _selectedMadhhab,
      'is_anonymous': _isAnonymous,
      'has_audio': _hasRecordedAudio,
      'audio_duration': _hasRecordedAudio ? '۰۰:${_recordSeconds.toString().padLeft(2, '0')}' : null,
      'has_book': attachedBook != null,
      'book_id': attachedBook?['bookId'],
      'book_title': attachedBook?['bookTitle'],
      'excerpt': attachedBook?['excerpt'],
      'status': serverRes['status'] ?? 'WAITING_SCHOLAR',
      'unread': 0,
      'lastMessage': attachedBook != null
          ? 'پیوست اثر «${attachedBook['bookTitle']}»: ${title.isNotEmpty ? title : textContent}'
          : (title.isNotEmpty ? title : textContent),
      'messages': [
        {
          'sender': 'user',
          'title': title.isNotEmpty ? title : 'پرسش بدون عنوان',
          'text': textContent,
          'time': 'هم‌اکنون',
          'has_audio': _hasRecordedAudio,
          'audio_duration': _hasRecordedAudio ? '۰۰:${_recordSeconds.toString().padLeft(2, '0')}' : null,
          'is_anonymous': _isAnonymous,
          if (attachedBook != null) ...{
            'bookId': attachedBook['bookId'],
            'bookTitle': attachedBook['bookTitle'],
            'excerpt': attachedBook['excerpt'],
            'source': attachedBook['source'],
          },
        },
      ],
    };

    widget.repo.addScholarChat(newChat);

    if (!mounted) return;
    Navigator.pop(context);
    widget.onInquiryCreated?.call();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('استفتاء شما مستقیماً برای ${targetScholar['name']} با کد $trackingCode ثبت شد.'),
        backgroundColor: EttehadColors.emerald,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  void _openScholarPicker() {
    ScholarPickerModal.show(
      context,
      widget.repo,
      currentScholarId: _selectedScholarId,
      onScholarSelected: (sc) {
        setState(() {
          _selectedScholarId = sc['id']?.toString();
          _syncMadhhabFromScholar(sc);
        });
      },
    );
  }

  void _openBookExcerptPicker() {
    BookExcerptPickerModal.show(
      context,
      widget.repo,
      onExcerptSelected: (excerptData) {
        setState(() {
          _attachedBookExcerpt = excerptData;
        });
      },
    );
  }

  Widget _buildBookAttachmentSection() {
    if (_attachedBookExcerpt == null) {
      return InkWell(
        onTap: _openBookExcerptPicker,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: const Color(0xFFF0FDF4),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: EttehadColors.emerald.withValues(alpha: 0.35)),
          ),
          child: const Row(
            children: [
              Icon(Icons.menu_book_rounded, color: EttehadColors.emeraldDark, size: 20),
              SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'پیوست کتاب یا گزیده متن (از کتابخانه یا تحلیل هوش مصنوعی)',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5, color: EttehadColors.emeraldDark),
                    ),
                    Text(
                      'امکان ارجاع مستقیم متن شبهه، مسئله یا فراز روایی به عالم دینی',
                      style: TextStyle(fontSize: 10, color: Colors.black54),
                    ),
                  ],
                ),
              ),
              Icon(Icons.add_circle_outline_rounded, color: EttehadColors.emeraldDark, size: 20),
            ],
          ),
        ),
      );
    }

    final bookTitle = _attachedBookExcerpt!['bookTitle'] ?? 'کتاب مرجع';
    final excerpt = (_attachedBookExcerpt!['excerpt'] ?? '').toString();
    final isAi = _attachedBookExcerpt!['source'] == 'ai';
    final sourceLabel = isAi ? 'تحلیل هوش مصنوعی' : 'کتابخانه دیجیتال';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FDF4),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: EttehadColors.emerald.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isAi ? Icons.auto_awesome_rounded : Icons.bookmark_added_rounded,
                color: isAi ? EttehadColors.amberDark : EttehadColors.emeraldDark,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'کتاب پیوست‌شده: $bookTitle',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: EttehadColors.navy),
                    ),
                    Text(
                      'منبع استناد: $sourceLabel',
                      style: TextStyle(
                        fontSize: 9.5,
                        color: isAi ? EttehadColors.amberDark : EttehadColors.emeraldDark,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.edit_note_rounded, size: 20, color: EttehadColors.primary),
                tooltip: 'تغییر کتاب یا فراز متن',
                onPressed: _openBookExcerptPicker,
              ),
              IconButton(
                icon: const Icon(Icons.close_rounded, size: 18, color: Colors.red),
                tooltip: 'حذف پیوست',
                onPressed: () => setState(() => _attachedBookExcerpt = null),
              ),
            ],
          ),
          if (excerpt.isNotEmpty) ...[
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: EttehadColors.border),
              ),
              child: Text(
                excerpt,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 10.5, color: Colors.black87, fontStyle: FontStyle.italic),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildScholarSelector() {
    final scholars = widget.repo.scholars;
    final selectedScholar = scholars.firstWhere(
      (s) => s['id']?.toString() == _selectedScholarId,
      orElse: () => scholars.isNotEmpty ? scholars.first : {},
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Expanded(
              child: Row(
                children: [
                  Icon(Icons.person_pin_rounded, color: EttehadColors.primary, size: 18),
                  SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      'انتخاب عالم دینی جهت ارسال مستقیم سوال',
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: EttehadColors.navy),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '${toPersianDigits(scholars.length)} استاد صاحب‌کرسی',
              style: const TextStyle(fontSize: 10.5, color: Colors.black54),
            ),
          ],
        ),
        const SizedBox(height: 8),

        // Advanced Filter & Search among 600 scholars
        InkWell(
          onTap: _openScholarPicker,
          borderRadius: BorderRadius.circular(14),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: EttehadColors.primary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: EttehadColors.primary.withValues(alpha: 0.25)),
            ),
            child: const Row(
              children: [
                Icon(Icons.tune_rounded, size: 18, color: EttehadColors.primary),
                SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'فیلتر پیشرفته بر اساس استان، شهر، مذهب، تخصص و مسجد',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: EttehadColors.primary),
                      ),
                      Text(
                        'جستجوی دقیق در میان بیش از ۶۰۰ عالم برجسته سراسر کشور',
                        style: TextStyle(fontSize: 9.5, color: Colors.black54),
                      ),
                    ],
                  ),
                ),
                Icon(Icons.chevron_left_rounded, size: 18, color: EttehadColors.primary),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),

        // Visual horizontal scholar picker cards
        SizedBox(
          height: 125,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: scholars.length,
            separatorBuilder: (_, _) => const SizedBox(width: 10),
            itemBuilder: (ctx, idx) {
              final sc = scholars[idx];
              final scId = sc['id']?.toString() ?? 'sc_$idx';
              final isSelected = _selectedScholarId == scId;
              final name = (sc['name'] ?? 'استاد').toString();
              final title = (sc['title'] ?? 'فقه و معارف').toString();
              final madhhab = (sc['madhhab'] ?? 'تقریب فریقین').toString();

              return InkWell(
                onTap: () {
                  setState(() {
                    _selectedScholarId = scId;
                    _syncMadhhabFromScholar(sc);
                  });
                },
                borderRadius: BorderRadius.circular(16),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 180,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: isSelected ? const Color(0xFFEFF6FF) : Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: isSelected ? EttehadColors.primary : EttehadColors.border,
                      width: isSelected ? 2.0 : 1.0,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: isSelected ? EttehadColors.primary.withValues(alpha: 0.16) : const Color(0x060A2E6E),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      )
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          CircleAvatar(
                            radius: 16,
                            backgroundColor: isSelected ? EttehadColors.primary : EttehadColors.navy,
                            child: Text(
                              name.characters.take(2).toString(),
                              style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontWeight: FontWeight.w900,
                                fontSize: 11,
                                color: isSelected ? EttehadColors.primary : EttehadColors.navy,
                              ),
                            ),
                          ),
                          if (isSelected)
                            const Icon(Icons.check_circle_rounded, color: EttehadColors.primary, size: 16),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 9.5, color: Colors.black54),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: isSelected ? Colors.white : EttehadColors.surfaceLow,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          madhhab,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            color: isSelected ? EttehadColors.primary : Colors.black87,
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

        // Selected scholar feedback confirmation strip
        if (selectedScholar.isNotEmpty) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFFF0FDF4),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFBBF7D0)),
            ),
            child: Row(
              children: [
                const Icon(Icons.verified_user_rounded, color: EttehadColors.emeraldDark, size: 14),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'سوال شما مستقیماً به دفتر ${selectedScholar['name']} ارجاع داده می‌شود.',
                    style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.emeraldDark),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: Container(
          height: MediaQuery.of(context).size.height * 0.90,
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              // Handle Bar
              Container(
                margin: const EdgeInsets.only(top: 10, bottom: 6),
                width: 44,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),

              // Title Bar
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(9),
                      decoration: BoxDecoration(
                        color: EttehadColors.amberDark.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.edit_note_rounded, color: EttehadColors.amberDark, size: 24),
                    ),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('طرح سوال و استفتاء اختصاصی', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: EttehadColors.navy)),
                          Text('ارسال مستقیم به عالم منتخب شما با امکان ضبط صدا و ارسال ناشناس', style: TextStyle(fontSize: 10.5, color: Colors.black54)),
                        ],
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close_rounded, size: 22),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),

              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    // Step 1: Explicit Scholar Selection
                    _buildScholarSelector(),
                    const SizedBox(height: 16),

                    // Step 2: Subject Field
                    const Text('موضوع یا عنوان سوال', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: EttehadColors.navy)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: _titleCtrl,
                      decoration: InputDecoration(
                        hintText: 'مثال: سوال پیرامون خمس سهام بورس یا احکام روزه مسافر',
                        filled: true,
                        fillColor: EttehadColors.surfaceLow,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: EttehadColors.border)),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: EttehadColors.border)),
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Step 3: Detailed question field
                    const Text('شرح پرسش یا متن استفتاء', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: EttehadColors.navy)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: _bodyCtrl,
                      maxLines: 4,
                      decoration: InputDecoration(
                        hintText: 'جزئیات سوال و شرایط خود را به طور کامل برای استاد بنویسید...',
                        filled: true,
                        fillColor: EttehadColors.surfaceLow,
                        contentPadding: const EdgeInsets.all(14),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: EttehadColors.border)),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: EttehadColors.border)),
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Step 4: Voice Recording Box (Requirement 3)
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: _isRecording ? Colors.red.shade50 : const Color(0xFFF8FAFC),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: _isRecording ? Colors.red.shade300 : EttehadColors.border,
                          width: _isRecording ? 1.5 : 1.0,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                _isRecording ? Icons.fiber_manual_record_rounded : Icons.mic_rounded,
                                color: _isRecording ? Colors.red : EttehadColors.primary,
                                size: 20,
                              ),
                              const SizedBox(width: 6),
                              Text(
                                _isRecording ? 'در حال ضبط پیام صوتی برای استاد...' : 'ضبط پیام صوتی (Voice Memo)',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                  color: _isRecording ? Colors.red.shade800 : EttehadColors.navy,
                                ),
                              ),
                              const Spacer(),
                              if (_isRecording)
                                Text(
                                  '۰۰:${_recordSeconds.toString().padLeft(2, '0')}',
                                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.red, fontSize: 13),
                                ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'اگر تایپ سوال برایتان دشوار است، می‌توانید پرسش خود را به صورت صوت شفاهی ضبط فرمایید.',
                            style: TextStyle(fontSize: 10.5, color: Colors.black54),
                          ),
                          const SizedBox(height: 10),

                          if (!_hasRecordedAudio) ...[
                            ElevatedButton.icon(
                              onPressed: _toggleRecording,
                              icon: Icon(_isRecording ? Icons.stop_rounded : Icons.mic_rounded, size: 18),
                              label: Text(_isRecording ? 'توقف ضبط صدا' : 'شروع ضبط صوت'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: _isRecording ? Colors.red : EttehadColors.primary,
                                foregroundColor: Colors.white,
                                elevation: 0,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                              ),
                            ),
                          ] else ...[
                            // Audio preview strip
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: EttehadColors.emerald.withValues(alpha: 0.4)),
                              ),
                              child: Row(
                                children: [
                                  IconButton(
                                    onPressed: () {
                                      setState(() => _isPlayingAudio = !_isPlayingAudio);
                                    },
                                    icon: Icon(
                                      _isPlayingAudio ? Icons.pause_circle_filled_rounded : Icons.play_circle_fill_rounded,
                                      color: EttehadColors.emerald,
                                      size: 32,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const Text('صوت ضبط‌شده پرسش', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5)),
                                        Text('مدت زمان: ۰۰:${_recordSeconds.toString().padLeft(2, '0')}', style: const TextStyle(fontSize: 10, color: Colors.black54)),
                                      ],
                                    ),
                                  ),
                                  IconButton(
                                    onPressed: _deleteAudio,
                                    icon: const Icon(Icons.delete_outline_rounded, color: Colors.red, size: 20),
                                    tooltip: 'حذف صوت',
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Step 5: Book & Excerpt Attachment (Library / AI)
                    _buildBookAttachmentSection(),
                    const SizedBox(height: 14),

                    // Step 6: Madhhab / School Selection
                    const Text('رویکرد فقهی و مذهبی پاسخ', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: EttehadColors.navy)),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: EttehadColors.surfaceLow,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: EttehadColors.border),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: _selectedMadhhab,
                          isExpanded: true,
                          items: _madhhabOptions.map((opt) {
                            return DropdownMenuItem<String>(
                              value: opt,
                              child: Text(opt, style: const TextStyle(fontSize: 12)),
                            );
                          }).toList(),
                          onChanged: (v) {
                            if (v != null) setState(() => _selectedMadhhab = v);
                          },
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Step 6: Anonymous Toggle
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: _isAnonymous ? const Color(0xFFEFF6FF) : EttehadColors.surfaceLow,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: _isAnonymous ? const Color(0xFF93C5FD) : EttehadColors.border,
                        ),
                      ),
                      child: Row(
                        children: [
                          Checkbox(
                            value: _isAnonymous,
                            activeColor: EttehadColors.primary,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                            onChanged: (v) => setState(() => _isAnonymous = v ?? false),
                          ),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'ارسال کاملاً ناشناس بدون ذکر نام و مشخصات',
                                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: EttehadColors.navy),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'نام کاربری، شماره تماس و پروفایل شما مخفی می‌ماند و صرفاً سوال با کد رهگیری بررسی می‌شود.',
                                  style: TextStyle(fontSize: 10, color: Colors.grey.shade700),
                                ),
                              ],
                            ),
                          ),
                          const Icon(Icons.security_rounded, color: EttehadColors.primary, size: 22),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Submit Button
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton.icon(
                        onPressed: _submitInquiry,
                        icon: const Icon(Icons.send_rounded, size: 18),
                        label: const Text('ثبت نهایی سوال و ارسال به استاد منتخب', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: EttehadColors.primary,
                          foregroundColor: Colors.white,
                          elevation: 2,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
