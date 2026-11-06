import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../../core/config.dart';
import '../../../data/ettehad_repository.dart';
import '../../core/theme.dart';
import '../library/library_screen.dart';
import '../profile/profile_sheet.dart';
import '../qna/widgets/scholar_chat_screen.dart';

class AiChatScreen extends StatefulWidget {
  final EttehadRepository repo;
  final String? initialPrompt;
  final bool? isKeyboardOpen;

  const AiChatScreen({
    super.key,
    required this.repo,
    this.initialPrompt,
    this.isKeyboardOpen,
  });

  @override
  State<AiChatScreen> createState() => _AiChatScreenState();
}

class _AiChatScreenState extends State<AiChatScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final TextEditingController _inputCtrl = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _inputFocusNode = FocusNode();

  String? _conversationId;
  String _currentSessionTitle = 'گفتگوی جدید معارفی';
  bool _isTyping = false;

  // Real-time live thinking status (Claude/Gemini style)
  String _currentThinkingStage = 'در حال تحلیل پرسش...';
  Timer? _thinkingTimer;

  final List<Map<String, dynamic>> _messages = [];

  List<String> _quickSuggestedPrompts = [
    'احکام معاملات رمزارز، بورس و سود بانکی',
    'مشاوره خانواده و احکام نکاح در مذاهب اسلامی',
    'قاعده لطف در کلام امامیه و استدلال‌های فریقین',
    'درمان وسواس فکری و اضطراب با اخلاق و سیره نبوی',
  ];

  @override
  void initState() {
    super.initState();
    _initDefaultSession();
    widget.repo.syncAiChatSessionsWithServer();
    widget.repo.fetchAiPromptSuggestions().then((prompts) {
      if (mounted && prompts.isNotEmpty) {
        setState(() => _quickSuggestedPrompts = prompts);
      }
    });
  }

  void _initDefaultSession() {
    final existing = widget.repo.getAiChatSessions();
    if (existing.isNotEmpty) {
      _loadSession(existing.first);
    } else {
      _startFreshConversation();
    }
  }

  @override
  void didUpdateWidget(covariant AiChatScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialPrompt != null &&
        widget.initialPrompt != oldWidget.initialPrompt &&
        widget.initialPrompt!.isNotEmpty) {
      _sendPrompt(widget.initialPrompt!);
    }
  }

  @override
  void dispose() {
    _inputFocusNode.dispose();
    _thinkingTimer?.cancel();
    _inputCtrl.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _startFreshConversation() {
    setState(() {
      _conversationId = 'sess_${DateTime.now().millisecondsSinceEpoch}';
      _currentSessionTitle = 'گفتگوی جدید';
      _messages.clear();
      _messages.add({
        'sender': 'ai',
        'text':
            'سلام علیکم! من «اتحادیار»، دستیار هوشمند معارفی شما هستم.\nپرسش خود را در زمینه قرآن کریم، فقه مقارن، عقاید اسلامی، اخلاق یا سبک زندگی مطرح فرمایید تا پاسخ دهم.',
        'bookCitation': null,
        'scholarRec': null,
        'suggestEscalation': false,
      });
    });
    _scrollToBottom();
  }

  void _loadSession(Map<String, dynamic> s) {
    setState(() {
      _conversationId = s['id']?.toString() ?? 'sess_${DateTime.now().millisecondsSinceEpoch}';
      _currentSessionTitle = (s['title'] ?? 'گفتگوی معارفی').toString();
      _messages.clear();

      final list = s['messages'] as List?;
      if (list != null && list.isNotEmpty) {
        for (final m in list) {
          _messages.add(Map<String, dynamic>.from(m as Map));
        }
      } else {
        _messages.add({
          'sender': 'ai',
          'text':
              'سلام علیکم! من «اتحادیار»، دستیار هوشمند معارفی شما هستم. در خدمت شما هستم.',
          'bookCitation': null,
          'scholarRec': null,
          'suggestEscalation': false,
        });
      }
    });
    _scrollToBottom();
  }

  void _persistCurrentSession() {
    _conversationId ??= 'sess_${DateTime.now().millisecondsSinceEpoch}';

    if (_currentSessionTitle == 'گفتگوی جدید' || _currentSessionTitle == 'گفتگوی جدید معارفی') {
      final firstUserMsg = _messages.firstWhere(
        (m) => m['sender'] == 'user',
        orElse: () => <String, dynamic>{},
      );
      if (firstUserMsg.isNotEmpty && firstUserMsg['text'] != null) {
        final t = firstUserMsg['text'].toString().trim();
        _currentSessionTitle = t.length > 28 ? '${t.substring(0, 28)}...' : t;
      }
    }

    widget.repo.saveAiChatSession(
      id: _conversationId!,
      title: _currentSessionTitle,
      department: 'اتحادیار هوشمند',
      messages: _messages,
    );
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showRenameDialog(String sessionId, String currentTitle) {
    final editCtrl = TextEditingController(text: currentTitle);
    showDialog(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          title: const Row(
            children: [
              Icon(Icons.edit_note_rounded, color: EttehadColors.primary),
              SizedBox(width: 8),
              Text('تغییر عنوان گفتگو', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
            ],
          ),
          content: TextField(
            controller: editCtrl,
            autofocus: true,
            decoration: InputDecoration(
              hintText: 'عنوان گفتگو را وارد کنید...',
              hintStyle: const TextStyle(fontSize: 12),
              filled: true,
              fillColor: EttehadColors.surfaceLow,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('انصراف', style: TextStyle(color: Colors.black54)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: EttehadColors.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () {
                final newTitle = editCtrl.text.trim();
                if (newTitle.isNotEmpty) {
                  widget.repo.renameAiChatSession(sessionId, newTitle);
                  if (_conversationId == sessionId) {
                    setState(() => _currentSessionTitle = newTitle);
                  }
                }
                Navigator.pop(ctx);
              },
              child: const Text('ذخیره'),
            ),
          ],
        ),
      ),
    );
  }

  void _startThinkingCycle(String query) {
    _thinkingTimer?.cancel();

    final List<String> stages;
    if (query.contains('حدیث') || query.contains('روایت') || query.contains('پیامبر') || query.contains('قال')) {
      stages = [
        'در حال تحلیل پرسش...',
        'در حال جستجو در کتب روایی...',
        'در حال استخراج سند و ترجمه حدیث...',
        'در حال تدوین پاسخ مستند...',
      ];
    } else if (query.contains('آیه') || query.contains('قرآن') || query.contains('سوره') || query.contains('تفسیر')) {
      stages = [
        'در حال تحلیل مفهوم و سیاق آیه...',
        'در حال جستجو در آیات و تفاسیر معتبر...',
        'در حال تطبیق دیدگاه‌های مفسران فریقین...',
        'در حال تدوین پاسخ قرآنی...',
      ];
    } else {
      stages = [
        'در حال تحلیل ابعاد مسئله...',
        'در حال جستجو در کتب و فتاوای فقهی...',
        'در حال استخراج ادله و موازین فقه مقارن...',
        'در حال نگارش پاسخ مستند...',
      ];
    }

    _currentThinkingStage = stages.first;
    int idx = 0;
    _thinkingTimer = Timer.periodic(const Duration(milliseconds: 1800), (t) {
      if (!mounted || !_isTyping) {
        t.cancel();
        return;
      }
      if (idx < stages.length - 1) {
        idx++;
        setState(() {
          _currentThinkingStage = stages[idx];
        });
      }
    });
  }

  void _stopThinkingCycle() {
    _thinkingTimer?.cancel();
    _thinkingTimer = null;
  }

  Map<String, dynamic> _resolveBookFromSource(Map<String, dynamic> src) {
    String? bookId;
    final url = (src['targetUrl'] ?? src['url'] ?? '').toString();
    if (url.contains('/book/')) {
      final parts = url.split('/book/')[1].split('/');
      if (parts.isNotEmpty && parts[0].isNotEmpty) {
        bookId = parts[0];
      }
    }
    bookId ??= src['bookId']?.toString() ?? src['book_id']?.toString() ?? src['id']?.toString();

    // 1. Exact or sanitized bookId match
    if (bookId != null && bookId.isNotEmpty && !bookId.startsWith('source://') && bookId != '1') {
      final match = widget.repo.books.firstWhere(
        (b) => b['id']?.toString() == bookId,
        orElse: () => <String, dynamic>{},
      );
      if (match.isNotEmpty) {
        final bCopy = Map<String, dynamic>.from(match);
        if (src['excerpt'] != null) bCopy['excerpt'] = src['excerpt'];
        return bCopy;
      }
    }

    // 2. Match by Title
    final title = (src['title'] ?? '').toString().trim();
    if (title.isNotEmpty) {
      for (final b in widget.repo.books) {
        final bTitle = (b['title'] ?? '').toString().trim();
        if (bTitle == title || title.contains(bTitle) || bTitle.contains(title)) {
          final bCopy = Map<String, dynamic>.from(b);
          if (src['excerpt'] != null) bCopy['excerpt'] = src['excerpt'];
          return bCopy;
        }
      }
      final keywords = [
        'الأربعون النووية',
        'القدسية',
        'القدوري',
        'الصالحین',
        'الشمائل',
        'بداية المجتهد',
        'التبيان',
        'شرائع الإسلام',
        'الجلالين',
        'عمدة الفقه',
        'القيرواني',
        'منهاج الطالبين',
        'الأذكار',
      ];
      for (final kw in keywords) {
        if (title.contains(kw)) {
          final match = widget.repo.books.firstWhere(
            (b) => (b['title'] ?? '').toString().contains(kw),
            orElse: () => <String, dynamic>{},
          );
          if (match.isNotEmpty) {
            final bCopy = Map<String, dynamic>.from(match);
            if (src['excerpt'] != null) bCopy['excerpt'] = src['excerpt'];
            return bCopy;
          }
        }
      }
    }

    // 3. Fallback to first book in repo
    if (widget.repo.books.isNotEmpty) {
      final fb = Map<String, dynamic>.from(widget.repo.books.first);
      if (title.isNotEmpty) fb['title'] = title;
      if (src['excerpt'] != null) fb['excerpt'] = src['excerpt'];
      return fb;
    }

    return {
      'id': bookId ?? 'bk_hadith_nawawi40',
      'title': title.isNotEmpty ? title : 'الأربعون النووية في الأحاديث الصحيحة النبوية',
      'author': src['author'] ?? src['madhhab'] ?? 'مشترک مذاهب',
      'category': 'حدیث و فقه',
      'excerpt': src['excerpt'],
    };
  }

  Map<String, dynamic> _generateSmartOfflineResponse(String query) {
    final q = query.trim().toLowerCase();

    // 1. Check if greeting
    final isGreeting = q.startsWith('سلام') ||
        q.startsWith('درود') ||
        q.contains('خوبی') ||
        q.contains('چطوری') ||
        q.contains('احوال');
    if (isGreeting) {
      return {
        'reply': 'سلام و درود بر شما همراه گرامی! در خدمت شما هستم. '
            'هر سوالی پیرامون معارف اسلامی، آیات قرآن، احکام شرعی، اخلاق یا کتابخانه دارید بفرمایید.',
        'book': null,
        'scholar': null,
        'escalate': false,
        'sources': null,
      };
    }

    // 2. Search local offline chunks
    final qWords = q
        .replaceAll(RegExp(r'[^\w\s\u0600-\u06FF]'), ' ')
        .split(' ')
        .where((w) => w.length > 2 && !['یک', 'بگو', 'چیست', 'درباره', 'مورد', 'برای', 'است', 'کند', 'های'].contains(w))
        .toList();

    Map<String, dynamic>? bestChunk;
    int maxMatches = 0;
    for (final ch in widget.repo.chunks) {
      final text = (ch['content'] ?? ch['text'] ?? '').toString();
      int matches = 0;
      for (final w in qWords) {
        if (text.contains(w)) matches++;
      }
      if (matches > maxMatches) {
        maxMatches = matches;
        bestChunk = ch;
      }
    }

    Map<String, dynamic>? citedBook;
    if (bestChunk != null) {
      final bId = bestChunk['book_id']?.toString() ?? bestChunk['bookId']?.toString();
      citedBook = widget.repo.books.firstWhere(
        (b) => b['id']?.toString() == bId,
        orElse: () => widget.repo.books.isNotEmpty ? widget.repo.books.first : <String, dynamic>{},
      );
    }

    // Scholar recommendation
    Map<String, dynamic>? recScholar;
    for (final s in widget.repo.scholars) {
      final spec = (s['specialties'] ?? '').toString();
      if (q.contains('رمزارز') || q.contains('بورس') || q.contains('مالی')) {
        if (spec.contains('معاملات') || spec.contains('بورس')) { recScholar = s; break; }
      } else if (q.contains('طلاق') || q.contains('ازدواج') || q.contains('خانواده')) {
        if (spec.contains('خانواده')) { recScholar = s; break; }
      }
    }
    recScholar ??= widget.repo.scholars.isNotEmpty ? widget.repo.scholars.first : null;

    String text;
    if (bestChunk != null && maxMatches > 0) {
      final chunkContent = (bestChunk['content'] ?? bestChunk['text'] ?? '').toString().trim();
      final excerpt = chunkContent.length > 550 ? '${chunkContent.substring(0, 550)}...' : chunkContent;
      final bookName = citedBook?['title']?.toString() ?? 'کتابخانه معارفی';
      text = '📖 پاسخ مستند از منبع «$bookName»:\n\n'
          '$excerpt\n\n'
          '📌 این مطلب از کتب معتبر کتابخانه استخراج شده و نسخه کامل آن در بخش مطالعه در دسترس است.';
    } else {
      text = 'پاسخ معارفی پیرامون «$query»:\n\n'
          'بر اساس آموزه‌های قرآن کریم و سنت معتبر اسلامی، موازین اخلاقی، تقوای الهی، صدق نیت و رعایت حقوق متقابل افراد مورد تأکید است.\n'
          'برای دسترسی به استنادات تخصصی فریقین، می‌توانید از بخش کتابخانه یا مشاوره با اساتید استفاده نمایید.';
    }

    return {
      'reply': text,
      'book': citedBook != null && citedBook.isNotEmpty ? citedBook : null,
      'scholar': recScholar,
      'escalate': q.contains('فتوا') || q.contains('استفتا') || q.contains('بیت کوین'),
      'sources': null,
    };
  }

  Future<void> _sendPrompt(String text) async {
    final q = text.trim();
    if (q.isEmpty || _isTyping) return;
    _inputCtrl.clear();

    setState(() {
      _messages.add({
        'sender': 'user',
        'text': q,
        'time': '${DateTime.now().hour.toString().padLeft(2, '0')}:${DateTime.now().minute.toString().padLeft(2, '0')}',
      });
      _isTyping = true;
    });
    _startThinkingCycle(q);
    _scrollToBottom();
    _persistCurrentSession();

    String? finalReply;
    Map<String, dynamic>? finalScholar;
    Map<String, dynamic>? finalBook;
    List<Map<String, dynamic>> finalSources = [];
    bool finalEscalation = false;
    bool streamSuccess = false;

    // 1. Ensure/resolve server conversationId
    if (_conversationId == null || _conversationId!.startsWith('sess_')) {
      try {
        final convClient = HttpClient()..connectionTimeout = const Duration(seconds: 5);
        final convReq = await convClient.postUrl(
          Uri.parse('${EttehadConfig.productionApiBase}/api/v1/ai/conversations'),
        );
        convReq.headers.contentType = ContentType.json;
        convReq.headers.set('User-Agent', 'Ettehad-App/2.0');
        if (widget.repo.authToken != null) {
          convReq.headers.set('Authorization', 'Bearer ${widget.repo.authToken}');
        }
        final cTitle = q.length > 28 ? '${q.substring(0, 28)}...' : q;
        convReq.add(utf8.encode(jsonEncode({'title': cTitle})));
        final convResp = await convReq.close().timeout(const Duration(seconds: 5));
        if (convResp.statusCode == 200) {
          final b = await convResp.transform(utf8.decoder).join();
          final j = jsonDecode(b);
          final sid = (j['data']?['conversationId'] ?? j['data']?['id'])?.toString();
          if (sid != null && sid.isNotEmpty) {
            _conversationId = sid;
          }
        }
        convClient.close();
      } catch (e) {
        debugPrint('Conv create warning: $e');
      }
    }

    // 2. Try Live SSE Streaming if we have a valid conversationId
    if (_conversationId != null && _conversationId!.startsWith('conv_')) {
      try {
        final streamClient = HttpClient()..connectionTimeout = const Duration(seconds: 20);
        final streamReq = await streamClient.postUrl(
          Uri.parse('${EttehadConfig.productionApiBase}/api/v1/ai/conversations/$_conversationId/stream'),
        );
        streamReq.headers.contentType = ContentType.json;
        streamReq.headers.set('User-Agent', 'Ettehad-App/2.0');
        streamReq.headers.set('Accept', 'text/event-stream');
        if (widget.repo.authToken != null) {
          streamReq.headers.set('Authorization', 'Bearer ${widget.repo.authToken}');
        }
        streamReq.add(utf8.encode(jsonEncode({'content': q})));
        final streamResp = await streamReq.close().timeout(const Duration(seconds: 120));

        if (streamResp.statusCode == 200) {
          String accumulated = '';
          final streamLines = streamResp
              .transform(utf8.decoder)
              .transform(const LineSplitter());

          int? aiMsgIdx;

          await for (final rawLine in streamLines) {
            final line = rawLine.trim();
            if (!line.startsWith('data: ')) continue;
            final jsonStr = line.substring(6).trim();
            if (jsonStr.isEmpty || jsonStr == '[DONE]') break;

            try {
              final ev = jsonDecode(jsonStr);
              if (ev is! Map) continue;
              final evType = ev['type']?.toString();
              final evMsg = ev['message']?.toString();

              if (evType == 'token') {
                _stopThinkingCycle();
                final delta = ev['delta']?.toString() ?? '';
                if (delta.isNotEmpty) {
                  accumulated += delta;
                  if (aiMsgIdx == null) {
                    aiMsgIdx = _messages.length;
                    setState(() {
                      _messages.add({
                        'sender': 'ai',
                        'text': accumulated,
                        'isStreaming': true,
                        'bookCitation': null,
                        'scholarRec': null,
                        'suggestEscalation': false,
                      });
                    });
                  } else {
                    final curIdx = aiMsgIdx;
                    if (curIdx < _messages.length) {
                      setState(() {
                        _messages[curIdx]['text'] = accumulated;
                      });
                    }
                  }
                  _scrollToBottom();
                }
              } else if (evType == 'status' || evType == 'plan' || evType == 'tool_call' || evType == 'tool_result' || evType == 'verify') {
                String stageText = '';
                if (evType == 'tool_call') {
                  final toolName = (ev['tool'] ?? ev['data']?['tool'] ?? '').toString();
                  if (toolName == 'search_library') {
                    stageText = 'در حال جستجو در کتب و منابع کتابخانه...';
                  } else if (toolName == 'search_quran') {
                    stageText = 'در حال جستجو و استخراج آیات قرآن...';
                  } else if (toolName == 'browse_book_toc') {
                    stageText = 'در حال بررسی ابواب و فصول کتاب...';
                  } else if (toolName == 'read_chunk') {
                    stageText = 'در حال مطالعه متن فصول کتاب...';
                  } else if (toolName == 'compare_madhhabs') {
                    stageText = 'در حال تطبیق آرای مذاهب اسلامی...';
                  } else if (toolName == 'search_consultations') {
                    stageText = 'در حال بررسی استفتائات و پاسخ‌ها...';
                  } else {
                    stageText = 'در حال کاوش در منابع و شواهد معارفی...';
                  }
                } else if (evType == 'plan') {
                  stageText = 'در حال تحلیل پرسش و تدوین مراحل بررسی...';
                } else if (evType == 'verify') {
                  stageText = 'در حال اعتبارسنجی احکام و مراجع...';
                } else if (evMsg != null && evMsg.isNotEmpty) {
                  stageText = evMsg.replaceAll(RegExp(r'^[^\w\s\u0600-\u06FF]+'), '').trim();
                  if (stageText.length > 35) stageText = '${stageText.substring(0, 35)}...';
                }

                if (stageText.isNotEmpty) {
                  setState(() {
                    _currentThinkingStage = stageText;
                  });
                }
              } else if (evType == 'sources') {
                final rawSrc = ev['sources'] as List?;
                if (rawSrc != null) {
                  finalSources = rawSrc.map((s) => Map<String, dynamic>.from(s as Map)).toList();
                  for (final src in finalSources) {
                    if (src['type'] == 'BOOK' && finalBook == null) {
                      finalBook = _resolveBookFromSource(src);
                      break;
                    }
                  }
                }
                finalEscalation = ev['suggestScholarEscalation'] == true;
              } else if (evType == 'done') {
                final ft = ev['fullText']?.toString();
                if (ft != null && ft.isNotEmpty) accumulated = ft;
                streamSuccess = true;
                break;
              }
            } catch (_) {}
          }

          if (accumulated.trim().isNotEmpty) {
            finalReply = accumulated;
            streamSuccess = true;
            final targetIdx = aiMsgIdx;
            if (targetIdx != null && targetIdx < _messages.length) {
              setState(() {
                _messages[targetIdx]['text'] = accumulated;
                _messages[targetIdx]['isStreaming'] = false;
                _messages[targetIdx]['bookCitation'] = finalBook;
                _messages[targetIdx]['scholarRec'] = finalScholar;
                _messages[targetIdx]['suggestEscalation'] = finalEscalation;
                _messages[targetIdx]['sources'] = finalSources;
              });
            }
          } else {
            final targetIdx = aiMsgIdx;
            if (targetIdx != null && targetIdx < _messages.length) {
              _messages.removeAt(targetIdx);
            }
          }
        }
        streamClient.close();
      } catch (e) {
        debugPrint('Streaming fallback notice: $e');
      }
    }

    // 3. Fallback to POST /api/v1/ai/chat if streaming was not successful
    if (!streamSuccess) {
      final hosts = EttehadConfig.apiHosts;
      final client = HttpClient()..connectionTimeout = const Duration(seconds: 20);

      for (final base in hosts) {
        try {
          final req = await client.postUrl(Uri.parse('$base/api/v1/ai/chat'));
          req.headers.contentType = ContentType.json;
          req.headers.set('User-Agent', 'Ettehad-App/2.0');
          if (widget.repo.authToken != null) {
            req.headers.set('Authorization', 'Bearer ${widget.repo.authToken}');
          }
          final payload = {
            'message': q,
            'section': 'فقه مقارن و تقریب',
            if (_conversationId != null && _conversationId!.startsWith('conv_')) 'conversationId': _conversationId,
          };
          req.add(utf8.encode(jsonEncode(payload)));
          final resp = await req.close().timeout(const Duration(seconds: 120));
          if (resp.statusCode == 200) {
            final body = await resp.transform(utf8.decoder).join();
            final json = jsonDecode(body);
            final resData = json['data'] ?? json;
            finalReply = (resData['reply'] ?? resData['content'])?.toString();
            if (resData['conversationId'] != null) {
              _conversationId = resData['conversationId'].toString();
            }
            if (resData['recommendedScholar'] is Map) {
              finalScholar = Map<String, dynamic>.from(resData['recommendedScholar']);
            }
            if (resData['recommendedBook'] is Map) {
              finalBook = _resolveBookFromSource(Map<String, dynamic>.from(resData['recommendedBook']));
            }
            if (resData['sources'] is List) {
              finalSources = List<Map<String, dynamic>>.from(
                (resData['sources'] as List).map((s) => Map<String, dynamic>.from(s as Map)),
              );
              if (finalBook == null && finalSources.isNotEmpty) {
                final bSrc = finalSources.firstWhere(
                  (s) => s['type'] == 'BOOK',
                  orElse: () => <String, dynamic>{},
                );
                if (bSrc.isNotEmpty) {
                  finalBook = _resolveBookFromSource(bSrc);
                }
              }
            }
            finalEscalation = resData['suggestScholarEscalation'] == true;
            if (finalReply != null && finalReply.isNotEmpty) break;
          }
        } catch (e) {
          debugPrint('Host $base error: $e');
        }
      }
      client.close();
    }

    _stopThinkingCycle();

    // 4. Honest error reporting if remote API failed completely (no fake mock responses per user instruction)
    if (finalReply == null || finalReply.trim().isEmpty) {
      finalReply = '⚠️ در دریافت پاسخ از سامانه هوشمند معارفی خطایی رخ داد یا زمان پاسخگویی به پایان رسید.\nلطفاً اتصال اینترنت خود را بررسی کرده و مجدداً سوال خود را ارسال فرمایید.';
      finalBook = null;
      finalScholar = null;
      finalEscalation = false;
      finalSources = [];
    }

    if (!mounted) return;
    setState(() {
      _isTyping = false;
      // If not already added via streaming, add now
      if (!streamSuccess) {
        _messages.add({
          'sender': 'ai',
          'text': finalReply,
          'bookCitation': finalBook,
          'scholarRec': finalScholar,
          'suggestEscalation': finalEscalation,
          'sources': finalSources.isNotEmpty ? finalSources : null,
        });
      }
    });

    _persistCurrentSession();
    _scrollToBottom();
  }

  void _openCitedBook(Map<String, dynamic> rawBook) {
    final book = _resolveBookFromSource(rawBook);
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: NativeBookReaderScreen(book: book, repo: widget.repo),
        ),
      ),
    );
  }

  void _handleMarkdownLink(String href, String text) {
    if (href.contains('/book/')) {
      _openCitedBook({'targetUrl': href, 'title': text});
    } else if (href.contains('/quran/')) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('منبع قرآنی: $text'),
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else {
      _openCitedBook({'targetUrl': href, 'title': text});
    }
  }

  void _openScholarChat(Map<String, dynamic> scholar) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Directionality(
          textDirection: TextDirection.rtl,
          child: ScholarChatRoomScreen(scholar: scholar, repo: widget.repo),
        ),
      ),
    );
  }

  /// ChatGPT-style Drawer (Sidebar) for Session Management
  Widget _buildChatGptSidebar() {
    final allSessions = widget.repo.getAiChatSessions();

    return Drawer(
      backgroundColor: const Color(0xFF1E293B), // ChatGPT dark slate
      child: SafeArea(
        child: Column(
          children: [
            // Header / Brand & New Chat Button
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
              child: Column(
                children: [
                  Row(
                    children: [
                      Container(
                        width: 38,
                        height: 38,
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: EttehadColors.primary.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: EttehadColors.primary.withValues(alpha: 0.4)),
                        ),
                        child: Image.asset(
                          'assets/images/logo_symbol_white.png',
                          fit: BoxFit.contain,
                          errorBuilder: (context, error, stackTrace) =>
                              const Icon(Icons.auto_awesome, color: Colors.white, size: 20),
                        ),
                      ),
                      const SizedBox(width: 10),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'اتحادیار هوشمند',
                              style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w900),
                            ),
                            Text(
                              'تاریخچه گفتگوها',
                              style: TextStyle(color: Colors.white54, fontSize: 11),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, color: Colors.white70),
                        onPressed: () => Navigator.pop(context),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),

                  // "+ گفتگوی جدید" (New Chat Button like ChatGPT)
                  InkWell(
                    onTap: () {
                      Navigator.pop(context);
                      _startFreshConversation();
                    },
                    borderRadius: BorderRadius.circular(14),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: EttehadColors.primary,
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [
                          BoxShadow(
                            color: EttehadColors.primary.withValues(alpha: 0.35),
                            blurRadius: 8,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.add_rounded, color: Colors.white, size: 20),
                          SizedBox(width: 8),
                          Text(
                            'گفتگوی جدید',
                            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const Divider(color: Colors.white12, height: 1),

            // Sessions List
            Expanded(
              child: allSessions.isEmpty
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(
                          'هنوز گفتگویی ثبت نشده است.\nبا ارسال اولین پیام، گفتگوها در این بخش ذخیره می‌شوند.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.white38, fontSize: 12, height: 1.6),
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      itemCount: allSessions.length,
                      itemBuilder: (ctx, idx) {
                        final s = allSessions[idx];
                        final sId = s['id']?.toString() ?? '';
                        final isCurrent = sId == _conversationId;

                        return Container(
                          margin: const EdgeInsets.only(bottom: 4),
                          decoration: BoxDecoration(
                            color: isCurrent ? Colors.white.withValues(alpha: 0.12) : Colors.transparent,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: ListTile(
                            dense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
                            leading: Icon(
                              Icons.chat_bubble_outline_rounded,
                              size: 18,
                              color: isCurrent ? EttehadColors.mint : Colors.white60,
                            ),
                            title: Text(
                              s['title']?.toString() ?? 'گفتگوی معارفی',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 12.5,
                                fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                                color: isCurrent ? Colors.white : Colors.white70,
                              ),
                            ),
                            subtitle: Text(
                              s['updatedAt']?.toString() ?? '',
                              style: const TextStyle(fontSize: 10, color: Colors.white38),
                            ),
                            trailing: PopupMenuButton<String>(
                              icon: const Icon(Icons.more_horiz_rounded, size: 18, color: Colors.white38),
                              color: const Color(0xFF0F172A),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              onSelected: (val) {
                                if (val == 'rename') {
                                  _showRenameDialog(sId, s['title']?.toString() ?? '');
                                } else if (val == 'delete') {
                                  widget.repo.deleteAiChatSession(sId);
                                  if (_conversationId == sId) {
                                    _startFreshConversation();
                                  }
                                  setState(() {});
                                }
                              },
                              itemBuilder: (ctx) => [
                                const PopupMenuItem(
                                  value: 'rename',
                                  child: Row(
                                    children: [
                                      Icon(Icons.edit_outlined, size: 16, color: Colors.white70),
                                      SizedBox(width: 8),
                                      Text('تغییر عنوان', style: TextStyle(color: Colors.white, fontSize: 12)),
                                    ],
                                  ),
                                ),
                                const PopupMenuItem(
                                  value: 'delete',
                                  child: Row(
                                    children: [
                                      Icon(Icons.delete_outline_rounded, size: 16, color: Colors.redAccent),
                                      SizedBox(width: 8),
                                      Text('حذف گفتگو', style: TextStyle(color: Colors.redAccent, fontSize: 12)),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            onTap: () {
                              Navigator.pop(context);
                              _loadSession(s);
                            },
                          ),
                        );
                      },
                    ),
            ),

            // Bottom Profile / Info Strip inside Drawer
            const Divider(color: Colors.white12, height: 1),
            InkWell(
              onTap: () {
                Navigator.pop(context); // Close drawer
                showEttehadUserProfile(context, widget.repo);
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 16,
                      backgroundColor: EttehadColors.primary.withValues(alpha: 0.3),
                      child: const Icon(Icons.person_rounded, color: Colors.white, size: 18),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.repo.isLoggedIn ? widget.repo.userFullName : 'مهمان گرامی اتحاد',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                          const Text(
                            'مدیریت و شخصی‌سازی پروفایل ‹',
                            style: TextStyle(color: EttehadColors.mint, fontSize: 9.5),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.tune_rounded, color: Colors.white54, size: 16),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThinkingProcessCard() {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Align(
        alignment: Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(16),
              topRight: Radius.circular(16),
              bottomRight: Radius.circular(16),
              bottomLeft: Radius.circular(4),
            ),
            border: Border.all(color: EttehadColors.primary.withValues(alpha: 0.2)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.03),
                blurRadius: 6,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: EttehadColors.primary,
                ),
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  _currentThinkingStage,
                  style: const TextStyle(
                    fontFamily: 'Vazirmatn',
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    color: EttehadColors.navy,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAiMarkdownBody(String rawText, {bool isStreaming = false}) {
    String text = rawText;
    if (isStreaming) {
      text = '$text ▌';
    }

    return MarkdownBody(
      data: text,
      selectable: true,
      onTapLink: (text, href, title) {
        if (href != null && href.isNotEmpty) {
          _handleMarkdownLink(href, text);
        }
      },
      styleSheet: MarkdownStyleSheet(
        p: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontSize: 13,
          height: 1.8,
          color: EttehadColors.ink,
        ),
        strong: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontWeight: FontWeight.w800,
          fontSize: 13,
          color: EttehadColors.navy,
        ),
        em: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontStyle: FontStyle.italic,
          fontSize: 13,
          color: EttehadColors.ink,
        ),
        h1: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontWeight: FontWeight.w900,
          fontSize: 15.5,
          height: 1.8,
          color: EttehadColors.navy,
        ),
        h2: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontWeight: FontWeight.w800,
          fontSize: 14,
          height: 1.75,
          color: EttehadColors.navy,
        ),
        h3: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontWeight: FontWeight.bold,
          fontSize: 13.5,
          height: 1.7,
          color: EttehadColors.primary,
        ),
        blockquote: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontSize: 12.5,
          height: 1.75,
          color: EttehadColors.navy,
        ),
        blockquoteDecoration: BoxDecoration(
          color: const Color(0xFFF1F5F9),
          borderRadius: BorderRadius.circular(8),
          border: const Border(
            right: BorderSide(color: EttehadColors.primary, width: 3.5),
          ),
        ),
        blockquotePadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        code: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontSize: 11.5,
          backgroundColor: Color(0xFFF1F5F9),
          color: EttehadColors.navy,
        ),
        codeblockDecoration: BoxDecoration(
          color: const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: EttehadColors.border),
        ),
        horizontalRuleDecoration: const BoxDecoration(
          border: Border(
            top: BorderSide(
              color: EttehadColors.border,
              width: 1.0,
            ),
          ),
        ),
        a: const TextStyle(
          fontFamily: 'Vazirmatn',
          color: EttehadColors.primary,
          fontWeight: FontWeight.bold,
          decoration: TextDecoration.underline,
        ),
        listBullet: const TextStyle(
          fontFamily: 'Vazirmatn',
          fontSize: 13,
          color: EttehadColors.primary,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: const Color(0xFFFBF9F4),
      resizeToAvoidBottomInset: true,
      // Drawer on right side for RTL (EndDrawer behaves on left in RTL; drawer is on start/right)
      drawer: _buildChatGptSidebar(),
      body: Column(
        children: [
          // ================= Minimalist ChatGPT-like Header =================
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(bottom: BorderSide(color: EttehadColors.border)),
            ),
            child: Row(
              children: [
                // Hamburger icon to open ChatGPT-style Sidebar
                InkWell(
                  onTap: () => _scaffoldKey.currentState?.openDrawer(),
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: EttehadColors.surfaceLow,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: EttehadColors.border),
                    ),
                    child: const Icon(Icons.menu_rounded, size: 20, color: EttehadColors.navy),
                  ),
                ),
                const SizedBox(width: 12),

                // Current Chat Title
                Expanded(
                  child: InkWell(
                    onTap: () {
                      if (_conversationId != null) {
                        _showRenameDialog(_conversationId!, _currentSessionTitle);
                      }
                    },
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                _currentSessionTitle,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w900,
                                  color: EttehadColors.navy,
                                ),
                              ),
                            ),
                            const SizedBox(width: 4),
                            const Icon(Icons.edit_outlined, size: 13, color: Colors.black38),
                          ],
                        ),
                        const SizedBox(height: 2),
                        const Text(
                          'اتحادیار هوشمند معارفی',
                          style: TextStyle(fontSize: 10.5, color: Colors.black45),
                        ),
                      ],
                    ),
                  ),
                ),

                // Quick New Chat Action Button
                IconButton(
                  tooltip: 'گفتگوی جدید',
                  icon: Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: EttehadColors.primary.withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.add_rounded, size: 18, color: EttehadColors.primary),
                  ),
                  onPressed: () {
                    _startFreshConversation();
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('گفتگوی جدید آغاز شد.'),
                        duration: Duration(seconds: 2),
                        behavior: SnackBarBehavior.floating,
                      ),
                    );
                  },
                ),
              ],
            ),
          ),

          // ================= Chat Messages Area (User on Right, AI on Left) =================
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.manual,
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 20),
              itemCount: _messages.length + (_isTyping && !_messages.any((m) => m['isStreaming'] == true) ? 1 : 0),
              itemBuilder: (ctx, i) {
                // Typing / Agent Thinking Indicator on Left (AI response side)
                if (i == _messages.length) {
                  return _buildThinkingProcessCard();
                }

                final msg = _messages[i];
                final isUser = msg['sender'] == 'user';
                final isStreaming = msg['isStreaming'] == true;
                final bookCit = msg['bookCitation'] as Map<String, dynamic>?;
                final scholarRec = msg['scholarRec'] as Map<String, dynamic>?;
                final suggestEsc = msg['suggestEscalation'] == true;

                // Requirement: User questions on RIGHT, AI responses on LEFT
                return Directionality(
                  textDirection: TextDirection.rtl,
                  child: Align(
                    alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 14),
                      constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.85),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: isUser ? EttehadColors.navy : Colors.white,
                        borderRadius: BorderRadius.only(
                          topLeft: const Radius.circular(18),
                          topRight: const Radius.circular(18),
                          bottomLeft: Radius.circular(isUser ? 18 : 4),
                          bottomRight: Radius.circular(isUser ? 4 : 18),
                        ),
                        border: isUser ? null : Border.all(color: EttehadColors.border),
                        boxShadow: [
                          BoxShadow(
                            color: isUser
                                ? EttehadColors.navy.withValues(alpha: 0.15)
                                : Colors.black.withValues(alpha: 0.04),
                            blurRadius: 6,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Sender Tag
                          Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                if (!isUser) ...[
                                  Image.asset(
                                    'assets/images/logo_symbol_color.png',
                                    width: 16,
                                    height: 16,
                                    errorBuilder: (context, error, stackTrace) =>
                                        const Icon(Icons.smart_toy_rounded, size: 16, color: EttehadColors.primary),
                                  ),
                                  const SizedBox(width: 6),
                                  const Text(
                                    'اتحادیار',
                                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: EttehadColors.primary),
                                  ),
                                ] else ...[
                                  const Icon(Icons.person_rounded, size: 14, color: Colors.white70),
                                  const SizedBox(width: 4),
                                  const Text(
                                    'شما',
                                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white70),
                                  ),
                                ],
                              ],
                            ),
                          ),

                          // Message Body Text (Markdown for AI, Clean Text for User)
                          if (isUser)
                            SelectableText(
                              (msg['text'] ?? '').toString(),
                              style: const TextStyle(
                                fontFamily: 'Vazirmatn',
                                fontSize: 13,
                                height: 1.75,
                                color: Colors.white,
                              ),
                            )
                          else
                            _buildAiMarkdownBody(
                              (msg['text'] ?? '').toString(),
                              isStreaming: isStreaming,
                            ),

                          // Escalation Warning
                          if (suggestEsc) ...[
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFEF3C7),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: const Color(0xFFF59E0B)),
                              ),
                              child: const Row(
                                children: [
                                  Icon(Icons.warning_amber_rounded, size: 16, color: Color(0xFFB45309)),
                                  SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      'این مسئله دارای ابعاد تخصصی است؛ پیشنهاد می‌شود با استاد یا عالم دینی مشورت نمایید.',
                                      style: TextStyle(fontSize: 10, color: Color(0xFF92400E)),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],

                          // Book Citation Card
                          if (bookCit != null) ...[
                            const SizedBox(height: 10),
                            InkWell(
                              onTap: () => _openCitedBook(bookCit),
                              borderRadius: BorderRadius.circular(12),
                              child: Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: EttehadColors.skyCardStart.withValues(alpha: 0.6),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: EttehadColors.primary.withValues(alpha: 0.3)),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(Icons.menu_book_rounded, size: 20, color: EttehadColors.primary),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            bookCit['title']?.toString() ?? 'منبع مطالعه',
                                            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: EttehadColors.primary),
                                          ),
                                          Text(
                                            bookCit['author']?.toString() ?? '',
                                            style: const TextStyle(fontSize: 10, color: Colors.black54),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const Icon(Icons.arrow_forward_ios_rounded, size: 12, color: EttehadColors.primary),
                                  ],
                                ),
                              ),
                            ),
                          ],

                          // Scholar Recommendation Card
                          if (scholarRec != null) ...[
                            const SizedBox(height: 10),
                            InkWell(
                              onTap: () => _openScholarChat(scholarRec),
                              borderRadius: BorderRadius.circular(12),
                              child: Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFFFFBEB),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: const Color(0xFFFDE68A)),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(Icons.school_rounded, size: 20, color: EttehadColors.amberDark),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            scholarRec['name']?.toString() ?? 'عالم معارفی',
                                            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: EttehadColors.amberDark),
                                          ),
                                          Text(
                                            '${scholarRec['title'] ?? ''} • تخصص: ${scholarRec['specialties'] ?? ''}',
                                            style: const TextStyle(fontSize: 10, color: Colors.black87),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const Icon(Icons.chat_bubble_outline_rounded, size: 16, color: EttehadColors.amberDark),
                                  ],
                                ),
                              ),
                            ),
                          ],

                          // Message Copy Action Button for AI
                          if (!isUser) ...[
                            const SizedBox(height: 6),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                InkWell(
                                  onTap: () {
                                    Clipboard.setData(ClipboardData(text: (msg['text'] ?? '').toString()));
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('متن پاسخ کپی شد.'),
                                        duration: Duration(seconds: 1),
                                        behavior: SnackBarBehavior.floating,
                                      ),
                                    );
                                  },
                                  borderRadius: BorderRadius.circular(8),
                                  child: const Padding(
                                    padding: EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.copy_rounded, size: 13, color: Colors.black38),
                                        SizedBox(width: 4),
                                        Text('کپی متن', style: TextStyle(fontSize: 10, color: Colors.black45)),
                                      ],
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                InkWell(
                                  onTap: () {
                                    final msgId = msg['id']?.toString() ?? 'msg_${msg.hashCode}';
                                    widget.repo.rateAiMessage(messageId: msgId, rating: 1);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('از بازخورد مثبت شما سپاسگزاریم.'),
                                        duration: Duration(seconds: 2),
                                        behavior: SnackBarBehavior.floating,
                                      ),
                                    );
                                  },
                                  borderRadius: BorderRadius.circular(8),
                                  child: const Padding(
                                    padding: EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                                    child: Icon(Icons.thumb_up_alt_outlined, size: 13, color: Colors.black38),
                                  ),
                                ),
                                const SizedBox(width: 4),
                                InkWell(
                                  onTap: () {
                                    final msgId = msg['id']?.toString() ?? 'msg_${msg.hashCode}';
                                    widget.repo.rateAiMessage(messageId: msgId, rating: -1);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('بازخورد شما جهت بهبود پاسخ‌های هوش مصنوعی ثبت شد.'),
                                        duration: Duration(seconds: 2),
                                        behavior: SnackBarBehavior.floating,
                                      ),
                                    );
                                  },
                                  borderRadius: BorderRadius.circular(8),
                                  child: const Padding(
                                    padding: EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                                    child: Icon(Icons.thumb_down_alt_outlined, size: 13, color: Colors.black38),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          ),

          // ================= Quick Prompts Strip (Only if 1 initial message) =================
          if (_messages.length <= 1)
            Container(
              key: const ValueKey('chat_quick_prompts_strip'),
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
              color: Colors.amber.shade50.withValues(alpha: 0.5),
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _quickSuggestedPrompts.length,
                separatorBuilder: (_, _) => const SizedBox(width: 6),
                itemBuilder: (ctx, idx) {
                  final p = _quickSuggestedPrompts[idx];
                  return ActionChip(
                    label: Text(p, style: const TextStyle(fontSize: 9.5, color: EttehadColors.ink)),
                    backgroundColor: Colors.white,
                    side: BorderSide(color: Colors.amber.shade200),
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    onPressed: () => _sendPrompt(p),
                  );
                },
              ),
            ),

          // ================= Modern Input Bar =================
          Container(
            key: const ValueKey('chat_input_bar_container'),
            padding: const EdgeInsets.fromLTRB(12, 6, 12, 8),
            decoration: const BoxDecoration(
              color: Color(0xFFFBF9F4),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: EttehadColors.border),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.04),
                          blurRadius: 6,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: TextField(
                      key: const ValueKey('chat_input_textfield'),
                      controller: _inputCtrl,
                      focusNode: _inputFocusNode,
                      textInputAction: TextInputAction.send,
                      minLines: 1,
                      maxLines: 4,
                      onSubmitted: _isTyping ? null : _sendPrompt,
                      decoration: const InputDecoration(
                        hintText: 'سؤال علمی، فقهی، قرآنی یا اخلاقی خود را بنویسید...',
                        hintStyle: TextStyle(fontSize: 12, color: Colors.black45),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                FloatingActionButton.small(
                  backgroundColor: _isTyping ? EttehadColors.primary.withValues(alpha: 0.6) : EttehadColors.primary,
                  foregroundColor: Colors.white,
                  elevation: 1,
                  onPressed: _isTyping ? null : () => _sendPrompt(_inputCtrl.text),
                  child: _isTyping
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Icon(Icons.arrow_upward_rounded, size: 20),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
