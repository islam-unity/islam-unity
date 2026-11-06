import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';
import 'scholar_chat_screen.dart';

class MyInquiriesTab extends StatelessWidget {
  final EttehadRepository repo;
  final VoidCallback onNewInquiryRequested;

  const MyInquiriesTab({
    super.key,
    required this.repo,
    required this.onNewInquiryRequested,
  });

  void _openChat(BuildContext context, Map<String, dynamic> scholar) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: ScholarChatRoomScreen(scholar: scholar, repo: repo),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final chats = repo.scholarChats;

    if (chats.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: EttehadColors.primary.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.forum_outlined, size: 36, color: EttehadColors.primary),
              ),
              const SizedBox(height: 16),
              const Text(
                'هنوز استفتائی ثبت نکرده‌اید',
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: EttehadColors.navy),
              ),
              const SizedBox(height: 6),
              const Text(
                'می‌توانید سوالات فقهی، حقوقی، تفسیری یا شبهات اعتقادی خود را با امکان ضبط صوت یا به صورت کاملاً ناشناس از اساتید بپرسید.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 11.5, color: Colors.black54, height: 1.6),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: onNewInquiryRequested,
                icon: const Icon(Icons.add_comment_rounded, size: 18),
                label: const Text('طرح اولین سوال و استفتاء', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      color: EttehadColors.primary,
      onRefresh: () async {
        await repo.syncConsultationThreadsWithServer();
      },
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 110),
        itemCount: chats.length,
        itemBuilder: (ctx, idx) {
          final chat = chats[idx];
          final sc = (chat['scholar'] ?? {}) as Map<String, dynamic>;
          final scholarName = (sc['name'] ?? 'دفتر پاسخگویی معارفی').toString();
          final scholarTitle = (sc['title'] ?? 'فقه و معارف').toString();
          final trackingCode = chat['tracking_code'] ?? chat['trackingCode'] ?? 'کد پیگیری: ${chat['id'] ?? (idx + 1)}';
          final lastMsg = (chat['lastMessage'] ?? 'پیام جدیدی وجود ندارد').toString();
          final hasAudio = chat['has_audio'] == true;
          final isAnonymous = chat['is_anonymous'] == true;
          final hasBook = chat['has_book'] == true || chat['book_title'] != null;
          final bookTitle = (chat['book_title'] ?? '').toString();

          final isWaiting = chat['status'] == 'WAITING_SCHOLAR' || chat['status'] == 'PENDING';
          final statusLabel = isWaiting ? 'در حال بررسی استاد' : 'پاسخ آماده است';
          final statusColor = isWaiting ? EttehadColors.amberDark : EttehadColors.emeraldDark;
          final statusBg = isWaiting ? const Color(0xFFFEF3C7) : const Color(0xFFD1FAE5);

        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: EttehadColors.border),
            boxShadow: const [
              BoxShadow(color: Color(0x080A2E6E), blurRadius: 8, offset: Offset(0, 2)),
            ],
          ),
          child: Material(
            color: Colors.transparent,
            borderRadius: BorderRadius.circular(18),
            child: InkWell(
              onTap: () => _openChat(context, sc),
              borderRadius: BorderRadius.circular(18),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Tracking code & Status row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.tag_rounded, size: 14, color: EttehadColors.primary),
                            const SizedBox(width: 4),
                            Text(
                              toPersianDigits(trackingCode),
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: EttehadColors.primary),
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: statusBg,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            statusLabel,
                            style: TextStyle(color: statusColor, fontSize: 9.5, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),

                    // Scholar Avatar & Name
                    Row(
                      children: [
                        CircleAvatar(
                          radius: 20,
                          backgroundColor: EttehadColors.navy,
                          child: Text(
                            scholarName.characters.take(2).toString(),
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                scholarName,
                                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.navy),
                              ),
                              Text(scholarTitle, style: const TextStyle(fontSize: 10, color: Colors.black54)),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_left_rounded, color: Colors.black45, size: 20),
                      ],
                    ),
                    const SizedBox(height: 10),

                    // Last message snippet
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      decoration: BoxDecoration(
                        color: EttehadColors.surfaceLow,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        children: [
                          if (hasAudio) ...[
                            const Icon(Icons.mic_rounded, size: 14, color: EttehadColors.primary),
                            const SizedBox(width: 4),
                          ],
                          Expanded(
                            child: Text(
                              lastMsg,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 11.5, color: EttehadColors.ink),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),

                    // Badges row (anonymous, book, time)
                    Row(
                      children: [
                        if (hasBook && bookTitle.isNotEmpty) ...[
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: EttehadColors.primary.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: EttehadColors.primary.withValues(alpha: 0.2)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.menu_book_rounded, size: 10, color: EttehadColors.primary),
                                const SizedBox(width: 3),
                                ConstrainedBox(
                                  constraints: const BoxConstraints(maxWidth: 140),
                                  child: Text(
                                    'کتاب: $bookTitle',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                        ],
                        if (isAnonymous) ...[
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.grey.shade100,
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: Colors.grey.shade300),
                            ),
                            child: const Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.visibility_off_rounded, size: 10, color: Colors.black54),
                                SizedBox(width: 3),
                                Text('طرح‌شده به صورت ناشناس', style: TextStyle(fontSize: 9, color: Colors.black54)),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                        ],
                        const Spacer(),
                        const Text('امروز • پاسخگویی آنلاین', style: TextStyle(fontSize: 9.5, color: Colors.black38)),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    ),
  );
}
}
