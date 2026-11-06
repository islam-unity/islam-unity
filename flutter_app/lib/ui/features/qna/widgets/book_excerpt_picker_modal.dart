import 'package:flutter/material.dart';
import 'package:ettehad_app/data/ettehad_repository.dart';
import 'package:ettehad_app/ui/core/theme.dart';

class BookExcerptPickerModal extends StatefulWidget {
  final EttehadRepository repo;
  final ValueChanged<Map<String, dynamic>> onExcerptSelected;

  const BookExcerptPickerModal({
    super.key,
    required this.repo,
    required this.onExcerptSelected,
  });

  static void show(
    BuildContext context,
    EttehadRepository repo, {
    required ValueChanged<Map<String, dynamic>> onExcerptSelected,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => BookExcerptPickerModal(
        repo: repo,
        onExcerptSelected: onExcerptSelected,
      ),
    );
  }

  @override
  State<BookExcerptPickerModal> createState() => _BookExcerptPickerModalState();
}

class _BookExcerptPickerModalState extends State<BookExcerptPickerModal> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _searchCtrl = TextEditingController();
  final TextEditingController _excerptCtrl = TextEditingController();

  Map<String, dynamic>? _selectedBook;

  final List<Map<String, String>> _aiPresets = [
    {
      'title': 'تحلیل هوش مصنوعی: حکم فقهی معاملات رمزارزها و مالیت دارایی دیجیتال',
      'bookTitle': 'فقه المعاملات الحدیثة',
      'excerpt': '«با توجه به بررسی ادله فریقین و حفظ اصل عدم غرر و منفعت عقلایی در معاملات، مالیت رمزارزها مورد بحث و تدقیق فقهای معاصر قرار گرفته است.»',
    },
    {
      'title': 'استناد هوش مصنوعی: اخوت قرآنی و احکام همزیستی مذاهب',
      'bookTitle': 'تفسیر المیزان (علامه طباطبایی)',
      'excerpt': '«در ذیل آیه إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ بیان شده که عقد اخوت تشریعی، حقوق و تکالیف متقابلی برای همه مسلمانان فراتر از تمایزات مذهبی ایجاد می‌کند.»',
    },
    {
      'title': 'تحلیل هوش مصنوعی: طهارت و غسل در فقه مقارن فریقین',
      'bookTitle': 'الفقه المنهجی علی مذهب الشافعی',
      'excerpt': '«بررسی تطبیقی شرایط موانع وضو و حکم جبیره بر اساس روایات معتبر شیعه و اهل سنت و تسهیل امور مکلفین.»',
    },
    {
      'title': 'استناد هوش مصنوعی: عدالت اقتصادی و خطبه‌های نهج‌البلاغه',
      'bookTitle': 'نهج‌البلاغه شریف (ترجمه و شرح)',
      'excerpt': '«عهدنامه مالک اشتر و اصول حاکمیت عادلانه و نفی احتکار و انحصار ثروت در جامعه اسلامی.»',
    },
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    if (widget.repo.books.isNotEmpty) {
      _selectedBook = widget.repo.books.first;
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchCtrl.dispose();
    _excerptCtrl.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> _getFilteredBooks() {
    final q = _searchCtrl.text.trim().toLowerCase();
    final books = widget.repo.books;
    if (q.isEmpty) return books;
    return books.where((b) {
      final title = (b['title'] ?? '').toString().toLowerCase();
      final author = (b['author'] ?? '').toString().toLowerCase();
      return title.contains(q) || author.contains(q);
    }).toList();
  }

  void _submitSelection({
    required String bookId,
    required String bookTitle,
    required String excerpt,
    required String source,
  }) {
    widget.onExcerptSelected({
      'bookId': bookId,
      'bookTitle': bookTitle,
      'excerpt': excerpt.trim(),
      'source': source,
    });
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final filteredBooks = _getFilteredBooks();

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Container(
        height: MediaQuery.of(context).size.height * 0.88,
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
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: EttehadColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.menu_book_rounded, color: EttehadColors.primary, size: 22),
                  ),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'پیوست کتاب یا فراز متن به عالم دینی',
                          style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: EttehadColors.navy),
                        ),
                        Text(
                          'ارسال مستقیم مشخصات کتاب یا گزیده متن هوش مصنوعی به استاد',
                          style: TextStyle(fontSize: 10, color: Colors.black54),
                        ),
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

            // Segmented TabBar
            Container(
              color: EttehadColors.surfaceLow,
              child: TabBar(
                controller: _tabController,
                indicatorColor: EttehadColors.primary,
                labelColor: EttehadColors.primary,
                unselectedLabelColor: Colors.black54,
                labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                tabs: const [
                  Tab(icon: Icon(Icons.library_books_rounded, size: 18), text: 'انتخاب از کتب کتابخانه'),
                  Tab(icon: Icon(Icons.auto_awesome_rounded, size: 18), text: 'فرازهای تحلیل هوش مصنوعی'),
                ],
              ),
            ),

            // TabBar View
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  // Tab 1: Library Books & Excerpt Input
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Search Book input
                        TextField(
                          controller: _searchCtrl,
                          onChanged: (_) => setState(() {}),
                          decoration: InputDecoration(
                            hintText: 'جستجو در عنوان یا مؤلف کتاب...',
                            hintStyle: const TextStyle(fontSize: 11.5),
                            prefixIcon: const Icon(Icons.search_rounded, size: 18, color: EttehadColors.primary),
                            filled: true,
                            fillColor: EttehadColors.surfaceLow,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                          ),
                        ),
                        const SizedBox(height: 10),

                        const Text('۱. کتاب مورد نظر را انتخاب کنید:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: EttehadColors.navy)),
                        const SizedBox(height: 6),

                        // Books horizontal selector
                        SizedBox(
                          height: 75,
                          child: ListView.builder(
                            scrollDirection: Axis.horizontal,
                            itemCount: filteredBooks.length,
                            itemBuilder: (ctx, idx) {
                              final b = filteredBooks[idx];
                              final isSel = _selectedBook?['id'] == b['id'];
                              final title = (b['title'] ?? 'کتاب').toString();
                              return Padding(
                                padding: const EdgeInsets.only(left: 8),
                                child: InkWell(
                                  onTap: () => setState(() => _selectedBook = b),
                                  borderRadius: BorderRadius.circular(12),
                                  child: Container(
                                    width: 140,
                                    padding: const EdgeInsets.all(8),
                                    decoration: BoxDecoration(
                                      color: isSel ? EttehadColors.primary.withValues(alpha: 0.1) : Colors.white,
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(color: isSel ? EttehadColors.primary : Colors.grey.shade300, width: isSel ? 1.5 : 1),
                                    ),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Text(
                                          title,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: isSel ? FontWeight.w900 : FontWeight.bold,
                                            color: isSel ? EttehadColors.primary : EttehadColors.ink,
                                          ),
                                        ),
                                        Text(
                                          (b['author'] ?? '').toString(),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(fontSize: 9.5, color: Colors.black45),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),

                        const SizedBox(height: 14),
                        const Text('۲. متن یا فراز مدنظر از این کتاب (اختیاری):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: EttehadColors.navy)),
                        const SizedBox(height: 6),

                        Expanded(
                          child: TextField(
                            controller: _excerptCtrl,
                            maxLines: null,
                            expands: true,
                            decoration: InputDecoration(
                              hintText: 'متن، عبارت یا مسئله‌ای از کتاب که می‌خواهید عالم دینی درباره آن نظر دهد را اینجا بنویسید یا الصاق کنید...',
                              hintStyle: const TextStyle(fontSize: 11, color: Colors.black45),
                              filled: true,
                              fillColor: EttehadColors.surfaceLow,
                              contentPadding: const EdgeInsets.all(12),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: EttehadColors.border)),
                            ),
                          ),
                        ),

                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          height: 42,
                          child: ElevatedButton.icon(
                            onPressed: () {
                              if (_selectedBook == null) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('لطفاً یک کتاب انتخاب کنید.')),
                                );
                                return;
                              }
                              _submitSelection(
                                bookId: _selectedBook!['id'].toString(),
                                bookTitle: _selectedBook!['title'].toString(),
                                excerpt: _excerptCtrl.text.isNotEmpty ? _excerptCtrl.text : '«ارجاع کلی به کتاب مرجع جهت بررسی و استفتاء»',
                                source: 'library',
                              );
                            },
                            icon: const Icon(Icons.check_circle_rounded, size: 18),
                            label: Text(
                              _selectedBook != null ? 'تأیید و پیوست اثر «${_selectedBook!['title']}»' : 'تأیید پیوست کتاب',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: EttehadColors.primary,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Tab 2: AI Generated Analysis & Citations
                  ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _aiPresets.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (ctx, idx) {
                      final p = _aiPresets[idx];
                      return Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: EttehadColors.border),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withValues(alpha: 0.02), blurRadius: 4, offset: const Offset(0, 1)),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.auto_awesome_rounded, size: 16, color: EttehadColors.amberDark),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    p['title']!,
                                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5, color: EttehadColors.navy),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: EttehadColors.surfaceLow,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                p['excerpt']!,
                                style: const TextStyle(fontSize: 10.5, color: Colors.black87, height: 1.5),
                              ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    'منبع: ${p['bookTitle']!}',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 10, color: EttehadColors.primary, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                ElevatedButton.icon(
                                  onPressed: () {
                                    final matchedBook = widget.repo.books.firstWhere(
                                      (b) => b['title'].toString().contains(p['bookTitle']!.split(' ').first),
                                      orElse: () => widget.repo.books.isNotEmpty ? widget.repo.books.first : {'id': '1'},
                                    );
                                    _submitSelection(
                                      bookId: matchedBook['id'].toString(),
                                      bookTitle: p['bookTitle']!,
                                      excerpt: p['excerpt']!,
                                      source: 'ai',
                                    );
                                  },
                                  icon: const Icon(Icons.send_rounded, size: 14),
                                  label: const Text('پیوست این تحلیل هوش به استفتاء', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: EttehadColors.emeraldDark,
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
