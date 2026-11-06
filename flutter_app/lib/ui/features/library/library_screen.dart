import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../data/ettehad_repository.dart';
import '../../core/theme.dart';
import '../qna/qna_screen.dart';

class LibraryScreen extends StatefulWidget {
  final EttehadRepository repo;
  final void Function(String bookId, String bookTitle)? onAskAiAboutBook;
  final VoidCallback? onOpenProfile;

  const LibraryScreen({
    super.key,
    required this.repo,
    this.onAskAiAboutBook,
    this.onOpenProfile,
  });

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  String _subView = 'storefront'; // 'storefront' | 'shelves'
  String _searchQuery = '';
  String _selectedCategoryId = 'all';
  String _selectedCategoryTitle = '';
  String _selectedAuthor = 'all';
  String _selectedPublisher = 'all';
  String _selectedEra = 'all';
  String _sortBy = 'popular'; // 'popular' | 'rating' | 'newest' | 'alpha'

  final PageController _heroCarouselCtrl = PageController();
  int _currentHeroSlide = 0;
  Timer? _heroTimer;

  static const List<Map<String, dynamic>> _showcaseCards = [
    {'id': 'all', 'title': 'همه کتاب‌ها', 'icon': Icons.menu_book_rounded},
    {'id': 'tafsir', 'title': 'تفسیر قرآن', 'icon': Icons.auto_stories_rounded},
    {'id': 'fiqh', 'title': 'فقه مقارن', 'icon': Icons.balance_rounded},
    {'id': 'hadith', 'title': 'حدیث نبوی', 'icon': Icons.history_edu_rounded},
    {'id': 'akhlaq', 'title': 'اخلاق و عرفان', 'icon': Icons.favorite_rounded},
    {'id': 'wahdat', 'title': 'وحدت و تقریب', 'icon': Icons.handshake_rounded},
  ];

  static const List<Map<String, dynamic>> _allCategoryFilters = [
    {'id': 'all', 'title': 'همه موضوعات', 'icon': Icons.auto_stories_rounded},
    {'id': 'tafsir', 'title': 'تفسیر قرآن', 'icon': Icons.menu_book_rounded},
    {'id': 'hadith', 'title': 'حدیث و روایات', 'icon': Icons.format_quote_rounded},
    {'id': 'fiqh', 'title': 'فقه مقارن', 'icon': Icons.gavel_rounded},
    {'id': 'kalam', 'title': 'کلام و عقاید', 'icon': Icons.psychology_rounded},
    {'id': 'akhlaq', 'title': 'اخلاق و سلوک', 'icon': Icons.spa_rounded},
    {'id': 'history', 'title': 'تاریخ و سیره', 'icon': Icons.history_edu_rounded},
    {'id': 'wahdat', 'title': 'تقریب مذاهب', 'icon': Icons.handshake_rounded},
  ];

  static const List<String> _authorFilters = [
    'all',
    'علامه طباطبایی',
    'شیخ طوسی',
    'امام علی بن ابی‌طالب (ع)',
    'امام خمینی (ره)',
    'دکتر مصطفی الخن',
    'ابن قدامه مقدسی',
    'شیخ محمود شلتوت',
  ];

  static const List<String> _publisherFilters = [
    'all',
    'دارالکتب الاسلامیه',
    'دارالعرفان',
    'بوستان کتاب',
    'دارالمعارف الاسلامیه',
    'مجمع جهانی تقریب',
  ];

  static const List<Map<String, String>> _eraFilters = [
    {'id': 'all', 'title': 'همه ادوار'},
    {'id': 'classic', 'title': 'کتب کهن و متقدم'},
    {'id': 'contemporary', 'title': 'معاصر و نوین'},
  ];

  @override
  void initState() {
    super.initState();
    _startHeroTimer();
  }

  void _startHeroTimer() {
    _heroTimer?.cancel();
    _heroTimer = Timer.periodic(const Duration(seconds: 4), (timer) {
      if (!mounted) return;
      if (_heroCarouselCtrl.hasClients) {
        final nextPage = (_currentHeroSlide + 1) % 3;
        _heroCarouselCtrl.animateToPage(
          nextPage,
          duration: const Duration(milliseconds: 650),
          curve: Curves.easeInOutCubic,
        );
      }
    });
  }

  @override
  void dispose() {
    _heroTimer?.cancel();
    _heroCarouselCtrl.dispose();
    super.dispose();
  }

  bool get _hasActiveFilters =>
      _selectedCategoryId != 'all' ||
      _selectedAuthor != 'all' ||
      _selectedPublisher != 'all' ||
      _selectedEra != 'all' ||
      _sortBy != 'popular';

  int get _activeFilterCount {
    var c = 0;
    if (_selectedCategoryId != 'all') c++;
    if (_selectedAuthor != 'all') c++;
    if (_selectedPublisher != 'all') c++;
    if (_selectedEra != 'all') c++;
    if (_sortBy != 'popular') c++;
    return c;
  }

  List<Map<String, dynamic>> get _filteredBooks {
    var list = widget.repo.books.where((b) {
      final title = (b['title'] ?? '').toString();
      final author = (b['author'] ?? '').toString();
      final desc = (b['description'] ?? '').toString();
      final pub = (b['publisher'] ?? '').toString();

      if (_searchQuery.trim().isNotEmpty) {
        final q = _searchQuery.trim().toLowerCase();
        if (!title.toLowerCase().contains(q) &&
            !author.toLowerCase().contains(q) &&
            !desc.toLowerCase().contains(q) &&
            !pub.toLowerCase().contains(q)) {
          return false;
        }
      }

      if (_selectedCategoryId != 'all') {
        final catId = (b['category_id'] ?? '').toString().toLowerCase();
        final tags = (b['tags'] ?? '').toString().toLowerCase();
        final topics = (b['topics'] ?? '').toString().toLowerCase();
        final t = title.toLowerCase();
        final d = desc.toLowerCase();

        final isHist = _selectedCategoryId.contains('hist') || _selectedCategoryId.contains('تاریخ');
        final isTaf = _selectedCategoryId.contains('taf') || _selectedCategoryId.contains('تفسیر');
        final isFiq = _selectedCategoryId.contains('fiq') || _selectedCategoryId.contains('فقه');
        final isHad = _selectedCategoryId.contains('had') || _selectedCategoryId.contains('حدیث');
        final isWah = _selectedCategoryId.contains('wah') || _selectedCategoryId.contains('وحدت');
        final isAkh = _selectedCategoryId.contains('akh') || _selectedCategoryId.contains('اخلاق');

        if (catId.contains(_selectedCategoryId) || tags.contains(_selectedCategoryId) || topics.contains(_selectedCategoryId)) {
          // direct match
        } else if (isHist) {
          if (!catId.contains('history') && !t.contains('تاریخ') && !t.contains('سیره') && !d.contains('تاریخ')) return false;
        } else if (isTaf) {
          if (!catId.contains('tafsir') && !t.contains('تفسیر') && !d.contains('قرآن')) return false;
        } else if (isFiq) {
          if (!catId.contains('fiqh') && !t.contains('فقه') && !t.contains('احکام') && !t.contains('شافعی') && !t.contains('حنبلی')) return false;
        } else if (isHad) {
          if (!catId.contains('hadith') && !t.contains('حدیث') && !t.contains('نهج')) return false;
        } else if (isWah) {
          if (!catId.contains('wahdat') && !tags.contains('وحدت') && !t.contains('اخوت')) return false;
        } else if (isAkh) {
          if (!catId.contains('akhlaq') && !t.contains('اخلاق') && !t.contains('حدیث')) return false;
        } else {
          if (!catId.contains(_selectedCategoryId) && !tags.contains(_selectedCategoryId)) return false;
        }
      }

      if (_selectedAuthor != 'all') {
        if (!author.contains(_selectedAuthor)) return false;
      }

      if (_selectedPublisher != 'all') {
        if (!pub.contains(_selectedPublisher)) return false;
      }

      if (_selectedEra == 'classic') {
        final year = (b['publication_year'] as num?)?.toInt() ?? 1400;
        if (year > 1350 && !title.contains('نهج') && !title.contains('المیزان') && !title.contains('فقه')) {
          return false;
        }
      } else if (_selectedEra == 'contemporary') {
        final year = (b['publication_year'] as num?)?.toInt() ?? 1400;
        if (year < 1350) return false;
      }

      return true;
    }).toList();

    if (_sortBy == 'rating') {
      list.sort((a, b) => ((b['rating'] as num?)?.toDouble() ?? 0).compareTo((a['rating'] as num?)?.toDouble() ?? 0));
    } else if (_sortBy == 'alpha') {
      list.sort((a, b) => (a['title'] ?? '').toString().compareTo((b['title'] ?? '').toString()));
    }

    return list;
  }

  void _openBookDetailModal(Map<String, dynamic> book) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _BookDetailModal(
        book: book,
        repo: widget.repo,
        onStartReading: () {
          Navigator.of(ctx).pop();
          _openBookReader(book);
        },
        onAskAi: () {
          Navigator.of(ctx).pop();
          widget.onAskAiAboutBook?.call(
            book['id'].toString(),
            (book['title'] ?? 'کتاب').toString(),
          );
        },
      ),
    );
  }

  void _openBookReader(Map<String, dynamic> book) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: NativeBookReaderScreen(
            book: book,
            repo: widget.repo,
          ),
        ),
      ),
    );
  }

  void _openDedicatedSearchScreen() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: _LibrarySearchScreen(
            repo: widget.repo,
            onOpenBook: (book) => _openBookDetailModal(book),
            onOpenFilterModal: _showFilterModal,
          ),
        ),
      ),
    );
  }

  void _openShelfFullScreen(String shelfTitle, List<Map<String, dynamic>> books) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => _ShelfBooksScreen(
          shelfTitle: shelfTitle,
          books: books,
          repo: widget.repo,
          onOpenBook: (book) => _openBookDetailModal(book),
        ),
      ),
    );
  }

  void _showAddShelfDialog() {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          backgroundColor: EttehadColors.paper,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Text('ساخت قفسه شخصی جدید', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          content: TextField(
            controller: controller,
            decoration: InputDecoration(
              hintText: 'نام قفسه (مثلاً: مطالعات تفسیری من)',
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('انصراف'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: EttehadColors.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: () {
                widget.repo.addShelf(controller.text);
                Navigator.of(ctx).pop();
              },
              child: const Text('ایجاد قفسه', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  static IconData _getIconData(String name) {
    switch (name) {
      case 'history_edu':
      case 'history':
      case 'hourglass_bottom':
        return Icons.history_edu_rounded;
      case 'auto_stories':
        return Icons.auto_stories_rounded;
      case 'balance':
        return Icons.balance_rounded;
      case 'menu_book':
        return Icons.menu_book_rounded;
      case 'format_quote':
        return Icons.format_quote_rounded;
      case 'psychology':
        return Icons.psychology_rounded;
      case 'spa':
      case 'self_improvement':
        return Icons.spa_rounded;
      case 'handshake':
        return Icons.handshake_rounded;
      case 'public':
        return Icons.public_rounded;
      case 'star':
      case 'workspace_premium':
        return Icons.star_rounded;
      case 'school':
        return Icons.school_rounded;
      case 'favorite':
        return Icons.favorite_rounded;
      case 'water_drop':
        return Icons.water_drop_rounded;
      case 'payments':
        return Icons.payments_rounded;
      case 'family_restroom':
        return Icons.family_restroom_rounded;
      case 'rule':
        return Icons.gavel_rounded;
      case 'new_releases':
        return Icons.new_releases_rounded;
      case 'lightbulb':
        return Icons.lightbulb_rounded;
      case 'record_voice_over':
        return Icons.record_voice_over_rounded;
      case 'people':
        return Icons.people_rounded;
      case 'verified':
        return Icons.verified_rounded;
      case 'forum':
        return Icons.forum_rounded;
      case 'location_city':
        return Icons.location_city_rounded;
      case 'devices':
        return Icons.devices_rounded;
      case 'account_balance':
        return Icons.account_balance_rounded;
      default:
        return Icons.category_rounded;
    }
  }

  void _openCategoriesFullScreen({String? initialCategory}) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (ctx) => _LibraryCategoriesFullScreen(
          repo: widget.repo,
          selectedCategoryId: _selectedCategoryId,
          initialExpandedId: initialCategory,
          onSelectCategory: (id, title) {
            setState(() {
              _selectedCategoryId = id;
              _selectedCategoryTitle = title;
              _searchQuery = '';
            });
          },
        ),
      ),
    );
  }

  void _showFilterModal() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Directionality(
          textDirection: TextDirection.rtl,
          child: Container(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.88,
            ),
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            decoration: const BoxDecoration(
              color: EttehadColors.paper,
              borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
            ),
            child: ListView(
              children: [
                Center(
                  child: Container(
                    width: 42,
                    height: 5,
                    margin: const EdgeInsets.only(bottom: 14),
                    decoration: BoxDecoration(
                      color: Colors.black26,
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.tune_rounded, color: EttehadColors.primary, size: 22),
                        const SizedBox(width: 8),
                        const Text(
                          'فیلترهای پیشرفته و موضوعی',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                        ),
                        if (_hasActiveFilters) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                            decoration: BoxDecoration(
                              color: EttehadColors.primary,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              '${toPersianDigits(_activeFilterCount)} فیلتر فعال',
                              style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ],
                    ),
                    TextButton(
                      onPressed: () {
                        setState(() {
                          _selectedCategoryId = 'all';
                          _selectedAuthor = 'all';
                          _selectedPublisher = 'all';
                          _selectedEra = 'all';
                          _sortBy = 'popular';
                          _searchQuery = '';
                        });
                        setModalState(() {});
                      },
                      child: const Text(
                        'بازنشانی همه',
                        style: TextStyle(color: EttehadColors.amberDark, fontWeight: FontWeight.bold, fontSize: 12),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 24),

                // 1. Categories
                const Text(
                  'دسته‌بندی موضوعی کتب:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: EttehadColors.navy),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _allCategoryFilters.map((cat) {
                    final active = _selectedCategoryId == cat['id'];
                    return ChoiceChip(
                      selected: active,
                      selectedColor: EttehadColors.primary,
                      backgroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(color: active ? EttehadColors.primary : EttehadColors.border),
                      ),
                      label: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(cat['icon'] as IconData, size: 14, color: active ? Colors.white : EttehadColors.primary),
                          const SizedBox(width: 6),
                          Text(
                            cat['title'] as String,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: active ? Colors.white : EttehadColors.navy,
                            ),
                          ),
                        ],
                      ),
                      onSelected: (sel) {
                        setState(() => _selectedCategoryId = cat['id'] as String);
                        setModalState(() {});
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),

                // 2. Authors
                const Text(
                  'مؤلف و نویسنده اثر:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: EttehadColors.navy),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _authorFilters.map((auth) {
                    final isAll = auth == 'all';
                    final active = _selectedAuthor == auth;
                    return ChoiceChip(
                      selected: active,
                      selectedColor: EttehadColors.primary,
                      backgroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(color: active ? EttehadColors.primary : EttehadColors.border),
                      ),
                      label: Text(
                        isAll ? 'همه مؤلفان' : auth,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: active ? Colors.white : EttehadColors.navy,
                        ),
                      ),
                      onSelected: (sel) {
                        setState(() => _selectedAuthor = auth);
                        setModalState(() {});
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),

                // 3. Publishers
                const Text(
                  'ناشر و مرکز نشر:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: EttehadColors.navy),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _publisherFilters.map((pub) {
                    final isAll = pub == 'all';
                    final active = _selectedPublisher == pub;
                    return ChoiceChip(
                      selected: active,
                      selectedColor: EttehadColors.primary,
                      backgroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(color: active ? EttehadColors.primary : EttehadColors.border),
                      ),
                      label: Text(
                        isAll ? 'همه ناشران' : pub,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: active ? Colors.white : EttehadColors.navy,
                        ),
                      ),
                      onSelected: (sel) {
                        setState(() => _selectedPublisher = pub);
                        setModalState(() {});
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),

                // 4. Time Era / History
                const Text(
                  'دوره تاریخی و زمان انتشار:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: EttehadColors.navy),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _eraFilters.map((era) {
                    final active = _selectedEra == era['id'];
                    return ChoiceChip(
                      selected: active,
                      selectedColor: EttehadColors.primary,
                      backgroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                        side: BorderSide(color: active ? EttehadColors.primary : EttehadColors.border),
                      ),
                      label: Text(
                        era['title']!,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: active ? Colors.white : EttehadColors.navy,
                        ),
                      ),
                      onSelected: (sel) {
                        setState(() => _selectedEra = era['id']!);
                        setModalState(() {});
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),

                // 5. Sorting
                const Text(
                  'مرتب‌سازی نتایج:',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: EttehadColors.navy),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    _buildSortChip('popular', 'محبوب‌ترین', Icons.trending_up_rounded, setModalState),
                    const SizedBox(width: 8),
                    _buildSortChip('rating', 'بالاترین امتیاز', Icons.star_rounded, setModalState),
                    const SizedBox(width: 8),
                    _buildSortChip('alpha', 'الفبایی', Icons.sort_by_alpha_rounded, setModalState),
                  ],
                ),
                const SizedBox(height: 26),

                // Apply Button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: EttehadColors.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      elevation: 2,
                    ),
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('اعمال فیلتر و مشاهده ویترین', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSortChip(String id, String title, IconData icon, StateSetter setModalState) {
    final active = _sortBy == id;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _sortBy = id);
          setModalState(() {});
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: active ? EttehadColors.navy : Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: active ? EttehadColors.navy : EttehadColors.border),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 14, color: active ? Colors.amberAccent : EttehadColors.primary),
              const SizedBox(width: 4),
              Text(
                title,
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.bold,
                  color: active ? Colors.white : EttehadColors.navy,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<Map<String, dynamic>> _getBooksForShelf(String key) {
    switch (key) {
      case 'tafsir':
        return widget.repo.books.where((b) {
          final t = (b['title'] ?? '').toString() + (b['category_id'] ?? '').toString();
          return t.contains('تفسیر') || t.contains('tafsir') || t.contains('قرآن');
        }).toList();
      case 'hadith':
        return widget.repo.books.where((b) {
          final t = (b['title'] ?? '').toString() + (b['category_id'] ?? '').toString();
          return t.contains('حدیث') || t.contains('روایت') || t.contains('نهج') || t.contains('hadith') || t.contains('صحیفه');
        }).toList();
      case 'fiqh':
        return widget.repo.books.where((b) {
          final t = (b['title'] ?? '').toString() + (b['category_id'] ?? '').toString();
          return t.contains('فقه') || t.contains('احکام') || t.contains('fiqh');
        }).toList();
      case 'kalam':
        return widget.repo.books.where((b) {
          final t = (b['title'] ?? '').toString() + (b['category_id'] ?? '').toString();
          return t.contains('کلام') || t.contains('عقاید') || t.contains('فلسفه') || t.contains('kalam');
        }).toList();
      case 'akhlaq':
        return widget.repo.books.where((b) {
          final t = (b['title'] ?? '').toString() + (b['category_id'] ?? '').toString();
          return t.contains('اخلاق') || t.contains('سلوک') || t.contains('عرفان') || t.contains('akhlaq') || t.contains('سیره');
        }).toList();
      case 'wahdat':
        return widget.repo.books.where((b) {
          final t = (b['title'] ?? '').toString() + (b['tags'] ?? '').toString();
          return t.contains('وحدت') || t.contains('تقریب') || t.contains('اخوت');
        }).toList();
      default:
        return widget.repo.books.take(7).toList();
    }
  }

  Widget _buildTopProfileHeader() {
    final avatarIndex = int.tryParse(widget.repo.userAvatar) ?? 0;
    const avatarIcons = [
      Icons.person_rounded,
      Icons.school_rounded,
      Icons.mosque_rounded,
      Icons.menu_book_rounded,
      Icons.history_edu_rounded,
      Icons.account_balance_rounded,
    ];
    final activeIcon = (avatarIndex >= 0 && avatarIndex < avatarIcons.length)
        ? avatarIcons[avatarIndex]
        : Icons.person_rounded;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: EttehadColors.border),
        boxShadow: [
          BoxShadow(
            color: EttehadColors.navy.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  padding: const EdgeInsets.all(5),
                  decoration: BoxDecoration(
                    color: EttehadColors.navy,
                    borderRadius: BorderRadius.circular(13),
                    boxShadow: [
                      BoxShadow(
                        color: EttehadColors.navy.withValues(alpha: 0.2),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Image.asset('assets/images/logo_symbol_white.png', fit: BoxFit.contain),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        'کتابخوان معارفی اتحاد',
                        style: TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w900,
                          color: EttehadColors.navy,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        widget.repo.isLoggedIn ? widget.repo.userFullName : 'دانشنامه و کتابخوان جامع اسلامی',
                        style: TextStyle(
                          fontSize: 10.5,
                          color: widget.repo.isLoggedIn ? EttehadColors.primary : Colors.black54,
                          fontWeight: widget.repo.isLoggedIn ? FontWeight.bold : FontWeight.normal,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),

          // Profile Button / Chip
          InkWell(
            onTap: widget.onOpenProfile,
            borderRadius: BorderRadius.circular(14),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: EttehadColors.primary.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: EttehadColors.primary.withValues(alpha: 0.25)),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 13,
                    backgroundColor: EttehadColors.primary,
                    child: Icon(
                      widget.repo.isLoggedIn ? activeIcon : Icons.account_circle_outlined,
                      color: Colors.white,
                      size: 16,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    widget.repo.isLoggedIn ? 'پروفایل' : 'ورود / نمایه',
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w900,
                      color: EttehadColors.primary,
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

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      color: EttehadColors.primary,
      onRefresh: () async {
        final synced = await widget.repo.syncWithBackend();
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(synced ? 'همگام‌سازی با سرور با موفقیت انجام شد.' : 'سرور در دسترس نیست؛ حالت آفلاین فعال است.'),
            duration: const Duration(seconds: 2),
          ),
        );
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
        children: [
          // 0. TOP APP BAR & USER PROFILE BAR
          _buildTopProfileHeader(),
          const SizedBox(height: 12),

          // 1. INNOVATIVE TOUCH SEGMENTED SWITCHER (WITH HAPTIC & FLUID SLIDER)
          _buildTouchSwitcher(),
          const SizedBox(height: 14),

          if (_subView == 'storefront') ...[
            // 2. SEARCH BAR WITH FILTER INTEGRATED INSIDE THE BOX
            GestureDetector(
              onTap: _openDedicatedSearchScreen,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: EttehadColors.border),
                  boxShadow: [
                    BoxShadow(
                      color: EttehadColors.navy.withValues(alpha: 0.05),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    const Icon(Icons.search_rounded, color: EttehadColors.primary, size: 28),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _searchQuery.isNotEmpty ? _searchQuery : 'جستجوی کتاب، نویسنده، ناشر یا مفهوم...',
                        style: TextStyle(
                          fontSize: 12.5,
                          color: _searchQuery.isNotEmpty ? EttehadColors.navy : Colors.black45,
                          fontWeight: _searchQuery.isNotEmpty ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    ),
                    if (_searchQuery.isNotEmpty)
                      GestureDetector(
                        onTap: () => setState(() => _searchQuery = ''),
                        child: const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 6),
                          child: Icon(Icons.close_rounded, size: 23, color: Colors.black45),
                        ),
                      ),
                    Container(
                      height: 20,
                      width: 1,
                      color: Colors.black12,
                      margin: const EdgeInsets.symmetric(horizontal: 6),
                    ),
                    // Categories Shortcut Button inside search box (Requirement: دکمه دسته‌بندی با زیرمجموعه‌های متعدد)
                    GestureDetector(
                      onTap: () => _openCategoriesFullScreen(),
                      child: Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: _selectedCategoryId != 'all' ? EttehadColors.primary.withValues(alpha: 0.12) : Colors.transparent,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Tooltip(
                          message: 'دسته‌بندی‌های موضوعی و تخصصی',
                          child: Badge(
                            isLabelVisible: _selectedCategoryId != 'all',
                            backgroundColor: EttehadColors.primary,
                            child: Icon(
                              Icons.account_tree_rounded,
                              size: 26,
                              color: _selectedCategoryId != 'all' ? EttehadColors.primary : Colors.black54,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),

            // 3. SHOWCASE HERO BANNER (FULL WIDTH ATTACHED TO SCREEN EDGES, HEIGHT +30%)
            SizedBox(
              height: 218.0,
              child: OverflowBox(
                minWidth: MediaQuery.of(context).size.width,
                maxWidth: MediaQuery.of(context).size.width,
                minHeight: 218.0,
                maxHeight: 218.0,
                alignment: Alignment.center,
                child: _buildShowcaseHeroCarousel(),
              ),
            ),
            const SizedBox(height: 24),

            // 4. CATEGORY ICONS ROW (ICONS BOOSTED +30%)
            _buildCompactCategoryIconsRow(),
            const SizedBox(height: 24),

            // Active category indicator bar (when filtered)
            if (_selectedCategoryId != 'all' || _hasActiveFilters)
              Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: EttehadColors.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: EttehadColors.primary.withValues(alpha: 0.2)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.filter_alt_rounded, size: 16, color: EttehadColors.primary),
                        const SizedBox(width: 6),
                        Text(
                          _selectedCategoryTitle.isNotEmpty
                              ? 'دسته‌بندی: $_selectedCategoryTitle'
                              : 'دسته‌بندی: ${_allCategoryFilters.firstWhere((c) => c['id'] == _selectedCategoryId, orElse: () => {'title': 'شاخه انتخابی'})['title']}',
                          style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
                        ),
                      ],
                    ),
                    GestureDetector(
                      onTap: () {
                        setState(() {
                          _selectedCategoryId = 'all';
                          _selectedAuthor = 'all';
                          _selectedPublisher = 'all';
                          _selectedEra = 'all';
                        });
                      },
                      child: const Row(
                        children: [
                          Text('نمایش همه', style: TextStyle(fontSize: 11, color: EttehadColors.amberDark, fontWeight: FontWeight.bold)),
                          SizedBox(width: 4),
                          Icon(Icons.close_rounded, size: 14, color: EttehadColors.amberDark),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

            // 6. MAIN SHOWCASE SHELVES & INTERSTITIAL PROMOTIONAL CARDS
            if (_selectedCategoryId != 'all') ...[
              // DYNAMIC CATEGORIZED SHOWCASE WITH MULTIPLE TITLES
              ..._buildDynamicCategorizedShowcase(_selectedCategoryId),
            ] else ...[
              // DEFAULT DIVERSE SHOWCASE SHELVES WITH INTERSTITIAL PROMOTIONAL CAMPAIGN CARDS
              _buildHorizontalShelf(
                'پربازدیدترین‌ها و کتب برگزیده',
                Icons.star_rounded,
                _getBooksForShelf('featured'),
              ),

              _buildHorizontalShelf(
                'تفسیر و علوم قرآن کریم',
                Icons.menu_book_rounded,
                _getBooksForShelf('tafsir'),
              ),

              // INTERSTITIAL PROMOTIONAL CAMPAIGN BOX 1 (کتاب‌های تازه انتشار با درصد تخفیف)
              _buildPromoCampaignBox(
                title: 'جشنواره آثار تازه انتشار و کتب ویژه',
                subtitle: 'تخفیف ویژه مطالعه آنلاین و دریافت خلاصه صوتی معارف فریقین',
                badgeText: '🔥 پیشنهاد ویژه جشنواره با ۳۰٪ تخفیف',
                promoBooks: widget.repo.books.take(4).toList(),
              ),

              _buildHorizontalShelf(
                'احادیث، روایات و جوامع حدیثی',
                Icons.format_quote_rounded,
                _getBooksForShelf('hadith'),
              ),

              _buildHorizontalShelf(
                'فقه مقارن و احکام مذاهب اسلامی',
                Icons.balance_rounded,
                _getBooksForShelf('fiqh'),
              ),

              // INTERSTITIAL PROMOTIONAL CAMPAIGN BOX 2 (مناسبتی هفته وحدت)
              _buildPromoCampaignBox(
                title: 'مجموعه تخصصی مناسبت هفته وحدت و تقریب',
                subtitle: 'آثار برگزیده علمای برجسته فریقین در مسیر تفاهم و همبستگی امت اسلام',
                badgeText: '✨ دسترسی رایگان به آثار مرجع',
                promoBooks: _getBooksForShelf('wahdat').isNotEmpty
                    ? _getBooksForShelf('wahdat')
                    : widget.repo.books.skip(2).take(4).toList(),
              ),

              _buildHorizontalShelf(
                'کلام، عقاید و فلسفه اسلامی',
                Icons.psychology_rounded,
                _getBooksForShelf('kalam'),
              ),

              _buildHorizontalShelf(
                'اخلاق، عرفان و سیره‌نگاری',
                Icons.spa_rounded,
                _getBooksForShelf('akhlaq'),
              ),
            ],
          ] else ...[
            // 7. MY SHELVES VIEW (قفسه‌های من)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'قفسه‌ها و میز مطالعه من',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                      ),
                      Text(
                        'چیدمان شخصی کتب بر اساس موضوعات پژوهشی شما',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 11, color: Colors.black54),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: _showAddShelfDialog,
                  icon: const Icon(Icons.add_rounded, size: 16),
                  label: const Text('قفسه جدید', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: EttehadColors.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            ...widget.repo.shelves.map((shelf) => _build3DShelfCard(shelf)),
          ],
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // TOUCH SWITCHER (Requirement 1: سوئیچر لمسی روان قفسه‌ها و ویترین)
  // -------------------------------------------------------------
  Widget _buildTouchSwitcher() {
    final isStorefront = _subView == 'storefront';
    return GestureDetector(
      onHorizontalDragEnd: (details) {
        if (details.primaryVelocity != null) {
          if (details.primaryVelocity! > 100 && !isStorefront) {
            HapticFeedback.lightImpact();
            setState(() => _subView = 'storefront');
          } else if (details.primaryVelocity! < -100 && isStorefront) {
            HapticFeedback.lightImpact();
            setState(() => _subView = 'shelves');
          }
        }
      },
      child: Container(
        height: 46,
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: EttehadColors.surfaceLow,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: EttehadColors.border),
        ),
        child: Stack(
          children: [
            AnimatedAlign(
              alignment: isStorefront ? Alignment.centerRight : Alignment.centerLeft,
              duration: const Duration(milliseconds: 240),
              curve: Curves.easeOutCubic,
              child: FractionallySizedBox(
                widthFactor: 0.5,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [EttehadColors.navy, EttehadColors.primary],
                      begin: Alignment.topRight,
                      end: Alignment.bottomLeft,
                    ),
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: EttehadColors.primary.withValues(alpha: 0.28),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: () {
                      if (!isStorefront) {
                        HapticFeedback.selectionClick();
                        setState(() => _subView = 'storefront');
                      }
                    },
                    child: Center(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.storefront_rounded,
                            size: 22,
                            color: isStorefront ? Colors.white : EttehadColors.navy.withValues(alpha: 0.7),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'ویترین و کاوش',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: isStorefront ? FontWeight.w900 : FontWeight.w600,
                              color: isStorefront ? Colors.white : EttehadColors.navy.withValues(alpha: 0.7),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: () {
                      if (isStorefront) {
                        HapticFeedback.selectionClick();
                        setState(() => _subView = 'shelves');
                      }
                    },
                    child: Center(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.shelves,
                            size: 22,
                            color: !isStorefront ? Colors.white : EttehadColors.navy.withValues(alpha: 0.7),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'قفسه‌های من',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: !isStorefront ? FontWeight.w900 : FontWeight.w600,
                              color: !isStorefront ? Colors.white : EttehadColors.navy.withValues(alpha: 0.7),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // -------------------------------------------------------------
  // SHOWCASE HERO POSTER CAROUSEL (Requirement: ارتفاع +۳۰٪ و چسبیده کامل به کناره‌ها)
  // -------------------------------------------------------------
  Widget _buildShowcaseHeroCarousel() {
    const double heroHeight = 218.0; // Increased by 30% from 168.0

    final slides = widget.repo.posters.isNotEmpty
        ? widget.repo.posters
        : [
            {
              'badge': '✨ ویترین جامع فریقین',
              'title': 'مخزن کتب تفسیری، روایی و فقه مقارن',
              'desc': 'همراه با کاوش معنایی و ارجاع مستقیم به دستیار هوشمند اتحادیار',
              'action': 'شروع مطالعه',
              'action_target': 'first_book',
              'gradient': [const Color(0xFF071F4A), const Color(0xFF0B57B8), const Color(0xFF0284C7)],
            },
            {
              'badge': '🕊️ جشنواره تقریب مذاهب',
              'title': 'آثار تطبیقی علمای برجسته فریقین',
              'desc': 'شناخت متقابل میراث علمی جهان اسلام فارغ از تعصبات مذهبی',
              'action': 'کتب تقریب',
              'action_target': 'wahdat',
              'gradient': [const Color(0xFF042F2E), const Color(0xFF0F766E), const Color(0xFF0D9488)],
            },
            {
              'badge': '📖 آثار تازه انتشار',
              'title': 'پژوهش‌های نوین و شروح معاصر',
              'desc': 'دسترسی نامحدود به متن کامل و استخراج هوشمند فهرست موضوعی',
              'action': 'آثار جدید',
              'action_target': 'search',
              'gradient': [const Color(0xFF4C1D95), const Color(0xFF6D28D9), const Color(0xFF9333EA)],
            },
          ];

    List<Color> parseGradient(dynamic g) {
      if (g is List<Color>) return g;
      if (g is List) {
        final colors = <Color>[];
        for (final item in g) {
          if (item is Color) {
            colors.add(item);
          } else if (item is String) {
            final hex = item.replaceFirst('#', '');
            final val = int.tryParse(hex.length == 6 ? 'FF$hex' : hex, radix: 16);
            if (val != null) colors.add(Color(val));
          }
        }
        if (colors.isNotEmpty) return colors;
      }
      return [const Color(0xFF071F4A), const Color(0xFF0B57B8), const Color(0xFF0284C7)];
    }

    return Column(
      children: [
        SizedBox(
          height: heroHeight,
          child: PageView.builder(
            controller: _heroCarouselCtrl,
            onPageChanged: (idx) => setState(() => _currentHeroSlide = idx),
            itemCount: slides.length,
            itemBuilder: (ctx, idx) {
              final s = slides[idx];
              final grad = parseGradient(s['gradient']);
              return Container(
                margin: EdgeInsets.zero,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: grad,
                    begin: Alignment.topRight,
                    end: Alignment.bottomLeft,
                  ),
                  borderRadius: BorderRadius.zero,
                  boxShadow: [
                    BoxShadow(
                      color: grad.first.withValues(alpha: 0.35),
                      blurRadius: 14,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: Stack(
                  children: [
                    Positioned(
                      left: -12,
                      bottom: -12,
                      child: Opacity(
                        opacity: 0.15,
                        child: Image.asset(
                          'assets/images/logo_symbol_white.png',
                          width: 140,
                          height: 140,
                          fit: BoxFit.contain,
                        ),
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                              decoration: BoxDecoration(
                                color: EttehadColors.amber,
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Text(
                                s['badge'] as String,
                                style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.bold),
                              ),
                            ),
                            Container(
                              width: 38,
                              height: 38,
                              padding: const EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.18),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Image.asset('assets/images/logo_symbol_white.png', fit: BoxFit.contain),
                            ),
                          ],
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              s['title'] as String,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(color: Colors.white, fontSize: 16.5, fontWeight: FontWeight.w900),
                            ),
                            const SizedBox(height: 5),
                            Text(
                              s['desc'] as String,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12, height: 1.35),
                            ),
                          ],
                        ),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.white,
                                foregroundColor: EttehadColors.navy,
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                visualDensity: VisualDensity.compact,
                              ),
                              onPressed: () {
                                if (idx == 0) {
                                  if (widget.repo.books.isNotEmpty) {
                                    _openBookDetailModal(widget.repo.books.first);
                                  }
                                } else if (idx == 1) {
                                  setState(() => _selectedCategoryId = 'wahdat');
                                } else {
                                  _openDedicatedSearchScreen();
                                }
                              },
                              child: Text(
                                s['action'] as String,
                                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900),
                              ),
                            ),
                            // Dots indicator
                            Row(
                              children: List.generate(
                                slides.length,
                                (dotIdx) => AnimatedContainer(
                                  duration: const Duration(milliseconds: 200),
                                  width: _currentHeroSlide == dotIdx ? 20 : 7,
                                  height: 7,
                                  margin: const EdgeInsets.only(right: 4),
                                  decoration: BoxDecoration(
                                    color: _currentHeroSlide == dotIdx ? Colors.amberAccent : Colors.white38,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // COMPACT CATEGORY ICONS (Requirement: ایکون‌ها +۳۰٪ بزرگتر)
  // -------------------------------------------------------------
  Widget _buildCompactCategoryIconsRow() {
    return SizedBox(
      height: 88, // Increased height from 68 (+30%)
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _showcaseCards.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (ctx, i) {
          final item = _showcaseCards[i];
          final isSelected = _selectedCategoryId == item['id'];
          return GestureDetector(
            onTap: () {
              HapticFeedback.selectionClick();
              setState(() => _selectedCategoryId = item['id'] as String);
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 104, // Increased width from 82 (+30%)
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topRight,
                  end: Alignment.bottomLeft,
                  colors: isSelected
                      ? [EttehadColors.navy, EttehadColors.primary]
                      : [EttehadColors.skyCardStart, EttehadColors.skyCardEnd],
                ),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: isSelected ? EttehadColors.amber : const Color(0xFF7DD3FC),
                  width: isSelected ? 1.6 : 0.8,
                ),
                boxShadow: [
                  BoxShadow(
                    color: EttehadColors.primary.withValues(alpha: isSelected ? 0.22 : 0.06),
                    blurRadius: 6,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    item['icon'] as IconData,
                    size: 29, // Increased icon size from 22 (+30%)
                    color: isSelected ? Colors.white : EttehadColors.navy,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    item['title'] as String,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w800,
                      color: isSelected ? Colors.white : EttehadColors.navy,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // -------------------------------------------------------------
  // DYNAMIC CATEGORIZED SHOWCASE (Requirement 10: با عناوین مختلف)
  // -------------------------------------------------------------
  List<Widget> _buildDynamicCategorizedShowcase(String catId) {
    final catLower = catId.toLowerCase();
    final matchingBooks = widget.repo.books.where((b) {
      final bCat = (b['category_id'] ?? b['categoryId'] ?? '').toString().toLowerCase();
      final title = (b['title'] ?? '').toString();
      final desc = (b['description'] ?? '').toString();
      if (bCat == catLower) return true;
      if (catLower.contains('fiqh') || catLower.contains('فقه')) {
        return bCat.contains('fiqh') || title.contains('فقه') || desc.contains('فقه') || title.contains('قدوري') || title.contains('بداية') || title.contains('شرائع') || title.contains('عمدة') || title.contains('منهاج') || title.contains('رسالة');
      }
      if (catLower.contains('hadith') || catLower.contains('حدیث')) {
        return bCat.contains('hadith') || title.contains('حدیث') || title.contains('أحاديث') || title.contains('صالحين') || title.contains('نووية');
      }
      if (catLower.contains('quran') || catLower.contains('taf') || catLower.contains('قرآن') || catLower.contains('تفسیر')) {
        return bCat.contains('quran') || title.contains('تفسير') || title.contains('قرآن') || desc.contains('قرآن');
      }
      if (catLower.contains('akhlaq') || catLower.contains('اخلاق')) {
        return bCat.contains('akhlaq') || title.contains('أذكار') || title.contains('آداب') || title.contains('أخلاق') || title.contains('تبيان');
      }
      if (catLower.contains('hist') || catLower.contains('تاریخ') || catLower.contains('سیره')) {
        return bCat.contains('history') || title.contains('شمائل') || title.contains('سیره');
      }
      return false;
    }).toList();

    if (matchingBooks.isNotEmpty) {
      return [
        _buildHorizontalShelf(
          'مجموعه آثار و کتب مرجع این بخش',
          Icons.auto_stories_rounded,
          matchingBooks,
        ),
        if (matchingBooks.length > 2)
          _buildHorizontalShelf(
            'پیشنهاد ویژه پژوهش و مطالعه تطبیقی',
            Icons.star_rounded,
            matchingBooks.reversed.toList(),
          ),
      ];
    } else {
      final filtered = _filteredBooks;
      return [
        _buildHorizontalShelf('کتب منتخب و اصلی این موضوع', Icons.category_rounded, filtered.take(4).toList()),
        if (filtered.length > 4)
          _buildHorizontalShelf('سایر منابع مطالعاتی و پژوهشی', Icons.library_books_rounded, filtered.skip(4).toList()),
      ];
    }
  }

  // -------------------------------------------------------------
  // HORIZONTAL SHELF (Requirements 5, 8, 11, 14: ابعاد +۳۰٪، لبه بینابینی، بیشتر)
  // -------------------------------------------------------------
  Widget _buildHorizontalShelf(String title, IconData icon, List<Map<String, dynamic>> shelfBooks) {
    if (shelfBooks.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header (Requirement 8 & 11: حذف شمارش اثر، اضافه شدن گزینه بیشتر)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    Icon(icon, size: 25, color: EttehadColors.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // More Action Link (Requirement 8)
              InkWell(
                borderRadius: BorderRadius.circular(8),
                onTap: () {
                  HapticFeedback.selectionClick();
                  _openShelfFullScreen(title, shelfBooks);
                },
                child: const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  child: Row(
                    children: [
                      Text(
                        'بیشتر',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: EttehadColors.primary),
                      ),
                      SizedBox(width: 2),
                      Icon(Icons.chevron_left_rounded, size: 22, color: EttehadColors.primary),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),

        // Horizontal Book Scroll (Requirement 14: ابعاد +۳۰٪: عرض 156 و ارتفاع قفسه 254)
        SizedBox(
          height: 254, // Increased by 30% from 195
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 4),
            itemCount: shelfBooks.length + 1, // +1 for the Trailing "More Books" Card
            separatorBuilder: (_, _) => const SizedBox(width: 14),
            itemBuilder: (ctx, i) {
              if (i < shelfBooks.length) {
                return _buildBookCoverOnShelf(shelfBooks[i], i);
              } else {
                // Requirement 8: کارت «کتاب‌های بیشتر» در انتهای اسکرول
                return _buildMoreBooksCard(title, shelfBooks);
              }
            },
          ),
        ),

        // Modern Hybrid Floating Shelf Ledge (Requirement 5: نه خیلی چوب، نه خیلی ساده)
        Container(
          height: 6,
          margin: const EdgeInsets.only(top: 3, bottom: 22),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [
                Color(0xFFE2E8F0),
                Color(0xFFCBD5E1),
                Color(0xFFF8FAFC),
                Color(0xFFCBD5E1),
                Color(0xFFE2E8F0),
              ],
            ),
            borderRadius: BorderRadius.circular(4),
            boxShadow: [
              BoxShadow(
                color: EttehadColors.navy.withValues(alpha: 0.12),
                blurRadius: 8,
                offset: const Offset(0, 3),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // -------------------------------------------------------------
  // BOOK COVER ON SHELF (Requirements 9 & 14: جلد شکیل و ابعاد +۳۰٪)
  // -------------------------------------------------------------
  Widget _buildBookCoverOnShelf(Map<String, dynamic> book, int index) {
    final title = (book['title'] ?? 'کتاب معارفی').toString();
    final author = (book['author'] ?? 'مؤلف اثر').toString();
    final rating = (book['rating'] as num?)?.toDouble() ?? 4.9;
    final catTitle = (book['category_id'] ?? 'کتاب').toString();
    final coverAsset = widget.repo.getCoverForBook(book);

    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        _openBookDetailModal(book);
      },
      child: Container(
        width: 156, // Increased by 30% from 120
        decoration: BoxDecoration(
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(10),
            bottomLeft: Radius.circular(10),
            topRight: Radius.circular(4),
            bottomRight: Radius.circular(4),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.32),
              blurRadius: 10,
              offset: const Offset(-4, 6),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(10),
            bottomLeft: Radius.circular(10),
            topRight: Radius.circular(4),
            bottomRight: Radius.circular(4),
          ),
          child: Stack(
            fit: StackFit.expand,
            children: [
              // Cover Artwork Image
              Image.asset(
                coverAsset,
                fit: BoxFit.cover,
                errorBuilder: (_, _, _) => Container(
                  color: const Color(0xFF0A2E6E),
                  padding: const EdgeInsets.all(12),
                  child: Center(
                    child: Text(
                      title,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
              ),
              // Spine shadow gradient on right edge (Persian RTL)
              Positioned(
                top: 0,
                bottom: 0,
                right: 0,
                width: 14,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Colors.black.withValues(alpha: 0.45), Colors.transparent],
                      begin: Alignment.centerRight,
                      end: Alignment.centerLeft,
                    ),
                  ),
                ),
              ),
              // Gradient scrim at bottom for text legibility
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                height: 75,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Colors.transparent, Colors.black.withValues(alpha: 0.85)],
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                    ),
                  ),
                ),
              ),
              // Top Badges (Category & Rating)
              Positioned(
                top: 8,
                left: 8,
                right: 8,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.amber.shade500,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        catTitle.length > 6 ? catTitle.substring(0, 6) : catTitle,
                        style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w900, color: Color(0xFF0A2E6E)),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.star_rounded, size: 12, color: Colors.amberAccent),
                          const SizedBox(width: 2),
                          Text(
                            toPersianDigits(rating.toStringAsFixed(1)),
                            style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              // Bottom Author & Title overlay
              Positioned(
                bottom: 8,
                left: 8,
                right: 8,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w900,
                        color: Colors.white,
                        shadows: [Shadow(color: Colors.black, blurRadius: 4)],
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      author,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 9.5,
                        color: Colors.white70,
                        shadows: [Shadow(color: Colors.black, blurRadius: 4)],
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

  // -------------------------------------------------------------
  // TRAILING MORE BOOKS CARD (Requirement 8: کارت کتاب‌های بیشتر)
  // -------------------------------------------------------------
  Widget _buildMoreBooksCard(String shelfTitle, List<Map<String, dynamic>> shelfBooks) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.lightImpact();
        _openShelfFullScreen(shelfTitle, shelfBooks);
      },
      child: Container(
        width: 140,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: EttehadColors.primary.withValues(alpha: 0.35), width: 1.5),
          boxShadow: [
            BoxShadow(
              color: EttehadColors.primary.withValues(alpha: 0.08),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: EttehadColors.primary.withValues(alpha: 0.1),
              ),
              child: const Icon(Icons.arrow_back_rounded, color: EttehadColors.primary, size: 26),
            ),
            const SizedBox(height: 12),
            const Text(
              'کتاب‌های بیشتر',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: EttehadColors.navy),
            ),
            const SizedBox(height: 4),
            const Text(
              'مشاهده همه آثار این بخش',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 9.5, color: Colors.black54),
            ),
          ],
        ),
      ),
    );
  }

  // -------------------------------------------------------------
  // INTERSTITIAL PROMOTIONAL CAMPAIGN BOX (Requirement 15: کادر رویدادی/تخفیفی با کتاب‌های درون‌کادری)
  // -------------------------------------------------------------
  Widget _buildPromoCampaignBox({
    required String title,
    required String subtitle,
    required String badgeText,
    required List<Map<String, dynamic>> promoBooks,
  }) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF7F1D1D), Color(0xFF991B1B), Color(0xFF450A0A)],
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.amber.shade400.withValues(alpha: 0.6), width: 1.4),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF7F1D1D).withValues(alpha: 0.35),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.amber.shade400,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    badgeText,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w900, color: Color(0xFF7F1D1D)),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.timer_outlined, size: 14, color: Colors.white70),
                  SizedBox(width: 4),
                  Text('فرصت ویژه مطالعه', style: TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.bold)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            title,
            style: const TextStyle(color: Colors.white, fontSize: 15.5, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 3),
          Text(
            subtitle,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11),
          ),
          const SizedBox(height: 14),

          // Horizontal scroll of promo books inside this box
          SizedBox(
            height: 200,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              itemCount: promoBooks.length,
              separatorBuilder: (_, _) => const SizedBox(width: 12),
              itemBuilder: (ctx, i) {
                final b = promoBooks[i];
                final cover = widget.repo.getCoverForBook(b);
                final bTitle = (b['title'] ?? '').toString();
                final bAuthor = (b['author'] ?? '').toString();

                return GestureDetector(
                  onTap: () {
                    HapticFeedback.selectionClick();
                    _openBookDetailModal(b);
                  },
                  child: Container(
                    width: 120,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.25),
                          blurRadius: 8,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Stack(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Image.asset(cover, fit: BoxFit.cover, width: 120, height: 200),
                        ),
                        // Discount Tag
                        Positioned(
                          top: 8,
                          right: 8,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.red.shade600,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Text(
                              '-۳۰٪',
                              style: TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w900),
                            ),
                          ),
                        ),
                        Positioned(
                          bottom: 0,
                          left: 0,
                          right: 0,
                          child: Container(
                            padding: const EdgeInsets.all(6),
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [Colors.transparent, Colors.black.withValues(alpha: 0.9)],
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                              ),
                              borderRadius: const BorderRadius.vertical(bottom: Radius.circular(12)),
                            ),
                            child: Column(
                              children: [
                                Text(
                                  bTitle,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                                ),
                                Text(
                                  bAuthor,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(color: Colors.white70, fontSize: 8.5),
                                ),
                              ],
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
        ],
      ),
    );
  }

  // -------------------------------------------------------------
  // MY SHELVES CARD (VIEW 2)
  // -------------------------------------------------------------
  Widget _build3DShelfCard(Map<String, dynamic> shelf) {
    final bookIds = List<String>.from(shelf['bookIds'] ?? []);
    final shelfBooks = widget.repo.books.where((b) => bookIds.contains(b['id'].toString())).toList();

    return Container(
      margin: const EdgeInsets.only(bottom: 18),
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: EttehadColors.border),
        boxShadow: [
          BoxShadow(
            color: EttehadColors.navy.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.shelves, color: EttehadColors.primary, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    (shelf['name'] ?? 'قفسه').toString(),
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: EttehadColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${toPersianDigits(shelfBooks.length)} کتاب',
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            height: 160,
            child: shelfBooks.isEmpty
                ? const Center(
                    child: Text(
                      'کتابی در این قفسه قرار ندارد؛ از ویترین اضافه کنید.',
                      style: TextStyle(fontSize: 11.5, color: Colors.black45),
                    ),
                  )
                : ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: shelfBooks.length,
                    separatorBuilder: (_, _) => const SizedBox(width: 14),
                    itemBuilder: (ctx, i) {
                      final b = shelfBooks[i];
                      final cover = widget.repo.getCoverForBook(b);
                      return GestureDetector(
                        onTap: () => _openBookDetailModal(b),
                        child: Container(
                          width: 100,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(8),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.22),
                                blurRadius: 6,
                                offset: const Offset(-2, 3),
                              ),
                            ],
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.asset(cover, fit: BoxFit.cover),
                          ),
                        ),
                      );
                    },
                  ),
          ),
          // Subtle modern shelf runner
          Container(
            height: 5,
            margin: const EdgeInsets.only(top: 8, bottom: 14),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFE2E8F0), Color(0xFFCBD5E1), Color(0xFFE2E8F0)],
              ),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================
// DEDICATED FULLSCREEN CATEGORIES TREE SCREEN (Fluent, Non-Boxy)
// =============================================================
class _LibraryCategoriesFullScreen extends StatefulWidget {
  final EttehadRepository repo;
  final String selectedCategoryId;
  final String? initialExpandedId;
  final void Function(String id, String title) onSelectCategory;

  const _LibraryCategoriesFullScreen({
    required this.repo,
    required this.selectedCategoryId,
    this.initialExpandedId,
    required this.onSelectCategory,
  });

  @override
  State<_LibraryCategoriesFullScreen> createState() => _LibraryCategoriesFullScreenState();
}

class _LibraryCategoriesFullScreenState extends State<_LibraryCategoriesFullScreen> {
  final TextEditingController _searchCtrl = TextEditingController();
  String _searchQuery = '';
  String? _expandedCategoryId;

  @override
  void initState() {
    super.initState();
    if (widget.initialExpandedId != null) {
      _expandedCategoryId = widget.initialExpandedId;
    } else if (widget.selectedCategoryId != 'all' && widget.selectedCategoryId.isNotEmpty) {
      for (final p in widget.repo.getParentCategories()) {
        final pId = p['id'] as String;
        if (pId == widget.selectedCategoryId || widget.selectedCategoryId.startsWith(pId)) {
          _expandedCategoryId = pId;
          break;
        }
      }
    }
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }



  @override
  Widget build(BuildContext context) {
    final allParents = widget.repo.getParentCategories();
    final query = _searchQuery.trim().toLowerCase();

    final filteredParents = allParents.where((p) {
      if (query.isEmpty) return true;
      final pTitle = (p['title'] as String).toLowerCase();
      if (pTitle.contains(query)) return true;
      final subcats = widget.repo.getSubcategories(p['id'] as String);
      return subcats.any((s) => (s['title'] as String).toLowerCase().contains(query));
    }).toList();

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Colors.white,
        appBar: AppBar(
          backgroundColor: Colors.white,
          elevation: 0,
          scrolledUnderElevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_forward_rounded, color: EttehadColors.navy),
            tooltip: 'بازگشت',
            onPressed: () => Navigator.pop(context),
          ),
          title: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'دسته‌بندی‌های موضوعی',
                style: TextStyle(
                  fontSize: 16.5,
                  fontWeight: FontWeight.w900,
                  color: EttehadColors.navy,
                ),
              ),
              Text(
                'انتخاب شاخه و زیرمجموعه‌های تخصصی',
                style: TextStyle(fontSize: 11, color: Colors.black54),
              ),
            ],
          ),
          actions: [
            TextButton.icon(
              onPressed: () {
                HapticFeedback.lightImpact();
                widget.onSelectCategory('all', '');
                Navigator.pop(context);
              },
              icon: const Icon(Icons.clear_all_rounded, size: 18, color: EttehadColors.primary),
              label: const Text(
                'همه کتاب‌ها',
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.bold,
                  color: EttehadColors.primary,
                ),
              ),
            ),
            const SizedBox(width: 8),
          ],
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(66),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Container(
                height: 48,
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: TextField(
                  controller: _searchCtrl,
                  onChanged: (val) {
                    setState(() {
                      _searchQuery = val;
                      if (val.trim().isNotEmpty && filteredParents.isNotEmpty) {
                        _expandedCategoryId = filteredParents.first['id'] as String;
                      }
                    });
                  },
                  textDirection: TextDirection.rtl,
                  decoration: InputDecoration(
                    hintText: 'جستجو در موضوعات (مثلاً: تاریخ معاصر، فقه، تفسیر...)',
                    hintStyle: const TextStyle(fontSize: 12.5, color: Colors.black45),
                    prefixIcon: const Icon(Icons.search_rounded, color: EttehadColors.primary, size: 22),
                    suffixIcon: _searchQuery.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.close_rounded, size: 18, color: Colors.black45),
                            onPressed: () {
                              _searchCtrl.clear();
                              setState(() => _searchQuery = '');
                            },
                          )
                        : null,
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
            ),
          ),
        ),
        body: filteredParents.isEmpty
            ? Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.search_off_rounded, size: 48, color: Colors.grey.shade400),
                    const SizedBox(height: 12),
                    Text(
                      'هیچ دسته‌بندی با عبارت «» یافت نشد',
                      style: const TextStyle(fontSize: 13, color: Colors.black54),
                    ),
                  ],
                ),
              )
            : ListView.separated(
                padding: const EdgeInsets.only(bottom: 32),
                itemCount: filteredParents.length,
                separatorBuilder: (_, _) => const Divider(height: 1, color: Color(0xFFF1F5F9)),
                itemBuilder: (ctx, i) {
                  final pCat = filteredParents[i];
                  final pId = pCat['id'] as String;
                  final pTitle = pCat['title'] as String;
                  final allSubcats = widget.repo.getSubcategories(pId);
                  
                  final subcats = query.isEmpty
                      ? allSubcats
                      : allSubcats.where((s) => (s['title'] as String).toLowerCase().contains(query)).toList();

                  final isExpanded = _expandedCategoryId == pId || query.isNotEmpty;
                  final isParentSelected = widget.selectedCategoryId == pId;

                  return Column(
                    children: [
                      // Smooth parent category tile (No boxy frames!)
                      InkWell(
                        onTap: () {
                          HapticFeedback.selectionClick();
                          setState(() {
                            _expandedCategoryId = isExpanded && query.isEmpty ? null : pId;
                          });
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
                          child: Row(
                            children: [
                              Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  color: isExpanded
                                      ? EttehadColors.primary
                                      : EttehadColors.primary.withValues(alpha: 0.08),
                                  borderRadius: BorderRadius.circular(13),
                                ),
                                child: Icon(
                                  _LibraryScreenState._getIconData(pCat['icon_name']?.toString() ?? 'menu_book'),
                                  size: 22,
                                  color: isExpanded ? Colors.white : EttehadColors.primary,
                                ),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      pTitle,
                                      style: TextStyle(
                                        fontSize: 15,
                                        fontWeight: FontWeight.w800,
                                        color: isParentSelected ? EttehadColors.primary : EttehadColors.navy,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      ' زیرمجموعه تخصصی',
                                      style: const TextStyle(fontSize: 11.5, color: Colors.black45),
                                    ),
                                  ],
                                ),
                              ),
                              AnimatedRotation(
                                turns: isExpanded ? 0.5 : 0.0,
                                duration: const Duration(milliseconds: 250),
                                curve: Curves.easeInOut,
                                child: Icon(
                                  Icons.keyboard_arrow_down_rounded,
                                  color: isExpanded ? EttehadColors.primary : Colors.black38,
                                  size: 26,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                      // Seamless Fluid Subcategories (Underneath, no card borders!)
                      AnimatedSize(
                        duration: const Duration(milliseconds: 260),
                        curve: Curves.easeInOutCubic,
                        child: isExpanded
                            ? Container(
                                color: const Color(0xFFF8FAFC),
                                padding: const EdgeInsets.only(top: 2, bottom: 8),
                                child: Column(
                                  children: [
                                    // Option 1: View all in this main category
                                    InkWell(
                                      onTap: () {
                                        HapticFeedback.lightImpact();
                                        widget.onSelectCategory(pId, pTitle);
                                        Navigator.pop(context);
                                      },
                                      child: Padding(
                                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 11),
                                        child: Row(
                                          children: [
                                            Container(
                                              width: 24,
                                              height: 24,
                                              decoration: BoxDecoration(
                                                color: EttehadColors.primary.withValues(alpha: 0.12),
                                                shape: BoxShape.circle,
                                              ),
                                              child: const Icon(Icons.grid_view_rounded, size: 13, color: EttehadColors.primary),
                                            ),
                                            const SizedBox(width: 12),
                                            Expanded(
                                              child: Text(
                                                'مشاهده تمام کتب شاخه «»',
                                                style: const TextStyle(
                                                  fontSize: 12.5,
                                                  fontWeight: FontWeight.w700,
                                                  color: EttehadColors.primary,
                                                ),
                                              ),
                                            ),
                                            const Icon(Icons.arrow_back_ios_new_rounded, size: 12, color: EttehadColors.primary),
                                          ],
                                        ),
                                      ),
                                    ),
                                    const Divider(height: 1, indent: 24, endIndent: 24, color: Color(0xFFEDF2F7)),

                                    // Subcategory rows
                                    ...subcats.map((sub) {
                                      final subId = sub['id'] as String;
                                      final subTitle = sub['title'] as String;
                                      final isSubActive = widget.selectedCategoryId == subId;

                                      return InkWell(
                                        onTap: () {
                                          HapticFeedback.lightImpact();
                                          widget.onSelectCategory(subId, ' ↳ ');
                                          Navigator.pop(context);
                                        },
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                                          color: isSubActive
                                              ? EttehadColors.primary.withValues(alpha: 0.08)
                                              : Colors.transparent,
                                          child: Row(
                                            children: [
                                              Container(
                                                width: 6,
                                                height: 6,
                                                decoration: BoxDecoration(
                                                  shape: BoxShape.circle,
                                                  color: isSubActive ? EttehadColors.primary : const Color(0xFF94A3B8),
                                                ),
                                              ),
                                              const SizedBox(width: 14),
                                              Expanded(
                                                child: Text(
                                                  subTitle,
                                                  style: TextStyle(
                                                    fontSize: 13,
                                                    fontWeight: isSubActive ? FontWeight.w800 : FontWeight.w500,
                                                    color: isSubActive ? EttehadColors.primary : EttehadColors.navy,
                                                  ),
                                                ),
                                              ),
                                              if (isSubActive)
                                                Container(
                                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                                  decoration: BoxDecoration(
                                                    color: EttehadColors.primary,
                                                    borderRadius: BorderRadius.circular(10),
                                                  ),
                                                  child: const Text(
                                                    'فعال',
                                                    style: TextStyle(
                                                      color: Colors.white,
                                                      fontSize: 10,
                                                      fontWeight: FontWeight.bold,
                                                    ),
                                                  ),
                                                )
                                              else
                                                const Icon(
                                                  Icons.arrow_back_ios_new_rounded,
                                                  size: 12,
                                                  color: Colors.black26,
                                                ),
                                            ],
                                          ),
                                        ),
                                      );
                                    }),
                                  ],
                                ),
                              )
                            : const SizedBox.shrink(),
                      ),
                    ],
                  );
                },
              ),
      ),
    );
  }
}

// =============================================================
// DEDICATED SHELF FULLSCREEN (نمایش همه آثار یک قفسه/موضوع)
// =============================================================
class _ShelfBooksScreen extends StatefulWidget {
  final String shelfTitle;
  final List<Map<String, dynamic>> books;
  final EttehadRepository repo;
  final void Function(Map<String, dynamic> book) onOpenBook;

  const _ShelfBooksScreen({
    required this.shelfTitle,
    required this.books,
    required this.repo,
    required this.onOpenBook,
  });

  @override
  State<_ShelfBooksScreen> createState() => _ShelfBooksScreenState();
}

class _ShelfBooksScreenState extends State<_ShelfBooksScreen> {
  final TextEditingController _searchCtrl = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final filtered = widget.books.where((b) {
      if (_query.trim().isEmpty) return true;
      final q = _query.trim().toLowerCase();
      final title = (b['title'] ?? '').toString().toLowerCase();
      final author = (b['author'] ?? '').toString().toLowerCase();
      return title.contains(q) || author.contains(q);
    }).toList();

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        appBar: AppBar(
          backgroundColor: Colors.white,
          elevation: 0,
          scrolledUnderElevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_forward_rounded, color: EttehadColors.navy),
            tooltip: 'بازگشت',
            onPressed: () => Navigator.pop(context),
          ),
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.shelfTitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 15.5,
                  fontWeight: FontWeight.w900,
                  color: EttehadColors.navy,
                ),
              ),
              Text(
                '${toPersianDigits(widget.books.length)} اثر برای مطالعه و کاوش پژوهشی',
                style: const TextStyle(fontSize: 10.5, color: Colors.black54),
              ),
            ],
          ),
        ),
        body: Column(
          children: [
            // Search field within this shelf
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              color: Colors.white,
              child: Container(
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: EttehadColors.border),
                ),
                child: TextField(
                  controller: _searchCtrl,
                  onChanged: (v) => setState(() => _query = v),
                  decoration: InputDecoration(
                    hintText: 'جستجو در آثار این بخش...',
                    hintStyle: const TextStyle(fontSize: 12, color: Colors.black45),
                    prefixIcon: const Icon(Icons.search_rounded, size: 20, color: EttehadColors.primary),
                    suffixIcon: _query.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear_rounded, size: 18),
                            onPressed: () {
                              _searchCtrl.clear();
                              setState(() => _query = '');
                            },
                          )
                        : null,
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                  ),
                ),
              ),
            ),
            const Divider(height: 1, color: EttehadColors.border),

            // Books Grid
            Expanded(
              child: filtered.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.search_off_rounded, size: 48, color: Colors.grey.shade400),
                          const SizedBox(height: 12),
                          const Text(
                            'اثری با این عنوان در این بخش یافت نشد.',
                            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.black54),
                          ),
                        ],
                      ),
                    )
                  : GridView.builder(
                      padding: const EdgeInsets.all(16),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        childAspectRatio: 0.58,
                        crossAxisSpacing: 14,
                        mainAxisSpacing: 16,
                      ),
                      itemCount: filtered.length,
                      itemBuilder: (ctx, i) {
                        final b = filtered[i];
                        final title = (b['title'] ?? 'کتاب').toString();
                        final author = (b['author'] ?? 'مؤلف گرامی').toString();
                        final rating = (b['rating'] ?? 4.8);
                        final coverUrl = (b['cover_url'] ?? b['cover'] ?? '').toString();

                        return InkWell(
                          borderRadius: BorderRadius.circular(14),
                          onTap: () {
                            HapticFeedback.lightImpact();
                            widget.onOpenBook(b);
                          },
                          child: Container(
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: EttehadColors.border),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.04),
                                  blurRadius: 8,
                                  offset: const Offset(0, 3),
                                ),
                              ],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                // Cover
                                Expanded(
                                  flex: 6,
                                  child: ClipRRect(
                                    borderRadius: const BorderRadius.vertical(top: Radius.circular(13)),
                                    child: coverUrl.isNotEmpty
                                        ? Image.network(
                                            coverUrl,
                                            fit: BoxFit.cover,
                                            errorBuilder: (_, _, _) => _defaultCover(title),
                                          )
                                        : _defaultCover(title),
                                  ),
                                ),
                                // Info
                                Expanded(
                                  flex: 4,
                                  child: Padding(
                                    padding: const EdgeInsets.all(10),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Text(
                                          title,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w900,
                                            color: EttehadColors.navy,
                                            height: 1.3,
                                          ),
                                        ),
                                        Text(
                                          author,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(fontSize: 10, color: Colors.black54),
                                        ),
                                        Row(
                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                          children: [
                                            Row(
                                              children: [
                                                const Icon(Icons.star_rounded, size: 14, color: Colors.amber),
                                                const SizedBox(width: 2),
                                                Text(
                                                  toPersianDigits(rating),
                                                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
                                                ),
                                              ],
                                            ),
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: EttehadColors.primary.withValues(alpha: 0.1),
                                                borderRadius: BorderRadius.circular(6),
                                              ),
                                              child: const Text(
                                                'مشاهده',
                                                style: TextStyle(
                                                  fontSize: 9.5,
                                                  fontWeight: FontWeight.bold,
                                                  color: EttehadColors.primary,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
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
          ],
        ),
      ),
    );
  }

  Widget _defaultCover(String title) {
    return Container(
      color: EttehadColors.primary.withValues(alpha: 0.12),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.menu_book_rounded, color: EttehadColors.primary, size: 36),
              const SizedBox(height: 6),
              Text(
                title,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// =============================================================
// DEDICATED FULLSCREEN CLEAN WHITE SEARCH SCREEN (Requirements 3 & 4)
// =============================================================
class _LibrarySearchScreen extends StatefulWidget {
  final EttehadRepository repo;
  final void Function(Map<String, dynamic> book) onOpenBook;
  final VoidCallback onOpenFilterModal;

  const _LibrarySearchScreen({
    required this.repo,
    required this.onOpenBook,
    required this.onOpenFilterModal,
  });

  @override
  State<_LibrarySearchScreen> createState() => _LibrarySearchScreenState();
}

class _LibrarySearchScreenState extends State<_LibrarySearchScreen> {
  final TextEditingController _ctrl = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  String _mode = 'text'; // 'text' | 'semantic'
  String _query = '';

  final List<String> _recentSearches = [
    'عدالت و حکومت در نهج‌البلاغه',
    'تفسیر المیزان',
    'احادیث اخلاقی',
    'فقه مقارن مذاهب',
    'طهارت و صلاة',
  ];

  static const List<String> _trendingKeywords = [
    'عدالت',
    'اخوت اسلامی',
    'تفسیر قرآن',
    'فقه شافعی',
    'سلوک معنوی',
    'حقوق مؤمنان',
    'سیره نبوی',
  ];

  bool _isSearchingSemantic = false;
  List<Map<String, dynamic>> _onlineSemanticResults = [];
  Timer? _semanticDebounce;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _semanticDebounce?.cancel();
    _ctrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onQueryChanged(String val) {
    setState(() => _query = val);
    if (_mode == 'semantic') {
      _triggerSemanticSearch(val);
    }
  }

  void _triggerSemanticSearch(String q) {
    _semanticDebounce?.cancel();
    final cleanQ = q.trim();
    if (cleanQ.isEmpty) {
      setState(() {
        _isSearchingSemantic = false;
        _onlineSemanticResults = [];
      });
      return;
    }

    setState(() => _isSearchingSemantic = true);
    _semanticDebounce = Timer(const Duration(milliseconds: 350), () async {
      try {
        final results = await widget.repo.searchBooksSemanticOnline(cleanQ);
        if (mounted && _query.trim() == cleanQ) {
          setState(() {
            _onlineSemanticResults = results;
            _isSearchingSemantic = false;
          });
        }
      } catch (_) {
        if (mounted) setState(() => _isSearchingSemantic = false);
      }
    });
  }

  List<Map<String, dynamic>> _getSearchResults() {
    if (_query.trim().isEmpty) return [];

    if (_mode == 'semantic') {
      if (_onlineSemanticResults.isNotEmpty) return _onlineSemanticResults;
      return widget.repo.searchBooksSemantic(_query);
    } else {
      final q = _query.trim().toLowerCase();
      return widget.repo.books.where((b) {
        final t = (b['title'] ?? '').toString().toLowerCase();
        final a = (b['author'] ?? '').toString().toLowerCase();
        final d = (b['description'] ?? '').toString().toLowerCase();
        final p = (b['publisher'] ?? '').toString().toLowerCase();
        return t.contains(q) || a.contains(q) || d.contains(q) || p.contains(q);
      }).toList();
    }
  }

  @override
  Widget build(BuildContext context) {
    final results = _getSearchResults();

    return Scaffold(
      backgroundColor: Colors.white, // Requirement 3: صفحه سفید اختصاصی
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_forward_rounded, color: EttehadColors.navy),
          onPressed: () => Navigator.pop(context),
        ),
        titleSpacing: 0,
        title: Container(
          height: 42,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            color: const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(12),
          ),
          child: TextField(
            controller: _ctrl,
            focusNode: _focusNode,
            onChanged: _onQueryChanged,
            decoration: InputDecoration(
              hintText: _mode == 'semantic'
                  ? 'جستجوی مفهومی (مثلاً: عدالت در جامعه، آرامش روح...)'
                  : 'نام کتاب، مؤلف یا ناشر...',
              hintStyle: const TextStyle(fontSize: 12, color: Colors.black45),
              border: InputBorder.none,
              prefixIcon: Icon(
                _mode == 'semantic' ? Icons.auto_awesome : Icons.search_rounded,
                size: 20,
                color: EttehadColors.primary,
              ),
              suffixIcon: _query.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.close_rounded, size: 18, color: Colors.black45),
                      onPressed: () {
                        _ctrl.clear();
                        setState(() => _query = '');
                      },
                    )
                  : null,
            ),
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'دسته‌بندی‌های موضوعی',
            icon: const Icon(Icons.tune_rounded, color: EttehadColors.primary),
            onPressed: widget.onOpenFilterModal,
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: Column(
        children: [
          // Mode Switcher: متنی / معنایی (Requirement 4)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: const Color(0xFFFAFAFA),
            child: Row(
              children: [
                _buildSearchModePill('text', 'جستجوی متنی دقیق', Icons.search_rounded),
                const SizedBox(width: 8),
                _buildSearchModePill('semantic', 'کاوش معنایی هوشمند', Icons.auto_awesome),
              ],
            ),
          ),
          const Divider(height: 1),

          Expanded(
            child: _query.trim().isEmpty
                ? _buildInitialSearchState()
                : _buildSearchResultsState(results),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchModePill(String id, String title, IconData icon) {
    final active = _mode == id;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() => _mode = id);
          if (id == 'semantic' && _query.trim().isNotEmpty) {
            _triggerSemanticSearch(_query);
          }
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.symmetric(vertical: 7),
          decoration: BoxDecoration(
            color: active ? EttehadColors.navy : Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: active ? EttehadColors.navy : EttehadColors.border),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 14, color: active ? Colors.amberAccent : EttehadColors.primary),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: active ? FontWeight.bold : FontWeight.w600,
                  color: active ? Colors.white : EttehadColors.navy,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInitialSearchState() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (_recentSearches.isNotEmpty) ...[
          const Row(
            children: [
              Icon(Icons.history_rounded, size: 18, color: Colors.black54),
              SizedBox(width: 6),
              Text(
                'جستجوهای اخیر شما',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: EttehadColors.navy),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _recentSearches.map((term) {
              return ActionChip(
                backgroundColor: const Color(0xFFF1F5F9),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                label: Text(term, style: const TextStyle(fontSize: 11, color: EttehadColors.navy)),
                onPressed: () {
                  _ctrl.text = term;
                  setState(() => _query = term);
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 24),
        ],

        const Row(
          children: [
            Icon(Icons.local_fire_department_rounded, size: 18, color: Colors.orange),
            SizedBox(width: 6),
            Text(
              'کلیدواژه‌های پرجستجو و موضوعات داغ',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: EttehadColors.navy),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _trendingKeywords.map((kw) {
            return ActionChip(
              avatar: const Icon(Icons.tag_rounded, size: 14, color: EttehadColors.primary),
              backgroundColor: const Color(0xFFE0F2FE),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              label: Text(kw, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
              onPressed: () {
                _ctrl.text = kw;
                setState(() => _query = kw);
              },
            );
          }).toList(),
        ),
        const SizedBox(height: 24),

        // Semantic search explanation card
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFEFF6FF), Color(0xFFDBEAFE)],
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF93C5FD)),
          ),
          child: const Row(
            children: [
              Icon(Icons.auto_awesome, color: EttehadColors.primary, size: 28),
              SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'جستجوی معنایی هوشمند',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                    ),
                    SizedBox(height: 3),
                    Text(
                      'حتی بدون دانستن نام کتاب، با جستجوی مفاهیم (مانند عدالت، برادری، احکام طهارت) کتاب‌های مرتبط را بیابید.',
                      style: TextStyle(fontSize: 11, color: Colors.black87, height: 1.3),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSearchResultsState(List<Map<String, dynamic>> results) {
    if (results.isEmpty) {
      return Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.search_off_rounded, size: 54, color: Colors.black26),
              const SizedBox(height: 12),
              Text(
                'اثری منطبق با «$_query» یافت نشد.',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black54),
              ),
              const SizedBox(height: 6),
              const Text(
                'پیشنهاد: حالت کاوش معنایی را فعال کنید یا از کلمات کلیدی عام‌تر استفاده فرمایید.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 11, color: Colors.black38),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () => _openBookRequestDialog(_query),
                icon: const Icon(Icons.add_task_rounded, size: 16),
                label: const Text('ثبت درخواست افزودن این کتاب به مخزن', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: results.length,
      separatorBuilder: (_, _) => const Divider(height: 16),
      itemBuilder: (ctx, i) {
        final b = results[i];
        final cover = widget.repo.getCoverForBook(b);
        final title = (b['title'] ?? '').toString();
        final author = (b['author'] ?? '').toString();
        final pub = (b['publisher'] ?? '').toString();
        final rating = (b['rating'] as num?)?.toDouble() ?? 4.8;
        final semanticReason = (b['semantic_reason'] ?? '').toString();

        return InkWell(
          onTap: () {
            widget.onOpenBook(b);
          },
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.asset(cover, width: 72, height: 104, fit: BoxFit.cover),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'مؤلف: $author',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 11, color: Colors.black54),
                      ),
                      if (pub.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          'نشر: $pub',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 10, color: Colors.black45),
                        ),
                      ],
                      const SizedBox(height: 6),
                      if (semanticReason.isNotEmpty) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFEF3C7),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFFFCD34D)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.auto_awesome, size: 11, color: Color(0xFFB45309)),
                              const SizedBox(width: 4),
                              Flexible(
                                child: Text(
                                  semanticReason,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: Color(0xFFB45309)),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ] else ...[
                        Row(
                          children: [
                            const Icon(Icons.star_rounded, size: 14, color: Colors.amber),
                            const SizedBox(width: 2),
                            Text(
                              toPersianDigits(rating.toStringAsFixed(1)),
                              style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.navy),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _openBookRequestDialog(String initialTitle) {
    final titleCtrl = TextEditingController(text: initialTitle);
    final authorCtrl = TextEditingController();
    bool isSubmitting = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (dialogCtx, setDialogState) => Directionality(
          textDirection: TextDirection.rtl,
          child: AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Row(
              children: [
                Icon(Icons.menu_book_rounded, color: EttehadColors.primary, size: 20),
                SizedBox(width: 8),
                Text('درخواست افزودن اثر به کتابخانه', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
              ],
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'اگر اثر مورد نظر شما در مخزن موجود نیست، عنوان آن را ثبت فرمایید تا در اولویت دیجیتال‌سازی و بارگذاری قرار گیرد.',
                  style: TextStyle(fontSize: 11, color: Colors.black54, height: 1.5),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: titleCtrl,
                  decoration: InputDecoration(
                    labelText: 'عنوان کتاب یا منبع',
                    filled: true,
                    fillColor: EttehadColors.surfaceLow,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: authorCtrl,
                  decoration: InputDecoration(
                    labelText: 'نام مؤلف / مترجم (اختیاری)',
                    filled: true,
                    fillColor: EttehadColors.surfaceLow,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: isSubmitting ? null : () => Navigator.pop(ctx),
                child: const Text('انصراف'),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: isSubmitting
                    ? null
                    : () async {
                        final t = titleCtrl.text.trim();
                        if (t.isEmpty) return;
                        setDialogState(() => isSubmitting = true);
                        final res = await widget.repo.submitBookRequest(
                          title: t,
                          author: authorCtrl.text.trim().isNotEmpty ? authorCtrl.text.trim() : null,
                        );
                        if (ctx.mounted) Navigator.pop(ctx);
                        final tracking = res?['trackingCode']?.toString() ?? 'ثبت شد';
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text('درخواست اثر «$t» با موفقیت در سرور ثبت شد. کد پیگیری: $tracking'),
                              backgroundColor: EttehadColors.emerald,
                              duration: const Duration(seconds: 4),
                            ),
                          );
                        }
                      },
                child: isSubmitting
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('ثبت در سرور', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// -------------------------------------------------------------
// COMPREHENSIVE 90% EXPANDABLE BOOK DETAIL MODAL (MATCHING STOREFRONT.HTML)
// -------------------------------------------------------------
class _BookDetailModal extends StatefulWidget {
  final Map<String, dynamic> book;
  final EttehadRepository repo;
  final VoidCallback onStartReading;
  final VoidCallback onAskAi;

  const _BookDetailModal({
    required this.book,
    required this.repo,
    required this.onStartReading,
    required this.onAskAi,
  });

  @override
  State<_BookDetailModal> createState() => _BookDetailModalState();
}

class _BookDetailModalState extends State<_BookDetailModal> {
  bool _isDescriptionExpanded = false;
  bool _isAiChatOpen = false;
  int _userReviewRating = 5;
  final TextEditingController _reviewInputCtrl = TextEditingController();
  final TextEditingController _aiModalChatCtrl = TextEditingController();
  final List<Map<String, String>> _aiModalMessages = [];
  final Set<String> _expandedShelves = {};
  bool _isAiModalThinking = false;

  @override
  void initState() {
    super.initState();
    final bookId = (widget.book['id'] ?? '').toString();
    if (bookId.isNotEmpty) {
      widget.repo.syncBookReviews(bookId);
    }
  }

  Future<void> _sendAiModalQuestion(String question) async {
    if (question.trim().isEmpty || _isAiModalThinking) return;
    final q = question.trim();
    _aiModalChatCtrl.clear();
    final bookId = (widget.book['id'] ?? '').toString();
    final bookTitle = (widget.book['title'] ?? 'این اثر').toString();

    setState(() {
      _aiModalMessages.add({'sender': 'user', 'text': q});
      _aiModalMessages.add({'sender': 'ai', 'text': 'در حال اتصال به اتحادیار (api.unitysi.ir) و کاوش در متن اثر...'});
      _isAiModalThinking = true;
    });

    try {
      final res = await widget.repo.askBookAi(
        bookId: bookId,
        bookTitle: bookTitle,
        query: q,
      );

      if (!mounted) return;
      setState(() {
        if (_aiModalMessages.isNotEmpty && _aiModalMessages.last['sender'] == 'ai') {
          _aiModalMessages.removeLast();
        }
        _aiModalMessages.add({
          'sender': 'ai',
          'text': res['reply']?.toString() ?? 'پاسخی از پایگاه داده معارفی دریافت نشد.',
        });
        _isAiModalThinking = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        if (_aiModalMessages.isNotEmpty && _aiModalMessages.last['sender'] == 'ai') {
          _aiModalMessages.removeLast();
        }
        _aiModalMessages.add({
          'sender': 'ai',
          'text': 'خطا در ارتباط با سرور هوش مصنوعی (api.unitysi.ir). لطفاً اینترنت خود را بررسی نمایید.',
        });
        _isAiModalThinking = false;
      });
    }
  }

  Widget _buildRichDescription(String description) {
    final cleanDesc = description
        .replaceAll(r'\r\n', '\n')
        .replaceAll(r'\r', '\n')
        .replaceAll(r'\n', '\n');
    final spans = <TextSpan>[];
    final regex = RegExp(r'\*\*(.*?)\*\*');
    int lastMatchEnd = 0;

    for (final match in regex.allMatches(cleanDesc)) {
      if (match.start > lastMatchEnd) {
        spans.add(TextSpan(
          text: cleanDesc.substring(lastMatchEnd, match.start),
          style: const TextStyle(
            fontSize: 12.5,
            height: 1.8,
            color: Colors.black87,
          ),
        ));
      }
      spans.add(TextSpan(
        text: match.group(1),
        style: const TextStyle(
          fontSize: 12.5,
          height: 1.8,
          fontWeight: FontWeight.w900,
          color: EttehadColors.navy,
        ),
      ));
      lastMatchEnd = match.end;
    }

    if (lastMatchEnd < cleanDesc.length) {
      spans.add(TextSpan(
        text: cleanDesc.substring(lastMatchEnd),
        style: const TextStyle(
          fontSize: 12.5,
          height: 1.8,
          color: Colors.black87,
        ),
      ));
    }

    return RichText(
      maxLines: _isDescriptionExpanded ? null : 3,
      overflow: _isDescriptionExpanded ? TextOverflow.clip : TextOverflow.ellipsis,
      text: TextSpan(
        children: spans.isEmpty
            ? [
                TextSpan(
                  text: cleanDesc,
                  style: const TextStyle(fontSize: 12.5, height: 1.8, color: Colors.black87),
                )
              ]
            : spans,
      ),
    );
  }

  void _showAddExcerptDialog(BuildContext context, String bookId) {
    final textCtrl = TextEditingController();
    final pageCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (dCtx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Row(
            children: [
              Icon(Icons.format_quote_rounded, color: EttehadColors.primary),
              SizedBox(width: 8),
              Text(
                'ثبت بریده‌ای از کتاب',
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: EttehadColors.navy),
              ),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'عیناً متن کتاب را به عنوان بریده‌ای ماندگار و ارزشمند وارد نمایید:',
                style: TextStyle(fontSize: 11.5, color: Colors.black87, height: 1.5),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: textCtrl,
                minLines: 3,
                maxLines: 5,
                decoration: InputDecoration(
                  hintText: 'متن عین کتاب را اینجا بنویسید...',
                  hintStyle: const TextStyle(fontSize: 11),
                  filled: true,
                  fillColor: EttehadColors.surfaceLow,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  contentPadding: const EdgeInsets.all(12),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: pageCtrl,
                decoration: InputDecoration(
                  hintText: 'شماره صفحه یا عنوان فصل (مثال: فصل دوم، صفحه ۴۵)',
                  hintStyle: const TextStyle(fontSize: 11),
                  filled: true,
                  fillColor: EttehadColors.surfaceLow,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dCtx).pop(),
              child: const Text('انصراف', style: TextStyle(color: Colors.black54)),
            ),
            ElevatedButton(
              onPressed: () {
                if (textCtrl.text.trim().isNotEmpty) {
                  widget.repo.addExcerpt(bookId, textCtrl.text, pageCtrl.text);
                  Navigator.of(dCtx).pop();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('بریده کتاب با موفقیت ثبت و افزوده شد.')),
                  );
                  setState(() {});
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: EttehadColors.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              child: const Text('ثبت بریده'),
            ),
          ],
        ),
      ),
    );
  }

  void _showShareModal(BuildContext context, Map<String, dynamic> book) {
    final title = (book['title'] ?? 'کتاب مرجع').toString();
    final author = (book['author'] ?? 'مؤلف نامشخص').toString();
    final publisher = (book['publisher'] ?? 'انتشارات معارف اسلامی').toString();
    final desc = (book['description'] ?? 'این اثر نفیس و گرانسنگ یکی از پایه‌های معرفتی و مبانی اصیل در حوزه تخصصی خود به شمار می‌رود.').toString();
    final snippet = desc.length > 170 ? '${desc.substring(0, 170)}...' : desc;

    final shareText = '''
📚 معرفی کتاب: «$title»
✍️ نویسنده: $author
🏢 ناشر: $publisher

📖 خلاصه‌ای از اثر:
$snippet

📲 دریافت و مطالعه در اپلیکیشن کتابخوان و دانشنامه هوشمند «اتحاد»:
🔹 دانلود از کافه‌بازار:
https://cafebazaar.ir/app/com.ettehad.app
🔹 دانلود از گوگل‌پلی:
https://play.google.com/store/apps/details?id=com.ettehad.app
'''.trim();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 44,
                  height: 5,
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: EttehadColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.share_rounded, color: EttehadColors.primary, size: 22),
                  ),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      'اشتراک‌گذاری کتاب',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              // Text Preview Box
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: EttehadColors.surfaceLow,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: EttehadColors.border),
                ),
                child: Text(
                  shareText,
                  style: const TextStyle(fontSize: 11, height: 1.6, color: Colors.black87),
                  maxLines: 7,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(height: 14),
              // Copy Button
              ElevatedButton.icon(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: shareText));
                  Navigator.of(ctx).pop();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('متن معرفی کتاب با موفقیت کپی شد. می‌توانید در سایر پیام‌رسان‌ها به اشتراک بگذارید.'),
                      duration: Duration(seconds: 2),
                    ),
                  );
                },
                icon: const Icon(Icons.copy_rounded, size: 18),
                label: const Text('کپی متن و اشتراک‌گذاری در سایر برنامه‌ها', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary,
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(46),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
              ),
              const SizedBox(height: 18),
              const Divider(color: EttehadColors.border),
              const SizedBox(height: 8),
              // Share to Scholar Section
              Row(
                children: [
                  const Icon(Icons.school_rounded, color: EttehadColors.navy, size: 18),
                  const SizedBox(width: 6),
                  const Text(
                    'اشتراک‌گذاری در اتحادکده با عالم دینی',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: EttehadColors.navy),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              const Text(
                'استاد یا عالم مدنظر خود را انتخاب کنید تا مشخصات این کتاب مستقیماً در گفتگوی ایشان ارسال شود:',
                style: TextStyle(fontSize: 11, color: Colors.black54),
              ),
              const SizedBox(height: 10),
              SizedBox(
                height: 115,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: widget.repo.scholars.length,
                  separatorBuilder: (_, _) => const SizedBox(width: 10),
                  itemBuilder: (c, idx) {
                    final scholar = widget.repo.scholars[idx];
                    return GestureDetector(
                      onTap: () {
                        Navigator.of(ctx).pop();
                        // Start or open scholar chat
                        widget.repo.startOrOpenScholarChat(scholar);
                        widget.repo.sendScholarMessage(
                          scholar['id'].toString(),
                          shareText,
                          bookId: book['id'].toString(),
                          bookTitle: title,
                        );
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('کتاب «$title» با موفقیت با ${scholar['name']} در اتحادکده به اشتراک گذاشته شد.'),
                            duration: const Duration(seconds: 2),
                          ),
                        );
                        // Open Scholar chat room directly
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => Directionality(
                              textDirection: TextDirection.rtl,
                              child: ScholarChatRoomScreen(
                                scholar: scholar,
                                repo: widget.repo,
                              ),
                            ),
                          ),
                        );
                      },
                      child: Container(
                        width: 130,
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: EttehadColors.surfaceLow,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: EttehadColors.border),
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            CircleAvatar(
                              radius: 18,
                              backgroundColor: EttehadColors.primary.withValues(alpha: 0.15),
                              child: const Icon(Icons.person_outline_rounded, color: EttehadColors.primary, size: 20),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              (scholar['name'] ?? '').toString(),
                              textAlign: TextAlign.center,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: EttehadColors.navy),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              (scholar['title'] ?? scholar['madhhab'] ?? 'استاد معارف').toString(),
                              textAlign: TextAlign.center,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 9.5, color: Colors.black54),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 10),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final book = widget.book;
    final bookId = book['id'].toString();
    final reviews = widget.repo.getBookReviews(bookId);
    final pendingReviews = widget.repo.getUserPendingReviews(bookId);
    final excerpts = widget.repo.getBookExcerpts(bookId);

    final similarBooks = widget.repo.getSimilarBooks(book);
    final sameAuthorBooks = widget.repo.getSameAuthorBooks(book);
    final samePublisherBooks = widget.repo.getSamePublisherBooks(book);

    final rating = book['rating'] ?? 4.8;
    final pages = book['page_count'] ?? 320;
    final author = (book['author'] ?? 'مؤلف نامشخص').toString();
    final publisher = (book['publisher'] ?? 'انتشارات معارف اسلامی').toString();
    final isSaved = widget.repo.isBookSaved(bookId);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: DraggableScrollableSheet(
        initialChildSize: 0.92,
        minChildSize: 0.65,
        maxChildSize: 0.98,
        builder: (ctx, scrollCtrl) => Container(
          decoration: const BoxDecoration(
            color: EttehadColors.paper,
            borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          ),
          child: Column(
            children: [
              // Grabber Handle
              const SizedBox(height: 12),
              Container(
                width: 48,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.black26,
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              Expanded(
                child: ListView(
                  controller: scrollCtrl,
                  padding: const EdgeInsets.fromLTRB(20, 18, 20, 64),
                  children: [
                    // 1. HERO: 3D COVER & BASIC DETAILS (MATCHING STOREFRONT.HTML)
                    Center(
                      child: Column(
                        children: [
                          // Upgraded High-Resolution Book Cover
                          Container(
                            width: 160,
                            height: 236,
                            decoration: BoxDecoration(
                              borderRadius: const BorderRadius.horizontal(
                                right: Radius.circular(4),
                                left: Radius.circular(14),
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.38),
                                  blurRadius: 18,
                                  offset: const Offset(-6, 8),
                                ),
                              ],
                            ),
                            child: ClipRRect(
                              borderRadius: const BorderRadius.horizontal(
                                right: Radius.circular(4),
                                left: Radius.circular(14),
                              ),
                              child: Image.asset(
                                widget.repo.getCoverForBook(book),
                                fit: BoxFit.cover,
                              ),
                            ),
                          ),
                          const SizedBox(height: 14),
                          Text(
                            (book['title'] ?? '').toString(),
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            author,
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '$publisher • منبع مرجع',
                            style: const TextStyle(fontSize: 11.5, color: Colors.black54),
                          ),
                          const SizedBox(height: 12),

                          // Rating and Quick Action Strip (Save & Share)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: EttehadColors.border),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.03),
                                  blurRadius: 8,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Flexible(
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(Icons.star_rounded, color: Colors.amber, size: 22),
                                      const SizedBox(width: 5),
                                      Text(
                                        toPersianDigits(rating),
                                        style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5),
                                      ),
                                      const SizedBox(width: 5),
                                      Flexible(
                                        child: Text(
                                          '(${toPersianDigits(reviews.length)} نظر)',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(color: Colors.black54, fontSize: 11.5),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 6),
                                Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    _iconBtn(
                                      isSaved ? Icons.bookmark_rounded : Icons.bookmark_border_rounded,
                                      isSaved ? 'نشان‌شده' : 'ذخیره',
                                      () {
                                        final nowSaved = widget.repo.toggleBookSaved(bookId);
                                        setState(() {});
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            content: Text(nowSaved
                                                ? 'کتاب «${book['title']}» در قفسه نشان‌شده‌ها ذخیره شد.'
                                                : 'کتاب «${book['title']}» از قفسه نشان‌شده‌ها حذف شد.'),
                                            duration: const Duration(seconds: 2),
                                          ),
                                        );
                                      },
                                      active: isSaved,
                                    ),
                                    const SizedBox(width: 8),
                                    _iconBtn(
                                      Icons.share_rounded,
                                      'اشتراک',
                                      () => _showShareModal(context, book),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),

                    // 2. PRIMARY ACTION BUTTONS: مطالعه اثر + گفتگو با کتاب
                    Row(
                      children: [
                        Expanded(
                          flex: 3,
                          child: ElevatedButton.icon(
                            onPressed: widget.onStartReading,
                            icon: const Icon(Icons.auto_stories_rounded, size: 22),
                            label: const Text('مطالعه اثر در کتابخوان', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: EttehadColors.primary,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                              elevation: 2,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          flex: 2,
                          child: ElevatedButton.icon(
                            onPressed: () => setState(() => _isAiChatOpen = !_isAiChatOpen),
                            icon: const Icon(Icons.psychology_rounded, size: 22),
                            label: Text(_isAiChatOpen ? 'بستن گفتگو' : 'گفتگو با کتاب', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: EttehadColors.amber,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                              elevation: 2,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),

                    // 3. COLLAPSIBLE EMBEDDED AI CHAT SECTION (EXPANDED TO 290PX)
                    if (_isAiChatOpen) ...[
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.amber.shade50,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: Colors.amber.shade300, width: 1.2),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.smart_toy_rounded, color: EttehadColors.amberDark, size: 22),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'گفتگو با هوش مصنوعی کتاب «${book['title']}»',
                                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.navy),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            // Quick prompt chips
                            SingleChildScrollView(
                              scrollDirection: Axis.horizontal,
                              child: Row(
                                children: [
                                  _promptChip('💡 پیام بنیادین اثر', () => _sendAiModalQuestion('دیدگاه و پیام بنیادین مؤلف در این اثر چیست؟')),
                                  const SizedBox(width: 8),
                                  _promptChip('📑 ساختار فصول', () => _sendAiModalQuestion('ساختار فصول و مهم‌ترین مباحث مطرح شده را بگو')),
                                  const SizedBox(width: 8),
                                  _promptChip('📖 نقل‌قول‌های کلیدی', () => _sendAiModalQuestion('مهم‌ترین نقل‌قول‌ها و استنادات این کتاب چیست؟')),
                                ],
                              ),
                            ),
                            const SizedBox(height: 12),
                            // Messages container (Enlarged)
                            Container(
                              constraints: const BoxConstraints(maxHeight: 290),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: Colors.amber.shade200),
                              ),
                              child: _aiModalMessages.isEmpty
                                  ? const Text(
                                      'سلام! من دستیار هوشمند این کتاب هستم. هر سوالی درباره مفاهیم و استدلال‌های این اثر دارید بپرسید تا با استناد به متن پاسخ دهم.',
                                      style: TextStyle(fontSize: 12.5, height: 1.7, color: Colors.black87),
                                    )
                                  : ListView.builder(
                                      shrinkWrap: true,
                                      itemCount: _aiModalMessages.length,
                                      itemBuilder: (ctx, i) {
                                        final msg = _aiModalMessages[i];
                                        final isUser = msg['sender'] == 'user';
                                        return Align(
                                          alignment: isUser ? Alignment.centerLeft : Alignment.centerRight,
                                          child: Container(
                                            margin: const EdgeInsets.only(bottom: 8),
                                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                                            decoration: BoxDecoration(
                                              color: isUser ? EttehadColors.primary : EttehadColors.surfaceLow,
                                              borderRadius: BorderRadius.circular(12),
                                            ),
                                            child: Text(
                                              msg['text']!,
                                              style: TextStyle(
                                                fontSize: 12,
                                                color: isUser ? Colors.white : Colors.black87,
                                                height: 1.6,
                                              ),
                                            ),
                                          ),
                                        );
                                      },
                                    ),
                            ),
                            const SizedBox(height: 10),
                            // Input field
                            Row(
                              children: [
                                Expanded(
                                  child: TextField(
                                    controller: _aiModalChatCtrl,
                                    onSubmitted: _sendAiModalQuestion,
                                    style: const TextStyle(fontSize: 12),
                                    decoration: InputDecoration(
                                      hintText: 'پرسش خود را درباره این کتاب بنویسید...',
                                      hintStyle: const TextStyle(fontSize: 11.5),
                                      filled: true,
                                      fillColor: Colors.white,
                                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: BorderSide(color: Colors.amber.shade200),
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Container(
                                  decoration: BoxDecoration(
                                    color: EttehadColors.amber,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: IconButton(
                                    icon: const Icon(Icons.send_rounded, color: Colors.white),
                                    onPressed: () => _sendAiModalQuestion(_aiModalChatCtrl.text),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 18),
                    ],

                    // 4. BOOK INTRODUCTION (WITH BOLD SUPPORT & EXPAND)
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: EttehadColors.border),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.03),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.menu_book_rounded, color: EttehadColors.primary, size: 20),
                              SizedBox(width: 8),
                              Text('معرفی کتاب', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: EttehadColors.navy)),
                            ],
                          ),
                          const SizedBox(height: 10),
                          _buildRichDescription(
                            (book['description'] ?? 'این اثر نفیس و گرانسنگ یکی از **پایه‌های معرفتی و مبانی اصیل** در حوزه تخصصی خود به شمار می‌رود که با رویکردی متقن، علمی و مقایسه‌ای نگاشته شده است. مؤلف در فصول مختلف با **دقت استدلالی و استناد به منابع اصیل** به بررسی زوایای مختلف موضوع پرداخته و تصویری جامع، ژرف و روشنگر را فراروی مخاطبان قرار می‌دهد.').toString(),
                          ),
                          GestureDetector(
                            onTap: () => setState(() => _isDescriptionExpanded = !_isDescriptionExpanded),
                            child: Padding(
                              padding: const EdgeInsets.only(top: 6),
                              child: Text(
                                _isDescriptionExpanded ? '(بستن متن)' : '(بیشتر...)',
                                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),

                    // 5. BOOK SPECIFICATIONS (INCREASED HEIGHT & HORIZONTAL SCROLL)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('مشخصات کتاب', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: EttehadColors.navy)),
                        const SizedBox(height: 10),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: EttehadColors.border),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.03),
                                  blurRadius: 8,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Row(
                              children: [
                                _specColumn(Icons.business_rounded, 'ناشر', publisher),
                                _specDivider(),
                                _specColumn(Icons.auto_stories_outlined, 'تعداد صفحات', toPersianDigits(pages)),
                                _specDivider(),
                                _specColumn(Icons.translate_rounded, 'زبان و قالب', (book['language'] ?? 'فارسی / عربی').toString()),
                                _specDivider(),
                                _specColumn(Icons.balance_rounded, 'رویکرد تقریب', 'تطبیقی فریقین'),
                                _specDivider(),
                                _specColumn(Icons.verified_rounded, 'نوع دسترسی', 'رایگان در سامانه'),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),

                    // 6. BOOK EXCERPTS (MOVED ABOVE REVIEWS + ADD EXCERPT FEATURE)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Row(
                              children: [
                                Icon(Icons.format_quote_rounded, color: EttehadColors.primary, size: 20),
                                SizedBox(width: 8),
                                Text('بریده‌ای از کتاب', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: EttehadColors.navy)),
                              ],
                            ),
                            TextButton.icon(
                              onPressed: () => _showAddExcerptDialog(context, bookId),
                              icon: const Icon(Icons.add_circle_outline_rounded, size: 16, color: EttehadColors.primary),
                              label: const Text('افزودن بریده', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: EttehadColors.primary)),
                              style: TextButton.styleFrom(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                minimumSize: Size.zero,
                                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          height: 135,
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemCount: excerpts.length,
                            separatorBuilder: (_, _) => const SizedBox(width: 16),
                            itemBuilder: (ctx, i) {
                              final exc = excerpts[i];
                              return Container(
                                width: 290,
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFFFFBEB),
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(color: Colors.amber.shade200),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.amber.withValues(alpha: 0.1),
                                      blurRadius: 6,
                                      offset: const Offset(0, 2),
                                    ),
                                  ],
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      (exc['text'] ?? '').toString(),
                                      maxLines: 3,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontSize: 11.5, height: 1.6, color: Color(0xFF78350F), fontWeight: FontWeight.w600),
                                    ),
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Text((exc['page'] ?? '').toString(), style: const TextStyle(fontSize: 10, color: Colors.black54)),
                                        const Icon(Icons.format_quote_rounded, color: Colors.amber, size: 16),
                                      ],
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),

                    // 7. USER REVIEWS (ENLARGED CARDS + AVATAR + USER NAME + STARS + COMMENT)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.rate_review_rounded, color: Colors.amber, size: 20),
                            const SizedBox(width: 8),
                            const Text('نظرات خوانندگان', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: EttehadColors.navy)),
                            const SizedBox(width: 8),
                            Text('(${toPersianDigits(reviews.length)} دیدگاه تأیید شده)', style: const TextStyle(fontSize: 11.5, color: Colors.black54)),
                          ],
                        ),
                        if (pendingReviews.isNotEmpty) ...[
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFFBEB),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: const Color(0xFFFDE68A)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Row(
                                  children: [
                                    Icon(Icons.hourglass_top_rounded, size: 16, color: Color(0xFFD97706)),
                                    SizedBox(width: 6),
                                    Text(
                                      'دیدگاه شما در صف بررسی مدیران قرار دارد',
                                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFFB45309)),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                ...pendingReviews.map((pr) => Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 2),
                                  child: Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          '«${pr['content']}»',
                                          style: const TextStyle(fontSize: 11, color: Colors.black87),
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFFEF3C7),
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: const Text('در انتظار تأیید', style: TextStyle(fontSize: 9.5, color: Color(0xFFB45309), fontWeight: FontWeight.bold)),
                                      ),
                                    ],
                                  ),
                                )),
                                const SizedBox(height: 4),
                                const Text(
                                  'پس از بررسی و تأیید ناظر محتوا، دیدگاه شما در فهرست عمومی نمایش داده می‌شود.',
                                  style: TextStyle(fontSize: 10, color: Colors.black54),
                                ),
                              ],
                            ),
                          ),
                        ],
                        const SizedBox(height: 10),
                        SizedBox(
                          height: 185,
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemCount: reviews.length,
                            separatorBuilder: (_, _) => const SizedBox(width: 16),
                            itemBuilder: (ctx, i) {
                              final rev = reviews[i];
                              final ratingVal = (rev['rating'] ?? 5) is num ? (rev['rating'] as num).toInt() : 5;
                              final authorName = (rev['author'] ?? 'کاربر محترم').toString();

                              return Container(
                                width: 320,
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(color: EttehadColors.border),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withValues(alpha: 0.03),
                                      blurRadius: 8,
                                      offset: const Offset(0, 3),
                                    ),
                                  ],
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    // Row: Avatar on right + (Name, Stars) in column next to it
                                    Row(
                                      crossAxisAlignment: CrossAxisAlignment.center,
                                      children: [
                                        CircleAvatar(
                                          radius: 19,
                                          backgroundColor: EttehadColors.primary.withValues(alpha: 0.12),
                                          child: Text(
                                            authorName.isNotEmpty ? authorName[0] : 'ک',
                                            style: const TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 14,
                                              color: EttehadColors.primary,
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                authorName,
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                                style: const TextStyle(
                                                  fontSize: 12,
                                                  fontWeight: FontWeight.w900,
                                                  color: EttehadColors.navy,
                                                ),
                                              ),
                                              const SizedBox(height: 3),
                                              Row(
                                                children: List.generate(5, (starIdx) {
                                                  return Icon(
                                                    starIdx < ratingVal ? Icons.star_rounded : Icons.star_border_rounded,
                                                    size: 15,
                                                    color: Colors.amber,
                                                  );
                                                }),
                                              ),
                                            ],
                                          ),
                                        ),
                                        Text(
                                          (rev['time'] ?? 'به‌تازگی').toString(),
                                          style: const TextStyle(fontSize: 10, color: Colors.black38),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 8),
                                    Expanded(
                                      child: Text(
                                        (rev['content'] ?? '').toString(),
                                        maxLines: 4,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(fontSize: 11.5, height: 1.6, color: Colors.black87),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),

                    // 8. SUBMIT NEW REVIEW & STARS (EXPANDED TO MULTI-LINE)
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: EttehadColors.border),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.03),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('ثبت دیدگاه شما', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: EttehadColors.primary)),
                              Row(
                                children: [1, 2, 3, 4, 5].map((star) {
                                  return GestureDetector(
                                    onTap: () => setState(() => _userReviewRating = star),
                                    child: Padding(
                                      padding: const EdgeInsets.symmetric(horizontal: 2),
                                      child: Icon(
                                        star <= _userReviewRating ? Icons.star_rounded : Icons.star_border_rounded,
                                        color: Colors.amber,
                                        size: 24,
                                      ),
                                    ),
                                  );
                                }).toList(),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _reviewInputCtrl,
                            minLines: 3,
                            maxLines: 5,
                            style: const TextStyle(fontSize: 12),
                            decoration: InputDecoration(
                              hintText: 'تجربه مطالعه، نقد یا دیدگاه ارزشمند خود درباره این کتاب را بنویسید...',
                              hintStyle: const TextStyle(fontSize: 11.5),
                              filled: true,
                              fillColor: EttehadColors.surfaceLow,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                              contentPadding: const EdgeInsets.all(12),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: ElevatedButton.icon(
                              onPressed: () {
                                if (_reviewInputCtrl.text.trim().isNotEmpty) {
                                  widget.repo.submitBookReview(bookId, _reviewInputCtrl.text, _userReviewRating.toDouble());
                                  _reviewInputCtrl.clear();
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text('دیدگاه شما با موفقیت ثبت شد و پس از بررسی و تأیید مدیر نمایش داده خواهد شد.'),
                                      duration: Duration(seconds: 4),
                                      behavior: SnackBarBehavior.floating,
                                    ),
                                  );
                                  setState(() {});
                                }
                              },
                              icon: const Icon(Icons.rate_review_rounded, size: 16),
                              label: const Text('ثبت نظر و تجربه', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: EttehadColors.primary,
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 22),

                    // 9. THREE RECOMMENDED 3D SHELVES AT THE BOTTOM (EXPANDED BOOK CARDS + HORIZONTAL SCROLL + "بیشتر" OPTION)
                    _bottomRecommendedShelf('آثار مشابه هم‌موضوع', similarBooks),
                    const SizedBox(height: 18),
                    _bottomRecommendedShelf('از همین نویسنده ($author)', sameAuthorBooks),
                    const SizedBox(height: 18),
                    _bottomRecommendedShelf('از همین ناشر ($publisher)', samePublisherBooks),
                    const SizedBox(height: 18),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _bottomRecommendedShelf(String title, List<Map<String, dynamic>> bookList) {
    if (bookList.isEmpty) return const SizedBox.shrink();
    final isExpanded = _expandedShelves.contains(title);
    final displayedBooks = isExpanded ? bookList : bookList.take(5).toList();
    final hasMore = bookList.length > 5;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Row(
                children: [
                  const Icon(Icons.shelves, size: 18, color: EttehadColors.primary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w900, color: EttehadColors.navy),
                    ),
                  ),
                ],
              ),
            ),
            if (hasMore)
              TextButton.icon(
                onPressed: () {
                  setState(() {
                    if (isExpanded) {
                      _expandedShelves.remove(title);
                    } else {
                      _expandedShelves.add(title);
                    }
                  });
                },
                icon: Icon(
                  isExpanded ? Icons.expand_less_rounded : Icons.arrow_back_rounded,
                  size: 14,
                  color: EttehadColors.primary,
                ),
                label: Text(
                  isExpanded ? 'کمتر' : 'بیشتر...',
                  style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                ),
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
          ],
        ),
        const SizedBox(height: 10),
        SizedBox(
          height: 170,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: displayedBooks.length + (!isExpanded && hasMore ? 1 : 0),
            separatorBuilder: (_, _) => const SizedBox(width: 16),
            itemBuilder: (ctx, i) {
              if (!isExpanded && hasMore && i == displayedBooks.length) {
                // "بیشتر" End Card
                return GestureDetector(
                  onTap: () {
                    setState(() {
                      _expandedShelves.add(title);
                    });
                  },
                  child: Container(
                    width: 95,
                    height: 140,
                    decoration: BoxDecoration(
                      color: EttehadColors.surfaceLow,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: EttehadColors.border, strokeAlign: BorderSide.strokeAlignInside),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: EttehadColors.primary.withValues(alpha: 0.1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.arrow_back_rounded, size: 20, color: EttehadColors.primary),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'مشاهده همه\n(بیشتر)',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.bold,
                            color: EttehadColors.primary,
                            height: 1.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }

              final b = displayedBooks[i];
              return GestureDetector(
                onTap: () {
                  Navigator.of(context).pop();
                  showModalBottomSheet(
                    context: context,
                    isScrollControlled: true,
                    backgroundColor: Colors.transparent,
                    builder: (c) => _BookDetailModal(
                      book: b,
                      repo: widget.repo,
                      onStartReading: () {
                        Navigator.of(c).pop();
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => Directionality(
                              textDirection: TextDirection.rtl,
                              child: NativeBookReaderScreen(book: b, repo: widget.repo),
                            ),
                          ),
                        );
                      },
                      onAskAi: () {
                        Navigator.of(c).pop();
                        widget.onAskAi();
                      },
                    ),
                  );
                },
                child: Row(
                  children: [
                    Container(
                      width: 10,
                      height: 140,
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(colors: [Color(0xFF061B42), Color(0xFF1D4ED8)]),
                        borderRadius: BorderRadius.horizontal(right: Radius.circular(4)),
                      ),
                    ),
                    Container(
                      width: 105,
                      height: 140,
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [EttehadColors.navy, EttehadColors.primary],
                          begin: Alignment.topRight,
                          end: Alignment.bottomLeft,
                        ),
                        borderRadius: const BorderRadius.horizontal(left: Radius.circular(10)),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.2),
                            blurRadius: 6,
                            offset: const Offset(-2, 4),
                          ),
                        ],
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.menu_book_rounded, color: Colors.amberAccent, size: 20),
                          const SizedBox(height: 6),
                          Text(
                            (b['title'] ?? '').toString(),
                            textAlign: TextAlign.center,
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 10.5,
                              fontWeight: FontWeight.bold,
                              height: 1.3,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            (b['author'] ?? '').toString(),
                            textAlign: TextAlign.center,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.75),
                              fontSize: 9,
                            ),
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
        Container(
          height: 8,
          margin: const EdgeInsets.only(top: 6),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFF92400E), Color(0xFFD97706), Color(0xFF78350F)]),
            borderRadius: BorderRadius.circular(4),
          ),
        ),
      ],
    );
  }

  Widget _specColumn(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 18, color: EttehadColors.primary),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 10, color: Colors.black54)),
          const SizedBox(height: 3),
          Text(
            value,
            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900, color: EttehadColors.navy),
          ),
        ],
      ),
    );
  }

  Widget _specDivider() {
    return Container(width: 1, height: 38, color: EttehadColors.border);
  }

  Widget _promptChip(String text, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.amber.shade300),
        ),
        child: Text(text, style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.amber.shade900)),
      ),
    );
  }

  Widget _iconBtn(IconData icon, String text, VoidCallback onTap, {bool active = false}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: active ? EttehadColors.primary.withValues(alpha: 0.12) : EttehadColors.surfaceLow,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: active ? EttehadColors.primary : EttehadColors.border),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: active ? EttehadColors.primary : EttehadColors.navy),
            const SizedBox(width: 5),
            Text(
              text,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: active ? EttehadColors.primary : EttehadColors.navy,
              ),
            ),
          ],
        ),
      ),
    );
  }
}


// -------------------------------------------------------------

// -----------------------------------------------------------------------------
// NATIVE BOOK READER SCREEN (WITH HORIZONTAL PAGING, TEXT ACTIONS, AI & PROGRESS)
// -----------------------------------------------------------------------------
class _ReaderBookPage {
  final int pageIndex;
  final int pageNumber;
  final int chapterIndex;
  final String chapterTitle;
  final String subchapterTitle;
  final List<String> paragraphs;

  const _ReaderBookPage({
    required this.pageIndex,
    required this.pageNumber,
    required this.chapterIndex,
    required this.chapterTitle,
    required this.subchapterTitle,
    required this.paragraphs,
  });
}

class NativeBookReaderScreen extends StatefulWidget {
  final Map<String, dynamic> book;
  final EttehadRepository repo;

  const NativeBookReaderScreen({
    super.key,
    required this.book,
    required this.repo,
  });

  @override
  State<NativeBookReaderScreen> createState() => _NativeBookReaderScreenState();
}

class _NativeBookReaderScreenState extends State<NativeBookReaderScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  late final List<Map<String, dynamic>> _chapters;
  late final PageController _pageController;

  int _totalPages = 1;
  int _currentPage = 1;
  int _currentChapterIndex = 0;
  List<_ReaderBookPage> _paginatedPages = [];
  String _drawerTab = 'toc'; // 'toc' | 'bookmarks'

  double _fontSize = 17.5;
  double _lineHeight = 1.95; // Standard scholarly line height
  String _fontFamily = 'Vazirmatn';
  String _themeMode = 'paper'; // 'paper' | 'sepia' | 'night'
  String _translationMode = 'interlinear'; // 'interlinear' | 'full' | 'off'
  String _appLanguage = 'fa'; // 'fa' | 'ar' | 'en'
  bool _zenMode = false;
  String _tocSearchQuery = '';

  // Active AI Chat Session state
  String _activeAiCategory = 'all';
  String? _currentSessionId;
  final List<Map<String, dynamic>> _currentChatMessages = [];

  @override
  void initState() {
    super.initState();
    String bookId = (widget.book['id'] ?? '').toString();
    if (bookId.contains('/book/')) {
      final parts = bookId.split('/book/')[1].split('/');
      if (parts.isNotEmpty && parts[0].isNotEmpty) {
        bookId = parts[0];
      }
    }

    var loaded = widget.repo.getChaptersForBook(bookId);
    if (loaded.isEmpty) {
      final bookTitle = (widget.book['title'] ?? '').toString().trim();
      if (bookTitle.isNotEmpty) {
        final matchedBook = widget.repo.books.firstWhere(
          (b) {
            final t = (b['title'] ?? '').toString().trim();
            return t == bookTitle || bookTitle.contains(t) || t.contains(bookTitle);
          },
          orElse: () => <String, dynamic>{},
        );
        if (matchedBook.isNotEmpty) {
          loaded = widget.repo.getChaptersForBook(matchedBook['id'].toString());
        }
      }
    }

    if (loaded.isEmpty && widget.repo.books.isNotEmpty) {
      loaded = widget.repo.getChaptersForBook(widget.repo.books.first['id'].toString());
    }

    if (loaded.isEmpty) {
      final defaultExcerpt = (widget.book['excerpt'] ?? widget.book['content'] ?? widget.book['title'] ?? 'محتوای منبع معارفی').toString();
      loaded = [
        {
          'id': 'ch_fallback_$bookId',
          'book_id': bookId.isNotEmpty ? bookId : '1',
          'title': (widget.book['title'] ?? 'فصل اول').toString(),
          'order_index': 1,
          'content': defaultExcerpt,
          'subchapters': [
            {'title': 'متن و شواهد فصل', 'page': 1}
          ],
        }
      ];
    }

    _chapters = loaded;
    _buildPaginatedPages();
    _currentPage = 1;
    _pageController = PageController(initialPage: 0);
    _syncChapterWithPage(_currentPage);
    _initDefaultAiChat();
  }

  List<String> _segmentTextIntoReadableParagraphs(String rawContent) {
    if (rawContent.trim().isEmpty) return [];

    // 1. Normalize escaped newlines (\r\n, \r, \n) and OpenITI markers
    String content = rawContent;
    if (content.contains(r'\n') || content.contains(r'\r')) {
      content = content
          .replaceAll(r'\r\n', '\n')
          .replaceAll(r'\r', '\n')
          .replaceAll(r'\n', '\n');
    }
    content = content
        .replaceAll('\r\n', '\n')
        .replaceAll('\r', '\n')
        .replaceAll(RegExp(r'\s*\|\|\s*AUTO\s*'), '\n\n')
        .replaceAll(RegExp(r'\s*###\s*'), '\n\n')
        .replaceAll(RegExp(r'\n{3,}'), '\n\n');

    // 2. Split on double newlines
    final rawParas = content
        .split(RegExp(r'\n\s*\n+'))
        .map((p) => p.trim())
        .where((p) => p.isNotEmpty)
        .toList();

    final List<String> result = [];

    // Classical Arabic & Persian sentence connection patterns for long chunks
    final connectorRegex = RegExp(
      r'(?<=\S)\s+(?=(?:ثم|فإن|فإذا|ومن|وقد|ويستحب|ويجوز|ولا يجوز|ويحرم|وقال|روى|فرع:|مسألة:|أما|سپس|بنابراین|در نتیجه|همچنین|از این رو)\s+)',
    );
    final punctuationRegex = RegExp(r'(?<=[\.\؛\؟\!])\s+');

    for (final p in rawParas) {
      // If the paragraph already has single newlines, honor those line breaks
      if (p.contains('\n')) {
        final lines = p.split('\n').map((l) => l.trim()).where((l) => l.isNotEmpty).toList();
        final List<String> subChunk = [];
        int subLen = 0;
        for (final l in lines) {
          subChunk.add(l);
          subLen += l.length;
          // Break line if long enough or ends with punctuation/dialogue mark
          if (subLen >= 220 ||
              l.endsWith('.') ||
              l.endsWith(':') ||
              l.endsWith('؛') ||
              l.endsWith('؟') ||
              l.endsWith('!') ||
              l.endsWith('»') ||
              l.endsWith('"')) {
            result.add(subChunk.join(' '));
            subChunk.clear();
            subLen = 0;
          }
        }
        if (subChunk.isNotEmpty) {
          result.add(subChunk.join(' '));
        }
        continue;
      }

      // If paragraph is within reasonable reading length (<= 350 chars), keep as is
      if (p.length <= 350) {
        result.add(p);
        continue;
      }

      // If paragraph is long, try splitting on punctuation first (. ؛ ؟ !)
      final punctPieces = p.split(punctuationRegex);
      for (final piece in punctPieces) {
        final trimmed = piece.trim();
        if (trimmed.isEmpty) continue;

        if (trimmed.length <= 350) {
          result.add(trimmed);
        } else {
          // Paragraph has no punctuation (classical text), split at natural sentence connectors
          final subPieces = trimmed.split(connectorRegex);
          final List<String> accum = [];
          int accumLen = 0;

          for (final sp in subPieces) {
            final spTrimmed = sp.trim();
            if (spTrimmed.isEmpty) continue;

            accum.add(spTrimmed);
            accumLen += spTrimmed.length;

            if (accumLen >= 220) {
              result.add(accum.join(' '));
              accum.clear();
              accumLen = 0;
            }
          }
          if (accum.isNotEmpty) {
            result.add(accum.join(' '));
          }
        }
      }
    }

    return result.isNotEmpty ? result : [content.trim()];
  }

  void _buildPaginatedPages() {
    final List<_ReaderBookPage> pages = [];
    int globalPageNum = 1;

    for (int chIdx = 0; chIdx < _chapters.length; chIdx++) {
      final ch = _chapters[chIdx];
      final chTitle = (ch['title'] ?? 'فصل ${chIdx + 1}').toString();
      final subchapters = List<Map<String, dynamic>>.from(ch['subchapters'] ?? []);
      final rawContent = (ch['content'] ?? ch['text'] ?? '').toString();

      List<String> rawParagraphs = _segmentTextIntoReadableParagraphs(rawContent);

      if (rawParagraphs.isEmpty) {
        rawParagraphs = [
          'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ\nالحمد لله رب العالمین و الصلاة و السلام علی سیدنا محمد و آله الطاهرین.'
        ];
      }

      // Group into 2 paragraphs per page (or max 3 if very short)
      // "طول افقی اسکرول خیلی زیاده برای یک کتاب. لطفاً بعد از چند پاراگراف کاربر باید اسکرول افقی کنه که مانند صفحه بعد باشه."
      List<String> currentChunk = [];
      int currentLength = 0;

      for (int pIdx = 0; pIdx < rawParagraphs.length; pIdx++) {
        final p = rawParagraphs[pIdx];
        currentChunk.add(p);
        currentLength += p.length;

        final bool isLast = pIdx == rawParagraphs.length - 1;
        final bool shouldBreak = currentChunk.length >= 2 || currentLength > 550 || isLast;

        if (shouldBreak) {
          final subTitle = subchapters.isNotEmpty
              ? (subchapters[pages.length % subchapters.length]['title'] ?? chTitle).toString()
              : chTitle;

          pages.add(_ReaderBookPage(
            pageIndex: pages.length,
            pageNumber: globalPageNum,
            chapterIndex: chIdx,
            chapterTitle: chTitle,
            subchapterTitle: subTitle,
            paragraphs: List<String>.from(currentChunk),
          ));
          globalPageNum++;
          currentChunk.clear();
          currentLength = 0;
        }
      }
    }

    if (pages.isEmpty) {
      pages.add(const _ReaderBookPage(
        pageIndex: 0,
        pageNumber: 1,
        chapterIndex: 0,
        chapterTitle: 'مقدمه',
        subchapterTitle: 'آغاز مطالعه',
        paragraphs: ['محتوای منبع در حال بارگذاری است...'],
      ));
    }

    _paginatedPages = pages;
    _totalPages = pages.length;
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _syncChapterWithPage(int page) {
    if (_paginatedPages.isEmpty) return;
    final pageItem = _paginatedPages[(page - 1).clamp(0, _paginatedPages.length - 1)];
    _currentChapterIndex = pageItem.chapterIndex;
  }

  void _jumpToPage(int page) {
    final target = page.clamp(1, _totalPages);
    setState(() {
      _currentPage = target;
      _syncChapterWithPage(target);
    });
    if (_pageController.hasClients) {
      _pageController.animateToPage(
        target - 1,
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  Color get _bgColor {
    switch (_themeMode) {
      case 'night':
        return const Color(0xFF0F172A);
      case 'sepia':
        return const Color(0xFFF4ECD8);
      default:
        return const Color(0xFFFDFBF7);
    }
  }

  Color get _textColor {
    return _themeMode == 'night' ? const Color(0xFFF1F5F9) : const Color(0xFF1E293B);
  }

  Color get _cardBgColor {
    return _themeMode == 'night' ? const Color(0xFF1E293B) : Colors.white;
  }

  Color get _transCardBgColor {
    switch (_themeMode) {
      case 'night':
        return const Color(0xFF162032);
      case 'sepia':
        return const Color(0xFFEBE1C7);
      default:
        return const Color(0xFFF6F8FC);
    }
  }

  // --- AI CHAT INITIALIZATION & SESSION MANAGEMENT ---
  void _initDefaultAiChat() {
    final bookTitle = (widget.book['title'] ?? 'کتاب').toString();
    _currentSessionId = 'conv_bk_${DateTime.now().millisecondsSinceEpoch}';
    _currentChatMessages.clear();
    _currentChatMessages.add({
      'role': 'assistant',
      'content':
          'سلام علیکم! من دستیار هوشمند «اتحادیار» متصل به پایگاه معارفی این کتاب هستم. پیرامون اثر ارزشمند «$bookTitle»، استنادات فریقین و مفاهیم هر فصل در خدمت شما هستم.',
      'citation': null,
    });
  }

  // --- TEXT SELECTION ACTIONS TOOLBAR (یک، پنج، شش) ---
  void _handleTextAction(String action, String selectedText) {
    final bookTitle = (widget.book['title'] ?? 'کتاب مرجع').toString();
    final bookId = widget.book['id'].toString();

    switch (action) {
      case 'ASK_AI':
        _openAiChatSheet(initialPrompt: 'پیرامون این فراز از کتاب:\n«$selectedText»\nسؤال من: ');
        break;

      case 'SHARE_AI':
        _showAiInsightDialog(selectedText);
        break;

      case 'SEND_TO_SCHOLAR':
        _showSendToScholarDialog(selectedText, bookTitle, bookId);
        break;

      case 'TRANSLATE':
        _showTranslationDialog(selectedText);
        break;

      case 'COPY':
        Clipboard.setData(ClipboardData(text: selectedText));
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('متن در حافظه موقت (Clipboard) کپی شد.'),
            duration: Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
        break;

      case 'HIGHLIGHT':
        final preview = selectedText.length > 50 ? selectedText.substring(0, 50) : selectedText;
        final chTitle = _chapters.isNotEmpty && _currentChapterIndex < _chapters.length
            ? (_chapters[_currentChapterIndex]['title'] ?? 'فصل').toString()
            : 'فصل جاری';
        widget.repo.togglePageBookmark(
          bookId,
          _currentPage,
          chapterTitle: chTitle,
          title: 'فراز برگزیده ص ${toPersianDigits(_currentPage)}',
          excerpt: selectedText,
          note: preview,
        );
        setState(() {});
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('فراز مورد نظر هایلایت و در نشانک‌ها ذخیره شد.'),
            duration: Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
        break;
    }
  }

  // Dialog: Instant AI Insight (اشتراک با هوش)
  void _showAiInsightDialog(String text) {
    final bookTitle = (widget.book['title'] ?? 'کتاب مرجع').toString();
    final bookId = widget.book['id'].toString();
    final analysisFuture = widget.repo.analyzeTextWithAi(
      bookId: bookId,
      bookTitle: bookTitle,
      text: text,
    );

    showDialog(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(colors: [Color(0xFFD97706), Color(0xFFF59E0B)]),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.auto_awesome, color: Colors.white, size: 18),
              ),
              const SizedBox(width: 8),
              const Text('تحلیل هوش مصنوعی فراز انتخابی', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900)),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.amber.shade50,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.amber.shade200),
                  ),
                  child: Text(
                    '«$text»',
                    style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: Color(0xFF78350F), height: 1.6),
                  ),
                ),
                const SizedBox(height: 12),
                const Text('پیام کلیدی و دلالت معرفتی:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                const SizedBox(height: 6),
                FutureBuilder<String>(
                  future: analysisFuture,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Padding(
                        padding: EdgeInsets.symmetric(vertical: 16),
                        child: Row(
                          children: [
                            SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: EttehadColors.primary)),
                            SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                'در حال اتصال به هوش مصنوعی و کاوش در متن اثر (api.unitysi.ir)...',
                                style: TextStyle(fontSize: 11.5, color: Colors.black54),
                              ),
                            ),
                          ],
                        ),
                      );
                    }
                    final analysisText = snapshot.data ?? 'این فراز از کتاب بر اصل انسجام ایمانی و تدبر در معارف اسلامی دلالت دارد.';
                    return Text(
                      analysisText,
                      style: const TextStyle(fontSize: 12, height: 1.8, color: Colors.black87),
                    );
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('بستن'),
            ),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: EttehadColors.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () {
                Navigator.pop(ctx);
                _openAiChatSheet(initialPrompt: 'لطفاً ابعاد تفسیری و کاربردی این فراز را بیشتر شرح بده:\n«$text»');
              },
              icon: const Icon(Icons.forum_rounded, size: 16),
              label: const Text('ادامه گفتگو با هوش', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  // Dialog: Send Excerpt to Scholar (پنج - ارسال متن به علما)
  void _showSendToScholarDialog(String text, String bookTitle, String bookId) {
    final scholars = widget.repo.scholars;
    String selectedScholarId = scholars.isNotEmpty ? scholars.first['id'].toString() : '1';
    final userNoteCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDlgState) => Directionality(
          textDirection: TextDirection.rtl,
          child: AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Row(
              children: [
                Icon(Icons.record_voice_over_rounded, color: EttehadColors.primary, size: 22),
                SizedBox(width: 8),
                Text('ارسال فراز کتاب به علمای معارفی', style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w900)),
              ],
            ),
            content: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('انتخاب استاد یا عالم پاسخگو:', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: EttehadColors.border),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        isExpanded: true,
                        value: selectedScholarId,
                        items: scholars.map((sc) {
                          return DropdownMenuItem<String>(
                            value: sc['id'].toString(),
                            child: Text(
                              '${sc['name']} (${sc['specialization'] ?? 'استاد حوزه و دانشگاه'})',
                              style: const TextStyle(fontSize: 11.5),
                            ),
                          );
                        }).toList(),
                        onChanged: (v) {
                          if (v != null) setDlgState(() => selectedScholarId = v);
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text('متن پیوست‌شده از کتاب:', style: TextStyle(fontSize: 11, color: Colors.black54)),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.black12),
                    ),
                    child: Text(
                      '«$text»\n[منبع: $bookTitle - صفحه ${toPersianDigits(_currentPage)}]',
                      style: const TextStyle(fontSize: 11, height: 1.6, color: Colors.black87),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text('پرسش یا ابهام شما (اختیاری):', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: userNoteCtrl,
                    maxLines: 2,
                    decoration: InputDecoration(
                      hintText: 'پرسش خود پیرامون استناد یا فتوای این فراز را بنویسید...',
                      hintStyle: const TextStyle(fontSize: 11),
                      filled: true,
                      fillColor: Colors.white,
                      contentPadding: const EdgeInsets.all(10),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: EttehadColors.border)),
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('انصراف'),
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: () {
                  widget.repo.sendBookExcerptToScholar(
                    scholarId: selectedScholarId,
                    excerpt: text,
                    bookId: bookId,
                    bookTitle: bookTitle,
                    userQuestion: userNoteCtrl.text,
                  );
                  Navigator.pop(ctx);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('فراز کتاب به همراه پرسش شما با موفقیت به دفتر عالم معارفی ارسال شد.'),
                      duration: Duration(seconds: 3),
                      backgroundColor: EttehadColors.primary,
                      behavior: SnackBarBehavior.floating,
                    ),
                  );
                },
                icon: const Icon(Icons.send_rounded, size: 16),
                label: const Text('ارسال به دفتر پاسخگویی', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Dialog: Instant Text Translation (شش - ترجمه متن بر اساس زبان برنامه)
  void _showTranslationDialog(String text) {
    final translationFuture = widget.repo.translateTextWithAi(
      text: text,
      targetLanguage: _appLanguage,
    );

    showDialog(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(10)),
                child: const Icon(Icons.translate_rounded, color: Colors.blue, size: 20),
              ),
              const SizedBox(width: 8),
              Text(
                'ترجمه فراز (زبان: ${_appLanguage == 'fa' ? 'فارسی' : _appLanguage == 'en' ? 'انگلیسی' : 'عربی'})',
                style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w900),
              ),
            ],
          ),
          content: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  'متن مبدأ:\n«$text»',
                  style: const TextStyle(fontSize: 11.5, height: 1.6, color: Colors.black54),
                ),
              ),
              const SizedBox(height: 12),
              FutureBuilder<String>(
                future: translationFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50.withValues(alpha: 0.5),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.blue.shade200),
                      ),
                      child: const Row(
                        children: [
                          SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: EttehadColors.primary)),
                          SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'در حال ترجمه برخط با هوش مصنوعی (api.unitysi.ir)...',
                              style: TextStyle(fontSize: 11.5, color: Colors.black54),
                            ),
                          ),
                        ],
                      ),
                    );
                  }
                  final translatedText = snapshot.data ?? 'ترجمه انجام نشد.';
                  return Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.blue.shade50.withValues(alpha: 0.5),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.blue.shade200),
                    ),
                    child: SelectableText(
                      translatedText,
                      style: const TextStyle(fontSize: 12.5, height: 1.85, fontWeight: FontWeight.w600, color: Color(0xFF0F172A)),
                    ),
                  );
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('بستن'),
            ),
            FutureBuilder<String>(
              future: translationFuture,
              builder: (context, snapshot) {
                final txt = snapshot.data;
                return ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: EttehadColors.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  onPressed: txt != null
                      ? () {
                          Clipboard.setData(ClipboardData(text: txt));
                          Navigator.pop(ctx);
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('ترجمه کپی شد.'), duration: Duration(seconds: 1)),
                          );
                        }
                      : null,
                  icon: const Icon(Icons.copy_rounded, size: 16),
                  label: const Text('کپی ترجمه', style: TextStyle(fontSize: 11)),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  // --- REVAMPED BOOK AI CHAT SHEET (چهارده و شانزده) ---
  void _openAiChatSheet({String? initialPrompt}) {
    final bookTitle = (widget.book['title'] ?? 'کتاب').toString();
    final promptController = TextEditingController(text: initialPrompt ?? '');
    String activeSheetTab = 'chat'; // 'chat' | 'history'

    widget.repo.fetchBookAiSessions(widget.book['id'].toString());
    widget.repo.fetchBookAiCategories();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheetState) {
          final sessions = widget.repo.getBookAiSessions(
            widget.book['id'].toString(),
            category: _activeAiCategory == 'all' ? null : _activeAiCategory,
          );

          return Directionality(
            textDirection: TextDirection.rtl,
            child: Container(
              height: MediaQuery.of(context).size.height * 0.88,
              padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
              decoration: BoxDecoration(
                color: _cardBgColor,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(26)),
                boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 20)],
              ),
              child: Column(
                children: [
                  const SizedBox(height: 8),
                  Center(
                    child: Container(
                      width: 44,
                      height: 4.5,
                      decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(10)),
                    ),
                  ),

                  // Header with Book Logo (چهارده - علامت ربات لوگوی کتاب)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 36,
                              height: 36,
                              padding: const EdgeInsets.all(3),
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(color: const Color(0xFFD97706), width: 1.8),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.amber.withValues(alpha: 0.3),
                                    blurRadius: 8,
                                    spreadRadius: 1,
                                  ),
                                ],
                              ),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(18),
                                child: Image.asset('assets/images/app_icon.png', fit: BoxFit.cover),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text('اتحادیار معارفی • $bookTitle',
                                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: EttehadColors.navy)),
                                    const SizedBox(width: 6),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: Colors.green.shade50,
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(color: Colors.green.shade200),
                                      ),
                                      child: const Text('ایجنت مادر فعال',
                                          style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.green)),
                                    ),
                                  ],
                                ),
                                Text(
                                  'دسته‌بندی فعال: ${_activeAiCategory == 'all' ? 'همه موضوعات' : _activeAiCategory} • صفحه ${toPersianDigits(_currentPage)}',
                                  style: const TextStyle(fontSize: 10, color: Colors.black54),
                                ),
                              ],
                            ),
                          ],
                        ),
                        IconButton(
                          icon: const Icon(Icons.close_rounded, size: 20),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                  ),

                  // Tab switcher: گفتگوی جاری | تاریخچه نشست‌ها
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 14),
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: InkWell(
                            onTap: () => setSheetState(() => activeSheetTab = 'chat'),
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 6),
                              decoration: BoxDecoration(
                                color: activeSheetTab == 'chat' ? Colors.white : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                                boxShadow: activeSheetTab == 'chat' ? const [BoxShadow(color: Colors.black12, blurRadius: 4)] : null,
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.chat_bubble_rounded, size: 14, color: activeSheetTab == 'chat' ? EttehadColors.primary : Colors.black54),
                                  const SizedBox(width: 6),
                                  Text(
                                    'گفت‌وگوی جاری',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: activeSheetTab == 'chat' ? FontWeight.bold : FontWeight.normal,
                                      color: activeSheetTab == 'chat' ? EttehadColors.primary : Colors.black54,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        Expanded(
                          child: InkWell(
                            onTap: () => setSheetState(() => activeSheetTab = 'history'),
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 6),
                              decoration: BoxDecoration(
                                color: activeSheetTab == 'history' ? Colors.white : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                                boxShadow: activeSheetTab == 'history' ? const [BoxShadow(color: Colors.black12, blurRadius: 4)] : null,
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.history_rounded, size: 14, color: activeSheetTab == 'history' ? EttehadColors.primary : Colors.black54),
                                  const SizedBox(width: 6),
                                  Text(
                                    'تاریخچه نشست‌ها (${toPersianDigits(sessions.length)})',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: activeSheetTab == 'history' ? FontWeight.bold : FontWeight.normal,
                                      color: activeSheetTab == 'history' ? EttehadColors.primary : Colors.black54,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Category horizontal pill bar with "+ افزودن دسته‌بندی" (چهارده)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          _categoryChip('all', 'همه موضوعات', _activeAiCategory == 'all', () {
                            setSheetState(() => _activeAiCategory = 'all');
                          }),
                          const SizedBox(width: 6),
                          ...widget.repo.bookAiCategories.map((c) {
                            final name = c['name'].toString();
                            final isSel = _activeAiCategory == name;
                            return Padding(
                              padding: const EdgeInsets.only(left: 6),
                              child: _categoryChip(c['id'].toString(), name, isSel, () {
                                setSheetState(() => _activeAiCategory = name);
                              }),
                            );
                          }),
                          const SizedBox(width: 6),
                          ActionChip(
                            avatar: const Icon(Icons.add_rounded, size: 14, color: EttehadColors.primary),
                            label: const Text('دسته‌بندی جدید', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: EttehadColors.primary)),
                            backgroundColor: EttehadColors.primary.withValues(alpha: 0.1),
                            side: const BorderSide(color: EttehadColors.primary),
                            onPressed: () => _showAddCategoryDialog(() => setSheetState(() {})),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const Divider(height: 1),

                  // TAB CONTENT
                  if (activeSheetTab == 'history')
                    Expanded(
                      child: sessions.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.history_toggle_off_rounded, size: 48, color: Colors.grey.shade400),
                                  const SizedBox(height: 10),
                                  const Text('هنوز نشستی در این موضوع ذخیره نشده است.', style: TextStyle(fontSize: 12, color: Colors.black54)),
                                  const SizedBox(height: 12),
                                  ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: EttehadColors.primary,
                                      foregroundColor: Colors.white,
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                    ),
                                    onPressed: () {
                                      _startNewAiSession();
                                      setSheetState(() => activeSheetTab = 'chat');
                                    },
                                    icon: const Icon(Icons.add_comment_rounded, size: 16),
                                    label: const Text('شروع گفت‌وگوی جدید', style: TextStyle(fontSize: 11.5)),
                                  ),
                                ],
                              ),
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.all(12),
                              itemCount: sessions.length,
                              separatorBuilder: (_, _) => const SizedBox(height: 8),
                              itemBuilder: (ctx, idx) {
                                final s = sessions[idx];
                                return InkWell(
                                  borderRadius: BorderRadius.circular(12),
                                  onTap: () {
                                    setSheetState(() {
                                      _currentSessionId = s['id'].toString();
                                      activeSheetTab = 'chat';
                                    });
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(color: EttehadColors.border),
                                    ),
                                    child: Row(
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.all(8),
                                          decoration: BoxDecoration(color: Colors.amber.shade50, borderRadius: BorderRadius.circular(10)),
                                          child: const Icon(Icons.bookmark_border_rounded, color: Color(0xFFD97706), size: 18),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(s['title'].toString(), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                                              const SizedBox(height: 2),
                                              Text(
                                                'موضوع: ${s['category'] ?? 'عمومی'} • ${toPersianDigits(s['messageCount'] ?? 1)} پیام',
                                                style: const TextStyle(fontSize: 10, color: Colors.black45),
                                              ),
                                            ],
                                          ),
                                        ),
                                        const Icon(Icons.chevron_left_rounded, size: 18, color: Colors.black38),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
                    )
                  else ...[
                    // Suggested Prompts
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      color: Colors.amber.shade50.withValues(alpha: 0.6),
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: [
                            _aiChip('خلاصه جامع این صفحه', () {
                              promptController.text = 'لطفاً خلاصه آموزه‌ها و نکات کلیدی صفحه ${toPersianDigits(_currentPage)} را بیان کن.';
                              setSheetState(() {});
                            }),
                            const SizedBox(width: 6),
                            _aiChip('روایات و اقوال فریقین', () {
                              promptController.text = 'دیدگاه‌های مقارن مذاهب پیرامون این موضوع در این فصل چیست؟';
                              setSheetState(() {});
                            }),
                            const SizedBox(width: 6),
                            _aiChip('ارجاع به آیات قرآن', () {
                              promptController.text = 'آیات مرتبط با فرازهای این فصل را با ذکر سوره و شماره آیه بیاور.';
                              setSheetState(() {});
                            }),
                          ],
                        ),
                      ),
                    ),

                    // Chat messages list
                    Expanded(
                      child: ListView.builder(
                        padding: const EdgeInsets.all(14),
                        itemCount: _currentChatMessages.length,
                        itemBuilder: (ctx, i) {
                          final m = _currentChatMessages[i];
                          final isUser = m['role'] == 'user';
                          final citation = m['citation'] as Map<String, dynamic>?;

                          return Align(
                            alignment: isUser ? Alignment.centerLeft : Alignment.centerRight,
                            child: Container(
                              margin: const EdgeInsets.only(bottom: 12),
                              constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.85),
                              child: Column(
                                crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      if (!isUser) ...[
                                        const CircleAvatar(
                                          radius: 10,
                                          backgroundImage: AssetImage('assets/images/app_icon.png'),
                                        ),
                                        const SizedBox(width: 6),
                                        const Text('اتحادیار معارفی', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: EttehadColors.primary)),
                                      ],
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: isUser ? EttehadColors.primary : Colors.white,
                                      borderRadius: BorderRadius.circular(16),
                                      border: Border.all(color: isUser ? EttehadColors.primary : EttehadColors.border),
                                      boxShadow: [
                                        BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 4, offset: const Offset(0, 2)),
                                      ],
                                    ),
                                    child: Text(
                                      m['content']!,
                                      style: TextStyle(
                                        fontSize: 12.5,
                                        height: 1.65,
                                        color: isUser ? Colors.white : EttehadColors.ink,
                                        fontWeight: isUser ? FontWeight.bold : FontWeight.normal,
                                      ),
                                    ),
                                  ),

                                  // CLICKABLE CITATION / EXCERPT BADGE (چهارده - کلیک روی متن و پرش به صفحه)
                                  if (citation != null) ...[
                                    const SizedBox(height: 6),
                                    InkWell(
                                      borderRadius: BorderRadius.circular(12),
                                      onTap: () {
                                        Navigator.pop(ctx);
                                        final targetPage = (citation['page'] as num?)?.toInt() ?? _currentPage;
                                        _jumpToPage(targetPage);
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            content: Text('پرش به صفحه ${toPersianDigits(targetPage)} بر اساس ارجاع هوش مصنوعی.'),
                                            duration: const Duration(seconds: 2),
                                            behavior: SnackBarBehavior.floating,
                                            backgroundColor: const Color(0xFFD97706),
                                          ),
                                        );
                                      },
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                        decoration: BoxDecoration(
                                          gradient: const LinearGradient(colors: [Color(0xFFFFFBEB), Color(0xFFFEF3C7)]),
                                          borderRadius: BorderRadius.circular(12),
                                          border: Border.all(color: const Color(0xFFF59E0B)),
                                          boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 4)],
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            const Icon(Icons.bookmark_added_rounded, size: 14, color: Color(0xFFD97706)),
                                            const SizedBox(width: 6),
                                            Text(
                                              'بریده منبع: ${citation['chapterTitle']} (صفحه ${toPersianDigits(citation['page'])}) • کلیک جهت پرش به متن',
                                              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Color(0xFF92400E)),
                                            ),
                                            const SizedBox(width: 4),
                                            const Icon(Icons.arrow_back_ios_rounded, size: 10, color: Color(0xFFD97706)),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),

                    // Input field
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: const BoxDecoration(
                        color: Colors.white,
                        border: Border(top: BorderSide(color: EttehadColors.border)),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: promptController,
                              decoration: const InputDecoration(
                                hintText: 'سؤال خود را درباره این صفحه یا فصل بپرسید...',
                                hintStyle: TextStyle(fontSize: 12),
                                border: InputBorder.none,
                              ),
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.send_rounded, color: EttehadColors.primary),
                            onPressed: () async {
                              final text = promptController.text.trim();
                              if (text.isEmpty) return;
                              promptController.clear();
                              final activeChapter = _chapters.isNotEmpty && _currentChapterIndex < _chapters.length
                                  ? _chapters[_currentChapterIndex]
                                  : {'title': 'فصل'};
                              final chTitle = (activeChapter['title'] ?? 'فصل ${_currentChapterIndex + 1}').toString();

                              setSheetState(() {
                                _currentChatMessages.add({'role': 'user', 'content': text, 'citation': null});
                                _currentChatMessages.add({
                                  'role': 'assistant',
                                  'content': 'در حال اتصال به اتحادیار (api.unitysi.ir) و کاوش در متن اثر...',
                                  'citation': null,
                                });
                              });

                              try {
                                final aiRes = await widget.repo.askBookAi(
                                  bookId: widget.book['id'].toString(),
                                  bookTitle: bookTitle,
                                  query: text,
                                  chapterTitle: chTitle,
                                  pageNumber: _currentPage,
                                  conversationId: _currentSessionId,
                                );

                                Map<String, dynamic>? cite;
                                if (aiRes['citations'] is List && (aiRes['citations'] as List).isNotEmpty) {
                                  final first = (aiRes['citations'] as List).first;
                                  if (first is Map) {
                                    cite = {
                                      'chapterTitle': first['chapterTitle'] ?? chTitle,
                                      'page': first['page'] ?? _currentPage,
                                      'quote': first['quote'] ?? 'استناد به متن کتاب «$bookTitle»',
                                    };
                                  }
                                }
                                cite ??= {
                                  'chapterTitle': chTitle,
                                  'page': _currentPage,
                                  'quote': 'متن استناد در صفحه ${toPersianDigits(_currentPage)}',
                                };

                                setSheetState(() {
                                  if (_currentChatMessages.isNotEmpty && _currentChatMessages.last['role'] == 'assistant') {
                                    _currentChatMessages.removeLast();
                                  }
                                  _currentChatMessages.add({
                                    'role': 'assistant',
                                    'content': aiRes['reply']?.toString() ?? 'پاسخی از پایگاه معارفی دریافت نشد.',
                                    'citation': cite,
                                  });
                                });

                                // Persist session
                                final previewTitle = text.length > 30 ? text.substring(0, 30) : text;
                                widget.repo.saveBookAiSession(widget.book['id'].toString(), {
                                  'id': _currentSessionId,
                                  'title': previewTitle,
                                  'category': _activeAiCategory == 'all' ? 'عمومی' : _activeAiCategory,
                                  'messageCount': _currentChatMessages.length,
                                  'updatedAt': DateTime.now().toIso8601String(),
                                });
                              } catch (e) {
                                setSheetState(() {
                                  if (_currentChatMessages.isNotEmpty && _currentChatMessages.last['role'] == 'assistant') {
                                    _currentChatMessages.removeLast();
                                  }
                                  _currentChatMessages.add({
                                    'role': 'assistant',
                                    'content': 'خطا در ارتباط با سرور هوش مصنوعی (api.unitysi.ir). لطفاً وضعیت اینترنت را بررسی فرمایید.',
                                    'citation': null,
                                  });
                                });
                              }
                            },
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  void _startNewAiSession() {
    _initDefaultAiChat();
    setState(() {});
  }

  void _showAddCategoryDialog(VoidCallback onAdded) {
    final nameCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('افزودن دسته‌بندی جدید هوش مصنوعی', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
          content: TextField(
            controller: nameCtrl,
            decoration: const InputDecoration(
              hintText: 'عنوان دسته‌بندی (مثلاً: شبهات تاریخی، نقد اقوال)',
              hintStyle: TextStyle(fontSize: 11),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('انصراف')),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: EttehadColors.primary, foregroundColor: Colors.white),
              onPressed: () {
                final txt = nameCtrl.text.trim();
                if (txt.isNotEmpty) {
                  widget.repo.addBookAiCategory(txt);
                  onAdded();
                  Navigator.pop(ctx);
                }
              },
              child: const Text('افزودن'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _categoryChip(String id, String label, bool isSelected, VoidCallback onTap) {
    return FilterChip(
      selected: isSelected,
      selectedColor: EttehadColors.primary,
      backgroundColor: const Color(0xFFF1F5F9),
      label: Text(
        label,
        style: TextStyle(
          fontSize: 10.5,
          fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
          color: isSelected ? Colors.white : EttehadColors.navy,
        ),
      ),
      onSelected: (_) => onTap(),
    );
  }

  Widget _aiChip(String label, VoidCallback onTap) {
    return ActionChip(
      label: Text(label, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
      backgroundColor: Colors.white,
      side: const BorderSide(color: Color(0xFFFBBF24)),
      onPressed: onTap,
    );
  }

  // --- TOP BAR TRANSLATION MODE SWITCHER (شش و هفت) ---
  void _cycleTranslationMode() {
    setState(() {
      if (_translationMode == 'interlinear') {
        _translationMode = 'full';
      } else if (_translationMode == 'full') {
        _translationMode = 'off';
      } else {
        _translationMode = 'interlinear';
      }
    });
    final label = _translationMode == 'interlinear'
        ? 'حالت ترجمه: زیر هر پاراگراف'
        : _translationMode == 'full'
            ? 'حالت ترجمه: کل صفحه'
            : 'ترجمه خاموش (فقط متن اصلی)';
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(label), duration: const Duration(milliseconds: 900), behavior: SnackBarBehavior.floating),
    );
  }

  // --- BUILD METHOD ---
  @override
  Widget build(BuildContext context) {
    final bookTitle = (widget.book['title'] ?? 'کتابخوان اتحاد').toString();
    final author = (widget.book['author'] ?? 'مؤلف معارفی').toString();
    final activeChapter = _chapters.isNotEmpty ? _chapters[_currentChapterIndex] : <String, dynamic>{};
    final chapterTitle = (activeChapter['title'] ?? 'فصل ${_currentChapterIndex + 1}').toString();

    // Progress percentage
    final double progressFraction = (_currentPage / _totalPages).clamp(0.0, 1.0);
    final int progressPercent = (progressFraction * 100).toInt();

    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: _bgColor,

      // RIGHT DRAWER: TABLE OF CONTENTS & BOOKMARKS (فهرست سرفصل‌ها و نشانک‌ها)
      // In RTL, Scaffold.drawer opens from the RIGHT!
      drawer: Drawer(
        backgroundColor: const Color(0xFFFDFBF7),
        child: Directionality(
          textDirection: TextDirection.rtl,
          child: SafeArea(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Drawer Header
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    border: Border(bottom: BorderSide(color: EttehadColors.border)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: EttehadColors.primary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.menu_book_rounded, color: EttehadColors.primary, size: 22),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('راهنمای مطالعه و نشانک‌ها',
                                style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w900, color: EttehadColors.navy)),
                            Text('$author • ${toPersianDigits(_chapters.length)} سرفصل',
                                style: const TextStyle(fontSize: 10.5, color: Colors.black54)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

                // Tab Switcher: سرفصل‌ها | نشانک‌ها
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: InkWell(
                          onTap: () => setState(() => _drawerTab = 'toc'),
                          borderRadius: BorderRadius.circular(8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 6),
                            decoration: BoxDecoration(
                              color: _drawerTab == 'toc' ? Colors.white : Colors.transparent,
                              borderRadius: BorderRadius.circular(8),
                              boxShadow: _drawerTab == 'toc' ? const [BoxShadow(color: Colors.black12, blurRadius: 4)] : null,
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.format_list_bulleted_rounded, size: 14, color: _drawerTab == 'toc' ? EttehadColors.primary : Colors.black54),
                                const SizedBox(width: 4),
                                Text(
                                  'سرفصل‌ها',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: _drawerTab == 'toc' ? FontWeight.bold : FontWeight.normal,
                                    color: _drawerTab == 'toc' ? EttehadColors.primary : Colors.black54,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      Expanded(
                        child: InkWell(
                          onTap: () => setState(() => _drawerTab = 'bookmarks'),
                          borderRadius: BorderRadius.circular(8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 6),
                            decoration: BoxDecoration(
                              color: _drawerTab == 'bookmarks' ? Colors.white : Colors.transparent,
                              borderRadius: BorderRadius.circular(8),
                              boxShadow: _drawerTab == 'bookmarks' ? const [BoxShadow(color: Colors.black12, blurRadius: 4)] : null,
                            ),
                            child: FittedBox(
                              fit: BoxFit.scaleDown,
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.bookmark_rounded, size: 14, color: _drawerTab == 'bookmarks' ? const Color(0xFFD97706) : Colors.black54),
                                  const SizedBox(width: 4),
                                  Text(
                                    'نشانک‌ها (${toPersianDigits(widget.repo.getBookBookmarks(widget.book['id'].toString()).length)})',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: _drawerTab == 'bookmarks' ? FontWeight.bold : FontWeight.normal,
                                      color: _drawerTab == 'bookmarks' ? const Color(0xFFD97706) : Colors.black54,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                if (_drawerTab == 'bookmarks') ...[
                  // BOOKMARKS LIST VIEW
                  Expanded(
                    child: Builder(
                      builder: (ctx) {
                        final bms = widget.repo.getBookBookmarks(widget.book['id'].toString());
                        if (bms.isEmpty) {
                          return Center(
                            child: Padding(
                              padding: const EdgeInsets.all(24),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.bookmark_border_rounded, size: 48, color: Colors.amber.shade300),
                                  const SizedBox(height: 12),
                                  const Text(
                                    'هنوز هیچ صفحه‌ای نشان‌گذاری نشده است.',
                                    style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Colors.black54),
                                  ),
                                  const SizedBox(height: 6),
                                  const Text(
                                    'برای نشان‌گذاری، آیکون نشانک در بالای صفحه را لمس کنید یا متن دلخواه را انتخاب و گزینه «نشانه‌گذاری» را بزنید.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(fontSize: 10.5, color: Colors.black45, height: 1.5),
                                  ),
                                ],
                              ),
                            ),
                          );
                        }
                        return ListView.separated(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          itemCount: bms.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 8),
                          itemBuilder: (ctx, i) {
                            final bm = bms[i];
                            final pNum = (bm['pageNumber'] as num?)?.toInt() ?? 1;
                            final title = (bm['title'] ?? 'صفحه $pNum').toString();
                            final excerpt = (bm['excerpt'] ?? '').toString();
                            final ch = (bm['chapterTitle'] ?? '').toString();

                            return Container(
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: Colors.amber.shade200),
                                boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 3)],
                              ),
                              child: ListTile(
                                dense: true,
                                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                leading: Container(
                                  padding: const EdgeInsets.all(6),
                                  decoration: BoxDecoration(
                                    color: Colors.amber.shade50,
                                    shape: BoxShape.circle,
                                  ),
                                  child: const Icon(Icons.bookmark_rounded, color: Color(0xFFD97706), size: 18),
                                ),
                                title: Text(
                                  title,
                                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy),
                                ),
                                subtitle: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    if (ch.isNotEmpty)
                                      Text(ch, style: const TextStyle(fontSize: 9.5, color: Colors.black54)),
                                    if (excerpt.isNotEmpty) ...[
                                      const SizedBox(height: 2),
                                      Text(
                                        '«${excerpt.length > 50 ? excerpt.substring(0, 50) : excerpt}...»',
                                        style: const TextStyle(fontSize: 10, color: Color(0xFF92400E), fontStyle: FontStyle.italic),
                                      ),
                                    ],
                                  ],
                                ),
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete_outline_rounded, size: 18, color: Colors.redAccent),
                                  tooltip: 'حذف نشانک',
                                  onPressed: () {
                                    widget.repo.removeBookmark(widget.book['id'].toString(), bm['id'].toString());
                                    setState(() {});
                                  },
                                ),
                                onTap: () {
                                  Navigator.pop(context);
                                  _jumpToPage(pNum);
                                },
                              ),
                            );
                          },
                        );
                      },
                    ),
                  ),
                ] else ...[
                  // Search Box
                  Padding(
                    padding: const EdgeInsets.all(10),
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: EttehadColors.border),
                      ),
                      child: TextField(
                        onChanged: (v) => setState(() => _tocSearchQuery = v),
                        decoration: const InputDecoration(
                          hintText: 'جستجوی سرفصل، زیرفصل یا شماره صفحه...',
                          hintStyle: TextStyle(fontSize: 11),
                          prefixIcon: Icon(Icons.search_rounded, size: 18, color: EttehadColors.primary),
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        ),
                      ),
                    ),
                  ),

                  // Hierarchical Chapter & Subchapter List (سه - زیرفصل‌ها حتماً نوشته شود)
                  Expanded(
                    child: ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      itemCount: _chapters.length,
                      itemBuilder: (ctx, chIdx) {
                        final ch = _chapters[chIdx];
                        final title = (ch['title'] ?? 'فصل ${chIdx + 1}').toString();
                        final subchapters = List<Map<String, dynamic>>.from(ch['subchapters'] ?? []);
                        final isCurrentChapter = chIdx == _currentChapterIndex;

                        if (_tocSearchQuery.trim().isNotEmpty) {
                          final q = _tocSearchQuery.trim();
                          final matchesTitle = title.contains(q);
                          final matchesSub = subchapters.any((s) => (s['title'] ?? '').toString().contains(q));
                          if (!matchesTitle && !matchesSub) return const SizedBox.shrink();
                        }

                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          decoration: BoxDecoration(
                            color: isCurrentChapter ? EttehadColors.primary.withValues(alpha: 0.05) : Colors.white,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: isCurrentChapter ? EttehadColors.primary.withValues(alpha: 0.5) : EttehadColors.border,
                              width: isCurrentChapter ? 1.5 : 1.0,
                            ),
                          ),
                          child: Material(
                            color: Colors.transparent,
                            child: Theme(
                              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                              child: ExpansionTile(
                              initiallyExpanded: isCurrentChapter,
                              leading: CircleAvatar(
                                radius: 12,
                                backgroundColor: isCurrentChapter ? EttehadColors.primary : Colors.black12,
                                child: Text(
                                  toPersianDigits(chIdx + 1),
                                  style: TextStyle(
                                    color: isCurrentChapter ? Colors.white : Colors.black87,
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                              title: Text(
                                title,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: isCurrentChapter ? FontWeight.w900 : FontWeight.bold,
                                  color: isCurrentChapter ? EttehadColors.primary : EttehadColors.navy,
                                ),
                              ),
                              subtitle: Text(
                                'شامل ${toPersianDigits(subchapters.length)} گفتار و زیرفصل',
                                style: const TextStyle(fontSize: 10, color: Colors.black45),
                              ),
                              children: subchapters.map((sub) {
                                final subTitle = (sub['title'] ?? 'گفتار').toString();
                                // Find page index corresponding to this subchapter
                                final matchingPageIdx = _paginatedPages.indexWhere((p) => p.chapterIndex == chIdx && p.subchapterTitle == subTitle);
                                final subPage = matchingPageIdx != -1
                                    ? matchingPageIdx + 1
                                    : (sub['page'] as num?)?.toInt() ?? ((chIdx * 4) + 1);
                                final isCurrentSub = (_currentPage == subPage);

                                return InkWell(
                                  onTap: () {
                                    _jumpToPage(subPage);
                                    Navigator.pop(context);
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                    margin: const EdgeInsets.only(bottom: 4, left: 8, right: 8),
                                    decoration: BoxDecoration(
                                      color: isCurrentSub ? EttehadColors.primary.withValues(alpha: 0.12) : const Color(0xFFF8FAFC),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Row(
                                      children: [
                                        Icon(
                                          Icons.subdirectory_arrow_left_rounded,
                                          size: 15,
                                          color: isCurrentSub ? EttehadColors.primary : Colors.black38,
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            subTitle,
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: isCurrentSub ? FontWeight.bold : FontWeight.normal,
                                              color: isCurrentSub ? EttehadColors.primary : Colors.black87,
                                            ),
                                          ),
                                        ),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: isCurrentSub ? EttehadColors.primary : Colors.black12,
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Text(
                                            'ص ${toPersianDigits(subPage)}',
                                            style: TextStyle(
                                              fontSize: 9,
                                              fontWeight: FontWeight.bold,
                                              color: isCurrentSub ? Colors.white : Colors.black54,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                        ),
                      );
                    },
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),

      // LEFT DRAWER: SETTINGS & TYPOGRAPHY (تنظیمات قلم و ظاهر - دو و هشت)
      // In RTL, Scaffold.endDrawer opens from the LEFT!
      endDrawer: Drawer(
        backgroundColor: const Color(0xFFFDFBF7),
        child: Directionality(
          textDirection: TextDirection.rtl,
          child: SafeArea(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: EttehadColors.navy.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.tune_rounded, color: EttehadColors.navy, size: 22),
                    ),
                    const SizedBox(width: 10),
                    const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('تنظیمات قلم و صفحه', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: EttehadColors.navy)),
                        Text('فاصله سطرها، اندازه فونت و نحوه ترجمه', style: TextStyle(fontSize: 10.5, color: Colors.black54)),
                      ],
                    ),
                  ],
                ),
                const Divider(height: 24),

                // Translation Placement Mode (هفت - محل قرارگیری ترجمه)
                const Text('نحوه نمایش ترجمه متن:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  children: [
                    {'id': 'interlinear', 'title': 'زیر هر پاراگراف'},
                    {'id': 'full', 'title': 'ترجمه کل صفحه'},
                    {'id': 'off', 'title': 'خاموش (فقط متن اصلی)'},
                  ].map((item) {
                    final isSel = _translationMode == item['id'];
                    return ChoiceChip(
                      selected: isSel,
                      selectedColor: EttehadColors.primary,
                      backgroundColor: Colors.white,
                      label: Text(
                        item['title']!,
                        style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: isSel ? Colors.white : EttehadColors.navy),
                      ),
                      onSelected: (_) => setState(() => _translationMode = item['id']!),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),

                // Target Translation Language (شش - بر اساس زبان برنامه)
                const Text('زبان ترجمه:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  children: [
                    {'id': 'fa', 'title': 'فارسی'},
                    {'id': 'ar', 'title': 'العربية (شرح عربی)'},
                    {'id': 'en', 'title': 'English'},
                  ].map((l) {
                    final isSel = _appLanguage == l['id'];
                    return ChoiceChip(
                      selected: isSel,
                      selectedColor: const Color(0xFF0284C7),
                      backgroundColor: Colors.white,
                      label: Text(
                        l['title']!,
                        style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: isSel ? Colors.white : EttehadColors.navy),
                      ),
                      onSelected: (_) => setState(() => _appLanguage = l['id']!),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),

                // Font Family
                const Text('قلم مطالعه:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  children: ['Vazirmatn', 'Amiri', 'Default'].map((f) {
                    final sel = _fontFamily == f;
                    final displayName = f == 'Vazirmatn' ? 'وزیرمتن' : f == 'Amiri' ? 'امیری قرآنی' : 'سیستمی';
                    return ChoiceChip(
                      selected: sel,
                      selectedColor: EttehadColors.primary,
                      backgroundColor: Colors.white,
                      label: Text(displayName, style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: sel ? Colors.white : EttehadColors.navy)),
                      onSelected: (_) => setState(() => _fontFamily = f),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),

                // Font Size
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('اندازه قلم متن:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                    Text('${toPersianDigits(_fontSize.toInt())} پیکسل', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: EttehadColors.primary)),
                  ],
                ),
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.text_decrease_rounded, size: 20),
                      onPressed: () => setState(() => _fontSize = (_fontSize - 1.0).clamp(13.0, 30.0)),
                    ),
                    Expanded(
                      child: Slider(
                        value: _fontSize,
                        min: 13.0,
                        max: 30.0,
                        activeColor: EttehadColors.primary,
                        onChanged: (v) => setState(() => _fontSize = v),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.text_increase_rounded, size: 20),
                      onPressed: () => setState(() => _fontSize = (_fontSize + 1.0).clamp(13.0, 30.0)),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Line Spacing (سیزده - استانداردسازی فاصله سطرها و خطوط)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('فاصله سطرها (ارتفاع خط):', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                    Text(toPersianDigits(_lineHeight.toStringAsFixed(2)), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: EttehadColors.primary)),
                  ],
                ),
                Slider(
                  value: _lineHeight,
                  min: 1.6,
                  max: 2.6,
                  divisions: 10,
                  activeColor: EttehadColors.primary,
                  onChanged: (v) => setState(() => _lineHeight = v),
                ),
                Row(
                  children: [
                    _spacingOption('فشرده (۱.۷۵)', 1.75),
                    const SizedBox(width: 6),
                    _spacingOption('استاندارد (۱.۹۵)', 1.95),
                    const SizedBox(width: 6),
                    _spacingOption('روان (۲.۲۵)', 2.25),
                  ],
                ),
                const SizedBox(height: 20),

                // Theme Mode
                const Text('تم و رنگ صفحه:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: EttehadColors.navy)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _themeCard('paper', 'کاغذی', const Color(0xFFFDFBF7), Colors.black87),
                    const SizedBox(width: 8),
                    _themeCard('sepia', 'سپیا', const Color(0xFFF4ECD8), const Color(0xFF5D4037)),
                    const SizedBox(width: 8),
                    _themeCard('night', 'شب', const Color(0xFF0F172A), Colors.white),
                  ],
                ),
                const SizedBox(height: 22),

                // Bookmarking
                Builder(
                  builder: (ctx) {
                    final bookId = widget.book['id'].toString();
                    final isBookmarked = widget.repo.isPageBookmarked(bookId, _currentPage);
                    return ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: isBookmarked ? const Color(0xFFD97706) : EttehadColors.navy,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 11),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: () {
                        final added = widget.repo.togglePageBookmark(
                          bookId,
                          _currentPage,
                          chapterTitle: chapterTitle,
                          title: 'صفحه ${toPersianDigits(_currentPage)}: $chapterTitle',
                        );
                        setState(() {});
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(added
                                ? 'نشانگر مطالعه در صفحه ${toPersianDigits(_currentPage)} ذخیره شد.'
                                : 'نشانک صفحه ${toPersianDigits(_currentPage)} حذف شد.'),
                            duration: const Duration(seconds: 2),
                          ),
                        );
                      },
                      icon: Icon(isBookmarked ? Icons.bookmark_remove_rounded : Icons.bookmark_add_rounded, size: 18),
                      label: Text(
                        isBookmarked ? 'حذف نشان از این صفحه' : 'نشان‌کردن این صفحه',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),

      // TOP BAR: BOOK TITLE + TOC + TRANSLATION + SETTINGS + AI + BOOKMARK
      appBar: _zenMode
          ? null
          : AppBar(
              backgroundColor: EttehadColors.navy,
              foregroundColor: Colors.white,
              elevation: 2,
              leading: IconButton(
                icon: const Icon(Icons.arrow_forward_rounded),
                onPressed: () => Navigator.pop(context),
              ),
              title: Column(
                children: [
                  Text(
                    bookTitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800),
                  ),
                  Text(
                    '$chapterTitle • صفحه ${toPersianDigits(_currentPage)} از ${toPersianDigits(_totalPages)}',
                    style: const TextStyle(fontSize: 9.5, color: Colors.white70),
                  ),
                ],
              ),
              actions: [
                // Quick Bookmark Toggle Button
                Builder(
                  builder: (ctx) {
                    final bookId = widget.book['id'].toString();
                    final isBm = widget.repo.isPageBookmarked(bookId, _currentPage);
                    return IconButton(
                      tooltip: isBm ? 'حذف نشان این صفحه' : 'نشان‌گذاری این صفحه',
                      icon: Icon(
                        isBm ? Icons.bookmark_rounded : Icons.bookmark_border_rounded,
                        color: isBm ? const Color(0xFFFBBF24) : Colors.white70,
                        size: 21,
                      ),
                      onPressed: () {
                        final added = widget.repo.togglePageBookmark(
                          bookId,
                          _currentPage,
                          chapterTitle: chapterTitle,
                          title: 'صفحه ${toPersianDigits(_currentPage)}: $chapterTitle',
                        );
                        setState(() {});
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(added
                                ? 'صفحه ${toPersianDigits(_currentPage)} به نشانک‌ها افزوده شد.'
                                : 'نشانک صفحه ${toPersianDigits(_currentPage)} حذف شد.'),
                            duration: const Duration(seconds: 2),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      },
                    );
                  },
                ),

                // 1. Table of Contents (opens right drawer in RTL)
                IconButton(
                  tooltip: 'فهرست سرفصل‌ها و نشانک‌ها',
                  icon: const Icon(Icons.format_list_bulleted_rounded, size: 21),
                  onPressed: () => _scaffoldKey.currentState?.openDrawer(),
                ),

                // 2. Translation Mode Switcher
                IconButton(
                  tooltip: 'تغییر نحوه نمایش ترجمه',
                  icon: Icon(
                    Icons.translate_rounded,
                    size: 20,
                    color: _translationMode != 'off' ? Colors.amberAccent : Colors.white70,
                  ),
                  onPressed: _cycleTranslationMode,
                ),

                // 3. Settings Drawer Trigger (opens left drawer in RTL)
                IconButton(
                  tooltip: 'تنظیمات قلم و فاصله سطرها',
                  icon: const Icon(Icons.tune_rounded, size: 21),
                  onPressed: () => _scaffoldKey.currentState?.openEndDrawer(),
                ),

                // 4. AI Book Assistant
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: () => _openAiChatSheet(),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(colors: [Color(0xFFD97706), Color(0xFFF59E0B)]),
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.auto_awesome, color: Colors.white, size: 14),
                          SizedBox(width: 4),
                          Text('اتحادیار', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Colors.white)),
                        ],
                      ),
                    ),
                  ),
                ),

                // 5. Zen Mode
                IconButton(
                  tooltip: 'حالت تمام‌صفحه و تمرکز',
                  icon: const Icon(Icons.fullscreen_rounded, size: 21),
                  onPressed: () => setState(() => _zenMode = true),
                ),
              ],
            ),

      // BODY: HORIZONTAL PAGED READING (حرکت افقی به جای عمودی، با صفحات ۲ الی ۳ پاراگرافی)
      body: GestureDetector(
        onTap: () {
          if (_zenMode) setState(() => _zenMode = false);
        },
        child: PageView.builder(
          controller: _pageController,
          itemCount: _totalPages,
          onPageChanged: (pageIndex) {
            final newPage = pageIndex + 1;
            setState(() {
              _currentPage = newPage;
              _syncChapterWithPage(newPage);
            });
          },
          itemBuilder: (context, pageIndex) {
            if (_paginatedPages.isEmpty) {
              return const Center(child: Text('محتوایی برای این بخش یافت نشد.'));
            }
            final pageItem = _paginatedPages[pageIndex.clamp(0, _paginatedPages.length - 1)];
            return _buildBookPage(pageItem: pageItem);
          },
        ),
      ),

      // BOTTOM STATUS BAR: BLUE PROGRESS LINE + MILESTONE FLAG (حرکت هم‌جهت نوار و پرچم در راستای راست‌به‌چپ)
      bottomNavigationBar: _zenMode
          ? null
          : Container(
              height: 52,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              decoration: BoxDecoration(
                color: _cardBgColor,
                border: const Border(top: BorderSide(color: EttehadColors.border)),
                boxShadow: [
                  BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 4, offset: const Offset(0, -2)),
                ],
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Progress Track with Milestone Flag (حرکت هم‌جهت نوار و پرچم در راستای راست‌به‌چپ)
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final trackWidth = constraints.maxWidth;
                      final progressWidth = trackWidth * progressFraction;
                      final flagRight = (progressWidth - 9).clamp(0.0, trackWidth - 18);

                      return SizedBox(
                        height: 16,
                        child: Stack(
                          clipBehavior: Clip.none,
                          alignment: Alignment.centerRight,
                          children: [
                            // Base grey track
                            Container(
                              height: 5,
                              width: trackWidth,
                              decoration: BoxDecoration(
                                color: _themeMode == 'night' ? Colors.white12 : const Color(0xFFE2E8F0),
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),

                            // Active Blue Progress Fill (شروع از راست و پیشروی به چپ همگام با پرچم)
                            Positioned(
                              right: 0,
                              top: 5.5,
                              child: Container(
                                height: 5,
                                width: progressWidth,
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(
                                    colors: [Color(0xFF0284C7), Color(0xFF38BDF8)],
                                  ),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                              ),
                            ),

                            // Milestone Flag Icon 🚩 (حرکت هم‌جهت با نوک نوار آبی)
                            Positioned(
                              right: flagRight,
                              top: -4,
                              child: Tooltip(
                                message: '${toPersianDigits(progressPercent)}٪ مطالعه شده',
                                child: Container(
                                  padding: const EdgeInsets.all(2),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    shape: BoxShape.circle,
                                    border: Border.all(color: const Color(0xFF0284C7), width: 1.5),
                                    boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
                                  ),
                                  child: const Icon(Icons.flag_rounded, size: 12, color: Color(0xFF0284C7)),
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),

                  // Reading Status Text
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'ص ${toPersianDigits(_currentPage)} از ${toPersianDigits(_totalPages)}',
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: _textColor),
                      ),
                      Flexible(
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                          decoration: BoxDecoration(
                            color: const Color(0xFF0284C7).withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.flag_rounded, size: 10, color: Color(0xFF0284C7)),
                              const SizedBox(width: 3),
                              Text(
                                '${toPersianDigits(progressPercent)}٪ مطالعه شده',
                                style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w900, color: Color(0xFF0284C7)),
                              ),
                            ],
                          ),
                        ),
                      ),
                      Text(
                        'فصل ${toPersianDigits(_currentChapterIndex + 1)} از ${toPersianDigits(_chapters.length)}',
                        style: const TextStyle(fontSize: 10, color: Colors.black45),
                      ),
                    ],
                  ),
                ],
              ),
            ),
    );
  }

  // --- BUILD INDIVIDUAL BOOK PAGE WITH REAL 2-3 PARAGRAPH PAGINATION & BOOKMARK RIBBON ---
  Widget _buildBookPage({required _ReaderBookPage pageItem}) {
    final chTitle = pageItem.chapterTitle;
    final subTitle = pageItem.subchapterTitle;
    final pageNum = pageItem.pageNumber;
    final paragraphs = pageItem.paragraphs;
    final bookId = widget.book['id'].toString();
    final isBookmarked = widget.repo.isPageBookmarked(bookId, pageNum);

    return Container(
      color: _bgColor,
      padding: const EdgeInsets.fromLTRB(22, 16, 22, 16),
      child: Stack(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Ornamental Chapter & Subchapter Header
              Center(
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(width: 28, height: 1, color: Colors.amber.shade600.withValues(alpha: 0.5)),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            '✦ $chTitle ✦',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.amber.shade800),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(width: 28, height: 1, color: Colors.amber.shade600.withValues(alpha: 0.5)),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subTitle,
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w900,
                        color: _themeMode == 'night' ? Colors.lightBlueAccent : EttehadColors.navy,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    const Divider(height: 1, color: Colors.black12),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Main Page Content with SelectableText & 2-3 paragraphs (طول افقی متناسب بدون نیاز به اسکرول بی‌پایان عمودی)
              Expanded(
                child: ListView.separated(
                  padding: EdgeInsets.zero,
                  physics: const BouncingScrollPhysics(),
                  itemCount: paragraphs.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 16),
                  itemBuilder: (ctx, pIdx) {
                    final pText = paragraphs[pIdx];

                    // Check translation mode (هفت)
                    if (_translationMode == 'full') {
                      return _buildSelectableParagraph(
                        text: _getTranslationForParagraph(pText, pIdx),
                        isTranslation: true,
                      );
                    } else if (_translationMode == 'interlinear') {
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _buildSelectableParagraph(text: pText, isTranslation: false),
                          const SizedBox(height: 6),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: _transCardBgColor,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: Colors.blue.withValues(alpha: 0.15)),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(Icons.translate_rounded, size: 13, color: Color(0xFF0284C7)),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    _getTranslationForParagraph(pText, pIdx),
                                    style: TextStyle(
                                      fontSize: _fontSize - 3.5,
                                      height: 1.75,
                                      color: _themeMode == 'night' ? Colors.white70 : const Color(0xFF334155),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      );
                    } else {
                      return _buildSelectableParagraph(text: pText, isTranslation: false);
                    }
                  },
                ),
              ),

              // Page Number Indicator
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Center(
                  child: Text(
                    '— صفحه ${toPersianDigits(pageNum)} از ${toPersianDigits(_totalPages)} —',
                    style: const TextStyle(fontSize: 10.5, color: Colors.black38, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ),

          // Bookmark Corner Ribbon
          if (isBookmarked)
            Positioned(
              top: -6,
              left: 4,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                decoration: const BoxDecoration(
                  color: Color(0xFFD97706),
                  borderRadius: BorderRadius.vertical(bottom: Radius.circular(8)),
                  boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 4, offset: Offset(0, 2))],
                ),
                child: const Icon(Icons.bookmark_rounded, size: 16, color: Colors.white),
              ),
            ),
        ],
      ),
    );
  }

  // Paragraph with Custom Text Selection Context Menu (یک - عملیات مختلف روی متن انتخابی)
  Widget _buildSelectableParagraph({required String text, required bool isTranslation}) {
    final cleanText = text
        .replaceAll(r'\r\n', '\n')
        .replaceAll(r'\r', '\n')
        .replaceAll(r'\n', '\n');
    return SelectableText(
      cleanText,
      textAlign: TextAlign.justify,
      style: TextStyle(
        fontFamily: isTranslation ? 'Vazirmatn' : (_fontFamily == 'Default' ? null : _fontFamily),
        fontSize: isTranslation ? _fontSize - 1.5 : _fontSize,
        height: _lineHeight,
        color: _textColor,
        letterSpacing: 0.15,
      ),
      contextMenuBuilder: (context, editableTextState) {
        final selectedText = editableTextState.textEditingValue.selection.textInside(editableTextState.textEditingValue.text).trim();

        return AdaptiveTextSelectionToolbar.buttonItems(
          anchors: editableTextState.contextMenuAnchors,
          buttonItems: [
            ContextMenuButtonItem(
              label: 'پرسیدن از هوش',
              onPressed: () {
                editableTextState.hideToolbar();
                if (selectedText.isNotEmpty) {
                  _handleTextAction('ASK_AI', selectedText);
                }
              },
            ),
            ContextMenuButtonItem(
              label: 'تحلیل فوری هوش',
              onPressed: () {
                editableTextState.hideToolbar();
                if (selectedText.isNotEmpty) {
                  _handleTextAction('SHARE_AI', selectedText);
                }
              },
            ),
            ContextMenuButtonItem(
              label: 'ارسال به علما',
              onPressed: () {
                editableTextState.hideToolbar();
                if (selectedText.isNotEmpty) {
                  _handleTextAction('SEND_TO_SCHOLAR', selectedText);
                }
              },
            ),
            ContextMenuButtonItem(
              label: 'ترجمه فراز',
              onPressed: () {
                editableTextState.hideToolbar();
                if (selectedText.isNotEmpty) {
                  _handleTextAction('TRANSLATE', selectedText);
                }
              },
            ),
            ContextMenuButtonItem(
              label: 'کپی',
              onPressed: () {
                editableTextState.hideToolbar();
                if (selectedText.isNotEmpty) {
                  _handleTextAction('COPY', selectedText);
                }
              },
            ),
            ContextMenuButtonItem(
              label: 'نشانه‌گذاری',
              onPressed: () {
                editableTextState.hideToolbar();
                if (selectedText.isNotEmpty) {
                  _handleTextAction('HIGHLIGHT', selectedText);
                }
              },
            ),
          ],
        );
      },
    );
  }

  final Map<String, String> _paraTranslations = {};
  final Set<String> _loadingTranslations = {};

  String _getTranslationForParagraph(String arabicOrOriginal, int idx) {
    if (_paraTranslations.containsKey(arabicOrOriginal)) {
      return _paraTranslations[arabicOrOriginal]!;
    }

    if (!_loadingTranslations.contains(arabicOrOriginal)) {
      _loadingTranslations.add(arabicOrOriginal);
      widget.repo.translateTextWithAi(
        text: arabicOrOriginal,
        targetLanguage: _appLanguage,
      ).then((res) {
        if (mounted) {
          setState(() {
            _loadingTranslations.remove(arabicOrOriginal);
            _paraTranslations[arabicOrOriginal] = res;
          });
        }
      }).catchError((_) {
        if (mounted) {
          setState(() {
            _loadingTranslations.remove(arabicOrOriginal);
            _paraTranslations[arabicOrOriginal] = 'امکان دریافت ترجمه برخط میسر نشد.';
          });
        }
      });
    }

    return 'در حال دریافت ترجمه از دستیار هوشمند...';
  }

  Widget _spacingOption(String label, double val) {
    final sel = (_lineHeight - val).abs() < 0.05;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _lineHeight = val),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: sel ? EttehadColors.primary : Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: sel ? EttehadColors.primary : EttehadColors.border),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 10.5,
              fontWeight: FontWeight.bold,
              color: sel ? Colors.white : EttehadColors.navy,
            ),
          ),
        ),
      ),
    );
  }

  Widget _themeCard(String id, String label, Color bg, Color text) {
    final sel = _themeMode == id;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _themeMode = id),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: sel ? EttehadColors.primary : Colors.black26, width: sel ? 2 : 1),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: text),
          ),
        ),
      ),
    );
  }
}
