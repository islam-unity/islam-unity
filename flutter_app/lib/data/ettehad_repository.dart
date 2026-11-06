import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../ui/core/config.dart';

class EttehadRepository extends ChangeNotifier {
  bool isInitialized = false;
  bool isOnlineSynced = false;
  String activeAppMode = 'user'; // 'user' or 'scholar'

  List<Map<String, dynamic>> categories = [];
  List<Map<String, dynamic>> hierarchicalCategories = [];
  List<Map<String, dynamic>> books = [];
  List<Map<String, dynamic>> chapters = [];
  List<Map<String, dynamic>> chunks = [];
  List<Map<String, dynamic>> shelves = [];
  List<Map<String, dynamic>> scholars = [];
  List<Map<String, dynamic>> threads = [];
  List<Map<String, dynamic>> posts = [];
  List<Map<String, dynamic>> aiSections = [];
  List<Map<String, dynamic>> prayerTimes = [];
  List<Map<String, dynamic>> dhikrs = [];
  List<Map<String, dynamic>> surahs = [];
  List<Map<String, dynamic>> tadabburList = [];
  Map<String, dynamic>? dailyVerse;
  List<Map<String, dynamic>> reciters = [];
  List<Map<String, dynamic>> dailyDhikrs = [];
  List<Map<String, dynamic>> publicFaqs = [];
  List<Map<String, dynamic>> posters = [];
  List<Map<String, dynamic>> thematicSurahs = [];

  // General Ettehad-Yar AI Chat Sessions Store
  final List<Map<String, dynamic>> _aiChatSessions = [];

  // Book AI Sessions & Categories Store
  final Map<String, List<Map<String, dynamic>>> _bookAiSessions = {};
  List<Map<String, dynamic>> bookAiCategories = [
    {'id': 'cat_general', 'name': 'عمومی و پرسش آزاد', 'icon': 'auto_stories'},
    {'id': 'cat_fiqh', 'name': 'فقه و احکام', 'icon': 'balance'},
    {'id': 'cat_tafsir', 'name': 'تفسیر و معارف', 'icon': 'menu_book'},
    {'id': 'cat_kalam', 'name': 'کلام و عقاید', 'icon': 'psychology'},
    {'id': 'cat_shobahat', 'name': 'پاسخ به شبهات', 'icon': 'help_center'},
    {'id': 'cat_akhlaq', 'name': 'اخلاق و سلوک', 'icon': 'spa'},
    {'id': 'cat_summary', 'name': 'خلاصه‌سازی و فیش‌برداری', 'icon': 'summarize'},
  ];

  // Book Reviews and Excerpts store (offline + synced)
  final Map<String, List<Map<String, dynamic>>> _bookReviews = {};
  final Map<String, List<Map<String, dynamic>>> _bookExcerpts = {};
  final Map<String, List<Map<String, dynamic>>> _bookBookmarks = {};

  // Authentication & User Profile State
  bool isLoggedIn = false;
  String? authToken;
  String? currentUserId;
  String? userPhoneNumber;
  String userFullName = 'پژوهشگر گرامی اتحاد';
  String userRole = 'SEEKER'; // SEEKER, SCHOLAR, ADMIN
  String scholarStatus = 'NONE'; // NONE, PENDING, APPROVED, REJECTED
  String? mosqueName;
  String? mosqueAddress;
  String userMadhhab = 'شیعه اثناعشری';
  String userKnowledgeLevel = 'GENERAL'; // GENERAL, ACADEMIC, SEMINARY
  String userEducation = 'دانشگاهی';
  List<String> userInterests = ['تفسیر و تدبر قرآنی', 'فقه و احکام شرعی', 'اخلاق و خودسازی'];
  String userAvatar = '0';
  bool isProfileCompleted = false;

  // Active multi-scholar conversations (max 5 active scholars)
  final List<Map<String, dynamic>> scholarChats = [];

  // Last read Quran position
  int lastReadSurahId = 18;
  String lastReadSurahName = 'الکهف';
  int lastReadAyah = 28;
  int lastReadPage = 293;
  int lastReadJuz = 15;

  // Complete 604 Osman Taha pages and 30 Juz maps
  Map<int, List<Map<String, dynamic>>> quranPages = {};
  List<Map<String, dynamic>> juzList = [];

  Future<void> initialize() async {
    if (isInitialized) return;
    try {
      // 0. Load auth and chat sessions from SharedPreferences
      await _loadAuthFromPrefs();
      await _loadAiChatSessionsFromPrefs();
      await _loadBookAiSessionsFromPrefs();
      await _loadBookBookmarksFromPrefs();
      await _loadBookReviewsFromPrefs();

      // 1. Load offline SQLite export JSON
      final dbStr = await rootBundle.loadString('assets/data/ettehad_offline_db.json');
      final Map<String, dynamic> dbJson = jsonDecode(dbStr);

      categories = List<Map<String, dynamic>>.from(dbJson['categories'] ?? []);
      hierarchicalCategories = List<Map<String, dynamic>>.from(dbJson['hierarchical_categories'] ?? []);
      books = List<Map<String, dynamic>>.from(dbJson['books'] ?? []);
      chapters = List<Map<String, dynamic>>.from(dbJson['chapters'] ?? []);
      chunks = List<Map<String, dynamic>>.from(dbJson['chunks'] ?? []);
      shelves = List<Map<String, dynamic>>.from(dbJson['shelves'] ?? []);
      scholars = List<Map<String, dynamic>>.from(dbJson['scholars'] ?? []);
      threads = List<Map<String, dynamic>>.from(dbJson['threads'] ?? []);
      posts = List<Map<String, dynamic>>.from(dbJson['posts'] ?? []);
      aiSections = List<Map<String, dynamic>>.from(dbJson['ai_sections'] ?? []);
      prayerTimes = List<Map<String, dynamic>>.from(dbJson['prayer_times'] ?? []);
      dhikrs = List<Map<String, dynamic>>.from(dbJson['dhikrs'] ?? []);
      tadabburList = List<Map<String, dynamic>>.from(dbJson['tadabbur'] ?? []);

      _ensureRichDefaults();

      // 2. Load complete offline Quran dataset (114 Surahs, 6236 Ayahs)
      final quranStr = await rootBundle.loadString('assets/data/quran_complete.json');
      final Map<String, dynamic> quranJson = jsonDecode(quranStr);
      if (quranJson['surahs'] is List) {
        surahs = List<Map<String, dynamic>>.from(quranJson['surahs']);
        _buildQuranPagesAndJuz();
      }
    } catch (e) {
      debugPrint('Error loading offline bundle: $e');
      _ensureRichDefaults();
    }

    isInitialized = true;
    notifyListeners();

    // 3. Auto-sync with backend (polls whenever server comes online)
    syncWithBackend();
    syncAiChatSessionsWithServer();
    syncScholarsFromBackend();
    syncFeedFromBackend();
    syncConsultationThreadsWithServer();
    fetchDailyVerse();
    fetchReciters();
    syncDailyDhikrs();
    fetchPosters();
    fetchPublicConsultationThreads();
    fetchBookAiCategories();
    fetchThematicSurahs();
  }

  Future<void> _loadAuthFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      authToken = prefs.getString('ettehad_auth_token');
      currentUserId = prefs.getString('ettehad_user_id');
      userPhoneNumber = prefs.getString('ettehad_user_phone');
      userFullName = prefs.getString('ettehad_user_name') ?? 'پژوهشگر گرامی اتحاد';
      userRole = prefs.getString('ettehad_user_role') ?? 'SEEKER';
      scholarStatus = prefs.getString('ettehad_scholar_status') ?? 'NONE';
      mosqueName = prefs.getString('ettehad_mosque_name');
      mosqueAddress = prefs.getString('ettehad_mosque_address');
      userMadhhab = prefs.getString('ettehad_user_madhhab') ?? 'شیعه اثناعشری';
      userKnowledgeLevel = prefs.getString('ettehad_user_knowledge_level') ?? 'GENERAL';
      userEducation = prefs.getString('ettehad_user_education') ?? 'دانشگاهی';
      userInterests = prefs.getStringList('ettehad_user_interests') ?? ['تفسیر و تدبر قرآنی', 'فقه و احکام شرعی', 'اخلاق و خودسازی'];
      userAvatar = prefs.getString('ettehad_user_avatar') ?? '0';
      isProfileCompleted = prefs.getBool('ettehad_is_profile_completed') ?? false;
      isLoggedIn = prefs.getBool('ettehad_is_logged_in') ?? false;
      activeAppMode = prefs.getString('ettehad_active_app_mode') ?? 'user';

      if (isLoggedIn && authToken != null) {
        _fetchUserProfileFromBackend();
      }
    } catch (e) {
      debugPrint('Error loading prefs: $e');
    }
  }

  Future<void> _saveAuthToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (authToken != null) await prefs.setString('ettehad_auth_token', authToken!);
      if (currentUserId != null) await prefs.setString('ettehad_user_id', currentUserId!);
      if (userPhoneNumber != null) await prefs.setString('ettehad_user_phone', userPhoneNumber!);
      await prefs.setString('ettehad_user_name', userFullName);
      await prefs.setString('ettehad_user_role', userRole);
      await prefs.setString('ettehad_scholar_status', scholarStatus);
      if (mosqueName != null) {
        await prefs.setString('ettehad_mosque_name', mosqueName!);
      } else {
        await prefs.remove('ettehad_mosque_name');
      }
      if (mosqueAddress != null) {
        await prefs.setString('ettehad_mosque_address', mosqueAddress!);
      } else {
        await prefs.remove('ettehad_mosque_address');
      }
      await prefs.setString('ettehad_user_madhhab', userMadhhab);
      await prefs.setString('ettehad_user_knowledge_level', userKnowledgeLevel);
      await prefs.setString('ettehad_user_education', userEducation);
      await prefs.setStringList('ettehad_user_interests', userInterests);
      await prefs.setString('ettehad_user_avatar', userAvatar);
      await prefs.setBool('ettehad_is_profile_completed', isProfileCompleted);
      await prefs.setBool('ettehad_is_logged_in', isLoggedIn);
      await prefs.setString('ettehad_active_app_mode', activeAppMode);
    } catch (e) {
      debugPrint('Error saving prefs: $e');
    }
  }

  Future<void> _clearAuthPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('ettehad_auth_token');
      await prefs.remove('ettehad_user_id');
      await prefs.remove('ettehad_user_phone');
      await prefs.remove('ettehad_user_name');
      await prefs.remove('ettehad_user_role');
      await prefs.remove('ettehad_scholar_status');
      await prefs.remove('ettehad_mosque_name');
      await prefs.remove('ettehad_mosque_address');
      await prefs.remove('ettehad_is_profile_completed');
      await prefs.remove('ettehad_is_logged_in');
    } catch (e) {
      debugPrint('Error clearing prefs: $e');
    }
  }

  Future<void> _loadAiChatSessionsFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = prefs.getString('ettehad_ai_chat_sessions');
      if (str != null && str.isNotEmpty) {
        final decoded = jsonDecode(str);
        if (decoded is List && decoded.isNotEmpty) {
          _aiChatSessions.clear();
          for (final item in decoded) {
            if (item is Map) {
              _aiChatSessions.add(Map<String, dynamic>.from(item));
            }
          }
        }
      }
    } catch (e) {
      debugPrint('Error loading ai chat sessions from prefs: $e');
    }
  }

  Future<void> _saveAiChatSessionsToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = jsonEncode(_aiChatSessions);
      await prefs.setString('ettehad_ai_chat_sessions', str);
    } catch (e) {
      debugPrint('Error saving ai chat sessions to prefs: $e');
    }
  }

  Future<void> _loadBookAiSessionsFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = prefs.getString('ettehad_book_ai_sessions');
      if (str != null && str.isNotEmpty) {
        final decoded = jsonDecode(str);
        if (decoded is Map && decoded.isNotEmpty) {
          _bookAiSessions.clear();
          decoded.forEach((key, val) {
            if (val is List) {
              _bookAiSessions[key.toString()] = List<Map<String, dynamic>>.from(
                val.map((e) => Map<String, dynamic>.from(e as Map)),
              );
            }
          });
        }
      }
    } catch (e) {
      debugPrint('Error loading book ai sessions from prefs: $e');
    }
  }

  Future<void> _saveBookAiSessionsToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = jsonEncode(_bookAiSessions);
      await prefs.setString('ettehad_book_ai_sessions', str);
    } catch (e) {
      debugPrint('Error saving book ai sessions to prefs: $e');
    }
  }

  Future<void> _loadBookBookmarksFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = prefs.getString('ettehad_book_bookmarks');
      if (str != null && str.isNotEmpty) {
        final decoded = jsonDecode(str);
        if (decoded is Map) {
          _bookBookmarks.clear();
          decoded.forEach((key, val) {
            if (val is List) {
              _bookBookmarks[key.toString()] = List<Map<String, dynamic>>.from(
                val.map((e) => Map<String, dynamic>.from(e as Map)),
              );
            }
          });
        }
      }
    } catch (e) {
      debugPrint('Error loading book bookmarks from prefs: $e');
    }
  }

  Future<void> _saveBookBookmarksToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = jsonEncode(_bookBookmarks);
      await prefs.setString('ettehad_book_bookmarks', str);
    } catch (e) {
      debugPrint('Error saving book bookmarks to prefs: $e');
    }
  }

  Future<void> _loadBookReviewsFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = prefs.getString('ettehad_book_reviews_v2');
      if (str != null && str.isNotEmpty) {
        final decoded = jsonDecode(str);
        if (decoded is Map) {
          _bookReviews.clear();
          decoded.forEach((key, val) {
            if (val is List) {
              _bookReviews[key.toString()] = List<Map<String, dynamic>>.from(
                val.map((e) => Map<String, dynamic>.from(e as Map)),
              );
            }
          });
        }
      }
    } catch (e) {
      debugPrint('Error loading book reviews from prefs: $e');
    }
  }

  Future<void> _saveBookReviewsToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = jsonEncode(_bookReviews);
      await prefs.setString('ettehad_book_reviews_v2', str);
    } catch (e) {
      debugPrint('Error saving book reviews to prefs: $e');
    }
  }

  Future<void> _fetchUserProfileFromBackend() async {
    if (authToken == null) return;
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/auth/me'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        req.headers.set('Authorization', 'Bearer $authToken');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['success'] == true && json['data'] != null) {
            final data = json['data'];
            userFullName = data['full_name'] ?? userFullName;
            userRole = data['role'] ?? userRole;
            scholarStatus = data['scholar_status'] ?? data['scholarStatus'] ?? scholarStatus;
            mosqueName = data['mosque_name'] ?? mosqueName;
            mosqueAddress = data['mosque_address'] ?? mosqueAddress;
            if (data['madhhab'] != null) userMadhhab = data['madhhab'].toString();
            if (data['knowledgeLevel'] != null) userKnowledgeLevel = data['knowledgeLevel'].toString();
            if (data['education'] != null) userEducation = data['education'].toString();
            if (data['interests'] is List) userInterests = List<String>.from(data['interests']);
            if (data['avatar'] != null) userAvatar = data['avatar'].toString();
            await _saveAuthToPrefs();
            notifyListeners();
            client.close();
            return;
          }
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<void> completeAuthWithoutExtraDetails() async {
    isProfileCompleted = true;
    isLoggedIn = true;
    await _saveAuthToPrefs();
    notifyListeners();
  }

  void _ensureRichDefaults() {
    if (shelves.isEmpty) {
      shelves = [
        {
          'id': 'shelf_reading',
          'name': 'در حال مطالعه',
          'icon': 'auto_stories',
          'bookIds': books.take(3).map((b) => b['id'].toString()).toList(),
        },
        {
          'id': 'shelf_favorites',
          'name': 'کتاب‌های برگزیده تقریب',
          'icon': 'bookmark_star',
          'bookIds': books.skip(1).take(3).map((b) => b['id'].toString()).toList(),
        },
        {
          'id': 'shelf_research',
          'name': 'پژوهش‌های قرآنی و فقهی',
          'icon': 'school',
          'bookIds': books.skip(2).take(3).map((b) => b['id'].toString()).toList(),
        },
      ];
    } else {
      for (var i = 0; i < shelves.length; i++) {
        if (shelves[i]['bookIds'] == null) {
          final start = (i * 2) % (books.isEmpty ? 1 : books.length);
          shelves[i] = Map<String, dynamic>.from(shelves[i])
            ..['bookIds'] = books.skip(start).take(3).map((b) => b['id'].toString()).toList();
        }
      }
    }

    if (_aiChatSessions.isEmpty) {
      _aiChatSessions.addAll([
        {
          'id': 'sess_fiqh_1',
          'title': 'احکام معاملات رمزارز و بورس',
          'department': 'فقه مقارن و تقریب',
          'updatedAt': 'امروز، ۱۰:۱۵',
          'bookId': null,
          'bookTitle': null,
          'messages': [
            {
              'sender': 'user',
              'text': 'دیدگاه فقهی و مبانی شرعی پیرامون معاملات رمزارزها و بازارهای مالی چیست؟',
            },
            {
              'sender': 'ai',
              'text': 'در فقه مقارن اسلامی، صحت یا بطلان معاملات مبتنی بر اصولی چون نفی غرر، حرمت اکل مال به باطل و دارا بودن مالیت و منفعت عقلایی سنجیده می‌شود.',
              'bookCitation': books.isNotEmpty ? books.first : null,
              'scholarRec': scholars.isNotEmpty ? scholars.first : null,
              'suggestEscalation': true,
            }
          ],
        },
        {
          'id': 'sess_kalam_2',
          'title': 'قاعده لطف و وحدت اسلامی',
          'department': 'کلام و عقاید اسلامی',
          'updatedAt': 'دیروز، ۱۶:۴۰',
          'bookId': null,
          'bookTitle': null,
          'messages': [
            {
              'sender': 'user',
              'text': 'قاعده لطف در کلام مقارن چگونه تبیین شده است؟',
            },
            {
              'sender': 'ai',
              'text': 'قاعده لطف یکی از قواعد بنیادین کلام عدلیه است که بر اساس آن، انجام هر امری که مکلّف را به طاعت نزدیک و از معصیت دور سازد بر خداوند حکیم لازم شمرده می‌شود.',
              'bookCitation': books.length > 1 ? books[1] : null,
              'scholarRec': null,
              'suggestEscalation': false,
            }
          ],
        },
      ]);
      _saveAiChatSessionsToPrefs();
    }
  }

  List<Map<String, dynamic>> getChaptersForBook(String bookId) {
    List<Map<String, dynamic>> rawList;
    final matched = chapters.where((c) => c['book_id']?.toString() == bookId || c['bookId']?.toString() == bookId).toList();
    if (matched.isNotEmpty) {
      rawList = matched;
    } else {
      final matchedChunks = chunks.where((c) => c['book_id']?.toString() == bookId || c['bookId']?.toString() == bookId).toList();
      if (matchedChunks.isNotEmpty) {
        rawList = [
          {
            'id': 'ch_chunks_$bookId',
            'book_id': bookId,
            'title': 'متن کامل و گزیده‌های دانشی کتاب',
            'order_index': 1,
            'content': matchedChunks.map((c) => c['content'] ?? c['text'] ?? '').join('\n\n'),
          }
        ];
      } else {
        rawList = [];
      }
    }

    // Ensure every chapter has well-formed subchapters (زیرفصل‌ها) with pages
    final result = <Map<String, dynamic>>[];
    for (var i = 0; i < rawList.length; i++) {
      final ch = Map<String, dynamic>.from(rawList[i]);
      final startPage = (i * 25) + 1;
      final existingSub = ch['subchapters'];

      // Populate content from paragraphs or chunks if needed
      if (ch['content'] == null || ch['content'].toString().trim().isEmpty) {
        var rawParas = ch['paragraphs'];
        if (rawParas is String && rawParas.trim().startsWith('[') && rawParas.trim().endsWith(']')) {
          try {
            rawParas = jsonDecode(rawParas);
          } catch (_) {}
        }
        if (rawParas is List && rawParas.isNotEmpty) {
          ch['content'] = rawParas.map((e) => e.toString()).join('\n\n');
        } else if (ch['chunks'] is List && (ch['chunks'] as List).isNotEmpty) {
          ch['content'] = (ch['chunks'] as List).map((c) => c['text'] ?? c['content'] ?? '').join('\n\n');
        }
      }

      if (ch['content'] != null) {
        String c = ch['content'].toString();
        if (c.contains(r'\n') || c.contains(r'\r')) {
          c = c.replaceAll(r'\r\n', '\n').replaceAll(r'\r', '\n').replaceAll(r'\n', '\n');
        }
        c = c.replaceAll(RegExp(r'\s*\|\|\s*AUTO\s*'), '\n\n').replaceAll(RegExp(r'\s*###\s*'), '\n\n');
        ch['content'] = c;
      }

      if (existingSub is List && existingSub.isNotEmpty) {
        ch['subchapters'] = existingSub.map((s) => Map<String, dynamic>.from(s as Map)).toList();
      } else {
        final chTitle = (ch['title'] ?? 'فصل ${i + 1}').toString();
        ch['subchapters'] = [
          {
            'id': 'sub_${ch['id']}_1',
            'title': chTitle,
            'page': startPage,
            'summary': '',
          },
        ];
      }
      ch['startPage'] = startPage;
      result.add(ch);
    }
    return result;
  }

  // --- GENERAL ETTEHAD-YAR AI CHAT SESSIONS & HISTORY METHODS ---

  List<Map<String, dynamic>> getAiChatSessions({String? department}) {
    if (department != null && department != 'همه' && department.isNotEmpty) {
      return _aiChatSessions.where((s) => s['department'] == department).toList();
    }
    return List.unmodifiable(_aiChatSessions);
  }

  Map<String, dynamic>? getAiChatSessionById(String sessionId) {
    try {
      return _aiChatSessions.firstWhere((s) => s['id'] == sessionId);
    } catch (_) {
      return null;
    }
  }

  void saveAiChatSession({
    required String id,
    required String title,
    required String department,
    required List<Map<String, dynamic>> messages,
    String? bookId,
    String? bookTitle,
  }) {
    final existingIdx = _aiChatSessions.indexWhere((s) => s['id'] == id);
    final now = DateTime.now();
    final timeStr = '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
    
    final sessionData = <String, dynamic>{
      'id': id,
      'title': title.trim().isEmpty ? 'گفتگوی معارفی' : title.trim(),
      'department': department,
      'updatedAt': 'امروز، $timeStr',
      'bookId': bookId,
      'bookTitle': bookTitle,
      'messages': messages.map((m) => Map<String, dynamic>.from(m)).toList(),
    };

    if (existingIdx != -1) {
      _aiChatSessions[existingIdx] = sessionData;
    } else {
      _aiChatSessions.insert(0, sessionData);
    }
    _saveAiChatSessionsToPrefs();
    notifyListeners();
  }

  void deleteAiChatSession(String sessionId) {
    _aiChatSessions.removeWhere((s) => s['id'] == sessionId);
    _saveAiChatSessionsToPrefs();
    notifyListeners();

    if (sessionId.startsWith('conv_') && authToken != null) {
      _deleteConversationOnServer(sessionId);
    }
  }

  void _deleteConversationOnServer(String sessionId) {
    if (authToken == null) return;
    try {
      final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
      client
          .deleteUrl(Uri.parse('${EttehadConfig.productionApiBase}/api/v1/ai/conversations/$sessionId'))
          .then((req) {
            req.headers.set('User-Agent', 'Ettehad-App/2.0');
            req.headers.set('Authorization', 'Bearer $authToken');
            return req.close();
          })
          .then((_) => client.close())
          .catchError((_) => client.close());
    } catch (_) {}
  }

  Future<void> syncAiChatSessionsWithServer() async {
    if (!isLoggedIn || authToken == null) return;
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 6);

    try {
      final req = await client.getUrl(
        Uri.parse('${EttehadConfig.productionApiBase}/api/v1/ai/conversations'),
      );
      req.headers.set('User-Agent', 'Ettehad-App/2.0');
      req.headers.set('Authorization', 'Bearer $authToken');
      final resp = await req.close().timeout(const Duration(seconds: 6));
      if (resp.statusCode == 200) {
        final body = await resp.transform(utf8.decoder).join();
        final json = jsonDecode(body);
        final List? serverConvs = json['data'] as List?;
        if (serverConvs != null && serverConvs.isNotEmpty) {
          bool hasChanges = false;
          for (final c in serverConvs) {
            final cId = c['id']?.toString();
            final cTitle = (c['title'] ?? 'گفتگوی معارفی').toString();
            if (cId == null || cId.isEmpty) continue;

            final existingIdx = _aiChatSessions.indexWhere((s) => s['id'] == cId);
            if (existingIdx == -1) {
              // Conversation exists on server but not in local cache (e.g. logging in on another device)
              try {
                final mReq = await client.getUrl(
                  Uri.parse('${EttehadConfig.productionApiBase}/api/v1/ai/conversations/$cId/messages'),
                );
                mReq.headers.set('User-Agent', 'Ettehad-App/2.0');
                mReq.headers.set('Authorization', 'Bearer $authToken');
                final mResp = await mReq.close().timeout(const Duration(seconds: 5));
                if (mResp.statusCode == 200) {
                  final mBody = await mResp.transform(utf8.decoder).join();
                  final mJson = jsonDecode(mBody);
                  final List? sMsgs = mJson['data'] as List?;
                  final loadedMessages = <Map<String, dynamic>>[];
                  if (sMsgs != null) {
                    for (final sm in sMsgs) {
                      loadedMessages.add({
                        'sender': sm['role'] == 'USER' ? 'user' : 'ai',
                        'text': sm['content'] ?? '',
                        'suggestEscalation': sm['suggestScholarEscalation'] == true,
                        'sources': sm['sources'],
                      });
                    }
                  }
                  if (loadedMessages.isNotEmpty) {
                    _aiChatSessions.add({
                      'id': cId,
                      'title': cTitle,
                      'department': 'اتحادیار هوشمند',
                      'updatedAt': 'همگام با سرور',
                      'messages': loadedMessages,
                    });
                    hasChanges = true;
                  }
                }
              } catch (_) {}
            }
          }
          if (hasChanges) {
            _saveAiChatSessionsToPrefs();
            notifyListeners();
          }
        }
      }
    } catch (e) {
      debugPrint('Sync AI sessions notice: $e');
    } finally {
      client.close();
    }
  }

  void renameAiChatSession(String sessionId, String newTitle) {
    final idx = _aiChatSessions.indexWhere((s) => s['id'] == sessionId);
    if (idx != -1 && newTitle.trim().isNotEmpty) {
      _aiChatSessions[idx]['title'] = newTitle.trim();
      _saveAiChatSessionsToPrefs();
      notifyListeners();
    }
  }

  // --- BOOK AI SESSIONS & CATEGORIES METHODS ---

  Future<List<Map<String, dynamic>>> fetchBookAiCategories() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/library/ai/categories'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final items = json['data'] as List?;
          if (items != null && items.isNotEmpty) {
            bookAiCategories = List<Map<String, dynamic>>.from(items);
            notifyListeners();
            client.close();
            return bookAiCategories;
          }
        }
      } catch (_) {}
    }
    client.close();
    return bookAiCategories;
  }

  Future<List<Map<String, dynamic>>> fetchBookAiSessions(String bookId, {String? category}) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final catQuery = (category != null && category != 'all') ? '?category=$category' : '';
        final req = await client.getUrl(Uri.parse('$base/v1/library/books/$bookId/ai/sessions$catQuery'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) req.headers.set('Authorization', 'Bearer $authToken');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final items = json['data'] as List?;
          if (items != null) {
            _bookAiSessions[bookId] = List<Map<String, dynamic>>.from(items);
            _saveBookAiSessionsToPrefs();
            notifyListeners();
            client.close();
            return _bookAiSessions[bookId]!;
          }
        }
      } catch (_) {}
    }
    client.close();
    return getBookAiSessions(bookId, category: category);
  }

  List<Map<String, dynamic>> getBookAiSessions(String bookId, {String? category}) {
    final list = _bookAiSessions[bookId] ?? [];
    if (category != null && category != 'all' && category.isNotEmpty) {
      return list.where((s) => s['category'] == category).toList();
    }
    return list;
  }

  Future<void> saveBookAiSession(String bookId, Map<String, dynamic> session) async {
    if (!_bookAiSessions.containsKey(bookId)) {
      _bookAiSessions[bookId] = [];
    }
    final existingIdx = _bookAiSessions[bookId]!.indexWhere((s) => s['id'] == session['id']);
    if (existingIdx != -1) {
      _bookAiSessions[bookId]![existingIdx] = session;
    } else {
      _bookAiSessions[bookId]!.insert(0, session);
    }
    _saveBookAiSessionsToPrefs();
    notifyListeners();

    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/library/books/$bookId/ai/sessions'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) req.headers.set('Authorization', 'Bearer $authToken');
        req.write(jsonEncode({
          'id': session['id'],
          'title': session['title'] ?? 'گفتگوی پیرامون اثر',
          'category': session['category'] ?? 'عمومی',
          'messages': session['messages'] ?? [],
        }));
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200 || resp.statusCode == 201) {
          client.close();
          return;
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<void> addBookAiCategory(String name, {String icon = 'category', String? description}) async {
    final clean = name.trim();
    if (clean.isEmpty) return;
    if (!bookAiCategories.any((c) => c['name'] == clean)) {
      bookAiCategories.add({
        'id': 'cat_${DateTime.now().millisecondsSinceEpoch}',
        'name': clean,
        'icon': icon,
        'description': description ?? '',
      });
      notifyListeners();
    }

    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/library/ai/categories'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) req.headers.set('Authorization', 'Bearer $authToken');
        req.write(jsonEncode({
          'name': clean,
          'icon': icon,
          'description': description ?? '',
        }));
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200 || resp.statusCode == 201) {
          client.close();
          return;
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<bool> sendBookExcerptToScholar({
    required String scholarId,
    required String excerpt,
    required String bookId,
    required String bookTitle,
    String? userQuestion,
  }) async {
    final message = userQuestion != null && userQuestion.trim().isNotEmpty
        ? 'پرسش پیرامون فراز کتاب «$bookTitle»:\n«$excerpt»\n\nپرسش: $userQuestion'
        : 'سلام علیکم؛ مایل به دریافت نظر و راهنمایی شما درباره این فراز از کتاب «$bookTitle» هستم:\n«$excerpt»';

    sendScholarMessage(
      scholarId,
      message,
      bookId: bookId,
      bookTitle: bookTitle,
      excerpt: excerpt,
    );

    final existingChat = scholarChats.firstWhere(
      (c) => c['scholar']?['id']?.toString() == scholarId,
      orElse: () => <String, dynamic>{},
    );
    final existingThreadId = existingChat['thread_id']?.toString();

    if (existingThreadId != null && existingThreadId.isNotEmpty) {
      await sendConsultationMessage(
        scholarId: scholarId,
        text: message,
        threadId: existingThreadId,
        bookId: bookId,
        bookTitle: bookTitle,
      );
    }
    return true;
  }

  // --- BOOKMARKS API (صفحات و فرازهای نشان‌شده) ---
  List<Map<String, dynamic>> getBookBookmarks(String bookId) {
    return _bookBookmarks[bookId] ?? [];
  }

  int get totalBookBookmarksCount {
    int total = 0;
    _bookBookmarks.forEach((_, list) => total += list.length);
    return total;
  }

  int get readBooksCount => _bookBookmarks.keys.length;

  bool isPageBookmarked(String bookId, int pageNumber) {
    final list = _bookBookmarks[bookId];
    if (list == null) return false;
    return list.any((b) => (b['pageNumber'] as num?)?.toInt() == pageNumber);
  }

  bool togglePageBookmark(
    String bookId,
    int pageNumber, {
    String? chapterTitle,
    String? title,
    String? note,
    String? excerpt,
  }) {
    final list = List<Map<String, dynamic>>.from(_bookBookmarks[bookId] ?? []);
    final existingIdx = list.indexWhere((b) => (b['pageNumber'] as num?)?.toInt() == pageNumber);
    bool added = false;
    if (existingIdx != -1) {
      list.removeAt(existingIdx);
      added = false;
    } else {
      list.insert(0, {
        'id': 'bm_${DateTime.now().millisecondsSinceEpoch}',
        'bookId': bookId,
        'pageNumber': pageNumber,
        'chapterTitle': chapterTitle ?? 'فصل جاری',
        'title': title ?? 'صفحه $pageNumber',
        'note': note ?? '',
        'excerpt': excerpt ?? '',
        'createdAt': DateTime.now().toIso8601String(),
      });
      added = true;
    }
    _bookBookmarks[bookId] = list;
    _saveBookBookmarksToPrefs();
    notifyListeners();
    return added;
  }

  void removeBookmark(String bookId, String bookmarkId) {
    final list = List<Map<String, dynamic>>.from(_bookBookmarks[bookId] ?? []);
    list.removeWhere((b) => b['id'] == bookmarkId);
    _bookBookmarks[bookId] = list;
    _saveBookBookmarksToPrefs();
    notifyListeners();
  }

  // --- REVIEWS & EXCERPTS API (دیدگاه‌ها و نظرات واقعی کاربران) ---
  List<Map<String, dynamic>> getBookReviews(String bookId, {bool onlyApproved = true}) {
    final all = _bookReviews[bookId] ?? [];
    if (onlyApproved) {
      return all.where((r) => r['isApproved'] == true).toList();
    }
    return all;
  }

  List<Map<String, dynamic>> getUserPendingReviews(String bookId) {
    if (!_bookReviews.containsKey(bookId)) return [];
    return _bookReviews[bookId]!.where((r) => r['isApproved'] != true).toList();
  }

  void addReview(String bookId, String text, double rating, {String? authorName}) {
    final list = List<Map<String, dynamic>>.from(_bookReviews[bookId] ?? []);
    list.insert(0, {
      'id': 'rev_user_${DateTime.now().millisecondsSinceEpoch}',
      'author': authorName ?? (isLoggedIn && userFullName.isNotEmpty ? userFullName : 'کاربر گرامی سامانه اتحاد'),
      'avatar': 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=120',
      'rating': rating,
      'time': 'هم‌اکنون',
      'content': text.trim(),
      'isApproved': true,
      'status': 'approved',
    });
    _bookReviews[bookId] = list;
    _saveBookReviewsToPrefs();
    notifyListeners();
  }

  void approveReview(String bookId, String reviewId) {
    final list = List<Map<String, dynamic>>.from(_bookReviews[bookId] ?? []);
    final idx = list.indexWhere((r) => r['id'] == reviewId);
    if (idx != -1) {
      list[idx]['isApproved'] = true;
      list[idx]['status'] = 'approved';
      _bookReviews[bookId] = list;
      _saveBookReviewsToPrefs();
      notifyListeners();
    }
  }

  Future<void> syncBookReviews(String bookId) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/library/books/$bookId/reviews'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final items = json['data'] as List?;
          if (items != null) {
            _bookReviews[bookId] = List<Map<String, dynamic>>.from(items);
            _saveBookReviewsToPrefs();
            notifyListeners();
            client.close();
            return;
          }
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<bool> submitBookReview(String bookId, String text, double rating) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/library/books/$bookId/reviews'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        req.write(jsonEncode({
          'rating': rating,
          'content': text.trim(),
          'authorName': isLoggedIn && userFullName.isNotEmpty ? userFullName : null,
        }));
        final resp = await req.close().timeout(const Duration(seconds: 5));
        if (resp.statusCode == 200 || resp.statusCode == 201) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['data'] != null) {
            final list = List<Map<String, dynamic>>.from(_bookReviews[bookId] ?? []);
            list.insert(0, Map<String, dynamic>.from(json['data']));
            _bookReviews[bookId] = list;
            _saveBookReviewsToPrefs();
            notifyListeners();
          }
          client.close();
          return true;
        }
      } catch (_) {}
    }
    client.close();
    addReview(bookId, text, rating);
    return true;
  }

  // --- CONNECTED BOOK AI & CHAT (اتصال به api.unitysi.ir) ---
  Future<Map<String, dynamic>> askBookAi({
    required String bookId,
    required String bookTitle,
    required String query,
    String? chapterTitle,
    int? pageNumber,
    String? selectedText,
    String? conversationId,
    List<Map<String, dynamic>>? history,
  }) async {
    final hosts = EttehadConfig.apiHosts;
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 15);

    for (final base in hosts) {
      // 1. اولویت نخست: متد تخصصی گفتگوی کتابخوان /api/v1/library/books/{bookId}/ai/chat
      try {
        final uri = Uri.parse('$base/api/v1/library/books/$bookId/ai/chat');
        final req = await client.postUrl(uri);
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'Ettehad-App/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final payload = {
          'query': query,
          if (conversationId != null) 'conversationId': conversationId,
          if (history != null) 'history': history,
          'context': {
            'bookId': bookId,
            'bookTitle': bookTitle,
            if (chapterTitle != null) 'chapterTitle': chapterTitle,
            if (pageNumber != null) 'pageNumber': pageNumber,
            if (selectedText != null) 'selectedText': selectedText,
          },
        };
        req.add(utf8.encode(jsonEncode(payload)));
        final resp = await req.close().timeout(const Duration(seconds: 60));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final resData = json['data'] ?? json;
          final answer = (resData['answer'] ?? resData['reply'] ?? resData['content'])?.toString() ?? '';
          if (answer.trim().isNotEmpty) {
            client.close();
            return {
              'success': true,
              'reply': answer,
              'conversationId': resData['conversationId'],
              'citations': resData['citations'] ?? resData['references'] ?? [],
            };
          }
        }
      } catch (e) {
        debugPrint('Book AI specific endpoint on $base warning: $e');
      }

      // 2. اولویت دوم: هوش عمومی سامانه با کانتکست کتاب /api/v1/ai/chat
      try {
        final uri = Uri.parse('$base/api/v1/ai/chat');
        final req = await client.postUrl(uri);
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'Ettehad-App/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final enrichedQuery = 'پیرامون کتاب «$bookTitle»${chapterTitle != null ? ' (فصل $chapterTitle)' : ''}${pageNumber != null ? ' (صفحه $pageNumber)' : ''}:\n$query';
        final payload = {
          'message': enrichedQuery,
          'section': 'کتابخانه و معارف اسلامی',
          if (conversationId != null) 'conversationId': conversationId,
        };
        req.add(utf8.encode(jsonEncode(payload)));
        final resp = await req.close().timeout(const Duration(seconds: 60));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final resData = json['data'] ?? json;
          final reply = (resData['reply'] ?? resData['content'])?.toString() ?? '';
          if (reply.trim().isNotEmpty) {
            client.close();
            return {
              'success': true,
              'reply': reply,
              'conversationId': resData['conversationId'],
              'citations': resData['sources'] ?? [],
            };
          }
        }
      } catch (e) {
        debugPrint('General AI chat endpoint on $base warning: $e');
      }
    }
    client.close();

    final fallbackAnswer = '⚠️ امکان ارتباط با دستیار هوشمند اتحادیار (api.unitysi.ir) پیرامون کتاب «$bookTitle» فراهم نشد. لطفاً اتصال اینترنت خود را بررسی نمایید.';
    return {
      'success': false,
      'isOffline': true,
      'reply': fallbackAnswer,
      'citations': [],
    };
  }

  List<Map<String, dynamic>> getBookExcerpts(String bookId) {
    if (_bookExcerpts.containsKey(bookId)) {
      return _bookExcerpts[bookId]!;
    }
    final matchedChunks = chunks.where((c) => c['book_id']?.toString() == bookId).toList();
    if (matchedChunks.isNotEmpty) {
      final res = matchedChunks.take(4).map((c) => {
        'id': c['id']?.toString() ?? 'exc_${DateTime.now().millisecondsSinceEpoch}',
        'text': '«${(c['content'] ?? c['text'] ?? '').toString().trim()}»',
        'page': 'صفحه ${c['page_number'] ?? '۱'}',
      }).toList();
      _bookExcerpts[bookId] = res;
      return res;
    }
    return [];
  }

  void addExcerpt(String bookId, String text, [String? page]) {
    final list = List<Map<String, dynamic>>.from(getBookExcerpts(bookId));
    final trimmed = text.trim();
    final formattedText = (trimmed.startsWith('«') && trimmed.endsWith('»'))
        ? trimmed
        : '«$trimmed»';
    list.insert(0, {
      'id': 'user_exc_${DateTime.now().millisecondsSinceEpoch}',
      'text': formattedText,
      'page': (page != null && page.trim().isNotEmpty) ? page.trim() : 'بریده ثبت شده توسط کاربر',
    });
    _bookExcerpts[bookId] = list;
    notifyListeners();
  }

  // --- SHELVES & SIMILAR BOOKS ---
  List<Map<String, dynamic>> getSimilarBooks(Map<String, dynamic> currentBook) {
    final catId = currentBook['category_id']?.toString() ?? '';
    final id = currentBook['id']?.toString() ?? '';
    final list = books.where((b) => b['id']?.toString() != id && b['category_id']?.toString() == catId).toList();
    if (list.isNotEmpty) return list;
    return books.where((b) => b['id']?.toString() != id).take(4).toList();
  }

  List<Map<String, dynamic>> getSameAuthorBooks(Map<String, dynamic> currentBook) {
    final author = (currentBook['author'] ?? '').toString();
    final id = currentBook['id']?.toString() ?? '';
    final firstPart = author.split(' ').first;
    final list = books.where((b) => b['id']?.toString() != id && (b['author'] ?? '').toString().contains(firstPart)).toList();
    if (list.isNotEmpty) return list;
    return books.where((b) => b['id']?.toString() != id).skip(2).take(4).toList();
  }

  List<Map<String, dynamic>> getSamePublisherBooks(Map<String, dynamic> currentBook) {
    final pub = (currentBook['publisher'] ?? '').toString();
    final id = currentBook['id']?.toString() ?? '';
    if (pub.isNotEmpty) {
      final list = books.where((b) => b['id']?.toString() != id && (b['publisher'] ?? '').toString() == pub).toList();
      if (list.isNotEmpty) return list;
    }
    return books.where((b) => b['id']?.toString() != id).skip(4).take(4).toList();
  }

  void addShelf(String name) {
    if (name.trim().isEmpty) return;
    shelves.add({
      'id': 'shelf_${DateTime.now().millisecondsSinceEpoch}',
      'name': name.trim(),
      'icon': 'shelves',
      'bookIds': <String>[],
    });
    notifyListeners();
  }

  bool isBookSaved(String bookId) {
    for (final shelf in shelves) {
      final list = List<String>.from(shelf['bookIds'] ?? []);
      if (list.contains(bookId)) return true;
    }
    return false;
  }

  bool toggleBookSaved(String bookId) {
    if (shelves.isEmpty) {
      shelves.add({
        'id': 'shelf_favorites',
        'name': 'کتاب‌های برگزیده',
        'icon': 'bookmark_star',
        'bookIds': <String>[],
      });
    }
    final favShelf = shelves.firstWhere(
      (s) => s['id'] == 'shelf_favorites',
      orElse: () => shelves.first,
    );
    final list = List<String>.from(favShelf['bookIds'] ?? []);
    bool saved = false;
    if (list.contains(bookId)) {
      list.remove(bookId);
      saved = false;
    } else {
      list.add(bookId);
      saved = true;
    }
    favShelf['bookIds'] = list;
    notifyListeners();
    return saved;
  }

  void toggleBookInShelf(String shelfId, String bookId) {
    final idx = shelves.indexWhere((s) => s['id'].toString() == shelfId);
    if (idx == -1) return;
    final list = List<String>.from(shelves[idx]['bookIds'] ?? []);
    if (list.contains(bookId)) {
      list.remove(bookId);
    } else {
      list.add(bookId);
    }
    shelves[idx]['bookIds'] = list;
    notifyListeners();
  }

  void updateLastReadQuran(int surahId, String surahName, int ayahNumber, {int? page, int? juz}) {
    lastReadSurahId = surahId;
    lastReadSurahName = surahName;
    lastReadAyah = ayahNumber;
    if (page != null && page >= 1 && page <= 604) {
      lastReadPage = page;
    } else {
      lastReadPage = getStartPageForSurah(surahId);
    }
    if (juz != null && juz >= 1 && juz <= 30) {
      lastReadJuz = juz;
    } else {
      lastReadJuz = getJuzForPage(lastReadPage);
    }
    notifyListeners();
    syncLastReadQuranToServer(surahId, ayahNumber, lastReadPage);
  }

  Future<void> syncLastReadQuranToServer(int surahId, int ayahNumber, int pageNumber) async {
    if (!isLoggedIn || authToken == null) return;
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.putUrl(Uri.parse('$base/v1/quran/user/last-read'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        req.headers.set('Authorization', 'Bearer $authToken');
        req.write(jsonEncode({
          'surahId': surahId,
          'ayahNumber': ayahNumber,
          'pageNumber': pageNumber,
        }));
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          client.close();
          return;
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<Map<String, dynamic>?> fetchAyahTools(int surahId, int ayahNumber) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/quran/ayahs/$surahId/$ayahNumber/tools'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['data'] is Map) {
            client.close();
            return Map<String, dynamic>.from(json['data']);
          }
        }
      } catch (_) {}
    }
    client.close();
    return null;
  }

  void _buildQuranPagesAndJuz() {
    final Map<int, List<Map<String, dynamic>>> pages = {};
    final Map<int, Map<String, dynamic>> juzMap = {};

    for (final s in surahs) {
      final surahId = (s['id'] as num?)?.toInt() ?? 1;
      final surahNameAr = (s['nameArabic'] ?? s['name'] ?? '').toString();
      final surahNameFa = (s['namePersian'] ?? s['meaning'] ?? '').toString();
      final revType = (s['revelationType'] ?? 'MAKKI').toString();
      final ayahCount = (s['ayahCount'] ?? (s['ayahs'] as List?)?.length ?? 0) as int;
      final ayahs = List<Map<String, dynamic>>.from(s['ayahs'] ?? []);

      for (int i = 0; i < ayahs.length; i++) {
        final a = ayahs[i];
        final pageNum = (a['page'] as num?)?.toInt() ?? 1;
        final juzNum = (a['juz'] as num?)?.toInt() ?? 1;
        final ayahNum = (a['ayahNumber'] ?? a['number'] ?? (i + 1)) as int;

        final ayahData = {
          ...a,
          'surahId': surahId,
          'surahNameArabic': surahNameAr,
          'surahNamePersian': surahNameFa,
          'revelationType': revType,
          'ayahCount': ayahCount,
          'ayahNumber': ayahNum,
          'isSurahStart': ayahNum == 1,
        };

        pages.putIfAbsent(pageNum, () => []).add(ayahData);

        if (!juzMap.containsKey(juzNum)) {
          juzMap[juzNum] = {
            'juzNumber': juzNum,
            'startSurahId': surahId,
            'startSurahName': surahNameAr,
            'startSurahPersian': surahNameFa,
            'startAyah': ayahNum,
            'startPage': pageNum,
            'endSurahId': surahId,
            'endSurahName': surahNameAr,
            'endSurahPersian': surahNameFa,
            'endAyah': ayahNum,
            'endPage': pageNum,
            'ayahCount': 0,
            'surahIds': <int>{},
          };
        }
        final j = juzMap[juzNum]!;
        j['endSurahId'] = surahId;
        j['endSurahName'] = surahNameAr;
        j['endSurahPersian'] = surahNameFa;
        j['endAyah'] = ayahNum;
        j['endPage'] = pageNum;
        j['ayahCount'] = (j['ayahCount'] as int) + 1;
        (j['surahIds'] as Set<int>).add(surahId);
      }
    }

    quranPages = pages;
    juzList = List.generate(30, (index) {
      final num = index + 1;
      final data = juzMap[num] ?? {};
      final sIds = (data['surahIds'] is Set ? (data['surahIds'] as Set<int>).toList() : <int>[]);
      sIds.sort();
      return {
        'juzNumber': num,
        'startSurahId': data['startSurahId'] ?? 1,
        'startSurahName': data['startSurahName'] ?? '',
        'startSurahPersian': data['startSurahPersian'] ?? '',
        'startAyah': data['startAyah'] ?? 1,
        'startPage': data['startPage'] ?? 1,
        'endSurahId': data['endSurahId'] ?? 1,
        'endSurahName': data['endSurahName'] ?? '',
        'endSurahPersian': data['endSurahPersian'] ?? '',
        'endAyah': data['endAyah'] ?? 1,
        'endPage': data['endPage'] ?? 1,
        'ayahCount': data['ayahCount'] ?? 0,
        'surahIds': sIds,
      };
    });
  }

  int getStartPageForSurah(int surahId) {
    final s = surahs.firstWhere((x) => x['id'] == surahId, orElse: () => {});
    return (s['startPage'] as num?)?.toInt() ?? 1;
  }

  int getStartPageForJuz(int juzNumber) {
    if (juzList.isEmpty && surahs.isNotEmpty) {
      _buildQuranPagesAndJuz();
    }
    if (juzNumber >= 1 && juzNumber <= juzList.length) {
      return (juzList[juzNumber - 1]['startPage'] as num?)?.toInt() ?? 1;
    }
    return 1;
  }

  int getJuzForPage(int pageNumber) {
    if (juzList.isEmpty && surahs.isNotEmpty) {
      _buildQuranPagesAndJuz();
    }
    for (final j in juzList) {
      final sp = (j['startPage'] as num?)?.toInt() ?? 1;
      final ep = (j['endPage'] as num?)?.toInt() ?? 604;
      if (pageNumber >= sp && pageNumber <= ep) {
        return j['juzNumber'] as int;
      }
    }
    return 1;
  }

  List<Map<String, dynamic>> getSurahsForJuz(int juzNumber) {
    if (juzList.isEmpty && surahs.isNotEmpty) {
      _buildQuranPagesAndJuz();
    }
    if (juzNumber < 1 || juzNumber > juzList.length) return [];
    final sIds = List<int>.from(juzList[juzNumber - 1]['surahIds'] ?? []);
    return surahs.where((s) => sIds.contains(s['id'])).toList();
  }

  List<Map<String, dynamic>> getAyahsForPage(int pageNumber) {
    if (quranPages.isEmpty && surahs.isNotEmpty) {
      _buildQuranPagesAndJuz();
    }
    return quranPages[pageNumber] ?? [];
  }

  void toggleAppMode() {
    activeAppMode = activeAppMode == 'user' ? 'scholar' : 'user';
    notifyListeners();
  }

  String startOrOpenScholarChat(Map<String, dynamic> scholar) {
    final scId = scholar['id'].toString();
    final existingIdx = scholarChats.indexWhere((c) => c['scholar']['id'].toString() == scId);
    if (existingIdx != -1) {
      return 'OPENED';
    }
    if (scholarChats.length >= 5) {
      return 'LIMIT_REACHED';
    }
    scholarChats.insert(0, {
      'scholar': scholar,
      'unread': 0,
      'lastMessage': 'گفتگوی جدید آغاز شد',
      'messages': [
        {
          'sender': 'scholar',
          'text': 'سلام علیکم و رحمة الله؛ به دفتر پاسخگویی ${scholar['name']} خوش آمدید. پرسش شرعی یا علمی خود را مطرح فرمایید.',
          'time': 'هم‌اکنون',
        }
      ],
    });
    notifyListeners();
    return 'CREATED';
  }

  void addScholarChat(Map<String, dynamic> chat) {
    scholarChats.insert(0, chat);
    notifyListeners();
  }

  Future<Map<String, dynamic>> createConsultationThread({
    required String title,
    required String body,
    required String category,
    String? targetScholarId,
    bool isAnonymous = false,
    Map<String, dynamic>? bookReference,
  }) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/consultation/threads'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final payload = {
          'title': title,
          'initialQuestionBody': body,
          'category': category,
          if (targetScholarId != null) 'targetScholarId': targetScholarId,
          'isAnonymous': isAnonymous,
          'isPublic': true,
          if (bookReference != null) 'attachments': [
            {
              'type': 'BOOK_REFERENCE',
              'title': bookReference['bookTitle'] ?? '',
              'url': (bookReference['bookId'] ?? '').toString(),
              'note': bookReference['excerpt'] ?? '',
            }
          ]
        };
        req.write(jsonEncode(payload));
        final resp = await req.close().timeout(const Duration(seconds: 6));
        final respBody = await resp.transform(utf8.decoder).join();
        final json = jsonDecode(respBody);
        if ((resp.statusCode == 200 || resp.statusCode == 201) && json['success'] == true) {
          client.close();
          final data = json['data'] ?? {};
          return {
            'success': true,
            'threadId': data['threadId'] ?? data['id'],
            'trackingCode': data['trackingCode'] ?? data['tracking_code'],
            'status': data['status'] ?? 'WAITING_SCHOLAR',
            'createdAtFa': data['createdAtFa'] ?? 'هم‌اکنون',
          };
        }
      } catch (e) {
        debugPrint('Create thread error on $base: $e');
      }
    }
    client.close();
    return {'success': false};
  }

  Future<void> syncConsultationThreadsWithServer() async {
    if (!isLoggedIn || authToken == null) return;
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/consultation/threads'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        req.headers.set('Authorization', 'Bearer $authToken');
        final resp = await req.close().timeout(const Duration(seconds: 5));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final List? items = json['data'] as List?;
          if (items != null && items.isNotEmpty) {
            for (final it in items) {
              final tId = (it['id'] ?? it['threadId'])?.toString();
              if (tId == null) continue;
              final idx = scholarChats.indexWhere((c) => c['thread_id'] == tId);
              final scholarObj = it['scholar'] ?? {
                'id': it['scholarId'] ?? '1',
                'name': it['scholarName'] ?? 'استاد معارفی',
                'title': it['category'] ?? 'پاسخگوی فقهی',
              };
              final chatData = {
                'thread_id': tId,
                'scholar': scholarObj,
                'tracking_code': it['trackingCode'] ?? it['tracking_code'] ?? 'ETH-Q-$tId',
                'status': it['status'] ?? 'WAITING_SCHOLAR',
                'lastMessage': it['title'] ?? 'استفتاء ثبت شده',
                'unread': 0,
                'messages': [
                  {
                    'sender': 'user',
                    'title': it['title'] ?? '',
                    'text': it['initialQuestionBody'] ?? it['snippet'] ?? '',
                    'time': it['createdAtFa'] ?? 'اخیراً',
                  }
                ],
              };
              if (idx != -1) {
                scholarChats[idx] = chatData;
              } else {
                scholarChats.insert(0, chatData);
              }
            }
            notifyListeners();
            client.close();
            return;
          }
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<bool> sendConsultationMessage({
    required String scholarId,
    required String text,
    String? threadId,
    String? bookId,
    String? bookTitle,
  }) async {
    sendScholarMessage(scholarId, text, bookId: bookId, bookTitle: bookTitle);

    if (authToken != null && threadId != null && threadId.isNotEmpty) {
      final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
      for (final base in EttehadConfig.apiHosts) {
        try {
          final req = await client.postUrl(Uri.parse('$base/v1/consultation/threads/$threadId/messages'));
          req.headers.contentType = ContentType.json;
          req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
          req.headers.set('Authorization', 'Bearer $authToken');
          final payload = {
            'text': text,
            if (bookId != null && bookTitle != null)
              'bookReference': {
                'bookId': bookId,
                'bookTitle': bookTitle,
              }
          };
          req.write(jsonEncode(payload));
          final resp = await req.close().timeout(const Duration(seconds: 5));
          if (resp.statusCode == 200 || resp.statusCode == 201) {
            client.close();
            // Fetch updated conversation history
            syncThreadMessages(threadId);
            return true;
          }
        } catch (_) {}
      }
      client.close();
    }
    return false;
  }

  void sendScholarMessage(String scholarId, String text, {String? bookId, String? bookTitle, String? excerpt}) {
    final idx = scholarChats.indexWhere((c) => c['scholar']['id'].toString() == scholarId);
    if (idx == -1 || text.trim().isEmpty) return;
    final msgs = List<Map<String, dynamic>>.from(scholarChats[idx]['messages'] ?? []);
    final userMsg = <String, dynamic>{
      'sender': 'user',
      'text': text.trim(),
      'time': 'هم‌اکنون',
    };
    if (bookId != null && bookTitle != null) {
      userMsg['bookId'] = bookId;
      userMsg['bookTitle'] = bookTitle;
    }
    if (excerpt != null && excerpt.isNotEmpty) {
      userMsg['excerpt'] = excerpt;
    }
    msgs.add(userMsg);
    scholarChats[idx]['messages'] = msgs;
    scholarChats[idx]['lastMessage'] = text.trim();
    notifyListeners();
  }

  Future<void> syncThreadMessages(String threadId) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/consultation/threads/$threadId'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final data = json['data'] ?? json;
          final msgs = data['messages'] as List?;
          if (msgs != null) {
            final idx = scholarChats.indexWhere((c) => c['thread_id']?.toString() == threadId);
            if (idx != -1) {
              scholarChats[idx]['messages'] = msgs.map((m) => {
                'id': m['id'],
                'sender': (m['senderRole'] == 'SCHOLAR' || m['isScholar'] == true) ? 'scholar' : 'user',
                'text': m['text'] ?? m['content'] ?? '',
                'time': m['time'] ?? m['createdAtFa'] ?? 'اخیراً',
                'bookId': m['bookReference']?['bookId'],
                'bookTitle': m['bookReference']?['bookTitle'],
              }).toList();
              if (data['status'] != null) {
                scholarChats[idx]['status'] = data['status'];
              }
              notifyListeners();
            }
          }
          client.close();
          return;
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<void> syncScholarsFromBackend() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/consultation/scholars?limit=100'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final list = (json['data'] is List) ? List<Map<String, dynamic>>.from(json['data']) : null;
          if (list != null && list.isNotEmpty) {
            scholars = list;
            notifyListeners();
            client.close();
            return;
          }
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<void> syncFeedFromBackend({String? category}) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final catQuery = (category != null && category != 'all') ? '?category=$category' : '';
        final req = await client.getUrl(Uri.parse('$base/v1/feed$catQuery'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          List? rawItems;
          if (json['data'] is Map && json['data']['items'] is List) {
            rawItems = json['data']['items'] as List;
          } else if (json['data'] is List) {
            rawItems = json['data'] as List;
          }
          if (rawItems != null && rawItems.isNotEmpty) {
            posts = List<Map<String, dynamic>>.from(rawItems);
            notifyListeners();
            client.close();
            return;
          }
        }
      } catch (_) {}
    }
    client.close();
  }

  Future<bool> toggleFeedLike(String postId) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/feed/$postId/like'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          client.close();
          return true;
        }
      } catch (_) {}
    }
    client.close();
    return false;
  }

  Future<bool> toggleFeedBookmark(String postId) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/feed/$postId/bookmark'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          client.close();
          return true;
        }
      } catch (_) {}
    }
    client.close();
    return false;
  }

  Future<String> translateTextWithAi({
    required String text,
    required String targetLanguage,
  }) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 15);
    String langName = 'فارسی روان';
    if (targetLanguage == 'en') langName = 'English';
    if (targetLanguage == 'ar') langName = 'العربية الفصحى';

    final prompt = 'لطفاً متن معارفی زیر را با بالاترین دقت، شیوایی و حفظ اصطلاحات دقیق به زبان $langName ترجمه کن. تنها خود ترجمه را بدون هیچ مقدمه یا مؤخره‌ای بازگردان:\n«$text»';

    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/api/v1/ai/chat'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        req.write(jsonEncode({
          'message': prompt,
          'section': 'ترجمه متون معارفی',
        }));
        final resp = await req.close().timeout(const Duration(seconds: 20));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final resData = json['data'] ?? json;
          final reply = (resData['reply'] ?? resData['content'])?.toString() ?? '';
          if (reply.trim().isNotEmpty) {
            client.close();
            return reply.trim();
          }
        }
      } catch (_) {}
    }
    client.close();
    return '⚠️ امکان ارتباط با سرویس هوش مصنوعی جهت ترجمه متن در حال حاضر فراهم نشد. لطفاً اتصال اینترنت خود را بررسی فرمایید.';
  }

  Future<String> analyzeTextWithAi({
    required String bookId,
    required String bookTitle,
    required String text,
  }) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 15);
    final prompt = 'تحلیل معارفی و دلالت معرفتی این فراز از کتاب «$bookTitle» را به صورت دقیق، کوتاه، علمی و نکته‌محور تبیین نما:\n«$text»';

    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/api/v1/library/books/$bookId/ai/chat'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        req.write(jsonEncode({
          'query': prompt,
          'context': {
            'bookId': bookId,
            'bookTitle': bookTitle,
            'selectedText': text,
          }
        }));
        final resp = await req.close().timeout(const Duration(seconds: 20));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final resData = json['data'] ?? json;
          final answer = (resData['answer'] ?? resData['reply'] ?? resData['content'])?.toString() ?? '';
          if (answer.trim().isNotEmpty) {
            client.close();
            return answer.trim();
          }
        }
      } catch (_) {}

      try {
        final req = await client.postUrl(Uri.parse('$base/api/v1/ai/chat'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        req.write(jsonEncode({
          'message': prompt,
          'section': 'تحلیل دانشی کتابخانه',
        }));
        final resp = await req.close().timeout(const Duration(seconds: 20));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final resData = json['data'] ?? json;
          final reply = (resData['reply'] ?? resData['content'])?.toString() ?? '';
          if (reply.trim().isNotEmpty) {
            client.close();
            return reply.trim();
          }
        }
      } catch (_) {}
    }
    client.close();
    return '⚠️ در دریافت تحلیل معرفتی از سرور هوشمند خطایی رخ داد. لطفاً اتصال اینترنت را بررسی نموده و مجدداً تلاش فرمایید.';
  }

  Future<Map<String, dynamic>?> fetchInterestsAndPresets() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/auth/interests-and-presets'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['data'] is Map) {
            client.close();
            return Map<String, dynamic>.from(json['data']);
          }
        }
      } catch (_) {}
    }
    client.close();
    return null;
  }

  Future<Map<String, dynamic>?> fetchDailyVerse() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/quran/daily-verse'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['data'] is Map) {
            dailyVerse = Map<String, dynamic>.from(json['data']);
            if (dailyVerse!['textArabic'] != null) {
              final id = 'daily_${dailyVerse!['surahId']}_${dailyVerse!['ayahNumber']}';
              tadabburList.removeWhere((t) => t['id'] == id);
              tadabburList.insert(0, {
                'id': id,
                'surah': dailyVerse!['surahName'] ?? 'قرآن کریم',
                'ayah': dailyVerse!['ayahNumber'] ?? 1,
                'arabic': dailyVerse!['textArabic'] ?? '',
                'translation': dailyVerse!['textPersian'] ?? '',
                'tadabbur': dailyVerse!['theme'] != null
                    ? 'محور مفهومی: ${dailyVerse!['theme']}'
                    : 'تدبر در کلام‌الله مجید',
              });
            }
            notifyListeners();
            client.close();
            return dailyVerse;
          }
        }
      } catch (_) {}
    }
    client.close();
    return dailyVerse;
  }

  Future<List<Map<String, dynamic>>> fetchReciters() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/quran/audio/reciters'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['data'] is List && (json['data'] as List).isNotEmpty) {
            reciters = List<Map<String, dynamic>>.from(json['data']);
            notifyListeners();
            client.close();
            return reciters;
          }
        }
      } catch (_) {}
    }
    client.close();
    return reciters;
  }

  Future<Map<String, dynamic>?> fetchSurahAudio(int surahId, {String reciterId = 'parhizgar'}) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/quran/audio/surahs/$surahId?reciter=$reciterId'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['data'] is Map) {
            client.close();
            return Map<String, dynamic>.from(json['data']);
          }
        }
      } catch (_) {}
    }
    client.close();
    return null;
  }

  Future<List<Map<String, dynamic>>> syncDailyDhikrs() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/dhikr?category=daily'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['data']?['items'] is List && (json['data']['items'] as List).isNotEmpty) {
            dailyDhikrs = List<Map<String, dynamic>>.from(json['data']['items']);
            notifyListeners();
            client.close();
            return dailyDhikrs;
          }
        }
      } catch (_) {}
    }
    client.close();
    return dailyDhikrs;
  }

  Future<List<Map<String, dynamic>>> fetchPublicConsultationThreads() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/consultation/threads?filter=PUBLIC'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          if (json['data'] is List) {
            publicFaqs = List<Map<String, dynamic>>.from(json['data']);
            notifyListeners();
            client.close();
            return publicFaqs;
          }
        }
      } catch (_) {}
    }
    client.close();
    return publicFaqs;
  }

  String getCoverForBook(Map<String, dynamic> book) {
    final raw = (book['cover_url'] ?? book['coverUrl'] ?? '').toString();
    if (raw.isNotEmpty && raw.startsWith('assets/')) {
      return raw;
    }
    final id = (book['id'] ?? '').toString();
    const map = {
      'bk_fiqh_quduri': 'assets/images/covers/cover_bk_fiqh_quduri.png',
      'bk_hadith_riyad': 'assets/images/covers/cover_bk_hadith_riyad.png',
      'bk_hadith_qudsi40': 'assets/images/covers/cover_bk_hadith_qudsi40.png',
      'bk_hadith_nawawi40': 'assets/images/covers/cover_bk_hadith_nawawi40.png',
      'bk_hadith_shamail': 'assets/images/covers/cover_bk_hadith_shamail.png',
      'bk_fiqh_bidayat': 'assets/images/covers/cover_bk_fiqh_bidayat.png',
      'bk_misc_tibyan': 'assets/images/covers/cover_bk_misc_tibyan.png',
      'bk_fiqh_sharai': 'assets/images/covers/cover_bk_fiqh_sharai.png',
      'bk_tafsir_jalalayn': 'assets/images/covers/cover_bk_tafsir_jalalayn.png',
      'bk_fiqh_umda': 'assets/images/covers/cover_bk_fiqh_umda.png',
      'bk_fiqh_risala': 'assets/images/covers/cover_bk_fiqh_risala.png',
      'bk_fiqh_minhaj': 'assets/images/covers/cover_bk_fiqh_minhaj.png',
      'bk_misc_adhkar': 'assets/images/covers/cover_bk_misc_adhkar.png',
    };
    if (map.containsKey(id)) {
      return map[id]!;
    }
    return 'assets/images/covers/cover_bk_hadith_riyad.png';
  }

  /// Semantic and contextual book search (کاوش معنایی برخط با هوش مصنوعی وکتوری Qdrant)
  Future<List<Map<String, dynamic>>> searchBooksSemanticOnline(String query) async {
    final q = query.trim();
    if (q.isEmpty) return [];

    final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/library/ai/semantic-search'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        req.write(jsonEncode({'query': q, 'limit': 8}));
        final resp = await req.close().timeout(const Duration(seconds: 6));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final items = json['data'] as List?;
          if (items != null && items.isNotEmpty) {
            final results = <Map<String, dynamic>>[];
            for (final it in items) {
              final bId = it['bookId']?.toString();
              final localBook = books.firstWhere((b) => b['id']?.toString() == bId, orElse: () => <String, dynamic>{});
              final map = Map<String, dynamic>.from(localBook.isNotEmpty ? localBook : it);
              map['id'] = bId ?? map['id'];
              map['title'] = it['bookTitle'] ?? map['title'];
              map['author'] = it['author'] ?? map['author'];
              final score = ((it['relevanceScore'] as num?)?.toDouble() ?? 0.85);
              final percent = (score * 100).toInt().clamp(50, 99);
              map['semantic_tag'] = 'تطابق هوشمند ($percent٪)';
              map['semantic_reason'] = it['reasoning'] ?? it['excerpt'] ?? 'یافت‌شده در کاوش برداری منابع';
              results.add(map);
            }
            client.close();
            return results;
          }
        }
      } catch (_) {}
    }
    client.close();
    return searchBooksSemantic(q);
  }

  /// Fallback local contextual search across real books
  List<Map<String, dynamic>> searchBooksSemantic(String rawQuery) {
    final q = rawQuery.trim().toLowerCase();
    if (q.isEmpty) return [];

    final results = <Map<String, dynamic>>[];
    final matchedIds = <String>{};

    for (final book in books) {
      final bId = book['id'].toString();
      if (matchedIds.contains(bId)) continue;

      final title = (book['title'] ?? '').toString().toLowerCase();
      final desc = (book['description'] ?? '').toString().toLowerCase();
      final tags = (book['tags'] is List ? (book['tags'] as List).join(' ') : (book['tags'] ?? '')).toString().toLowerCase();
      final author = (book['author'] ?? '').toString().toLowerCase();
      final cat = (book['category'] ?? book['categoryId'] ?? '').toString().toLowerCase();

      if (title.contains(q) || desc.contains(q) || tags.contains(q) || author.contains(q) || cat.contains(q)) {
        matchedIds.add(bId);
        final bookCopy = Map<String, dynamic>.from(book);
        bookCopy['semantic_tag'] = 'تطابق موضوعی';
        bookCopy['semantic_reason'] = 'یافت‌شده در متن و مشخصات دانشی کتاب';
        results.add(bookCopy);
      }
    }

    return results;
  }

  Future<List<Map<String, dynamic>>> fetchPosters() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/library/posters'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final items = json['data'] as List?;
          if (items != null && items.isNotEmpty) {
            posters = List<Map<String, dynamic>>.from(items);
            notifyListeners();
            client.close();
            return posters;
          }
        }
      } catch (_) {}
    }
    client.close();
    return posters;
  }

  Future<List<Map<String, dynamic>>> fetchNearbyMosquesAndScholars({double lat = 35.6892, double lon = 51.3890}) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/consultation/scholars/nearby?lat=$lat&lon=$lon'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final items = json['data'] as List?;
          if (items != null && items.isNotEmpty) {
            client.close();
            return List<Map<String, dynamic>>.from(items);
          }
        }
      } catch (_) {}
    }
    client.close();
    return scholars.map((s) => {
      'id': s['id'],
      'name': s['mosque'] ?? 'مسجد جامع ${s['name']}',
      'city': s['city'] ?? 'تهران',
      'address': s['address'] ?? '${s['city'] ?? "تهران"}، ${s['mosque'] ?? "مسجد جامع و مرکز معارفی"}',
      'distance': '${s['distanceKm'] ?? "۱.۵"} کیلومتر',
      'distanceKm': s['distanceKm'] ?? 1.5,
      'scholar': s['name'],
      'scholarTitle': s['title'],
      'prayers': 'اقامه نمازهای یومیه و پاسخ به مسائل شرعی',
      'features': (s['specialties'] is List) ? List<String>.from(s['specialties']) : ['پاسخ‌گویی به سوالات فقهی', 'کرسی تفسیر قرآن'],
      'type': (s['madhhab'] ?? '').toString().contains('شیعه') ? 'fatwa' : 'unity',
      'is_open': true,
      'meeting_slots': s['meeting_slots'] ?? [],
    }).toList();
  }

  Future<List<Map<String, dynamic>>> fetchThematicSurahs() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/quran/thematic-surahs'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final items = json['data'] as List?;
          if (items != null && items.isNotEmpty) {
            thematicSurahs = List<Map<String, dynamic>>.from(items);
            notifyListeners();
            client.close();
            return thematicSurahs;
          }
        }
      } catch (_) {}
    }
    client.close();
    return thematicSurahs;
  }

  Future<List<String>> fetchAiPromptSuggestions() async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.getUrl(Uri.parse('$base/v1/ai/prompt-suggestions'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) req.headers.set('Authorization', 'Bearer $authToken');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final items = json['data'] as List?;
          if (items != null && items.isNotEmpty) {
            final prompts = items.map((e) => (e['prompt'] ?? e['title'] ?? e.toString()).toString()).toList();
            client.close();
            return prompts;
          }
        }
      } catch (_) {}
    }
    client.close();
    return [
      'احکام معاملات رمزارز، بورس و سود بانکی',
      'مشاوره خانواده و احکام نکاح در مذاهب اسلامی',
      'قاعده لطف در کلام امامیه و استدلال‌های فریقین',
      'درمان وسواس فکری و اضطراب با اخلاق و سیره نبوی',
    ];
  }

  Future<bool> rateAiMessage({
    required String messageId,
    required int rating,
    String? comment,
  }) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/ai/messages/$messageId/rating'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) req.headers.set('Authorization', 'Bearer $authToken');
        req.write(jsonEncode({
          'rating': rating,
          if (comment != null) 'feedbackText': comment,
        }));
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          client.close();
          return true;
        }
      } catch (_) {}
    }
    client.close();
    return false;
  }

  Future<Map<String, dynamic>?> submitBookRequest({
    required String title,
    String? author,
    String? note,
  }) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/library/requests'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) req.headers.set('Authorization', 'Bearer $authToken');
        req.write(jsonEncode({
          'type': 'REQUEST_EXISTING',
          'title': title.trim(),
          'author': author?.trim(),
          'description': note?.trim() ?? 'درخواست از طریق بخش جستجوی کتب',
          'userName': userFullName,
          'userContact': userPhoneNumber,
        }));
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200 || resp.statusCode == 201) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          client.close();
          return Map<String, dynamic>.from(json['data'] ?? {});
        }
      } catch (_) {}
    }
    client.close();
    return null;
  }

  Future<bool> toggleConsultationBookmark(String threadId) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/consultation/threads/$threadId/bookmark'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) req.headers.set('Authorization', 'Bearer $authToken');
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          client.close();
          return true;
        }
      } catch (_) {}
    }
    client.close();
    return false;
  }

  Future<bool> updateConsultationStatus(String threadId, String status) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.patchUrl(Uri.parse('$base/v1/consultation/threads/$threadId/status'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) req.headers.set('Authorization', 'Bearer $authToken');
        req.write(jsonEncode({'status': status}));
        final resp = await req.close().timeout(const Duration(seconds: 4));
        if (resp.statusCode == 200) {
          final idx = scholarChats.indexWhere((c) => c['thread_id'] == threadId);
          if (idx != -1) {
            scholarChats[idx]['status'] = status;
            notifyListeners();
          }
          client.close();
          return true;
        }
      } catch (_) {}
    }
    client.close();
    return false;
  }

  List<Map<String, dynamic>> getParentCategories() {
    if (hierarchicalCategories.isNotEmpty) return hierarchicalCategories;
    return categories.where((c) => c['parent_id'] == null || c['parentId'] == null).toList();
  }

  List<Map<String, dynamic>> getSubcategories(String parentId) {
    final parent = hierarchicalCategories.firstWhere((p) => p['id'] == parentId, orElse: () => {});
    if (parent.isNotEmpty && parent['subcategories'] is List) {
      return List<Map<String, dynamic>>.from(parent['subcategories']);
    }
    return categories.where((c) => c['parent_id'] == parentId || c['parentId'] == parentId).toList();
  }

  // --- DYNAMIC BACKEND SYNC (Auto-Build shelves & books when backend runs) ---
  Future<bool> syncWithBackend() async {
    final client = HttpClient()..connectionTimeout = const Duration(milliseconds: 3500);

    for (final base in EttehadConfig.apiHosts) {
      try {
        // 1. Fetch real books from FastAPI backend
        final req = await client.getUrl(Uri.parse('$base/v1/library/books?limit=100'));
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        final resp = await req.close().timeout(const Duration(milliseconds: 4000));
        if (resp.statusCode == 200) {
          final body = await resp.transform(utf8.decoder).join();
          final json = jsonDecode(body);
          final serverBooks = (json['data'] is List) ? List<Map<String, dynamic>>.from(json['data']) : null;

          if (serverBooks != null && serverBooks.isNotEmpty) {
            books = serverBooks;
            isOnlineSynced = true;

            // 2. Fetch categories to construct shelves automatically
            try {
              final catReq = await client.getUrl(Uri.parse('$base/v1/library/categories'));
              catReq.headers.set('User-Agent', 'EttehadMobileApp/2.0');
              final catResp = await catReq.close().timeout(const Duration(milliseconds: 2500));
              if (catResp.statusCode == 200) {
                final catBody = await catResp.transform(utf8.decoder).join();
                final catJson = jsonDecode(catBody);
                if (catJson['data'] is List) {
                  categories = List<Map<String, dynamic>>.from(catJson['data']);
                  _buildShelvesFromCategories();
                }
              }
            } catch (_) {}

            // 3. Fetch real prayer times
            try {
              final pReq = await client.getUrl(Uri.parse('$base/v1/prayer-times'));
              pReq.headers.set('User-Agent', 'EttehadMobileApp/2.0');
              final pResp = await pReq.close().timeout(const Duration(milliseconds: 2500));
              if (pResp.statusCode == 200) {
                final pBody = await pResp.transform(utf8.decoder).join();
                final pJson = jsonDecode(pBody);
                if (pJson['data']?['cities'] is List) {
                  prayerTimes = List<Map<String, dynamic>>.from(pJson['data']['cities']);
                }
              }
            } catch (_) {}

            // 4. Fetch real dhikrs
            try {
              final dReq = await client.getUrl(Uri.parse('$base/v1/dhikr'));
              dReq.headers.set('User-Agent', 'EttehadMobileApp/2.0');
              final dResp = await dReq.close().timeout(const Duration(milliseconds: 2500));
              if (dResp.statusCode == 200) {
                final dBody = await dResp.transform(utf8.decoder).join();
                final dJson = jsonDecode(dBody);
                if (dJson['data']?['items'] is List) {
                  dhikrs = List<Map<String, dynamic>>.from(dJson['data']['items']);
                }
              }
            } catch (_) {}

            notifyListeners();
            client.close();
            return true;
          }
        }
      } catch (_) {}
    }
    client.close();
    return false;
  }

  void _buildShelvesFromCategories() {
    final List<Map<String, dynamic>> newShelves = [];
    for (final cat in categories) {
      final catId = cat['id']?.toString() ?? '';
      final catTitle = cat['title']?.toString() ?? cat['name']?.toString() ?? 'قفسه';
      final matchingBooks = books.where((b) => (b['category_id']?.toString() == catId || b['categoryId']?.toString() == catId)).map((b) => b['id'].toString()).toList();
      if (matchingBooks.isNotEmpty) {
        newShelves.add({
          'id': 'shelf_cat_$catId',
          'name': catTitle,
          'icon': 'menu_book',
          'bookIds': matchingBooks,
        });
      }
    }
    if (newShelves.isNotEmpty) {
      shelves = newShelves;
    }
  }

  // --- AUTHENTICATION (Melipayamak OTP & Direct Register/Login) ---
  Future<Map<String, dynamic>> sendOtp(String phoneNumber) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);

    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/auth/send-otp'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        req.write(jsonEncode({'phone_number': phoneNumber}));
        final resp = await req.close().timeout(const Duration(seconds: 5));
        final body = await resp.transform(utf8.decoder).join();
        final json = jsonDecode(body);

        if (resp.statusCode == 200 && json['success'] == true) {
          client.close();
          return {
            'success': true,
            'message': json['data']?['message'] ?? 'کد تأیید با موفقیت پیامک شد.',
            'phoneNumber': json['data']?['phoneNumber'] ?? phoneNumber,
            'expiresIn': json['data']?['expiresIn'] ?? 300,
          };
        } else {
          final errorMsg = json['message'] ?? json['detail'] ?? 'خطا در ارسال کد تأیید';
          client.close();
          return {'success': false, 'message': errorMsg};
        }
      } catch (_) {}
    }
    client.close();
    return {
      'success': false,
      'message': 'ارتباط با سرور برقرار نشد. لطفاً اینترنت خود را بررسی کنید.'
    };
  }

  Future<Map<String, dynamic>> verifyOtp({
    required String phoneNumber,
    required String code,
  }) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);

    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/auth/verify-otp'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        req.write(jsonEncode({
          'phone_number': phoneNumber,
          'code': code,
        }));
        final resp = await req.close().timeout(const Duration(seconds: 5));
        final body = await resp.transform(utf8.decoder).join();
        final json = jsonDecode(body);

        if (resp.statusCode == 200 && json['success'] == true) {
          final data = json['data'] ?? {};
          authToken = data['access_token'];
          currentUserId = data['user_id'];
          userPhoneNumber = phoneNumber;
          userFullName = data['full_name'] ?? 'پژوهشگر معارفی';
          userRole = data['role'] ?? 'SEEKER';
          scholarStatus = data['scholar_status'] ?? data['scholarStatus'] ?? 'NONE';
          mosqueName = data['mosque_name'];
          mosqueAddress = data['mosque_address'];

          if (data['madhhab'] != null && data['madhhab'].toString().isNotEmpty) {
            userMadhhab = data['madhhab'].toString();
          }
          if (data['knowledgeLevel'] != null) {
            userKnowledgeLevel = data['knowledgeLevel'].toString();
          }
          if (data['education'] != null) {
            userEducation = data['education'].toString();
          }
          if (data['interests'] is List && (data['interests'] as List).isNotEmpty) {
            userInterests = List<String>.from(data['interests']);
          }
          if (data['avatar'] != null) {
            userAvatar = data['avatar'].toString();
          }

          final bool isNew = data['isNewUser'] == true ||
              userFullName.startsWith('کاربر ') ||
              userInterests.isEmpty;
          
          if (isNew) {
            isLoggedIn = false;
            isProfileCompleted = false;
            await _saveAuthToPrefs();
          } else {
            isLoggedIn = true;
            isProfileCompleted = true;
            await _saveAuthToPrefs();
            notifyListeners();
          }

          if (userRole == 'SCHOLAR' && scholarStatus == 'APPROVED') {
            activeAppMode = 'scholar';
          }

          client.close();
          return {
            'success': true,
            'isNewUser': isNew,
            'data': data
          };
        } else {
          final errorMsg = json['message'] ?? json['detail'] ?? 'کد تأیید نامعتبر است.';
          client.close();
          return {'success': false, 'message': errorMsg};
        }
      } catch (_) {}
    }
    client.close();
    return {
      'success': false,
      'message': 'عدم دسترسی به سرور جهت تأیید هویت.'
    };
  }

  Future<Map<String, dynamic>> registerWithPassword({
    required String phoneNumber,
    required String fullName,
    required String password,
    String role = 'SEEKER',
    String? mosqueName,
    String? mosqueAddress,
  }) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);

    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/auth/register'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        req.write(jsonEncode({
          'phone_number': phoneNumber,
          'full_name': fullName,
          'password': password,
          'role': role,
          'mosque_name': mosqueName,
          'mosque_address': mosqueAddress,
        }));
        final resp = await req.close().timeout(const Duration(seconds: 5));
        final body = await resp.transform(utf8.decoder).join();
        final json = jsonDecode(body);

        if (resp.statusCode == 200 && json['success'] == true) {
          client.close();
          final loginRes = await loginWithPassword(
            phoneNumber: phoneNumber,
            password: password,
            isFromRegister: true,
          );
          userFullName = fullName;
          userRole = role;
          this.mosqueName = mosqueName;
          this.mosqueAddress = mosqueAddress;
          await _saveAuthToPrefs();
          return {
            'success': true,
            'isNewUser': true,
            'data': loginRes['data'],
          };
        } else {
          final errorMsg = json['message'] ?? json['detail'] ?? 'خطا در ثبت‌نام کاربر';
          client.close();
          return {'success': false, 'message': errorMsg};
        }
      } catch (_) {}
    }
    client.close();
    return {'success': false, 'message': 'ارتباط با سرور برقرار نشد.'};
  }

  Future<Map<String, dynamic>> loginWithPassword({
    required String phoneNumber,
    required String password,
    bool isFromRegister = false,
  }) async {
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);

    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.postUrl(Uri.parse('$base/v1/auth/login'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        req.write(jsonEncode({
          'phone_number': phoneNumber,
          'password': password,
        }));
        final resp = await req.close().timeout(const Duration(seconds: 5));
        final body = await resp.transform(utf8.decoder).join();
        final json = jsonDecode(body);

        if (resp.statusCode == 200 && json['success'] == true) {
          final data = json['data'] ?? {};
          authToken = data['access_token'];
          currentUserId = data['user_id'];
          userPhoneNumber = phoneNumber;
          userFullName = data['full_name'] ?? 'پژوهشگر معارفی';
          userRole = data['role'] ?? 'SEEKER';
          scholarStatus = data['scholar_status'] ?? data['scholarStatus'] ?? 'NONE';
          mosqueName = data['mosque_name'];
          mosqueAddress = data['mosque_address'];

          if (userRole == 'SCHOLAR' && scholarStatus == 'APPROVED') {
            activeAppMode = 'scholar';
          }

          if (isFromRegister) {
            isLoggedIn = false;
            isProfileCompleted = false;
            await _saveAuthToPrefs();
            client.close();
            return {'success': true, 'isNewUser': true, 'data': data};
          }

          final bool incomplete = userFullName.startsWith('کاربر ') || userInterests.isEmpty;
          if (incomplete) {
            isLoggedIn = false;
            isProfileCompleted = false;
            await _saveAuthToPrefs();
          } else {
            isLoggedIn = true;
            isProfileCompleted = true;
            await _saveAuthToPrefs();
            notifyListeners();
          }

          client.close();
          return {'success': true, 'isNewUser': incomplete, 'data': data};
        } else {
          final errorMsg = json['message'] ?? json['detail'] ?? 'شماره یا رمز عبور اشتباه است.';
          client.close();
          return {'success': false, 'message': errorMsg};
        }
      } catch (_) {}
    }
    client.close();
    return {'success': false, 'message': 'عدم دسترسی به سرور جهت ورود.'};
  }

  Future<Map<String, dynamic>> updateProfile({
    String? fullName,
    String? madhhab,
    String? knowledgeLevel,
    String? education,
    List<String>? interests,
    String? avatar,
    String? role,
    String? mosqueName,
    String? mosqueAddress,
  }) async {
    // 1. Immediately update local state
    if (fullName != null && fullName.trim().isNotEmpty) {
      userFullName = fullName.trim();
    }
    if (madhhab != null && madhhab.isNotEmpty) userMadhhab = madhhab;
    if (knowledgeLevel != null && knowledgeLevel.isNotEmpty) userKnowledgeLevel = knowledgeLevel;
    if (education != null && education.isNotEmpty) userEducation = education;
    if (interests != null && interests.isNotEmpty) userInterests = List<String>.from(interests);
    if (avatar != null && avatar.isNotEmpty) userAvatar = avatar;
    if (role != null && role.isNotEmpty) {
      userRole = role;
      if (role == 'SCHOLAR' && scholarStatus == 'NONE') {
        scholarStatus = 'PENDING';
      }
    }
    if (mosqueName != null) this.mosqueName = mosqueName;
    if (mosqueAddress != null) this.mosqueAddress = mosqueAddress;

    isProfileCompleted = true;
    isLoggedIn = true;
    await _saveAuthToPrefs();
    notifyListeners();

    // 2. Sync with backend API
    final payload = <String, dynamic>{};
    if (fullName != null) payload['fullName'] = fullName.trim();
    if (madhhab != null) payload['madhhab'] = madhhab;
    if (knowledgeLevel != null) payload['knowledgeLevel'] = knowledgeLevel;
    if (education != null) payload['education'] = education;
    if (interests != null) payload['interests'] = interests;
    if (avatar != null) payload['avatar'] = avatar;
    if (role != null) payload['role'] = role;
    if (mosqueName != null) payload['mosqueName'] = mosqueName;
    if (mosqueAddress != null) payload['mosqueAddress'] = mosqueAddress;

    final client = HttpClient()..connectionTimeout = const Duration(seconds: 4);
    for (final base in EttehadConfig.apiHosts) {
      try {
        final req = await client.putUrl(Uri.parse('$base/v1/auth/profile'));
        req.headers.contentType = ContentType.json;
        req.headers.set('User-Agent', 'EttehadMobileApp/2.0');
        if (authToken != null) {
          req.headers.set('Authorization', 'Bearer $authToken');
        }
        req.write(jsonEncode(payload));
        final resp = await req.close().timeout(const Duration(seconds: 5));
        final body = await resp.transform(utf8.decoder).join();
        final json = jsonDecode(body);
        if (resp.statusCode == 200 && json['success'] == true) {
          client.close();
          return {'success': true, 'data': json['data']};
        }
      } catch (_) {}
    }
    client.close();
    return {'success': true, 'message': 'مشخصات با موفقیت ذخیره شد.'};
  }

  Future<void> logout() async {
    isLoggedIn = false;
    isProfileCompleted = false;
    authToken = null;
    currentUserId = null;
    userPhoneNumber = null;
    userFullName = 'پژوهشگر گرامی اتحاد';
    userRole = 'SEEKER';
    scholarStatus = 'NONE';
    mosqueName = null;
    mosqueAddress = null;
    activeAppMode = 'user';
    await _clearAuthPrefs();
    notifyListeners();
  }
}
