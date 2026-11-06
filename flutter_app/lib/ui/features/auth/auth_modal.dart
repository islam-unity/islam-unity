import 'dart:async';
import 'package:flutter/material.dart';
import '../../../data/ettehad_repository.dart';
import '../../core/theme.dart';
import 'profile_setup_card.dart';


void showEttehadAuthModal(BuildContext context, EttehadRepository repo, {VoidCallback? onSuccess}) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (ctx) => Directionality(
      textDirection: TextDirection.rtl,
      child: EttehadAuthSheet(repo: repo, onSuccess: onSuccess),
    ),
  );
}

class EttehadAuthSheet extends StatefulWidget {
  final EttehadRepository repo;
  final VoidCallback? onSuccess;

  const EttehadAuthSheet({
    super.key,
    required this.repo,
    this.onSuccess,
  });

  @override
  State<EttehadAuthSheet> createState() => _EttehadAuthSheetState();
}

class _EttehadAuthSheetState extends State<EttehadAuthSheet> {
  // Mode: 0: OTP Mobile, 1: Enter OTP Code, 2: Password Login/Register
  int _step = 0;
  bool _isPasswordLoginMode = false;
  bool _isScholarRegister = false;

  final TextEditingController _phoneCtrl = TextEditingController();
  final TextEditingController _otpCtrl = TextEditingController();
  final TextEditingController _fullNameCtrl = TextEditingController();
  final TextEditingController _passwordCtrl = TextEditingController();
  final TextEditingController _mosqueNameCtrl = TextEditingController();
  final TextEditingController _mosqueAddressCtrl = TextEditingController();

  bool _isLoading = false;
  String? _errorMessage;
  int _resendCountdown = 0;
  Timer? _timer;

  @override
  void dispose() {
    _timer?.cancel();
    _phoneCtrl.dispose();
    _otpCtrl.dispose();
    _fullNameCtrl.dispose();
    _passwordCtrl.dispose();
    _mosqueNameCtrl.dispose();
    _mosqueAddressCtrl.dispose();
    super.dispose();
  }

  void _startTimer(int seconds) {
    _timer?.cancel();
    setState(() => _resendCountdown = seconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) {
        t.cancel();
        return;
      }
      if (_resendCountdown <= 1) {
        t.cancel();
        setState(() => _resendCountdown = 0);
      } else {
        setState(() => _resendCountdown--);
      }
    });
  }

  String _cleanPhone(String val) {
    return val.trim().replaceAll(' ', '').replaceAll('-', '');
  }

  Future<void> _handleSendOtp() async {
    final phone = _cleanPhone(_phoneCtrl.text);
    if (phone.isEmpty || phone.length < 10) {
      setState(() => _errorMessage = 'لطفاً یک شماره موبایل معتبر (مانند ۰۹۱۲۳۴۵۶۷۸۹) وارد کنید.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final res = await widget.repo.sendOtp(phone);
    if (!mounted) return;

    setState(() => _isLoading = false);

    if (res['success'] == true) {
      setState(() {
        _step = 1;
        _errorMessage = null;
      });
      _startTimer(120);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(res['message'] ?? 'کد تأیید ارسال شد'),
          backgroundColor: EttehadColors.primary,
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else {
      setState(() => _errorMessage = res['message'] ?? 'خطا در ارسال پیامک');
    }
  }

  Future<void> _handleVerifyOtp() async {
    final phone = _cleanPhone(_phoneCtrl.text);
    final code = _otpCtrl.text.trim();

    if (code.length < 4) {
      setState(() => _errorMessage = 'لطفاً کد ۵ رقمی پیامک‌شده را وارد نمایید.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final res = await widget.repo.verifyOtp(phoneNumber: phone, code: code);
    if (!mounted) return;

    setState(() => _isLoading = false);

    if (res['success'] == true) {
      if (res['isNewUser'] == true || !widget.repo.isProfileCompleted) {
        setState(() {
          _step = 3;
          _errorMessage = null;
        });
      } else {
        Navigator.pop(context);
        widget.onSuccess?.call();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('خوش آمدید! ${widget.repo.userFullName}'),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } else {
      setState(() => _errorMessage = res['message'] ?? 'کد تأیید نامعتبر است.');
    }
  }

  Future<void> _handlePasswordAuth() async {
    final phone = _cleanPhone(_phoneCtrl.text);
    final password = _passwordCtrl.text.trim();

    if (phone.isEmpty || password.isEmpty) {
      setState(() => _errorMessage = 'شماره تلفن و رمز عبور الزامی است.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    Map<String, dynamic> res;
    if (_isPasswordLoginMode) {
      res = await widget.repo.loginWithPassword(phoneNumber: phone, password: password);
    } else {
      final fullName = _fullNameCtrl.text.trim();
      if (fullName.isEmpty) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'نام و نام‌خانوادگی الزامی است.';
        });
        return;
      }
      res = await widget.repo.registerWithPassword(
        phoneNumber: phone,
        fullName: fullName,
        password: password,
        role: _isScholarRegister ? 'SCHOLAR' : 'SEEKER',
        mosqueName: _mosqueNameCtrl.text.trim().isNotEmpty ? _mosqueNameCtrl.text.trim() : null,
        mosqueAddress: _mosqueAddressCtrl.text.trim().isNotEmpty ? _mosqueAddressCtrl.text.trim() : null,
      );
    }

    if (!mounted) return;
    setState(() => _isLoading = false);

    if (res['success'] == true) {
      if (res['isNewUser'] == true || !widget.repo.isProfileCompleted) {
        setState(() {
          _step = 3;
          _errorMessage = null;
        });
      } else {
        Navigator.pop(context);
        widget.onSuccess?.call();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('ورود با موفقیت انجام شد: ${widget.repo.userFullName}'),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } else {
      setState(() => _errorMessage = res['message'] ?? 'خطا در عملیات ورود/ثبت‌نام');
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      padding: EdgeInsets.fromLTRB(20, 16, 20, 20 + bottomInset),
      decoration: const BoxDecoration(
        color: EttehadColors.paper,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 44,
                height: 4.5,
                decoration: BoxDecoration(
                  color: Colors.black26,
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Top Header Icon and Title
            Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: EttehadColors.primary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Image.asset(
                    'assets/images/logo_symbol_color.png',
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) => const Icon(
                      Icons.lock_person_rounded,
                      color: EttehadColors.primary,
                      size: 26,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _step == 3
                            ? 'شخصی‌سازی و تکمیل پروفایل'
                            : (_step == 1
                                ? 'تأیید شماره تلفن همراه'
                                : (_step == 2
                                    ? (_isPasswordLoginMode ? 'ورود با گذرواژه' : 'ثبت‌نام با گذرواژه')
                                    : 'ورود / ثبت‌نام سریع با پیامک')),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                          color: EttehadColors.navy,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        _step == 3
                            ? 'مشخصات خود را برای تطبیق کتب و پاسخ‌ها کامل فرمایید'
                            : (_step == 1
                                ? 'کد پیامک‌شده از سامانه ملی‌پیامک را وارد فرمایید'
                                : 'سامانه معارفی و کتابخوان هوشمند اتحاد'),
                        style: const TextStyle(fontSize: 11, color: Colors.black54),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, color: Colors.black45),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(height: 1),
            const SizedBox(height: 16),

            // Error Banner
            if (_errorMessage != null)
              Container(
                margin: const EdgeInsets.only(bottom: 14),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEE2E2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFEF4444)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline_rounded, color: Color(0xFFB91C1C), size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(fontSize: 11.5, color: Color(0xFF991B1B)),
                      ),
                    ),
                  ],
                ),
              ),

            // Step 0: Phone Number Input (Melipayamak OTP)
            if (_step == 0) ...[
              const Text(
                'شماره تلفن همراه',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: EttehadColors.navy),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: _phoneCtrl,
                keyboardType: TextInputType.phone,
                textAlign: TextAlign.left,
                textDirection: TextDirection.ltr,
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, letterSpacing: 1.5),
                decoration: InputDecoration(
                  hintText: '09123456789',
                  hintStyle: const TextStyle(color: Colors.black26),
                  prefixIcon: const Icon(Icons.phone_iphone_rounded, color: EttehadColors.primary),
                  filled: true,
                  fillColor: Colors.white,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: const BorderSide(color: EttehadColors.border),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: const BorderSide(color: EttehadColors.border),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: const BorderSide(color: EttehadColors.primary, width: 2),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF0FDF4),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFF86EFAC)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.mark_email_read_rounded, color: Color(0xFF16A34A), size: 20),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: Text(
                        'کد ورود فوری ۵ رقمی توسط سامانه پیامک خدماتی ملی‌پیامک به شماره شما ارسال می‌گردد.',
                        style: TextStyle(fontSize: 11, color: Color(0xFF166534), height: 1.4),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _isLoading ? null : _handleSendOtp,
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  elevation: 0,
                ),
                child: _isLoading
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                    : const Text('دریافت کد تأیید پیامکی', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              ),
              const SizedBox(height: 12),
              Center(
                child: TextButton(
                  onPressed: () => setState(() {
                    _step = 2;
                    _isPasswordLoginMode = true;
                    _errorMessage = null;
                  }),
                  child: const Text(
                    'ورود با شماره موبایل و رمز عبور',
                    style: TextStyle(color: EttehadColors.primary, fontSize: 12.5, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],

            // Step 1: OTP Code Verification
            if (_step == 1) ...[
              Text(
                'کد ارسال‌شده به شماره ${_phoneCtrl.text} را وارد کنید:',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: EttehadColors.navy),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _otpCtrl,
                keyboardType: TextInputType.number,
                textAlign: TextAlign.center,
                maxLength: 6,
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, letterSpacing: 8, color: EttehadColors.primary),
                decoration: InputDecoration(
                  counterText: '',
                  hintText: '• • • • •',
                  filled: true,
                  fillColor: Colors.white,
                  contentPadding: const EdgeInsets.symmetric(vertical: 14),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: const BorderSide(color: EttehadColors.border),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: const BorderSide(color: EttehadColors.primary, width: 2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _isLoading ? null : _handleVerifyOtp,
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  elevation: 0,
                ),
                child: _isLoading
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                    : const Text('تأیید و ورود به برنامه', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  TextButton.icon(
                    onPressed: () => setState(() {
                      _step = 0;
                      _otpCtrl.clear();
                      _errorMessage = null;
                    }),
                    icon: const Icon(Icons.arrow_back_rounded, size: 16),
                    label: const Text('تغییر شماره موبایل', style: TextStyle(fontSize: 12)),
                  ),
                  if (_resendCountdown > 0)
                    Text(
                      'ارسال مجدد (${_resendCountdown}s)',
                      style: const TextStyle(fontSize: 12, color: Colors.black45),
                    )
                  else
                    TextButton(
                      onPressed: _isLoading ? null : _handleSendOtp,
                      child: const Text('ارسال مجدد کد', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                ],
              ),
            ],

            // Step 2: Password Login / Register Mode
            if (_step == 2) ...[
              // Switch Tabs: Login / Register
              Container(
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(12),
                ),
                padding: const EdgeInsets.all(4),
                child: Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() {
                          _isPasswordLoginMode = true;
                          _errorMessage = null;
                        }),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: _isPasswordLoginMode ? Colors.white : Colors.transparent,
                            borderRadius: BorderRadius.circular(10),
                            boxShadow: _isPasswordLoginMode
                                ? [const BoxShadow(color: Colors.black12, blurRadius: 4, offset: Offset(0, 1))]
                                : [],
                          ),
                          child: Center(
                            child: Text(
                              'ورود با رمز عبور',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: _isPasswordLoginMode ? FontWeight.bold : FontWeight.normal,
                                color: _isPasswordLoginMode ? EttehadColors.primary : Colors.black54,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() {
                          _isPasswordLoginMode = false;
                          _errorMessage = null;
                        }),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: !_isPasswordLoginMode ? Colors.white : Colors.transparent,
                            borderRadius: BorderRadius.circular(10),
                            boxShadow: !_isPasswordLoginMode
                                ? [const BoxShadow(color: Colors.black12, blurRadius: 4, offset: Offset(0, 1))]
                                : [],
                          ),
                          child: Center(
                            child: Text(
                              'ثبت‌نام جدید',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: !_isPasswordLoginMode ? FontWeight.bold : FontWeight.normal,
                                color: !_isPasswordLoginMode ? EttehadColors.primary : Colors.black54,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              if (!_isPasswordLoginMode) ...[
                const Text('نام و نام‌خانوادگی', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
                const SizedBox(height: 4),
                TextField(
                  controller: _fullNameCtrl,
                  decoration: InputDecoration(
                    hintText: 'مثال: علی رضایی',
                    prefixIcon: const Icon(Icons.person_rounded, color: EttehadColors.primary),
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: EttehadColors.border)),
                  ),
                ),
                const SizedBox(height: 10),
              ],

              const Text('شماره موبایل', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
              const SizedBox(height: 4),
              TextField(
                controller: _phoneCtrl,
                keyboardType: TextInputType.phone,
                textAlign: TextAlign.left,
                textDirection: TextDirection.ltr,
                decoration: InputDecoration(
                  hintText: '09123456789',
                  prefixIcon: const Icon(Icons.phone_android_rounded, color: EttehadColors.primary),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: EttehadColors.border)),
                ),
              ),
              const SizedBox(height: 10),

              const Text('رمز عبور', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5)),
              const SizedBox(height: 4),
              TextField(
                controller: _passwordCtrl,
                obscureText: true,
                decoration: InputDecoration(
                  hintText: 'حداقل ۶ کاراکتر',
                  prefixIcon: const Icon(Icons.lock_outline_rounded, color: EttehadColors.primary),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: EttehadColors.border)),
                ),
              ),

              if (!_isPasswordLoginMode) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: EttehadColors.border),
                  ),
                  child: SwitchListTile(
                    title: const Text('ثبت‌نام به عنوان عالم دینی / امام جماعت مسجد', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold)),
                    value: _isScholarRegister,
                    activeThumbColor: EttehadColors.primary,
                    contentPadding: EdgeInsets.zero,
                    onChanged: (v) => setState(() => _isScholarRegister = v),
                  ),
                ),
                if (_isScholarRegister) ...[
                  const SizedBox(height: 8),
                  TextField(
                    controller: _mosqueNameCtrl,
                    decoration: InputDecoration(
                      hintText: 'نام مسجد یا مرکز حوزوی',
                      prefixIcon: const Icon(Icons.mosque_rounded, color: EttehadColors.primary),
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _mosqueAddressCtrl,
                    decoration: InputDecoration(
                      hintText: 'آدرس / شهر مسجد',
                      prefixIcon: const Icon(Icons.location_on_rounded, color: EttehadColors.primary),
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ],
              ],

              const SizedBox(height: 18),
              ElevatedButton(
                onPressed: _isLoading ? null : _handlePasswordAuth,
                style: ElevatedButton.styleFrom(
                  backgroundColor: EttehadColors.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: _isLoading
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                    : Text(_isPasswordLoginMode ? 'ورود به حساب' : 'تکمیل ثبت‌نام', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              ),
              const SizedBox(height: 10),
              Center(
                child: TextButton.icon(
                  onPressed: () => setState(() {
                    _step = 0;
                    _errorMessage = null;
                  }),
                  icon: const Icon(Icons.sms_rounded, size: 16),
                  label: const Text('بازگشت به ورود سریع با پیامک (OTP)', style: TextStyle(fontSize: 12)),
                ),
              ),
            ],
              // STEP 3: PROFILE SETUP & PERSONALIZATION
              if (_step == 3) ...[
                EttehadProfileSetupCard(
                  repo: widget.repo,
                  isInitialSetup: true,
                  onComplete: () {
                    Navigator.pop(context);
                    widget.onSuccess?.call();
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('مشخصات شما با موفقیت ثبت شد: ${widget.repo.userFullName}'),
                        backgroundColor: const Color(0xFF10B981),
                        behavior: SnackBarBehavior.floating,
                      ),
                    );
                  },
                  onSkip: () {
                    widget.repo.completeAuthWithoutExtraDetails();
                    Navigator.pop(context);
                    widget.onSuccess?.call();
                  },
                ),
              ],
          ],
        ),
      ),
    );
  }
}
