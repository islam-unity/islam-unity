# مستندات جامع فنی و راهنمای اتصال فرانت‌اند به بک‌اند «اتحاد» (Ettehad API)
> **مخصوص ارائه به هوش مصنوعی فرانت‌اند و برنامه‌نویسان کلاینت**  
> نسخه API: `1.0.0` | دامنه سرور: `https://api.unitysi.ir` | آخرین بازبینی: مارس ۲۰۲۶

---

## ۱. اطلاعات پایه سرور و پیکربندی شبکه (Network & Base Configuration)

- **Base URL سرور اصلی:**  
  `https://api.unitysi.ir`
- **پیش‌وند تمامی روت‌های نسخه ۱:**  
  `https://api.unitysi.ir/v1`
- **آدرس وب‌سوکت زنده (WebSocket URL):**  
  `wss://api.unitysi.ir/v1/ws?token={JWT_ACCESS_TOKEN}`
- **مستندات تعاملی Swagger:**  
  `https://api.unitysi.ir/docs`
- **مستندات ریداک (ReDoc):**  
  `https://api.unitysi.ir/redoc`
- **فایل استاندارد OpenAPI JSON:**  
  `https://api.unitysi.ir/openapi.json`
- **پیش‌وند آدرس فایل‌های چندرسانه‌ای استاتیک و آپلودها:**  
  `https://api.unitysi.ir/media/uploads/...`

---

## ۲. هدرهای استاندارد درخواست‌ها (HTTP Request Headers)

تمامی درخواست‌ها به سرور باید هدرهای زیر را شامل شوند:

```http
Content-Type: application/json
Accept-Language: fa-IR
X-App-Version: 1.0.0
X-Device-Id: <UUID_یکتای_دستگاه_کاربر>
Authorization: Bearer <JWT_ACCESS_TOKEN>   (برای روت‌های نیازمند لاگین)
```

> **نکته:** برای درخواست‌های آپلود فایل (مانند `/v1/consultation/media/upload`)، هدر `Content-Type` نباید به صورت دستی مقداردهی شود تا کلاینت نوع `multipart/form-data` همراه با `boundary` را به صورت خودکار تنظیم کند.

---

## ۳. فرمت استاندارد پاسخ‌ها و مدیریت خطاها (Response Envelope & Errors)

### ۳.۱. ساختار پاسخ‌های موفق (Standard Success Envelope)
تمامی پاسخ‌های موفق بک‌اند بدون استثنا درون این فرمت برگشت داده می‌شوند:
```json
{
  "success": true,
  "data": { ... } یا [ ... ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 42,
    "totalPages": 3
  },
  "timestamp": "2026-03-07T14:20:00Z"
}
```
*(فیلد `meta` برای خروجی‌های صفحه‌بندی‌شده ارسال می‌شود).*

### ۳.۲. ساختار پاسخ‌های خطا (Standard Error Envelope)
در صورت بروز خطا، کدهای وضعیتی استاندارد HTTP (۴۰۰، ۴۰۱، ۴۰۳، ۴۰۴، ۴۱۳، ۴۲۹، ۵۰۰) همراه با بدنه زیر بازگردانده می‌شوند:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "اطلاعات ورودی ناقص است یا فرمت درستی ندارد.",
    "details": [
      {
        "field": "body -> phone_number",
        "message": "Field required"
      }
    ]
  },
  "timestamp": "2026-03-07T14:20:00Z"
}
```

### ۳.۳. جدول کدهای خطای اختصاصی سیستم (Error Code Matrix)
| کد خطا (`code`) | وضعیت HTTP | مفهوم و سناریو |
| :--- | :---: | :--- |
| `VALIDATION_FAILED` | `400` | خطای اعتبارسنجی پارامترهای ارسالی در بادی یا کوئری |
| `TOKEN_MISSING` | `401` | هدر `Authorization` ارسال نشده است |
| `TOKEN_EXPIRED` | `401` | توکن JWT منقضی یا نامعتبر شده است |
| `ACCESS_DENIED` | `403` | کاربر مجوز دسترسی به این منبع یا کارتابل را ندارد (مثلا روت‌های عالم) |
| `THREAD_NOT_FOUND` | `404` | گفتگوی مشاوره با این شناسه یافت نشد |
| `BOOK_NOT_FOUND` | `404` | کتاب مورد نظر در کتابخانه موجود نیست |
| `SURAH_NOT_FOUND` | `404` | شماره سوره یا آیه نامعتبر است |
| `ATTACHMENT_OVERSIZE` | `413` | حجم فایل ارسالی بیش از ۲۵ مگابایت است |
| `AI_RATE_LIMIT` | `429` | سقف مجاز پرسش از هوش مصنوعی پر شده است |
| `INTERNAL_SERVER_ERROR` | `500` | خطای داخلی سرور |

---

## ۴. حساب‌های کاربری پیش‌فرض جهت تست (Demo Credentials)

| نقش کاربر | شماره تماس | رمز عبور | نام کاربر | نوع دسترسی |
| :--- | :--- | :--- | :--- | :--- |
| **کاربر عادی (سائل)** | `09121111111` | `123456` | علی رضایی | طرح سوال، چت با AI، مطالعه قرآن و کتابخانه |
| **استاد / عالم دینی** | `09122222222` | `123456` | حجت‌الاسلام دکتر محمدرضا عابدی | دسترسی کامل به کارتابل پاسخ‌گویی به سوالات و پاسخ‌های آماده |

---

## ۵. مستندات تفصیلی اندپوینت‌ها (API Endpoints Reference)

---

### بخش ۱: احراز هویت و مدیریت کاربران (`/v1/auth`)

#### ۱.۱. ثبت‌نام کاربر جدید
- **متد و آدرس:** `POST /v1/auth/register`
- **احراز هویت:** ندارد (عمومی)
- **بدنه درخواست (Request Body):**
```json
{
  "phone_number": "09129876543",
  "full_name": "محمد حسینی",
  "password": "mypassword123",
  "role": "SEEKER",
  "madhhab": "شیعه اثناعشری"
}
```
> مقادیر مجاز `role`: `"SEEKER"` (کاربر عادی), `"SCHOLAR"` (عالم)  
> مقادیر مجاز `madhhab`: `"شیعه اثناعشری"`, `"اهل سنت (حنفی)"`, `"اهل سنت (شافعی)"`

- **پاسخ موفق (HTTP 200):**
```json
{
  "success": true,
  "data": {
    "userId": "usr_99f3b8a1",
    "phoneNumber": "09129876543",
    "fullName": "محمد حسینی",
    "role": "SEEKER"
  },
  "timestamp": "2026-03-07T14:20:00Z"
}
```

---

#### ۱.۲. ورود و دریافت توکن JWT
- **متد و آدرس:** `POST /v1/auth/login`
- **احراز هویت:** ندارد (عمومی)
- **بدنه درخواست (Request Body):**
```json
{
  "phone_number": "09121111111",
  "password": "123456"
}
```
- **پاسخ موفق (HTTP 200):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "user_id": "usr_seeker_1",
    "role": "SEEKER",
    "full_name": "علی رضایی"
  },
  "timestamp": "2026-03-07T14:20:00Z"
}
```

---

#### ۱.۳. دریافت اطلاعات پروفایل کاربر لاگین‌شده
- **متد و آدرس:** `GET /v1/auth/me`
- **احراز هویت:** دارد (`Bearer <token>`)
- **پاسخ موفق (HTTP 200):**
```json
{
  "success": true,
  "data": {
    "id": "usr_seeker_1",
    "phoneNumber": "09121111111",
    "fullName": "علی رضایی",
    "role": "SEEKER",
    "madhhab": "شیعه اثناعشری",
    "age": 28,
    "gender": "MALE",
    "education": "کارشناسی ارشد مهندسی نرم‌افزار",
    "interests": ["TAFSIR", "AKHLAQ"],
    "knowledgeLevel": "ACADEMIC",
    "learningGoals": "آشنایی عمیق‌تر با مفاهیم تدبر در قرآن کریم و فضایل اخلاقی در نهج‌البلاغه",
    "avatar": "/media/avatars/user_1.png"
  },
  "timestamp": "2026-03-07T14:20:00Z"
}
```

---

#### ۱.۴. ویرایش پروفایل، مشخصات فردی و علایق معارفی کاربر
- **متد و آدرس:** `PUT /v1/auth/profile`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست (اختیاری - هر فیلدی ارسال شود به‌روزرسانی می‌شود):**
```json
{
  "fullName": "سارا حسینی",
  "madhhab": "شیعه اثناعشری",
  "age": 26,
  "gender": "FEMALE",
  "education": "کارشناسی ارشد علوم قرآن و حدیث",
  "interests": ["TAFSIR", "AKHLAQ", "LIFESTYLE"],
  "knowledgeLevel": "ACADEMIC",
  "learningGoals": "پژوهش در آیات تدبر و سبک زندگی اسلامی",
  "avatar": "/media/avatars/user_sara.png"
}
```
- **پاسخ موفق (HTTP 200):** اطلاعات کامل و به‌روزرسانی‌شده پروفایل کاربر.

---

#### ۱.۵. دریافت متادیتای علایق، مقاطع تحصیلی و قالب‌های ربات (جهت فرم‌های پروفایل و آنبوردینگ)
- **متد و آدرس:** `GET /v1/auth/interests-and-presets`
- **احراز هویت:** اختیاری / عمومی
- **خروجی:**
```json
{
  "success": true,
  "data": {
    "interestCategories": [
      {
        "id": "TAFSIR",
        "title": "تفسیر و تدبر قرآنی",
        "description": "تأمل در آیات کلام‌الله، شأن نزول، مفاهیم عمیق و تفاسیر معتبر فریقین",
        "iconName": "menu_book",
        "isPrimary": true
      },
      {
        "id": "AKHLAQ",
        "title": "اخلاق، عرفان و خودسازی",
        "description": "تهذیب نفس، فضایل و رذایل اخلاقی، سیر و سلوک معنوی و نصایح اهل‌بیت (ع)",
        "iconName": "self_improvement",
        "isPrimary": false
      },
      {
        "id": "AHKAM",
        "title": "فقه و احکام شرعی",
        "description": "احکام عبادی، معاملات، احکام کاربردی بانوان و آقایان و استفتائات شرعی",
        "iconName": "gavel",
        "isPrimary": false
      },
      {
        "id": "KALAM",
        "title": "کلام و عقاید اسلامی",
        "description": "اصول دین، توحید، نبوت، امامت، معاد و پاسخ به شبهات فکری و اعتقادی معاصر",
        "iconName": "psychology",
        "isPrimary": false
      },
      {
        "id": "HISTORY",
        "title": "تاریخ و سیره نبوی و اهل‌بیت (ع)",
        "description": "زندگی‌نامه پیامبر اعظم و ائمه اطهار، تمدن اسلامی و تحلیل رویدادهای صدر اسلام",
        "iconName": "history_edu",
        "isPrimary": false
      },
      {
        "id": "LIFESTYLE",
        "title": "سبک زندگی، خانواده و تربیت دینی",
        "description": "آداب معاشرت اسلامی، همسرداری، آرامش خانوادگی و اصول تربیت معارفی فرزندان",
        "iconName": "family_restroom",
        "isPrimary": false
      }
    ],
    "knowledgeLevels": [
      {"code": "GENERAL", "title": "عمومی و کاربردی", "description": "بیان ساده، روان، شیوا و قابل فهم برای عموم مخاطبان بدون اصطلاحات پیچیده"},
      {"code": "ACADEMIC", "title": "دانشگاهی و تحلیلی", "description": "رویکرد علمی، مستند، استدلالی با استناد به منابع معتبر دانشگاهی و حوزوی"},
      {"code": "SEMINARY", "title": "حوزوی و تخصصی", "description": "بررسی فنی ادله نقلی و عقلی، مصطلحات اصولی، فقهی، رجالی و تفسیری"}
    ],
    "educationLevels": [
      "زیر دیپلم", "دیپلم", "کاردانی", "کارشناسی", "کارشناسی ارشد", "دکتری", "سطح ۱ حوزه", "سطح ۲ حوزه", "سطح ۳ حوزه", "سطح ۴ و خارج فقه"
    ],
    "genders": [
      {"code": "MALE", "title": "آقا"},
      {"code": "FEMALE", "title": "خانم"}
    ],
    "botRolePresets": [
      {
        "key": "TAFSIR_RESEARCHER",
        "title": "پژوهشگر تدبر و تفسیر قرآنی",
        "description": "تمرکز ویژه بر آیات، شأن نزول، مفردات قرآنی و استناد دقیق به تفاسیر",
        "defaultTone": "SCHOLARLY_FORMAL",
        "defaultAvatar": "/media/avatars/bot_tafsir.png",
        "systemRoleDescription": "پژوهشگر تخصصی تدبر و تفسیر قرآن کریم با استناد به آیات و تفاسیر فریقین"
      },
      {
        "key": "ETHICS_MENTOR",
        "title": "مربی اخلاق و خودسازی",
        "description": "بیان دلگرم‌کننده، تهذیب نفس، فضایل معنوی و توصیه‌های انسان‌ساز",
        "defaultTone": "MYSTICAL_SPIRITUAL",
        "defaultAvatar": "/media/avatars/bot_ethics.png",
        "systemRoleDescription": "مربی اخلاق و معنویت با تأکید بر پالایش درون و سیره اخلاقی معصومین"
      },
      {
        "key": "FIQH_ADVISOR",
        "title": "مشاور احکام شرعی و مسائل روز",
        "description": "پاسخ‌های صریح، منظم و مستند به فتاوا با رعایت تقریب و فقه مقارن",
        "defaultTone": "CONCISE_DIRECT",
        "defaultAvatar": "/media/avatars/bot_fiqh.png",
        "systemRoleDescription": "مشاور دقیق در احکام شرعی، تکالیف عملی و پاسخ به استفتائات"
      },
      {
        "key": "FAMILY_LIFESTYLE",
        "title": "مشاور سبک زندگی و خانواده معارفی",
        "description": "راهنمایی‌های کاربردی بر اساس قرآن و سنت برای آرامش در خانه و خانواده",
        "defaultTone": "FRIENDLY_WARM",
        "defaultAvatar": "/media/avatars/bot_family.png",
        "systemRoleDescription": "مشاور امین در مسائل خانواده، آداب معاشرت و تربیت معارفی"
      },
      {
        "key": "GENERAL_ASSISTANT",
        "title": "دستیار جامع معارف اسلامی",
        "description": "راهنمای همه‌جانبه و متوازن در تمامی حوزه‌های قرآنی، روایی، فقهی و تاریخی",
        "defaultTone": "FRIENDLY_WARM",
        "defaultAvatar": "/media/avatars/bot_general.png",
        "systemRoleDescription": "دستیار پیشرفته و جامع معارفی اتحاد برای پاسخ به تمام پرسش‌های اسلامی"
      },
      {
        "key": "CUSTOM",
        "title": "نقش سفارشی کاربر",
        "description": "تعریف آزادانه هویت و دستورالعمل دلخواه توسط خود کاربر",
        "defaultTone": "FRIENDLY_WARM",
        "defaultAvatar": null,
        "systemRoleDescription": "دستیار سفارشی کاربر مطابق با دستورات تنظیم‌شده"
      }
    ]
  }
}
```

---

### بخش ۲: سرویس پاسخ‌کده و مشاوره تخصصی (`/v1/consultation`)

#### ۲.۱. فهرست اساتید و علما با فیلتر پیشرفته
- **متد و آدرس:** `GET /v1/consultation/scholars`
- **احراز هویت:** اختیاری
- **پارامترهای کوئری (Query Params):**
  - `q` (اختیاری): جستجو در نام، تخصص یا بیوگرافی
  - `madhhab` (اختیاری): فیلتر مذهب (`شیعه اثناعشری`, `اهل سنت (حنفی)`, `اهل سنت (شافعی)`)
  - `city` (اختیاری): نام شهر (مثلاً `قم`, `مشهد`, `سنندج`)
  - `mosque` (اختیاری): مرکز فقهی یا مسجد
  - `specialty` (اختیاری): تخصص فقهی
  - `minRating` (اختیاری): حداقل امتیاز (مثلاً `4.5`)
  - `sort` (اختیاری): مرتب‌سازی (`RANK_RATING`, `ANSWERS_COUNT`, `RESPONSE_SPEED`) - پیش‌فرض: `RANK_RATING`
  - `page` (پیش‌فرض: `1`)
  - `limit` (پیش‌فرض: `20`, حداکثر: `100`)

- **نمونه خروجی دیتا:**
```json
{
  "success": true,
  "data": [
    {
      "id": "scholar_1",
      "name": "حجت‌الاسلام دکتر محمدرضا عابدی",
      "title": "استاد سطوح عالی حوزه علمیه و دکترای فقه و حقوق",
      "specialties": ["احکام شرعی و فقهی", "معاملات و بورس", "مسائل نوین پزشکی"],
      "rating": 4.98,
      "answerCount": 542,
      "responseTimeHours": 2,
      "rank": 1,
      "avatarColorHex": "0xFF8C6239",
      "avatarUrl": "https://cdn.ettehad.app/avatars/scholar_1.jpg",
      "isVerified": true,
      "madhhab": "شیعه اثناعشری",
      "city": "قم",
      "mosque": "مرکز فقهی ائمه اطهار (ع)",
      "bio": "دانش‌آموخته حوزه علمیه قم با بیش از ۱۵ سال سابقه پاسخگویی..."
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 6,
    "totalPages": 1
  }
}
```

---

#### ۲.۲. دریافت متادیتای فیلترهای علما (شهرها، مساجد، مذاهب، تخصص‌ها)
- **متد و آدرس:** `GET /v1/consultation/scholars/metadata`
- **احراز هویت:** ندارد
- **خروجی:** آرایه‌های یکتای مقادیر موجود در دیتابیس برای پر کردن دراپ‌داون‌های فیلتر در فرانت.

---

#### ۲.۳. آپلود فایل چندرسانه‌ای (صوت، تصویر، ویدئو)
- **متد و آدرس:** `POST /v1/consultation/media/upload`
- **احراز هویت:** دارد (`Bearer <token>`)
- **Content-Type:** `multipart/form-data`
- **فیلدهای فرم (Form Data):**
  - `file`: فایل باینری (حداکثر ۲۵ مگابایت)
  - `type`: نوع فایل (`VOICE`, `VIDEO`, `IMAGE`, `DOCUMENT`) - پیش‌فرض: `VOICE`
  - `title`: عنوان اختیاری فایل
  - `durationSeconds`: طول فایل صوتی/تصویری به ثانیه (اختیاری)
- **پاسخ موفق:**
```json
{
  "success": true,
  "data": {
    "mediaId": "att_voice_8d3c1a2f",
    "type": "VOICE",
    "title": "صدای سوال احکام.m4a",
    "durationSeconds": 45,
    "fileUrl": "/media/uploads/att_voice_8d3c1a2f.m4a",
    "fileSizeBytes": 1048576
  }
}
```

---

#### ۲.۴. ایجاد گفتگو / طرح سوال جدید در ویزارد مشاوره
- **متد و آدرس:** `POST /v1/consultation/threads`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست (Request Body):**
```json
{
  "title": "حکم شرعی معامله در بازار آتی طلا و ارز",
  "initialQuestionBody": "با سلام، آیا ورود به معاملات اهرم‌دار آتی طلا از دیدگاه فقهی صحیح است؟",
  "category": "احکام و معاملات مالی",
  "targetScholarId": "scholar_1",
  "isAnonymous": false,
  "isPublic": true,
  "isUrgent": false,
  "attachments": [
    {
      "mediaId": "att_voice_8d3c1a2f",
      "type": "VOICE",
      "title": "توضیح صوتی معامله",
      "durationSeconds": 45,
      "fileUrl": "/media/uploads/att_voice_8d3c1a2f.m4a",
      "fileSizeBytes": 1048576
    }
  ]
}
```
- **پاسخ موفق (HTTP 201):**
```json
{
  "success": true,
  "data": {
    "threadId": "th_10928374",
    "status": "OPEN",
    "createdAtFa": "۱۴۰۴/۱۲/۱۷",
    "trackingCode": "ETH-Q-49201"
  }
}
```

---

#### ۲.۵. لیست گفتگوهای کاربر
- **متد و آدرس:** `GET /v1/consultation/threads`
- **احراز هویت:** دارد (`Bearer <token>`)
- **پارامترهای کوئری:**
  - `filter`: مقادیر مجاز: `ALL`, `PENDING`, `ANSWERED`, `BOOKMARKED`, `PUBLIC` (پیش‌فرض: `ALL`)
  - `category`: دسته‌بندی موضوعی
  - `q`: کلیدواژه جستجو
  - `sort`: `LAST_ACTIVITY` یا `NEWEST`
  - `page`: شماره صفحه
  - `limit`: تعداد در هر صفحه

---

#### ۲.۶. جزئیات گفتگو و تاریخچه کامل پیام‌ها
- **متد و آدرس:** `GET /v1/consultation/threads/{threadId}`
- **احراز هویت:** دارد (`Bearer <token>`)
- **خروجی:** اطلاعات کامل پرونده، مشخصات عالم مربوطه، لیست پیام‌ها به ترتیب زمانی، و پیوست‌ها.

---

#### ۲.۷. ارسال پیام جدید در گفتگو
- **متد و آدرس:** `POST /v1/consultation/threads/{threadId}/messages`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست:**
```json
{
  "text": "بر اساس فتوای مراجع، معاملات اهرمی در صورتی که واقعی نباشد جایز نیست.",
  "citation": "استفتاء شماره ۴۸۱۲ از دفتر آیت‌الله العظمی سیستانی",
  "attachmentId": null
}
```
*(فیلد `citation` مخصوص استناد فقهی و روایی عالم است).*

---

#### ۲.۸. تغییر وضعیت گفتگو (باز / بسته)
- **متد و آدرس:** `PATCH /v1/consultation/threads/{threadId}/status`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست:**
```json
{
  "status": "CLOSED"
}
```
*(مقادیر مجاز: `OPEN`, `CLOSED`)*

---

#### ۲.۹. نشان‌کردن / لغو نشان گفتگو (Bookmark Toggle)
- **متد و آدرس:** `POST /v1/consultation/threads/{threadId}/bookmark`
- **احراز هویت:** دارد (`Bearer <token>`)
- **پاسخ:** `{"isBookmarked": true}` یا `{"isBookmarked": false}`

---

#### ۲.۱۰. تغییر وضعیت نمایش گفتگو (عمومی / خصوصی)
- **متد و آدرس:** `PATCH /v1/consultation/threads/{threadId}/visibility`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست:**
```json
{
  "isPublic": true
}
```

---

#### ۲.۱۱. کارتابل اختصاصی سوالات ارجاعی به عالم (مخصوص نقش عالم)
- **متد و آدرس:** `GET /v1/consultation/scholar/inbox`
- **احراز هویت:** دارد (نقش کاربر باید `SCHOLAR` یا `ADMIN` باشد)

---

#### ۲.۱۲. لیست و ثبت پاسخ‌های آماده عالم (Quick Replies)
- **دریافت لیست پاسخ‌های آماده:** `GET /v1/consultation/scholar/quick-replies`
- **ایجاد پاسخ آماده جدید:** `POST /v1/consultation/scholar/quick-replies`
- **بدنه ثبت:**
```json
{
  "title": "سلام و تحیت آغازین",
  "content": "با سلام و درود و آرزوی قبولی طاعات و عبادات شما، در خصوص پرسش مطروحه...",
  "category": "مقدمه"
}
```

---

### بخش ۳: کتابخانه دیجیتال و ابزارهای پژوهشی هوش مصنوعی (`/v1/library`)

#### ۳.۱. پوسترهای ویترین کتابخانه
- **متد و آدرس:** `GET /v1/library/posters`
- **احراز هویت:** ندارد

---

#### ۳.۲. فهرست دسته‌بندی‌های هشت‌گانه کتابخانه
- **متد و آدرس:** `GET /v1/library/categories`
- **احراز هویت:** ندارد

---

#### ۳.۳. فهرست کتب با فیلتر و جستجو
- **متد و آدرس:** `GET /v1/library/books`
- **پارامترهای کوئری:**
  - `categoryId`: شناسه دسته
  - `q`: جستجو در عنوان، نویسنده، تگ‌ها
  - `isFeatured`: `true` یا `false`
  - `tag`: فیلتر برچسب
  - `page` و `limit`

---

#### ۳.۴. شناسنامه کامل کتاب و فهرست فصول (TOC)
- **متد و آدرس:** `GET /v1/library/books/{bookId}`
- **خروجی:** مشخصات نشر، نویسنده، مترجم، تعداد صفحات، امتیاز و آرایه `chapters` شامل شماره فصل، عنوان و زمان تخمینی مطالعه به دقیقه (`readingTimeMinutes`).

---

#### ۳.۵. متن کامل فصل و پاراگراف‌ها (جهت Reader)
- **متد و آدرس:** `GET /v1/library/books/{bookId}/chapters/{chapterId}`
- **خروجی:** آرایه `paragraphs` شامل متون پاراگراف‌ها جهت رندر در کتابخوان دیجیتال.

---

#### ۳.۶. ذخیره درصد مطالعه و موقعیت پاراگراف (Progress Sync)
- **متد و آدرس:** `PUT /v1/library/books/{bookId}/progress`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست:**
```json
{
  "currentChapterId": "ch_nahj_01",
  "currentParagraphIndex": 4,
  "percentage": 35.5
}
```

---

#### ۳.۷. نشان‌کردن کتاب به عنوان علاقه‌مندی
- **متد و آدرس:** `POST /v1/library/books/{bookId}/favorite`
- **احراز هویت:** دارد (`Bearer <token>`)
- **خروجی:** `{"isFavorite": true}` یا `{"isFavorite": false}`

---

#### ۳.۸. مدیریت قفسه‌های شخصی کاربر (User Shelves)
- **دریافت قفسه‌ها به همراه کتاب‌ها:** `GET /v1/library/user/shelves`
- **ایجاد قفسه جدید:** `POST /v1/library/user/shelves`
  - بدنه: `{"title": "مطالعه ماه رمضان", "colorHex": "#4CAF50", "description": "برنامه مطالعاتی"}`
- **افزودن کتاب به قفسه:** `POST /v1/library/user/shelves/{shelfId}/books?bookId={bookId}`
- **حذف کتاب از قفسه:** `DELETE /v1/library/user/shelves/{shelfId}/books/{bookId}`

---

#### ۳.۹. هایلایت‌ها و یادداشت‌های متنی کتابخوان
- **دریافت هایلایت‌های کاربر:** `GET /v1/library/user/highlights?bookId={bookId}`
- **ثبت هایلایت جدید:** `POST /v1/library/books/{bookId}/highlights`
  - بدنه درخواست:
```json
{
  "chapterId": "ch_nahj_01",
  "selectedText": "الْحَمْدُ لِلَّهِ الَّذِي لَا يَبْلُغُ مِدْحَتَهُ الْقَائِلُونَ",
  "note": "نکته‌ای پیرامون توحید ذاتی",
  "colorHex": "#FFE082"
}
```
- **حذف هایلایت:** `DELETE /v1/library/user/highlights/{highlightId}`

---

#### ۳.۱۰. استریم دستیار هوشمند بافت‌محور کتابخوان (Contextual Reader AI Assistant - SSE Stream)
- **متد و آدرس:** `POST /v1/library/books/{bookId}/ai/reader-stream`
- **احراز هویت:** اختیاری (در صورت ارسال توکن، امکان ذخیره خودکار به عنوان هایلایت و یادداشت فراهم است)
- **نوع بازگشتی:** `text/event-stream` (Server-Sent Events)
- **توضیحات:** هنگام انتخاب متنی توسط کاربر در کتابخوان یا طرح سوال پیرامون بخشی از کتاب، این متد بافت پیرامونی (پاراگراف‌های قبل و بعد)، عنوان فصل و مشخصات کتاب را شناسایی کرده و پاسخ هوش مصنوعی را به صورت زنده استریم می‌کند.
- **بدنه درخواست (Request Body):**
```json
{
  "chapterId": "chap_nahj_1",
  "paragraphIndex": 0,
  "selectedText": "الْحَمْدُ لِلَّهِ الَّذِي لَا يَبْلُغُ مِدْحَتَهُ الْقَائِلُونَ",
  "actionType": "EXPLAIN",
  "userQuery": null,
  "conversationId": null,
  "saveAsHighlight": true,
  "colorHex": "#FFE082"
}
```
> **مقادیر مجاز `actionType`:**
> 1. `EXPLAIN`: شرح، تبیین مراد نویسنده و واژه‌شناسی عبارت
> 2. `SUMMARIZE`: خلاصه‌سازی پیام اصلی و جان‌مایه فراز
> 3. `TRANSLATE_IRAB`: ترجمه دقیق فارسی و نکات ادبی، صرفی، نحوی و اعرابی
> 4. `PRACTICAL_LESSONS`: استخراج درس‌های کاربردی، رفتاری و سبک زندگی
> 5. `CUSTOM_QUERY`: طرح هرگونه پرسش آزاد کاربر با بافت متن انتخابی (متن سوال در `userQuery` قرار می‌گیرد)
>
> **فیلدهای اختیاری:**
> - `conversationId`: شناسه گفتگو جهت ادامه‌دار بودن چت و طرح سوالات بعدی در همان بافت متن.
> - `saveAsHighlight`: در صورت `true` بودن، پاسخ به صورت مستقیم به عنوان هایلایت و یادداشت حاشیه‌ای ذخیره می‌شود.

- **نمونه ساختار رویدادهای زنده استریم (SSE Events):**
```text
data: {"event": "start", "conversationId": "conv_lib_4f81", "bookTitle": "نهج‌البلاغه", "chapterTitle": "خطبه نخست", "actionType": "EXPLAIN"}

data: {"event": "delta", "delta": "این فراز بیانگر "}

data: {"event": "delta", "delta": "توحید ذاتی پروردگار است... "}

data: {"event": "done", "conversationId": "conv_lib_4f81", "fullText": "...", "citations": [{"volume": 1, "page": 1, "chapter": "خطبه نخست", "quote": "..."}], "highlightId": "hl_39ac12"}
```

---

#### ۳.۱۱. چت هوشمند مستند با کتاب (AI Book Chat with Citations)
- **متد و آدرس:** `POST /v1/library/books/{bookId}/ai/chat`
- **احراز هویت:** اختیاری / عمومی
- **بدنه درخواست:**
```json
{
  "query": "دیدگاه نهج‌البلاغه در مورد حق زمامدار و حق مردم نسبت به یکدیگر چیست؟"
}
```
- **نمونه پاسخ:**
```json
{
  "success": true,
  "data": {
    "answer": "امیرالمؤمنین (ع) در خطبه ۲۱۶ بزرگ‌ترین حقوق واجب را حق متقابل حاکم و شهروندان می‌دانند...",
    "citations": [
      {
        "volume": 1,
        "page": 333,
        "chapter": "خطبه ۲۱۶",
        "quote": "فَقَدْ جَعَلَ اللَّهُ سُبْحَانَهُ لِي عَلَيْكُمْ حَقّاً بِوِلَايَةِ أَمْرِكُمْ..."
      }
    ]
  }
}
```

---

#### ۳.۱۱. ابزارهای تحلیلی هوش مصنوعی فصل کتاب (Chapter Analysis Tools)
- **متد و آدرس:** `POST /v1/library/ai/analyze`
- **بدنه درخواست:**
```json
{
  "bookId": "book_nahj",
  "chapterId": "ch_nahj_01",
  "analysisType": "SUMMARY"
}
```
> **انواع مجاز `analysisType`:**
> 1. `SUMMARY`: خلاصه فشرده محتوای فصل
> 2. `EXPLAIN_TERMS`: تشریح واژگان و اصطلاحات کلیدی
> 3. `CROSS_REFERENCES`: ارتباطات و ارجاعات متقاطع با سایر فصول و منابع
> 4. `PRACTICAL_LESSONS`: درس‌های کاربردی و سبک زندگی
> 5. `REFLECTIVE_QUIZ`: پرسش‌های تأمل‌برانگیز و کوییز معارفی

---

#### ۳.۱۲. کاوش معنایی برداری در متون کتب (Semantic Search)
- **متد و آدرس:** `POST /v1/library/ai/semantic-search`
- **بدنه درخواست:**
```json
{
  "query": "عدالت اجتماعی و تقسیم بیت‌المال",
  "limit": 5
}
```

---

#### ۳.۱۳. ورود سلسله‌مراتبی کتاب و فصول در دیتابیس رابطه‌ای و پایگاه برداری (Hierarchical Ingestion)
- **متد و آدرس:** `POST /v1/library/ingest-json`
- **توضیحات:** این متد ساختار سلسله‌مراتبی کتاب (شامل فصول، زیرفصل‌ها، بندها، مذهب و موضوعات) را به صورت خودکار در جداول SQL و کالکشن وکتوری Qdrant ذخیره و ایندکس می‌کند.
- **نمونه بدنه درخواست (JSON):**
```json
{
  "bookId": "bk_shafii_alumm",
  "title": "کتاب الأم",
  "author": "محمد بن إدریس الشافعی",
  "madhhab": "شافعی",
  "category": "فقه و احکام",
  "sections": [
    {
      "sectionId": "sec_taharah_01",
      "majorTopic": "کتاب الطهارة",
      "chapters": [
        {
          "chapterId": "ch_waters_01",
          "title": "باب المیاه و النجاسات",
          "subchapters": [
            {
              "subchapterId": "sub_najis_01",
              "title": "اقسام آب‌های نجس",
              "chunks": [
                {
                  "chunkId": "chk_water_001",
                  "textPersian": "آب کمتر از دو قله به مجرد برخورد نجاست متنجس می‌گردد...",
                  "textArabic": "الماء اذا کان دون القلتین تنجس...",
                  "topics": ["طهارت", "آب نجس", "قلتین"]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```
- **خروجی:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "bookId": "bk_shafii_alumm",
    "title": "کتاب الأم",
    "madhhab": "شافعی",
    "totalChapters": 1,
    "totalChunksIndexed": 1
  }
}
```

---

### بخش ۴: سرویس قرآن کریم و بسته پژوهشی تدبر (`/v1/quran`)

#### ۴.۱. آیه روز
- **متد و آدرس:** `GET /v1/quran/daily-verse`
- **خروجی:** اطلاعات آیه، ترجمه فارسی، سوره، جزء، صفحه، و تم مفهومی روز (`theme`).

---

#### ۴.۲. فهرست ۱۱۴ سوره قرآن کریم
- **متد و آدرس:** `GET /v1/quran/surahs`
- **پارامترهای کوئری:**
  - `q`: جستجو در نام عربی یا فارسی یا پینگلیش
  - `revelationType`: `MAKKI` یا `MADANI`
  - `juz`: فیلتر جزء (۱ تا ۳۰)
  - `sort`: `MUSHAF`, `REVELATION`, `AYAH_COUNT_DESC`, `AYAH_COUNT_ASC`

---

#### ۴.۳. شناسنامه یک سوره
- **متد و آدرس:** `GET /v1/quran/surahs/{surahId}` (مثلاً `/v1/quran/surahs/49`)

---

#### ۴.۴. متن آیات سوره به همراه ترجمه‌ها
- **متد و آدرس:** `GET /v1/quran/surahs/{surahId}/ayahs`
- **پارامترهای کوئری:**
  - `translation`: `ansarian` (انصاریان), `makarem` (مکارم), `fooladvand` (فولادوند)
  - `page`: شماره صفحه صفحه‌بندی اختیاری
  - `limit`: تعداد آیه در صفحه

---

#### ۴.۵. آیات منطبق بر ۶۰۴ صفحه استاندارد مصحف عثمان طه
- **متد و آدرس:** `GET /v1/quran/mushaf/pages/{pageNumber}` (مثلاً صفحه ۵۱۶)
- **خروجی:** شماره جزء، حزب، و آرایه آیات دقیق صفحه با وضعیت `isBookmarked`.

---

#### ۴.۶. بسته جامع تدبر و پژوهش آیه (Tadabbur Tools)
- **متد و آدرس:** `GET /v1/quran/ayahs/{surahId}/{ayahNumber}/tools` (مثلاً `/v1/quran/ayahs/49/10/tools`)
- **خروجی شامل:**
  - `translations`: ترجمه‌های تطبیقی (انصاریان، مکارم، فولادوند)
  - `briefTafsir`: تفسیر فشرده و المیزان/نمونه
  - `keywords`: ریشه‌شناسی و ترجمه واژگان آیه
  - `aiTadabbur`: آرایه ۳ نکته تدبری تحلیلی هوشمند
  - `reflectionQuestion`: پرسش تامل‌برانگیز شخصی
  - `relatedAyahs`: آیات مرتبط و موضوعی

---

#### ۴.۷. فهرست قاریان معتبر
- **متد و آدرس:** `GET /v1/quran/audio/reciters`
- **قاریان موجود:**
  - `parhizgar` (استاد شهریار پرهیزگار - ترتیل آموزشی)
  - `abdulbasit` (استاد عبدالباسط عبدالصمد - تحقیق و مجود)
  - `menshawi` (استاد محمد صدیق منشاوی - ترتیل حزین)
  - `hussary` (استاد محمود خلیل الحصری - ترتیل متقن)

---

#### ۴.۸. صوت سوره و زمان‌بندی همزمان آیه به آیه (Audio Segments)
- **متد و آدرس:** `GET /v1/quran/audio/surahs/{surahId}?reciterId=parhizgar`
- **خروجی:** لینک استریم صوت و آرایه `segments`:
```json
{
  "surahId": 49,
  "reciterId": "parhizgar",
  "audioUrl": "https://cdn.ettehad.app/audio/quran/parhizgar/049.mp3",
  "durationMs": 482000,
  "segments": [
    {
      "ayahNumber": 1,
      "startMs": 0,
      "endMs": 14200
    },
    {
      "ayahNumber": 2,
      "startMs": 14201,
      "endMs": 28500
    }
  ]
}
```
*(فرانت‌اند با این اطلاعات، آیه در حال پخش را به صورت خودکار هایلایت می‌کند).*

---

#### ۴.۹. بوک‌مارک و سنک مطالعه قرآن
- **لیست نشان‌های کاربر:** `GET /v1/quran/user/bookmarks`
- **تغییر نشان آیه (Bookmark Toggle):** `POST /v1/quran/user/bookmarks`
  - بدنه: `{"surahId": 49, "ayahNumber": 10}`
- **همگام‌سازی آخرین آیه خوانده شده:** `PUT /v1/quran/user/last-read`
  - بدنه: `{"surahId": 49, "ayahNumber": 10, "pageNumber": 516, "timestamp": 1741350000}`

---

#### ۴.۱۰. موتور جستجوی قرآن کریم
- **متد و آدرس:** `GET /v1/quran/search`
- **پارامترهای کوئری:**
  - `q`: کلیدواژه جستجو (عربی، فارسی، یا ریشه)
  - `scope`: قلمرو جستجو (`ALL`, `TEXT_ARABIC`, `TRANSLATION`, `ROOT`)
  - `juz`: محدودسازی به جزء دلخواه (اختیاری)

---

### بخش ۵: دستیار هوشمند معارفی و گفتگوی AI (`/v1/ai`)

#### ۵.۱. لیست جلسات گفتگوی کاربر
- **متد و آدرس:** `GET /v1/ai/conversations`
- **احراز هویت:** دارد (`Bearer <token>`)

---

#### ۵.۲. ایجاد جلسه گفتگوی جدید
- **متد و آدرس:** `POST /v1/ai/conversations`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست:**
```json
{
  "title": "پرسش درباره احکام خمس سهام",
  "initialQuery": "آیا به سود نقدی سهام در پایان سال مالی خمس تعلق می‌گیرد؟"
}
```
- **خروجی:** `{"conversationId": "ai_conv_91a2...", "createdAt": 1741350000}`

---

#### ۵.۳. تاریخچه پیام‌های یک گفتگو
- **متد و آدرس:** `GET /v1/ai/conversations/{conversationId}/messages`
- **احراز هویت:** دارد (`Bearer <token>`)

---

#### ۵.۴. حذف یک جلسه گفتگو
- **متد و آدرس:** `DELETE /v1/ai/conversations/{conversationId}`
- **احراز هویت:** دارد (`Bearer <token>`)

---

#### ۵.۵. ارسال پیام عادی (پاسخ یکجا JSON همراه استنادات)
- **متد و آدرس:** `POST /v1/ai/conversations/{conversationId}/messages`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست:**
```json
{
  "content": "سلام، لطفاً برادری ایمانی در قرآن را با آیه مستند توضیح دهید.",
  "overridePersona": {
    "tone": "FRIENDLY_WARM",
    "fiqhApproach": "APPROXIMATION_UNITY",
    "detailLevel": "STANDARD",
    "includeAyahAddress": true,
    "includeHadithReferences": true
  }
}
```
- **نمونه خروجی:**
```json
{
  "success": true,
  "data": {
    "messageId": "msg_ai_8a12",
    "conversationId": "ai_conv_91a2",
    "role": "ASSISTANT",
    "content": "خداوند متعال در قرآن کریم مؤمنان را برادر یکدیگر نامیده است [۱](source://quran/surah/49/ayah/10) و در روایات نیز بر آن تأکید شده است [۲](source://book/bk_102/chapter/ch_4)...\n\n📚 **منابع و مراجع مورد استناد:**\n• [۱] [قرآن کریم، سوره ۴۹، آیه ۱۰](source://quran/surah/49/ayah/10)",
    "sources": [
      {
        "index": 1,
        "type": "QURAN",
        "title": "قرآن کریم، سوره ۴۹، آیه ۱۰",
        "targetUrl": "source://quran/surah/49/ayah/10",
        "excerpt": "«إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ»",
        "pageNumber": 516
      },
      {
        "index": 2,
        "type": "BOOK",
        "title": "کتاب الأم (باب المیاه)",
        "targetUrl": "source://book/bk_shafii_01/chapter/ch_1",
        "excerpt": "آب کمتر از دو قله به مجرد برخورد نجاست متنجس می‌گردد...",
        "madhhab": "شافعی"
      }
    ],
    "suggestScholarEscalation": false,
    "escalationCategory": "احکام شرعی و فقهی",
    "referencedAyahs": [
      {
        "surahId": 49,
        "ayahNumber": 10,
        "text": "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ"
      }
    ],
    "referencedHadiths": [
      {
        "source": "اصول کافی، ج ۲، ص ۱۶۶",
        "text": "المُؤمِنُ أخُو المُؤمِنِ، عَيْنُهُ و دَلِيلُهُ"
      }
    ],
    "tokenUsage": {
      "promptTokens": 145,
      "outputTokens": 320,
      "cachedTokens": 0,
      "totalTokens": 465,
      "costUsd": 0.0001068,
      "costIrr": 101.46,
      "currency": "IRR"
    },
    "timestamp": 1741350020,
    "isLiked": null
  }
}
```
> **نکته کلیدی برای فرانت‌اند:**
> ۱. در فیلد `content`، رفرنس‌ها به صورت لینک‌های مارک‌داون `[۱](source://...)` قرار دارند که با لمس کاربر باید او را مستقیماً به صفحه آیه یا فصل کتاب منتقل کنند.
> ۲. فیلد `tokenUsage` شامل تعداد توکن ورودی (`promptTokens`)، خروجی (`outputTokens`)، کش (`cachedTokens`) و هزینه محاسبه‌شده به دلار (`costUsd`) و ریال (`costIrr`) بر اساس نرخ روز دلار است.
> ۳. اگر `suggestScholarEscalation: true` باشد، یعنی در منابع کتب پاسخ قطعی یافت نشده و یک کارت با دکمه تعاملی **«ارسال این پرسش به عالم دینی»** به کاربر نمایش داده می‌شود.

---

#### ۵.۶. استریم زنده مراحل کار ایجنت و پاسخ متنی (Server-Sent Events - SSE)
- **متد و آدرس:** `POST /v1/ai/conversations/{conversationId}/stream`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست:** همانند اندپوینت قبلی (`{"content": "..."}`)
- **نوع پاسخ (Content-Type):** `text/event-stream`
- **قالب رویدادها (SSE Events):**
```text
data: {"type": "status", "stage": "ROUTING", "message": "🔍 در حال تشخیص حوزه موضوعی، مذهب و استخراج زوایای مختلف سوال..."}

data: {"type": "status", "stage": "SEARCHING", "message": "🔍 جستجو در منابع درختی و کتابخانه (تلاش ۱ از ۲)..."}

data: {"type": "status", "stage": "EVALUATING", "message": "⚖️ ارزیابی کیفیت و کفایت فقهی/معارفی منابع با مدل تصمیم‌گیر Jev..."}

data: {"type": "sources", "sources": [...], "suggestScholarEscalation": false, "escalationCategory": "احکام شرعی و فقهی"}

data: {"type": "chunk", "chunk": "سلام و درود "}

data: {"type": "chunk", "chunk": "بر شما همراه گرامی! "}

data: {"type": "usage", "usage": {"promptTokens": 145, "outputTokens": 320, "cachedTokens": 0, "totalTokens": 465, "costUsd": 0.0001068, "costIrr": 101.46, "currency": "IRR"}}

data: {"done": true, "messageId": "msg_ai_...", "suggestScholarEscalation": false, "tokenUsage": {...}}
```

---

#### ۵.۷. دریافت و به‌روزرسانی پرسونای دینی و هویت ربات
- **دریافت تنظیمات فعلی:** `GET /v1/ai/persona`
- **به‌روزرسانی تنظیمات:** `PUT /v1/ai/persona`
- **فیلدهای پرسونای هوش مصنوعی:**
  - `botName`: نام نمایشی دستیار (پیش‌فرض: `دستیار معارفی اتحاد`، قابل تغییر توسط کاربر مثلاً «یار تدبر»، «مشاور امین»)
  - `botRolePreset`: قالب نقش آماده ربات (`TAFSIR_RESEARCHER`, `ETHICS_MENTOR`, `FIQH_ADVISOR`, `FAMILY_LIFESTYLE`, `GENERAL_ASSISTANT`, `CUSTOM`)
  - `botAvatar`: آدرس آیکون یا تصویر دستیار (اختیاری)
  - `tone`: لحن پاسخگویی (`FRIENDLY_WARM` صمیمی و همدلانه, `SCHOLARLY_FORMAL` علمی و حوزوی, `CONCISE_FAST` کوتاه و خلاصه, `POETIC_SPIRITUAL` لطیف و عرفانی)
  - `fiqhApproach`: رویکرد مذهبی (`APPROXIMATION_UNITY` تقریب مذاهب و وحدت، `COMPARATIVE` مقایسه‌ای تطبیقی، `SHIA_JA'FARI` فقه امامیه، `SUNNI_HANAFI` فقه حنفی، `SUNNI_SHAFI'I` فقه شافعی)
  - `detailLevel`: سطح تفصیل (`BRIEF`, `STANDARD`, `ACADEMIC_DEEP`)
  - `includeAyahAddress`: استناد به نشانی آیه و سوره (`true`/`false`)
  - `includeHadithReferences`: ذکر منبع روایی (`true`/`false`)
  - `customPromptInstructions`: دستورالعمل سفارشی کاربر برای AI

---

#### ۵.۸. دریافت فهرست قالب‌های نقشی آماده ربات (Persona Presets)
- **متد و آدرس:** `GET /v1/ai/persona/presets`
- **احراز هویت:** اختیاری / عمومی
- **خروجی:** لیست کامل نقش‌های آماده ربات شامل کلید، عنوان، توضیحات، لحن پیش‌فرض و آواتار.

---

#### ۵.۹. پیشنهادهای هوشمند پرامپت معارفی برای شروع گفتگو (متناسب با علایق)
- **متد و آدرس:** `GET /v1/ai/prompt-suggestions`
- **احراز هویت:** اختیاری (در صورت ارسال توکن `Bearer <token>`، پیشنهادها بر اساس علایق موضوعی کاربر در تگ‌های `interests` شخصی‌سازی و اولویت‌بندی می‌شوند).
- **خروجی:** لیست کارت‌های پیشنهادی گفتگو با عنوان، پرامپت کامل و آیکون.

---

#### ۵.۹. ثبت امتیاز و بازخورد (Like/Dislike) برای پیام AI
- **متد و آدرس:** `POST /v1/ai/messages/{messageId}/rating`
- **احراز هویت:** دارد (`Bearer <token>`)
- **بدنه درخواست:**
```json
{
  "isLiked": true,
  "feedbackText": "پاسخ بسیار مستند و آرامش‌بخش بود."
}
```

---

#### ۵.۱۰. مدیریت هزینه‌ها، تعرفه مدل‌ها و نرخ ارز (Token Pricing & Usage Analytics)

##### ۵.۱۰.۱. دریافت تنظیمات تعرفه توکن‌ها و نرخ دلار به ریال
- **متد و آدرس:** `GET /v1/ai/cost-config`
- **خروجی:**
```json
{
  "success": true,
  "data": {
    "usdToIrrRate": 950000.0,
    "currencyName": "IRR",
    "modelsPricing": [
      {
        "modelName": "gemini-1.5-flash",
        "inputCostPerMillionUsd": 0.075,
        "outputCostPerMillionUsd": 0.30,
        "cachedCostPerMillionUsd": 0.01875,
        "isActive": true
      }
    ]
  }
}
```

##### ۵.۱۰.۲. به‌روزرسانی نرخ دلار به ریال و تعرفه توکن‌ها (پنل ادمین)
- **متد و آدرس:** `PUT /v1/ai/cost-config`
- **بدنه درخواست:**
```json
{
  "usdToIrrRate": 1000000.0,
  "currencyName": "IRR",
  "modelsPricing": [
    {
      "modelName": "gemini-1.5-flash",
      "inputCostPerMillionUsd": 0.075,
      "outputCostPerMillionUsd": 0.30,
      "cachedCostPerMillionUsd": 0.01875,
      "isActive": true
    }
  ]
}
```

##### ۵.۱۰.۳. گزارش کلی مصرف توکن‌ها و هزینه‌ها به دلار و ریال
- **متد و آدرس:** `GET /v1/ai/usage-stats`
- **خروجی:**
```json
{
  "success": true,
  "data": {
    "totalRequests": 142,
    "totalPromptTokens": 85400,
    "totalOutputTokens": 124300,
    "totalCachedTokens": 18200,
    "totalTokens": 227900,
    "totalCostUsd": 0.04398,
    "totalCostIrr": 41781.0,
    "usdToIrrRate": 950000.0,
    "recentLogs": [
      {
        "id": "usg_48a912bc01",
        "modelName": "gemini-1.5-flash",
        "conversationId": "conv_91a2",
        "promptTokens": 120,
        "outputTokens": 340,
        "cachedTokens": 0,
        "totalTokens": 460,
        "costUsd": 0.000111,
        "costIrr": 105.45,
        "timestamp": 1741350020000
      }
    ]
  }
}
```

##### ۵.۱۰.۴. گزارش مصرف توکن و هزینه یک گفتگوی خاص
- **متد و آدرس:** `GET /v1/ai/conversations/{conversationId}/usage`
- **خروجی:** همانند فرمت گزارش کلی، با فیلتر روی همان گفتگو.

---

#### ۵.۱۱. مدیریت و تفکیک مدل‌ها و Base URL تمام بخش‌ها (Per-Section Models & Base URLs)

تمامی بخش‌های هوش مصنوعی سیستم دارای امکان تفکیک کامل مدل (Model Name)، آدرس پایه سرویس (Base URL / Proxy)، کلید دسترسی (API Key) و نوع ارائه‌دهنده (Gemini یا OpenAI-compatible) هستند.

بخش‌های تفکیک‌شده در سامانه:
1. `chat`: گفتگوی هوشمند معارفی و استریم پاسخ
2. `embedding`: تولید بردارهای ۷۶۸ بعدی جهت جستجوی معنایی و پایگاه داده کیودرانت (Qdrant)
3. `agentic_rag`: موتور عامل هوشمند RAG، استخراج قصد کاربر و بسط چندگانه کوئری
4. `jev`: موتور تصمیم‌گیری سریع سامانه یک JEV و ارزیابی کفایت شواهد
5. `library`: چت تخصصی با متن کتب اسلامی و تحلیل عمیق فصول
6. `quran`: تدبر و تحلیل هوشمند آیات قرآنی
7. `consultation`: دستیار هوشمند مشاوران و پیشنهاد پیش‌نویس پاسخ

##### ۵.۱۱.۱. دریافت تنظیمات مدل و Base URL تمام بخش‌ها
- **متد و آدرس:** `GET /v1/ai/models-config`
- **نمونه خروجی:**
```json
{
  "success": true,
  "data": [
    {
      "sectionKey": "chat",
      "sectionNameFa": "گفتگوی هوشمند معارفی (AI Chat)",
      "descriptionFa": "پاسخ به سوالات معارفی، احکام و استنادات قرآنی/روایی و استریم زنده پاسخ",
      "modelName": "gemini-1.5-flash",
      "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
      "apiKeyMasked": "AIza...9876",
      "hasCustomApiKey": true,
      "provider": "gemini",
      "isActive": true,
      "extraParams": {
        "temperature": 0.7,
        "maxTokens": 2048
      },
      "updatedAt": 1741350020000
    },
    {
      "sectionKey": "embedding",
      "sectionNameFa": "تعبیه برداری و جستجوی معنایی (Vector Embeddings)",
      "descriptionFa": "تولید بردار ۷۶۸ بعدی جهت جستجوی معنایی و پایگاه داده کیودرانت (Qdrant)",
      "modelName": "text-embedding-004",
      "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
      "apiKeyMasked": null,
      "hasCustomApiKey": false,
      "provider": "gemini",
      "isActive": true
    }
  ]
}
```

##### ۵.۱۱.۲. به‌روزرسانی مدل و Base URL یک بخش خاص
- **متد و آدرس:** `PUT /v1/ai/models-config/{section}`
- **بادی درخواست نمونه:**
```json
{
  "modelName": "gpt-4o-mini",
  "baseUrl": "https://api.openai.com/v1",
  "apiKey": "sk-proj-...",
  "provider": "openai_compatible",
  "isActive": true,
  "extraParams": {
    "temperature": 0.4
  }
}
```

##### ۵.۱۱.۳. به‌روزرسانی گروهی بخش‌ها
- **متد و آدرس:** `PUT /v1/ai/models-config`
- **بادی درخواست نمونه:**
```json
{
  "sections": [
    {
      "sectionKey": "chat",
      "modelName": "gemini-2.0-flash",
      "baseUrl": "https://generativelanguage.googleapis.com/v1beta"
    },
    {
      "sectionKey": "embedding",
      "modelName": "text-embedding-3-small",
      "baseUrl": "https://api.openai.com/v1",
      "provider": "openai_compatible"
    }
  ]
}
```

##### ۵.۱۱.۴. تست اتصال و سنجش زمان تاخیر مدل و Base URL
- **متد و آدرس:** `POST /v1/ai/models-config/{section}/test`
- **بادی درخواست (اختیاری):**
```json
{
  "modelName": "gemini-1.5-flash",
  "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
  "testPrompt": "بررسی اتصال"
}
```
- **نمونه خروجی:**
```json
{
  "success": true,
  "data": {
    "sectionKey": "chat",
    "modelName": "gemini-1.5-flash",
    "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
    "provider": "gemini",
    "success": true,
    "message": "ارتباط با مدل با موفقیت برقرار شد و پاسخ دریافت گردید.",
    "latencyMs": 312.45,
    "sampleResponse": "سلام"
  }
}
```

##### ۵.۱۱.۵. تعیین مدل اختصاصی در هر درخواست چت (Per-Request Model Override)
در زمان ارسال پیام به هوش مصنوعی (`POST /v1/ai/conversations/{id}/messages` یا استریم)، کلاینت می‌تواند مدل دلخواه خود را در فیلد `model` تعیین کند:
```json
{
  "content": "حکم خمس سرمایه‌گذاری چیست؟",
  "model": "gemini-1.5-pro"
}
```
هزینه و توکن مصرفی بر اساس مدل انتخابی کاربر محاسبه و در فاکتور مصرفی ذخیره می‌شود.

##### ۵.۱۱.۶. پیشنهاد پیش‌نویس پاسخ مشاوره توسط هوش مصنوعی
- **متد و آدرس:** `POST /v1/consultation/threads/{threadId}/ai-draft`
- **هدر:** `Authorization: Bearer <token>`
- **خروجی:** متن پیش‌نویس پاسخ فقهی و مستند تولیدشده بر اساس مدل بخش `consultation`.

---

### بخش ۶: وب‌سوکت بلادرنگ (Real-Time WebSocket)

- **آدرس اتصال:** `wss://api.unitysi.ir/v1/ws?token=<JWT_TOKEN>`
- در هنگام اتصال اولیه، توکن اعتبارسنجی می‌شود؛ اگر نامعتبر یا منقضی باشد، وب‌سوکت با کد `4001` بسته می‌شود.

#### ساختار پیام‌های ارسالی از کلاینت به وب‌سوکت:
1. **عضویت در کانال یک گفتگو:**
```json
{
  "action": "subscribe",
  "channel": "consultation:th_10928374"
}
```
یا برای چت هوش مصنوعی:
```json
{
  "action": "subscribe",
  "channel": "ai:ai_conv_91a2"
}
```
*(سرور در پاسخ پیام `{"event": "SUBSCRIBED", "channel": "..."}` ارسال می‌کند).*

2. **لغو عضویت در کانال:**
```json
{
  "action": "unsubscribe",
  "channel": "consultation:th_10928374"
}
```

3. **ارسال پینگ (Keep-Alive Ping):**
```json
{
  "action": "ping"
}
```
*(سرور در پاسخ `{"event": "PONG"}` می‌دهد).*

#### ساختار پیام‌های دریافتی از سرور (Push Events):
هنگامی که پیام جدیدی در ترید ثبت شود یا عالم پاسخ دهد، سرور پیامی با این قالب پخش می‌کند:
```json
{
  "event": "NEW_MESSAGE",
  "channel": "consultation:th_10928374",
  "data": {
    "messageId": "msg_8921",
    "senderRole": "SCHOLAR",
    "text": "پاسخ جدید عالم...",
    "citation": "...",
    "createdAt": "2026-03-07T14:22:00Z"
  }
}
```

---

### بخش ۷: روت‌های سلامت سیستم (System Health)

- **اطلاعات سرویس:** `GET https://api.unitysi.ir/`
- **هلث‌چک:** `GET https://api.unitysi.ir/health`

---

## ۶. الگوهای کلاینت تایپ‌اسکریپت و Axios برای توسعه‌دهنده فرانت

جهت تسهیل کدنویسی فرانت‌اند، این اینترفیس‌ها و اینستنس نمونه را می‌توانید مستقیماً در پروژه فرانت استفاده فرمایید:

```typescript
// types/api.ts
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
  timestamp: string;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
}

// services/apiClient.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: 'https://api.unitysi.ir/v1',
  headers: {
    'Content-Type': 'application/json',
    'Accept-Language': 'fa-IR',
    'X-App-Version': '1.0.0',
    'X-Device-Id': 'client-device-unique-id'
  }
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response.data, // مستقیماً آبجکت پاکت استاندارد برگشت داده می‌شود
  (error) => {
    if (error.response?.status === 401) {
      // توکن منقضی شده؛ هدایت به لاگین
      localStorage.removeItem('access_token');
    }
    return Promise.reject(error.response?.data?.error || error);
  }
);
```
