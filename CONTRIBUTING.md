<div align="center">

# 🤝 Contributing to Islam Unity / مشارکت در اتحاد اسلامی

**Thank you for your interest in contributing!**

**از علاقه شما به مشارکت سپاسگزاریم!**

[English](#english) · [فارسی](#فارسی)

</div>

---

<a id="english"></a>

## 🌍 English

### Welcome!

Islam Unity is an open-source project, and we welcome contributions from everyone — developers, designers, Islamic scholars, translators, and users. Every contribution, no matter how small, helps make Islamic knowledge more accessible to people around the world.

### 📋 How to Contribute

#### 1. Fork & Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/islam-unity/islam-unity.git
cd islam-unity
```

#### 2. Create a Branch

Use a descriptive branch name following the convention:

```bash
git checkout -b feature/add-bookmark-system     # New feature
git checkout -b fix/quran-search-pagination      # Bug fix
git checkout -b docs/update-api-guide            # Documentation
```

**Branch naming conventions:**

| Prefix | Use Case |
|--------|----------|
| `feature/` | New features or enhancements |
| `fix/` | Bug fixes |
| `docs/` | Documentation updates |
| `style/` | Code style / formatting (no logic changes) |
| `refactor/` | Code refactoring |
| `test/` | Adding or updating tests |

#### 3. Make Your Changes

Write clean, well-documented code. Follow the code style guidelines below.

#### 4. Commit Your Changes

We follow **Conventional Commits** for commit messages:

```bash
git commit -m "feat: add Quran bookmark feature"
git commit -m "fix: resolve pagination issue in search API"
git commit -m "docs: update installation instructions"
git commit -m "style: format admin dashboard CSS"
git commit -m "refactor: simplify AI chat session handling"
git commit -m "test: add unit tests for library service"
```

**Commit message format:** `type: short description`

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes |
| `style` | Formatting, whitespace (no code logic changes) |
| `refactor` | Code restructuring without changing behavior |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks (dependencies, configs) |

#### 5. Push & Open a Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub with:

- ✅ A clear title following commit conventions
- ✅ A description of what changed and why
- ✅ Screenshots or GIFs if it's a UI change
- ✅ Reference to any related issues (e.g., `Closes #42`)

---

### 🛠️ Development Setup

#### Backend (Python / FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your local settings

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v
```

#### Flutter App

```bash
cd flutter_app

# Install dependencies
flutter pub get

# Run analysis
flutter analyze

# Run tests
flutter test

# Run the app
flutter run
```

#### Admin Dashboard

The admin dashboard is a vanilla JS SPA served by the backend. No separate build step is needed — just edit the files in `backend/app/admin/static/` and refresh the browser.

---

### 🎨 Code Style Guidelines

#### Python (Backend)

- Follow **PEP 8** conventions
- Use **type hints** for all function parameters and return values
- Write **docstrings** for all public functions and classes
- Use `async/await` for all database and HTTP operations
- Keep functions focused — one function, one responsibility

#### JavaScript (Admin Dashboard)

- Use **ES2022** features (modules, optional chaining, nullish coalescing)
- Follow consistent naming: `camelCase` for variables/functions, `PascalCase` for classes
- Add JSDoc comments for complex functions

#### Dart / Flutter (Mobile App)

- Follow [Effective Dart](https://dart.dev/effective-dart) style guide
- Use `const` constructors where possible
- Keep widgets small and focused

---

### 🏷️ Areas Open for Contribution

We especially welcome contributions in these areas:

| Label | Description |
|-------|-------------|
| 🐛 `bug` | Confirmed bugs that need fixing |
| ✨ `enhancement` | Feature requests and improvements |
| 📝 `documentation` | README, API docs, inline comments |
| 🌐 `translation` | Translating content to other languages (Arabic, Turkish, Urdu, English) |
| ♿ `accessibility` | Improving accessibility and RTL support |
| 🧪 `testing` | Adding or improving test coverage |
| 🎨 `design` | UI/UX improvements |
| 📖 `islamic-content` | Adding or verifying Islamic texts and references |
| 🤖 `ai` | AI model integration, prompts, RAG improvements |

---

### 🌱 Good First Issues

New to open source or this project? Look for issues labeled **`good first issue`** — these are specifically chosen for newcomers and include clear descriptions of what needs to be done.

Some ideas for your first contribution:

- 📝 Fix a typo in documentation
- 🌐 Translate a section of the README
- 🧪 Add a unit test for an existing service
- 🎨 Improve a CSS style in the admin dashboard
- 📖 Add comments to undocumented functions

---

### 📜 Pull Request Process

1. **Fill out the PR template** with all relevant information
2. **Ensure your code passes** all existing tests
3. **Add tests** for new functionality
4. **Update documentation** if your changes affect the public API or user-facing features
5. **Wait for review** — the project owner will review your PR and may request changes
6. **Respond to feedback** promptly and make requested adjustments
7. Once approved, your PR will be merged! 🎉

---

### ⚖️ Code of Conduct

- Be respectful and inclusive in all interactions
- Provide constructive feedback
- Respect the Islamic values and scholarly tradition that this project serves
- Credit original sources when adding Islamic content

---

### 📄 License

By contributing, you agree that your contributions will be licensed under the same **GPL-3.0 License** that covers the project.

---

<a id="فارسی"></a>

<div dir="rtl">

## 🌙 فارسی

### خوش آمدید!

اتحاد اسلامی یک پروژه اوپن سورس است و ما از مشارکت همه استقبال می‌کنیم — توسعه‌دهندگان، طراحان، علمای اسلامی، مترجمان و کاربران. هر مشارکتی، هرچند کوچک، به دسترسی‌پذیرتر شدن معارف اسلامی برای مردم سراسر جهان کمک می‌کند.

---

### 📋 نحوه مشارکت

#### ۱. فورک و کلون

</div>

```bash
# مخزن را در GitHub فورک کنید، سپس:
git clone https://github.com/islam-unity/islam-unity.git
cd islam-unity
```

<div dir="rtl">

#### ۲. ایجاد شاخه

از نام‌گذاری توصیفی شاخه استفاده کنید:

</div>

```bash
git checkout -b feature/add-bookmark-system     # ویژگی جدید
git checkout -b fix/quran-search-pagination      # رفع باگ
git checkout -b docs/update-api-guide            # مستندات
```

<div dir="rtl">

**قراردادهای نام‌گذاری شاخه:**

| پیشوند | کاربرد |
|--------|--------|
| `feature/` | ویژگی‌ها یا بهبودهای جدید |
| `fix/` | رفع باگ‌ها |
| `docs/` | به‌روزرسانی مستندات |
| `style/` | قالب‌بندی کد (بدون تغییر منطق) |
| `refactor/` | بازسازی کد |
| `test/` | اضافه کردن یا به‌روزرسانی تست‌ها |

#### ۳. اعمال تغییرات

کد تمیز و مستند بنویسید. از راهنمای سبک کدنویسی زیر پیروی کنید.

#### ۴. کامیت تغییرات

ما از **Conventional Commits** پیروی می‌کنیم:

</div>

```bash
git commit -m "feat: add Quran bookmark feature"
git commit -m "fix: resolve pagination issue in search API"
git commit -m "docs: update installation instructions"
```

<div dir="rtl">

**فرمت پیام کامیت:** `type: توضیح کوتاه`

| نوع | توضیح |
|------|-------|
| `feat` | ویژگی جدید |
| `fix` | رفع باگ |
| `docs` | تغییرات مستندات |
| `style` | قالب‌بندی (بدون تغییر منطق کد) |
| `refactor` | بازسازی کد بدون تغییر رفتار |
| `test` | اضافه کردن یا به‌روزرسانی تست‌ها |
| `chore` | وظایف نگهداری (وابستگی‌ها، تنظیمات) |

#### ۵. پوش و ایجاد Pull Request

</div>

```bash
git push origin feature/your-feature-name
```

<div dir="rtl">

سپس یک Pull Request در GitHub باز کنید با:

- ✅ عنوان واضح مطابق قراردادهای کامیت
- ✅ توضیح درباره تغییرات و دلیل آن‌ها
- ✅ تصاویر یا GIF در صورت تغییرات رابط کاربری
- ✅ ارجاع به مسائل مرتبط (مثلاً `Closes #42`)

---

### 🛠️ راه‌اندازی محیط توسعه

#### بک‌اند (Python / FastAPI)

</div>

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # ویندوز
# source venv/bin/activate    # مک / لینوکس
pip install -r requirements.txt
cp .env.example .env
# فایل .env را با تنظیمات محلی ویرایش کنید
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest tests/ -v               # اجرای تست‌ها
```

<div dir="rtl">

#### اپلیکیشن Flutter

</div>

```bash
cd flutter_app
flutter pub get
flutter analyze
flutter test
flutter run
```

<div dir="rtl">

#### پنل مدیریت

پنل مدیریت یک SPA ساده با Vanilla JS است که توسط بک‌اند سرو می‌شود. نیازی به مرحله ساخت جداگانه نیست — فقط فایل‌های موجود در `backend/app/admin/static/` را ویرایش کنید و مرورگر را رفرش کنید.

---

### 🎨 راهنمای سبک کدنویسی

#### Python (بک‌اند)

- از قراردادهای **PEP 8** پیروی کنید
- از **type hints** برای تمام پارامترها و مقادیر بازگشتی استفاده کنید
- **docstring** برای تمام توابع و کلاس‌های عمومی بنویسید
- از `async/await` برای تمام عملیات دیتابیس و HTTP استفاده کنید
- توابع را متمرکز نگه دارید — هر تابع، یک مسئولیت

#### JavaScript (پنل مدیریت)

- از ویژگی‌های **ES2022** استفاده کنید
- نام‌گذاری یکسان: `camelCase` برای متغیرها/توابع، `PascalCase` برای کلاس‌ها
- برای توابع پیچیده کامنت JSDoc بنویسید

#### Dart / Flutter (اپلیکیشن موبایل)

- از راهنمای [Effective Dart](https://dart.dev/effective-dart) پیروی کنید
- در صورت امکان از سازنده‌های `const` استفاده کنید
- ویجت‌ها را کوچک و متمرکز نگه دارید

---

### 🏷️ حوزه‌های باز برای مشارکت

ما به‌ویژه از مشارکت در این حوزه‌ها استقبال می‌کنیم:

| برچسب | توضیحات |
|-------|---------|
| 🐛 `bug` | باگ‌های تأیید شده که نیاز به رفع دارند |
| ✨ `enhancement` | درخواست ویژگی و بهبودها |
| 📝 `documentation` | README، مستندات API، کامنت‌های کد |
| 🌐 `translation` | ترجمه محتوا به زبان‌های دیگر (عربی، ترکی، اردو، انگلیسی) |
| ♿ `accessibility` | بهبود دسترسی‌پذیری و پشتیبانی RTL |
| 🧪 `testing` | اضافه کردن یا بهبود پوشش تست |
| 🎨 `design` | بهبودهای UI/UX |
| 📖 `islamic-content` | اضافه کردن یا تأیید متون و مراجع اسلامی |
| 🤖 `ai` | یکپارچگی مدل AI، پرامپت‌ها، بهبود RAG |

---

### 🌱 ایشوهای مناسب برای شروع

تازه‌وارد به اوپن سورس هستید یا با این پروژه آشنا نیستید؟ به دنبال ایشوهای با برچسب **`good first issue`** بگردید — این ایشوها به‌طور خاص برای تازه‌واردان انتخاب شده‌اند و توضیحات واضحی از کار مورد نیاز دارند.

چند ایده برای اولین مشارکت شما:

- 📝 رفع یک غلط املایی در مستندات
- 🌐 ترجمه بخشی از README
- 🧪 اضافه کردن تست واحد برای یک سرویس موجود
- 🎨 بهبود یک استایل CSS در پنل مدیریت
- 📖 اضافه کردن کامنت به توابع مستندنشده

---

### 📜 فرآیند Pull Request

۱. **قالب PR را کامل کنید** با تمام اطلاعات مرتبط
۲. **اطمینان حاصل کنید** که کدتان تمام تست‌های موجود را پاس می‌کند
۳. **تست اضافه کنید** برای عملکردهای جدید
۴. **مستندات را به‌روزرسانی کنید** اگر تغییرات شما بر API عمومی یا ویژگی‌های کاربرمحور تأثیر می‌گذارد
۵. **منتظر بررسی باشید** — مالک پروژه PR شما را بررسی می‌کند و ممکن است تغییراتی درخواست کند
۶. **به بازخوردها سریعاً پاسخ دهید** و تنظیمات درخواست شده را اعمال کنید
۷. پس از تأیید، PR شما ادغام خواهد شد! 🎉

---

### ⚖️ آیین‌نامه رفتاری

- در تمام تعاملات محترمانه و فراگیر باشید
- بازخورد سازنده ارائه دهید
- به ارزش‌های اسلامی و سنت علمی که این پروژه خدمت می‌کند احترام بگذارید
- هنگام اضافه کردن محتوای اسلامی، منابع اصلی را ذکر کنید

---

### 📄 مجوز

با مشارکت در این پروژه، شما موافقت می‌کنید که مشارکت‌هایتان تحت همان مجوز **GPL-3.0** که پروژه را پوشش می‌دهد، منتشر شود.

</div>
