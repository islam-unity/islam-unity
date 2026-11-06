import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';
import 'scholar_chat_screen.dart';

class PublicFaqTab extends StatefulWidget {
  final EttehadRepository repo;

  const PublicFaqTab({super.key, required this.repo});

  @override
  State<PublicFaqTab> createState() => _PublicFaqTabState();
}

class _PublicFaqTabState extends State<PublicFaqTab> {
  final TextEditingController _searchCtrl = TextEditingController();
  final Set<int> _expandedIndices = {0}; // First open by default
  String _selectedTopic = 'all';

  final List<Map<String, String>> _topics = [
    {'key': 'all', 'label': 'همه استفتائات'},
    {'key': 'moamelat', 'label': 'معاملات و بورس'},
    {'key': 'kalam', 'label': 'کلام و عقاید'},
    {'key': 'ebadat', 'label': 'احکام عبادی'},
    {'key': 'taqrib', 'label': 'تقریب و فقه مقارن'},
    {'key': 'quran', 'label': 'قرآن و تفسیر'},
  ];

  @override
  void initState() {
    super.initState();
    widget.repo.fetchPublicConsultationThreads().then((_) {
      if (mounted) setState(() {});
    });
  }

  final List<Map<String, dynamic>> _defaultFaqs = [
    {
      'topic': 'moamelat',
      'category': 'معاملات و فناوری',
      'categoryColor': EttehadColors.amberDark,
      'madhhab': 'دیدگاه تطبیقی مراجع و فریقین',
      'question': 'حکم شرعی خرید و فروش رمزارزها، توکن‌ها و معاملات الگوریتمی در بازارهای مالی چیست؟',
      'responder': 'پاسخ شورای عالی فقهی و آیت‌الله دکتر موسوی:',
      'responderBadge': 'مستند به قواعد فقه الاقتصاد',
      'answer':
          'معاملات رمزارزها و دارایی‌های دیجیتال در صورتی که دارای ارزش مبادله‌ای عقلایی بوده، متضمن غرر نباشد و در بستر قانون صورت گیرد، با رعایت شرایط عامه صحت بیع نافذ است. از ورود به طرح‌های پانزی و قمارگونه اجتناب شود.',
      'source': 'استفتاء شماره ۴۸۲۹ • کتاب التجاره، ص ۱۲۴',
    },
    {
      'topic': 'kalam',
      'category': 'کلام و حکمت',
      'categoryColor': EttehadColors.primary,
      'madhhab': 'مشترک فریقین',
      'question': 'چگونه عدل الهی با وجود تفاوت‌های فردی، بیماری‌های مادرزادی و تفاوت در موقعیت انسان‌ها سازگار است؟',
      'responder': 'پاسخ آیت‌الله دکتر موسوی و اساتید کلام اسلامی:',
      'responderBadge': 'مستند به حکمت متعالیه و قرآن',
      'answer':
          'عدالت الهی به معنای تساوی یکنواخت ریاضی نیست، بلکه به معنای اعطاء کل ذی حق حقه و وضع کل شیء فی موضعه است. خداوند تکالیف و بازخواست هر بنده را دقیقاً متناسب با وسع، استعداد و ابتلائات او قرار می‌دهد (لا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا).',
      'source': 'منبع: اسفار اربعه، ج ۶ • تفسیر المیزان، ذیل آیه ۲۸۶ بقره',
    },
    {
      'topic': 'taqrib',
      'category': 'تقریب و فقه مقارن',
      'categoryColor': EttehadColors.emeraldDark,
      'madhhab': 'تقریب مذاهب اسلامی',
      'question': 'حکم اقتدا به امام جماعت اهل سنت در حرمین شریفین و مساجد مشترک چیست؟',
      'responder': 'پاسخ مراجع معظم تقلید و علمای مجمع تقریب:',
      'responderBadge': 'سیره متواتر اهل‌بیت (ع)',
      'answer':
          'نماز جماعت با برادران اهل سنت در حرمین شریفین و هر نقطه‌ای که سبب تقویت وحدت و عزت اسلامی شود مستحب مؤکد است و ثواب نماز در صف اول پشت سر پیامبر (ص) را دارد و اعاده آن لازم نیست.',
      'source': 'وسائل الشیعه، باب صلاة الجماعه • الفقه علی المذاهب الاربعه',
    },
    {
      'topic': 'quran',
      'category': 'قرآن و تدبر',
      'categoryColor': Colors.teal,
      'madhhab': 'علوم قرآن',
      'question': 'راز و حکمت حروف مقطعه در ابتدای ۲۹ سوره قرآن کریم چیست؟',
      'responder': 'پاسخ حجت‌الاسلام والمسلمین قرائتی:',
      'responderBadge': 'تفسیر نور و مجمع‌البیان',
      'answer':
          'یکی از مهم‌ترین حکمت‌های حروف مقطعه اعجاز قرآن است؛ یعنی این کتاب معجزه‌آسا که بشر از آوردن حتی یک سوره مشابه آن ناتوان است، از همین حروف الفبای ساده در دسترس همگان ساخته شده است.',
      'source': 'تفسیر نور، مقدمه سوره مبارکه بقره',
    },
    {
      'topic': 'ebadat',
      'category': 'فقه عبادات',
      'categoryColor': Color(0xFF1499DE),
      'madhhab': 'فقه مقارن',
      'question': 'محاسبه مسافت شرعی و حکم نماز مسافر در سفرهای متداول روزانه و کاری چگونه است؟',
      'responder': 'پاسخ دفتر استفتائات فقه معاصر:',
      'responderBadge': 'اجماع فقهای معاصر',
      'answer':
          'کسی که شغل او در سفر است یا هفته‌ای حداقل سه روز برای کار یا تحصیل به مسافت شرعی (حداقل ۴۱ تا ۴۴ کیلومتر رفت و برگشت) تردد می‌کند، نماز وی کامل و روزه‌اش صحیح است.',
      'source': 'رساله آموزشی احکام معاصر، مسئله ۵۱۲',
    },
  ];

  List<Map<String, dynamic>> get _allFaqs {
    final list = List<Map<String, dynamic>>.from(_defaultFaqs);
    if (widget.repo.publicFaqs.isNotEmpty) {
      for (final t in widget.repo.publicFaqs) {
        final messages = t['messages'] as List?;
        String answer = '';
        String responder = 'پاسخ شورای استفتائات';
        if (messages != null && messages.isNotEmpty) {
          final scholarMsg = messages.firstWhere(
            (m) => m['isScholar'] == true || m['senderRole'] == 'SCHOLAR',
            orElse: () => messages.last,
          );
          answer = (scholarMsg['content'] ?? '').toString();
          if (scholarMsg['senderName'] != null) {
            responder = 'پاسخ ${scholarMsg['senderName']}';
          }
        }
        list.insert(0, {
          'topic': t['category'] ?? 'ebadat',
          'category': t['categoryName'] ?? 'استفتاء فقهی',
          'categoryColor': EttehadColors.primary,
          'madhhab': t['madhhab'] ?? 'عمومی',
          'question': t['title'] ?? t['question'] ?? 'پرسش شرعی',
          'responder': responder,
          'responderBadge': 'پاسخ برخط مستند',
          'answer': answer.isNotEmpty ? answer : (t['description'] ?? 'پاسخ این مسئله در سامانه ثبت شده است.'),
          'source': 'سامانه معارفی اتحاد • شماره رهگیری ${t['tracking_code'] ?? t['id'] ?? ''}',
        });
      }
    }
    return list;
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
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
    final query = _searchCtrl.text.trim().toLowerCase();

    final filtered = _allFaqs.where((f) {
      final matchesTopic = _selectedTopic == 'all' || f['topic'] == _selectedTopic;
      final matchesSearch = query.isEmpty ||
          f['question'].toString().toLowerCase().contains(query) ||
          f['answer'].toString().toLowerCase().contains(query) ||
          f['category'].toString().toLowerCase().contains(query);
      return matchesTopic && matchesSearch;
    }).toList();

    return Column(
      children: [
        // Search field
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          child: TextField(
            controller: _searchCtrl,
            onChanged: (_) => setState(() {}),
            decoration: InputDecoration(
              hintText: 'جستجو در هزاران پاسخ و استفتائات مستند...',
              hintStyle: const TextStyle(fontSize: 12),
              prefixIcon: const Icon(Icons.search_rounded, color: EttehadColors.primary, size: 20),
              suffixIcon: query.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear_rounded, size: 18),
                      onPressed: () {
                        _searchCtrl.clear();
                        setState(() {});
                      },
                    )
                  : null,
              filled: true,
              fillColor: Colors.white,
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: EttehadColors.border)),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: EttehadColors.border)),
            ),
          ),
        ),

        // Topic chips
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _topics.map((t) {
                final isSelected = _selectedTopic == t['key'];
                return Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: InkWell(
                    onTap: () => setState(() => _selectedTopic = t['key']!),
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: isSelected ? EttehadColors.primary : Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isSelected ? EttehadColors.primary : EttehadColors.border,
                        ),
                      ),
                      child: Text(
                        t['label']!,
                        style: TextStyle(
                          fontSize: 11,
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
        const SizedBox(height: 8),

        // FAQ List
        Expanded(
          child: filtered.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.search_off_rounded, size: 44, color: Colors.grey.shade400),
                      const SizedBox(height: 8),
                      const Text('استفتائی با این عبارت یافت نشد.', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.black54)),
                    ],
                  ),
                )
              : RefreshIndicator(
                  color: EttehadColors.primary,
                  onRefresh: () async {
                    await widget.repo.fetchPublicConsultationThreads();
                    if (mounted) setState(() {});
                  },
                  child: ListView.builder(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
                    itemCount: filtered.length,
                    itemBuilder: (ctx, i) {
                    final item = filtered[i];
                    final isOpen = _expandedIndices.contains(i);
                    final catColor = item['categoryColor'] as Color;

                    return Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: EttehadColors.border),
                        boxShadow: const [
                          BoxShadow(color: Color(0x06000000), blurRadius: 6, offset: Offset(0, 2)),
                        ],
                      ),
                      child: Column(
                        children: [
                          InkWell(
                            onTap: () {
                              setState(() {
                                if (isOpen) {
                                  _expandedIndices.remove(i);
                                } else {
                                  _expandedIndices.add(i);
                                }
                              });
                            },
                            borderRadius: BorderRadius.circular(16),
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                                    decoration: BoxDecoration(
                                      color: catColor.withValues(alpha: 0.12),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      item['category'],
                                      style: TextStyle(color: catColor, fontSize: 10, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      item['question'],
                                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, height: 1.5, color: EttehadColors.navy),
                                    ),
                                  ),
                                  Icon(
                                    isOpen ? Icons.expand_less_rounded : Icons.expand_more_rounded,
                                    color: Colors.black45,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          if (isOpen)
                            Container(
                              padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                              decoration: const BoxDecoration(
                                border: Border(top: BorderSide(color: Color(0xFFF1EDE2))),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const SizedBox(height: 10),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        item['responder'],
                                        style: const TextStyle(color: EttehadColors.primary, fontWeight: FontWeight.bold, fontSize: 11),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFEFF6FF),
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(
                                          item['responderBadge'],
                                          style: const TextStyle(color: EttehadColors.primary, fontSize: 9.5, fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    item['answer'],
                                    style: const TextStyle(fontSize: 12, height: 1.7, color: EttehadColors.ink),
                                  ),
                                  const SizedBox(height: 10),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        item['source'],
                                        style: const TextStyle(fontSize: 10, color: Colors.black45),
                                      ),
                                      InkWell(
                                        onTap: () {
                                          final defaultScholar = widget.repo.scholars.isNotEmpty
                                              ? widget.repo.scholars.first
                                              : {'name': 'استاد موسوی', 'id': 'scholar_1'};
                                          _openScholarChat(defaultScholar);
                                        },
                                        child: const Row(
                                          children: [
                                            Text('گفتگوی تکمیلی با استاد', style: TextStyle(color: EttehadColors.primary, fontSize: 11, fontWeight: FontWeight.bold)),
                                            Icon(Icons.chevron_left_rounded, size: 14, color: EttehadColors.primary),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                    );
                  },
                ),
              ),
        ),
      ],
    );
  }
}
