# Security Policy | سیاست امنیتی

<div dir="rtl" align="right">

## سیاست امنیتی (فارسی) 🔒

### نسخه‌های پشتیبانی‌شده

| نسخه | وضعیت پشتیبانی |
| --- | --- |
| 1.0.x | ✅ پشتیبانی فعال |
| < 1.0 | ❌ بدون پشتیبانی |

### گزارش آسیب‌پذیری 🛡️

اگر یک آسیب‌پذیری امنیتی در پروژه اسلام یونیتی کشف کردید، لطفاً **به‌صورت مسئولانه** آن را گزارش دهید.

> ⚠️ **مهم:** لطفاً آسیب‌پذیری‌های امنیتی را به‌عنوان Issue عمومی در GitHub گزارش **ندهید**.

#### نحوه گزارش‌دهی

1. **ایمیل:** آسیب‌پذیری را به آدرس **islamunity.security@gmail.com** ارسال کنید.
2. **عنوان:** از قالب `[SECURITY] توضیح مختصر آسیب‌پذیری` استفاده کنید.
3. **محتوا:** لطفاً اطلاعات زیر را در گزارش خود بگنجانید:
   - نوع آسیب‌پذیری (مثلاً: XSS، SQL Injection، CSRF، و غیره)
   - مسیر فایل(های) مرتبط با مشکل
   - مراحل بازتولید مشکل (Proof of Concept)
   - تأثیر بالقوه آسیب‌پذیری
   - پیشنهاد رفع (در صورت وجود)

#### زمان‌بندی پاسخ‌گویی ⏱️

| مرحله | زمان |
| --- | --- |
| تأیید دریافت گزارش | حداکثر ۴۸ ساعت |
| ارزیابی اولیه | حداکثر ۱ هفته |
| ارائه وصله امنیتی (بحرانی) | حداکثر ۲ هفته |
| ارائه وصله امنیتی (غیربحرانی) | حداکثر ۱ ماه |

#### چه مواردی آسیب‌پذیری امنیتی محسوب می‌شوند؟ 🔍

- ✅ دسترسی غیرمجاز به داده‌های کاربران
- ✅ تزریق کد (SQL Injection، XSS، Command Injection)
- ✅ دور زدن مکانیزم‌های احراز هویت یا مجوزدهی
- ✅ نشت اطلاعات حساس (توکن‌ها، رمزهای عبور، کلیدهای API)
- ✅ آسیب‌پذیری‌های CSRF و SSRF
- ✅ اجرای کد از راه دور (RCE)
- ✅ آسیب‌پذیری‌های مسیریابی فایل (Path Traversal)
- ✅ مشکلات امنیتی در وابستگی‌ها (Dependencies)

#### چه مواردی آسیب‌پذیری امنیتی محسوب **نمی‌شوند**؟

- ❌ باگ‌های عملکردی که تأثیر امنیتی ندارند
- ❌ مشکلات رابط کاربری یا طراحی
- ❌ درخواست ویژگی‌های جدید
- ❌ مشکلات سازگاری مرورگر

#### قدردانی 🏆

ما از تمام محققان امنیتی که به‌صورت مسئولانه آسیب‌پذیری‌ها را گزارش می‌دهند سپاسگزاریم. نام شما (با اجازه خودتان) در بخش **قدردانی‌های امنیتی** ذکر خواهد شد.

</div>

---

## Security Policy (English) 🔒

### Supported Versions

| Version | Support Status |
| --- | --- |
| 1.0.x | ✅ Actively supported |
| < 1.0 | ❌ Not supported |

### Reporting a Vulnerability 🛡️

If you discover a security vulnerability in the Islam Unity project, please report it **responsibly**.

> ⚠️ **Important:** Please do **NOT** report security vulnerabilities as public GitHub Issues.

#### How to Report

1. **Email:** Send the vulnerability details to **islamunity.security@gmail.com**
2. **Subject:** Use the format `[SECURITY] Brief description of vulnerability`
3. **Content:** Please include the following information in your report:
   - Type of vulnerability (e.g., XSS, SQL Injection, CSRF, etc.)
   - File path(s) related to the issue
   - Steps to reproduce (Proof of Concept)
   - Potential impact of the vulnerability
   - Suggested fix (if available)

#### Response Timeline ⏱️

| Stage | Timeframe |
| --- | --- |
| Acknowledgment of report | Within 48 hours |
| Initial assessment | Within 1 week |
| Security patch (critical) | Within 2 weeks |
| Security patch (non-critical) | Within 1 month |

#### What Qualifies as a Security Vulnerability? 🔍

- ✅ Unauthorized access to user data
- ✅ Code injection (SQL Injection, XSS, Command Injection)
- ✅ Bypassing authentication or authorization mechanisms
- ✅ Sensitive information leakage (tokens, passwords, API keys)
- ✅ CSRF and SSRF vulnerabilities
- ✅ Remote Code Execution (RCE)
- ✅ Path Traversal vulnerabilities
- ✅ Security issues in dependencies

#### What Does NOT Qualify as a Security Vulnerability?

- ❌ Functional bugs with no security impact
- ❌ UI/UX or design issues
- ❌ Feature requests
- ❌ Browser compatibility issues

#### Acknowledgments 🏆

We appreciate all security researchers who responsibly disclose vulnerabilities. Your name (with your permission) will be listed in the **Security Acknowledgments** section.

### Security Best Practices for Contributors

When contributing to Islam Unity, please follow these security best practices:

1. **Never commit secrets:** Do not commit API keys, tokens, passwords, or database credentials.
2. **Use environment variables:** Store all sensitive configuration in `.env` files (already in `.gitignore`).
3. **Validate input:** Always validate and sanitize user input on both client and server sides.
4. **Keep dependencies updated:** Regularly update dependencies to patch known vulnerabilities.
5. **Follow least privilege:** Request only the minimum permissions necessary.
