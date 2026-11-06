import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';
import 'mosques_map_modal.dart';
import 'scholar_chat_screen.dart';

class InquiryTrackerHero extends StatelessWidget {
  final EttehadRepository repo;
  final VoidCallback onNewInquiryRequested;

  const InquiryTrackerHero({
    super.key,
    required this.repo,
    required this.onNewInquiryRequested,
  });

  void _openActiveChat(BuildContext context) {
    if (repo.scholarChats.isNotEmpty) {
      final chat = repo.scholarChats.first;
      final sc = chat['scholar'] as Map<String, dynamic>;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => Directionality(
            textDirection: TextDirection.rtl,
            child: ScholarChatRoomScreen(scholar: sc, repo: repo),
          ),
        ),
      );
    } else {
      onNewInquiryRequested();
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasActiveChat = repo.scholarChats.isNotEmpty;
    final firstChat = hasActiveChat ? repo.scholarChats.first : null;
    final trackingCode = firstChat?['tracking_code'] ?? 'ETH-Q-8472';
    final scholarName = firstChat?['scholar']?['name'] ?? 'آیت‌الله دکتر موسوی';

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0A2E6E), Color(0xFF0F5257), Color(0xFF1499DE)],
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
        ),
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0A2E6E).withValues(alpha: 0.25),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top row: SLA badge and Mosques Map button
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: EttehadColors.amberDark,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.verified_rounded, color: Colors.white, size: 12),
                    SizedBox(width: 4),
                    Text(
                      'میز استفتائات و پاسخ‌گویی معارفی',
                      style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
              InkWell(
                onTap: () => MosquesMapModal.show(context, repo: repo),
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.25)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.mosque_rounded, color: Color(0xFFA5F3FC), size: 14),
                      SizedBox(width: 4),
                      Text(
                        'نقشه مساجد (GPS)',
                        style: TextStyle(color: Color(0xFFA5F3FC), fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          const Text(
            'ارتباط مستقیم، مستند و علمی با اساتید و مراجع',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 14.5,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'امکان ثبت پرسش متنی، ضبط پیام صوتی یا ارسال کاملاً ناشناس با دریافت کد رهگیری آنی.',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.85),
              fontSize: 11,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 12),

          // Active inquiry strip or Action Row
          if (hasActiveChat) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withValues(alpha: 0.25)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.mark_email_read_rounded, color: Colors.amberAccent, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'گفتگوی فعال: کد رهگیری ${toPersianDigits(trackingCode)}',
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11.5),
                        ),
                        Text(
                          'پاسخ $scholarName آماده است',
                          style: const TextStyle(color: Color(0xFFCCFBF1), fontSize: 9.5),
                        ),
                      ],
                    ),
                  ),
                  InkWell(
                    onTap: () => _openActiveChat(context),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFBBF24),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text(
                        'مشاهده پاسخ',
                        style: TextStyle(
                          color: Color(0xFF0A2E6E),
                          fontWeight: FontWeight.w900,
                          fontSize: 10.5,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],

          // Quick New Question Action button
          SizedBox(
            width: double.infinity,
            height: 42,
            child: ElevatedButton.icon(
              onPressed: onNewInquiryRequested,
              icon: const Icon(Icons.edit_note_rounded, size: 20),
              label: const Text('طرح سوال و استفتاء جدید (متنی یا صوتی)', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12)),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: EttehadColors.navy,
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
