import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';
import '../../library/library_screen.dart';
import 'book_excerpt_picker_modal.dart';

class ScholarChatRoomScreen extends StatefulWidget {
  final Map<String, dynamic> scholar;
  final EttehadRepository repo;

  const ScholarChatRoomScreen({
    super.key,
    required this.scholar,
    required this.repo,
  });

  @override
  State<ScholarChatRoomScreen> createState() => _ScholarChatRoomScreenState();
}

class _ScholarChatRoomScreenState extends State<ScholarChatRoomScreen> {
  final TextEditingController _ctrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  bool _isVoiceRecording = false;

  @override
  void initState() {
    super.initState();
    widget.repo.addListener(_onRepoChanged);
    _syncLatestMessages();
  }

  void _syncLatestMessages() {
    final scId = widget.scholar['id']?.toString();
    final chat = widget.repo.scholarChats.firstWhere(
      (c) => c['scholar']?['id']?.toString() == scId,
      orElse: () => <String, dynamic>{},
    );
    final threadId = chat['thread_id']?.toString();
    if (threadId != null && threadId.isNotEmpty) {
      widget.repo.syncThreadMessages(threadId);
    }
  }

  void _onRepoChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    widget.repo.removeListener(_onRepoChanged);
    _ctrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _sendMessage() {
    final text = _ctrl.text.trim();
    if (text.isEmpty) return;

    final scId = widget.scholar['id'].toString();
    final chat = widget.repo.scholarChats.firstWhere(
      (c) => c['scholar']?['id']?.toString() == scId,
      orElse: () => <String, dynamic>{},
    );
    final threadId = chat['thread_id']?.toString();

    widget.repo.sendConsultationMessage(
      scholarId: scId,
      text: text,
      threadId: threadId,
    );
    _ctrl.clear();

    Future.delayed(const Duration(milliseconds: 150), () {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _openBookExcerptPicker() {
    BookExcerptPickerModal.show(
      context,
      widget.repo,
      onExcerptSelected: (excerptData) {
        final scId = widget.scholar['id'].toString();
        final excerpt = (excerptData['excerpt'] ?? '').toString();
        final bookId = (excerptData['bookId'] ?? '').toString();
        final bookTitle = (excerptData['bookTitle'] ?? '').toString();
        final userNote = _ctrl.text.trim();

        final chat = widget.repo.scholarChats.firstWhere(
          (c) => c['scholar']?['id']?.toString() == scId,
          orElse: () => <String, dynamic>{},
        );
        final threadId = chat['thread_id']?.toString();

        widget.repo.sendBookExcerptToScholar(
          scholarId: scId,
          excerpt: excerpt,
          bookId: bookId,
          bookTitle: bookTitle,
          userQuestion: userNote.isNotEmpty ? userNote : null,
        );

        if (threadId != null && threadId.isNotEmpty) {
          final noteText = userNote.isNotEmpty
              ? 'پرسش پیرامون فراز کتاب «$bookTitle»:\n«$excerpt»\n\nپرسش: $userNote'
              : 'فراز کتاب «$bookTitle»:\n«$excerpt»';
          widget.repo.sendConsultationMessage(
            scholarId: scId,
            text: noteText,
            threadId: threadId,
            bookId: bookId,
            bookTitle: bookTitle,
          );
        }
        _ctrl.clear();

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('فراز کتاب «$bookTitle» خدمت دفتر استاد ارسال شد.'),
            backgroundColor: EttehadColors.emerald,
          ),
        );

        Future.delayed(const Duration(milliseconds: 200), () {
          if (_scrollCtrl.hasClients) {
            _scrollCtrl.animateTo(
              _scrollCtrl.position.maxScrollExtent,
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeOut,
            );
          }
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final scId = widget.scholar['id'].toString();
    final chat = widget.repo.scholarChats.firstWhere(
      (c) => c['scholar']['id'].toString() == scId,
      orElse: () => {'messages': []},
    );
    final messages = List<Map<String, dynamic>>.from(chat['messages'] ?? []);
    final scholarName = (widget.scholar['name'] ?? 'استاد معارفی').toString();
    final scholarTitle = (widget.scholar['title'] ?? 'فقه و معارف اسلامی').toString();

    return Scaffold(
      backgroundColor: EttehadColors.paper,
      appBar: AppBar(
        backgroundColor: EttehadColors.navy,
        foregroundColor: Colors.white,
        titleSpacing: 0,
        title: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: Colors.white.withValues(alpha: 0.2),
              child: Text(
                scholarName.characters.take(2).toString(),
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    scholarName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Colors.white),
                  ),
                  Text(
                    scholarTitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 9.5, color: Colors.white.withValues(alpha: 0.8)),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('دفتر پاسخ‌گویی $scholarName: روزهای زوج ساعت ۱۶ الی ۲۰'),
                  backgroundColor: EttehadColors.primary,
                ),
              );
            },
            icon: const Icon(Icons.info_outline_rounded, size: 20),
            tooltip: 'اطلاعات پاسخ‌گویی استاد',
          ),
          if (chat['thread_id'] != null && (chat['thread_id'] as String).isNotEmpty)
            PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert_rounded, color: Colors.white, size: 20),
              tooltip: 'گزینه‌های گفتگو',
              onSelected: (val) async {
                final tId = chat['thread_id'].toString();
                if (val == 'bookmark') {
                  final ok = await widget.repo.toggleConsultationBookmark(tId);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(ok ? 'وضعیت نشان گفتگو به‌روزرسانی شد.' : 'خطا در ثبت نشان.'),
                        backgroundColor: EttehadColors.primary,
                      ),
                    );
                  }
                } else if (val == 'close') {
                  await widget.repo.updateConsultationStatus(tId, 'CLOSED');
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('گفتگو با موفقیت بسته شد.'),
                        backgroundColor: EttehadColors.emerald,
                      ),
                    );
                  }
                } else if (val == 'open') {
                  await widget.repo.updateConsultationStatus(tId, 'OPEN');
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('گفتگو مجدداً بازگشایی شد.'),
                        backgroundColor: EttehadColors.emerald,
                      ),
                    );
                  }
                }
              },
              itemBuilder: (ctx) => [
                const PopupMenuItem(
                  value: 'bookmark',
                  child: Row(
                    children: [
                      Icon(Icons.bookmark_outline_rounded, size: 18, color: EttehadColors.navy),
                      SizedBox(width: 8),
                      Text('نشان‌کردن گفتگو', style: TextStyle(fontSize: 12)),
                    ],
                  ),
                ),
                PopupMenuItem(
                  value: (chat['status'] == 'CLOSED') ? 'open' : 'close',
                  child: Row(
                    children: [
                      Icon(
                        (chat['status'] == 'CLOSED') ? Icons.lock_open_rounded : Icons.check_circle_outline_rounded,
                        size: 18,
                        color: EttehadColors.navy,
                      ),
                      SizedBox(width: 8),
                      Text(
                        (chat['status'] == 'CLOSED') ? 'بازگشایی گفتگو' : 'تکمیل و بستن گفتگو',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
        ],
      ),
      body: Column(
        children: [
          // Security and Tracking Notice Banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            color: const Color(0xFFEFF6FF),
            child: Row(
              children: [
                const Icon(Icons.verified_user_rounded, color: EttehadColors.primary, size: 16),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'ارتباط مستقیم و محرمانه با دفتر استفتائات ${widget.scholar['name']}',
                    style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: EttehadColors.emerald.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Text('پاسخگوی برخط', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: EttehadColors.emeraldDark)),
                ),
              ],
            ),
          ),

          // Messages list
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(14),
              itemCount: messages.length,
              itemBuilder: (ctx, i) {
                final m = messages[i];
                final isUser = m['sender'] == 'user';
                final hasAudio = m['has_audio'] == true;
                final audioDuration = m['audio_duration']?.toString() ?? '۰۰:۳۰';
                final isAnonymous = m['is_anonymous'] == true;
                final bookId = m['bookId']?.toString();
                final bookTitle = m['bookTitle']?.toString();
                final excerpt = m['excerpt']?.toString();

                return Align(
                  alignment: isUser ? Alignment.centerLeft : Alignment.centerRight,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(12),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
                    decoration: BoxDecoration(
                      color: isUser ? EttehadColors.primary : Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: isUser ? null : Border.all(color: EttehadColors.border),
                      boxShadow: const [
                        BoxShadow(color: Color(0x08000000), blurRadius: 6, offset: Offset(0, 2)),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Anonymous indicator if user
                        if (isUser && isAnonymous) ...[
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.visibility_off_rounded, size: 12, color: Colors.white.withValues(alpha: 0.8)),
                              const SizedBox(width: 4),
                              Text('ارسال ناشناس', style: TextStyle(fontSize: 9.5, color: Colors.white.withValues(alpha: 0.8))),
                            ],
                          ),
                          const SizedBox(height: 4),
                        ],

                        // Audio Player Bubble
                        if (hasAudio) ...[
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            margin: const EdgeInsets.only(bottom: 6),
                            decoration: BoxDecoration(
                              color: isUser ? Colors.white.withValues(alpha: 0.2) : EttehadColors.surfaceLow,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.play_circle_fill_rounded, color: isUser ? Colors.white : EttehadColors.primary, size: 24),
                                const SizedBox(width: 6),
                                Text(
                                  'پیام صوتی ($audioDuration)',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: isUser ? Colors.white : EttehadColors.navy,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],

                        // Main Text Message
                        Text(
                          (m['text'] ?? '').toString(),
                          style: TextStyle(
                            fontSize: 12.5,
                            height: 1.7,
                            color: isUser ? Colors.white : EttehadColors.ink,
                          ),
                        ),

                        // Attached Excerpt Quote (from Library or AI)
                        if (excerpt != null && excerpt.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: isUser ? Colors.white.withValues(alpha: 0.18) : const Color(0xFFF1F5F9),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: isUser ? Colors.white24 : EttehadColors.border),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(
                                  Icons.format_quote_rounded,
                                  size: 16,
                                  color: isUser ? Colors.white70 : EttehadColors.primary,
                                ),
                                const SizedBox(width: 4),
                                Expanded(
                                  child: Text(
                                    excerpt,
                                    style: TextStyle(
                                      fontSize: 10.5,
                                      fontStyle: FontStyle.italic,
                                      height: 1.5,
                                      color: isUser ? Colors.white : Colors.black87,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],

                        // Attached Book Citation if exists
                        if (bookId != null && bookTitle != null) ...[
                          const SizedBox(height: 8),
                          InkWell(
                            onTap: () {
                              final book = widget.repo.books.firstWhere(
                                (b) => b['id'].toString() == bookId,
                                orElse: () => widget.repo.books.first,
                              );
                              Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => Directionality(
                                    textDirection: TextDirection.rtl,
                                    child: NativeBookReaderScreen(book: book, repo: widget.repo),
                                  ),
                                ),
                              );
                            },
                            child: Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: isUser ? Colors.white.withValues(alpha: 0.15) : EttehadColors.skyCardStart,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.menu_book_rounded, color: isUser ? Colors.white : EttehadColors.primary, size: 16),
                                  const SizedBox(width: 6),
                                  Flexible(
                                    child: Text(
                                      'ارجاع به کتاب: $bookTitle',
                                      style: TextStyle(
                                        fontSize: 10.5,
                                        fontWeight: FontWeight.bold,
                                        color: isUser ? Colors.white : EttehadColors.primary,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 4),
                                  Icon(Icons.chevron_left_rounded, color: isUser ? Colors.white : EttehadColors.primary, size: 14),
                                ],
                              ),
                            ),
                          ),
                        ],

                        const SizedBox(height: 4),
                        Align(
                          alignment: Alignment.bottomLeft,
                          child: Text(
                            (m['time'] ?? '').toString(),
                            style: TextStyle(
                              fontSize: 9.5,
                              color: isUser ? Colors.white.withValues(alpha: 0.7) : Colors.black38,
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

          // Message input bar
          Container(
            padding: const EdgeInsets.all(10),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: EttehadColors.border)),
            ),
            child: SafeArea(
              child: Row(
                children: [
                  IconButton(
                    onPressed: _openBookExcerptPicker,
                    icon: const Icon(Icons.menu_book_rounded, color: EttehadColors.primary),
                    tooltip: 'پیوست کتاب یا گزیده متن (کتابخانه / هوش مصنوعی)',
                  ),
                  IconButton(
                    onPressed: () {
                      setState(() => _isVoiceRecording = !_isVoiceRecording);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(_isVoiceRecording ? 'ضبط صدا آغاز شد... برای پایان دوباره بزنید.' : 'پیام صوتی آماده ارسال است.'),
                          duration: const Duration(seconds: 2),
                        ),
                      );
                    },
                    icon: Icon(
                      _isVoiceRecording ? Icons.mic_rounded : Icons.mic_none_rounded,
                      color: _isVoiceRecording ? Colors.red : EttehadColors.primary,
                    ),
                    tooltip: 'ارسال صوت',
                  ),
                  Expanded(
                    child: TextField(
                      controller: _ctrl,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _sendMessage(),
                      decoration: InputDecoration(
                        hintText: 'پرسش یا پاسخ تکمیلی خود را بنویسید...',
                        hintStyle: const TextStyle(fontSize: 12),
                        filled: true,
                        fillColor: EttehadColors.surfaceLow,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: _sendMessage,
                    borderRadius: BorderRadius.circular(24),
                    child: Container(
                      width: 42,
                      height: 42,
                      decoration: const BoxDecoration(
                        color: EttehadColors.primary,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.send_rounded, color: Colors.white, size: 18),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
