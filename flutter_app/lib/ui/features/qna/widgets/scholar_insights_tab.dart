import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';
import 'new_inquiry_modal.dart';
import 'scholar_chat_screen.dart';

class ScholarInsightsTab extends StatefulWidget {
  final EttehadRepository repo;

  const ScholarInsightsTab({super.key, required this.repo});

  @override
  State<ScholarInsightsTab> createState() => _ScholarInsightsTabState();
}

class _ScholarInsightsTabState extends State<ScholarInsightsTab> {
  String _selectedCategory = 'all';
  final Set<String> _likedPostIds = {};
  final Set<String> _savedPostIds = {};

  @override
  void initState() {
    super.initState();
    widget.repo.syncFeedFromBackend();
  }

  final List<Map<String, String>> _categories = [
    {'key': 'all', 'label': 'همه مطالب'},
    {'key': 'FIQH', 'label': 'فقه و احکام نوین'},
    {'key': 'TAFSIR', 'label': 'تفسیر و تدبر'},
    {'key': 'KALAM', 'label': 'کلام و عقاید'},
    {'key': 'UNITY', 'label': 'تقریب و فقه مقارن'},
    {'key': 'AKHLAQ', 'label': 'اخلاق و معرفت'},
  ];

  void _openInquiryForPost(Map<String, dynamic> post, Map<String, dynamic>? scholar) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => NewInquiryModal(
        repo: widget.repo,
      ),
    );
  }

  void _openScholarChat(Map<String, dynamic> scholar) {
    widget.repo.startOrOpenScholarChat(scholar);
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: ScholarChatRoomScreen(scholar: scholar, repo: widget.repo),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final allPosts = widget.repo.posts;

    // Filter posts
    final filtered = _selectedCategory == 'all'
        ? allPosts
        : allPosts.where((p) {
            final cat = (p['category'] ?? '').toString().toUpperCase();
            final title = (p['title'] ?? '').toString();
            final content = (p['content'] ?? '').toString();
            if (_selectedCategory == 'FIQH') return cat.contains('FIQH') || title.contains('فقه') || content.contains('فقه');
            if (_selectedCategory == 'TAFSIR') return cat.contains('TAFSIR') || title.contains('تفسیر') || content.contains('قرآن');
            if (_selectedCategory == 'KALAM') return cat.contains('KALAM') || title.contains('کلام') || content.contains('عدل');
            if (_selectedCategory == 'UNITY') return cat.contains('UNITY') || title.contains('وحدت') || content.contains('فریقین');
            if (_selectedCategory == 'AKHLAQ') return cat.contains('AKHLAQ') || title.contains('اخلاق');
            return true;
          }).toList();

    return Column(
      children: [
        // Category Filter Chips
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _categories.map((c) {
                final isSelected = _selectedCategory == c['key'];
                return Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: InkWell(
                    onTap: () {
                      setState(() => _selectedCategory = c['key']!);
                      widget.repo.syncFeedFromBackend(category: c['key']!);
                    },
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: isSelected ? EttehadColors.primary : Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isSelected ? EttehadColors.primary : EttehadColors.border,
                        ),
                        boxShadow: isSelected
                            ? [
                                BoxShadow(
                                  color: EttehadColors.primary.withValues(alpha: 0.25),
                                  blurRadius: 6,
                                  offset: const Offset(0, 2),
                                )
                              ]
                            : null,
                      ),
                      child: Text(
                        c['label']!,
                        style: TextStyle(
                          fontSize: 11.5,
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
        ),

        // Posts List
        Expanded(
          child: filtered.isEmpty
              ? _buildEmptyState()
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
                  itemCount: filtered.length,
                  itemBuilder: (ctx, idx) => _buildPostCard(filtered[idx]),
                ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.article_outlined, size: 48, color: Colors.grey.shade400),
          const SizedBox(height: 10),
          const Text('مطلبی در این موضوع یافت نشد.', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.black54)),
          const SizedBox(height: 4),
          const Text('موضوع دیگری را از نوار بالای صفحه انتخاب فرمایید.', style: TextStyle(fontSize: 11, color: Colors.black45)),
        ],
      ),
    );
  }

  Widget _buildPostCard(Map<String, dynamic> post) {
    final postId = (post['id'] ?? '').toString();
    final title = (post['title'] ?? '').toString();
    final content = (post['content'] ?? '').toString();
    final scholarId = post['scholar_id']?.toString();
    final isLiked = _likedPostIds.contains(postId);
    final isSaved = _savedPostIds.contains(postId);

    final scholar = widget.repo.scholars.firstWhere(
      (s) => s['id']?.toString() == scholarId,
      orElse: () => {
        'name': post['author_name'] ?? 'استاد و پژوهشگر معارفی',
        'title': 'استاد حوزه و دانشگاه',
        'city': 'قم / تهران',
      },
    );

    final authorName = scholar['name']?.toString() ?? 'استاد معارفی';
    final authorTitle = scholar['title']?.toString() ?? 'فقه و کلام اسلامی';
    final madhhab = post['madhhab'] ?? scholar['madhhab'] ?? 'تقریب فریقین';
    final likesCount = (post['likes_count'] ?? 120) + (isLiked ? 1 : 0);
    final viewsCount = post['views_count'] ?? 1500;

    // Parse Quran references if JSON string
    List<dynamic> quranRefs = [];
    if (post['quran_references'] != null) {
      try {
        if (post['quran_references'] is String) {
          quranRefs = jsonDecode(post['quran_references']);
        } else if (post['quran_references'] is List) {
          quranRefs = post['quran_references'];
        }
      } catch (_) {}
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: EttehadColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A0F5257),
            blurRadius: 10,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Scholar Header
          Row(
            children: [
              InkWell(
                onTap: () => _openScholarChat(scholar),
                child: CircleAvatar(
                  radius: 22,
                  backgroundColor: EttehadColors.navy,
                  child: Text(
                    authorName.characters.take(2).toString(),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          authorName,
                          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.navy),
                        ),
                        const SizedBox(width: 4),
                        const Icon(Icons.verified_rounded, color: EttehadColors.primary, size: 15),
                      ],
                    ),
                    const SizedBox(height: 1),
                    Text(authorTitle, style: const TextStyle(fontSize: 10, color: Colors.black54)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFEFF6FF),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  madhhab.toString(),
                  style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Post Title
          Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, height: 1.4, color: EttehadColors.ink),
          ),
          const SizedBox(height: 8),

          // Content body
          Text(
            content,
            style: const TextStyle(fontSize: 12.5, height: 1.7, color: Color(0xFF334155)),
          ),
          const SizedBox(height: 10),

          // Quran Reference Callout Box
          if (quranRefs.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: EttehadColors.surfaceLow,
                borderRadius: BorderRadius.circular(12),
                border: const Border(right: BorderSide(color: EttehadColors.emerald, width: 3.5)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.auto_stories_rounded, size: 14, color: EttehadColors.emeraldDark),
                      const SizedBox(width: 6),
                      Text(
                        'استناد قرآنی: سوره ${(quranRefs.first['surah'] ?? '')} • آیه ${toPersianDigits(quranRefs.first['ayah'])}',
                        style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.emeraldDark),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    (quranRefs.first['text'] ?? '').toString(),
                    style: const TextStyle(fontSize: 12, height: 1.6, color: EttehadColors.navy, fontStyle: FontStyle.italic),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],

          // Footer metrics and actions
          Row(
            children: [
              // Like
              InkWell(
                onTap: () {
                  setState(() {
                    if (isLiked) {
                      _likedPostIds.remove(postId);
                    } else {
                      _likedPostIds.add(postId);
                    }
                  });
                  widget.repo.toggleFeedLike(postId);
                },
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  child: Row(
                    children: [
                      Icon(
                        isLiked ? Icons.favorite_rounded : Icons.favorite_outline_rounded,
                        size: 16,
                        color: isLiked ? Colors.red : Colors.black54,
                      ),
                      const SizedBox(width: 4),
                      Text(toPersianDigits(likesCount), style: const TextStyle(fontSize: 11, color: Colors.black54)),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 12),

              // Views
              Row(
                children: [
                  const Icon(Icons.remove_red_eye_outlined, size: 16, color: Colors.black45),
                  const SizedBox(width: 4),
                  Text(toPersianDigits(viewsCount), style: const TextStyle(fontSize: 11, color: Colors.black54)),
                ],
              ),
              const Spacer(),

              // Bookmark
              IconButton(
                onPressed: () {
                  setState(() {
                    if (isSaved) {
                      _savedPostIds.remove(postId);
                    } else {
                      _savedPostIds.add(postId);
                    }
                  });
                  widget.repo.toggleFeedBookmark(postId);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(isSaved ? 'مطلب از نشان‌ها حذف شد.' : 'مطلب در نشان‌های شما ذخیره شد.'),
                      duration: const Duration(seconds: 2),
                    ),
                  );
                },
                icon: Icon(
                  isSaved ? Icons.bookmark_rounded : Icons.bookmark_outline_rounded,
                  size: 18,
                  color: isSaved ? EttehadColors.amberDark : Colors.black54,
                ),
                tooltip: 'ذخیره مطلب',
              ),

              // Ask question about this post
              ElevatedButton.icon(
                onPressed: () => _openInquiryForPost(post, scholar),
                icon: const Icon(Icons.chat_bubble_outline_rounded, size: 14),
                label: const Text('طرح سوال از استاد', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary.withValues(alpha: 0.1),
                  foregroundColor: EttehadColors.primary,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                    side: BorderSide(color: EttehadColors.primary.withValues(alpha: 0.25)),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
