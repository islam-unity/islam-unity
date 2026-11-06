# راهنمای جامع پلتفرم توسعه‌دهندگان (Ettehad Developer Platform API)

پلتفرم توسعه‌دهندگان سامانه «اتحاد» به برنامه‌نویسان و تیم‌های توسعه پروژه‌های اسلامی و معارفی این امکان را می‌دهد تا به سادگی و از طریق یک کلید API اختصاصی (`X-API-Key`)، از توانمندی‌های پیشرفته **هوش مصنوعی معارفی (RAG قرآنی و روایی)** و **مخزن دیجیتال کتب اسلامی** در اپلیکیشن‌ها، بات‌ها و وب‌سایت‌های مستقل خود استفاده نمایند.

---

## ۱. راهنمای شروع سریع (Quick Start)

### مرحله ۱: دریافت کلید API
اگر حساب کاربری دارید، با ارسال درخواست زیر کلید API اختصاصی خود را دریافت کنید:

```http
POST /v1/developer/keys
Authorization: Bearer <YOUR_JWT_TOKEN>
Content-Type: application/json

{
  "label": "پروژه همراه نور - سرور اصلی"
}
```

پاسخ شامل کلید با پیشوند `ak_live_...` خواهد بود (این کلید تنها یک‌بار به شما نمایش داده می‌شود؛ آن را ذخیره فرمایید).

### مرحله ۲: فراخوانی هوش مصنوعی
کلید خود را در هدر `X-API-Key` قرار داده و اولین درخواست را ارسال کنید:

```bash
curl -X POST "https://api.ettehad-islamic.org/v1/developer/chat/completions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ak_live_your_secret_key_here" \
  -d '{
    "model": "ettehad-islamic-v1",
    "messages": [
      {"role": "user", "content": "حکم شرعی روزه مسافر چیست؟"}
    ]
  }'
```

---

## ۲. مشخصات اندپوینت‌های هوش مصنوعی (AI Platform)

### ۲.۱. چت معارفی سازگار با استاندارد OpenAI
این اندپوینت کاملاً منطبق بر ساختار رسمی `/chat/completions` شرکت OpenAI است؛ به این معنی که می‌توانید مستقیماً از پکیج‌های رسمی `openai` در پایتون، جاوااسکریپت یا کلاینت‌های LangChain و LlamaIndex استفاده نمایید.

- **آدرس:** `POST /v1/developer/chat/completions`
- **احراز هویت:** هدر `X-API-Key`
- **استریمینگ:** بله (`"stream": true` با فرمت استاندارد SSE)
- **پارامترهای تنظیمی در `extra_params`:**
  - `madhab`: مذهب فقهی (`jafari`, `hanafi`, `shafii`, `maliki`, `hanbali`, `taqrib`)
  - `tone`: لحن پاسخ (`youth` [صمیمی جوانان], `academic` [علمی-حوزوی], `general` [عمومی])

#### بدنه نمونه درخواست:
```json
{
  "model": "ettehad-islamic-v1",
  "messages": [
    {"role": "system", "content": "پاسخ‌ها را مختصر و مستند بیان کن."},
    {"role": "user", "content": "فضیلت صلوات بر پیامبر (ص) در روایات فریقین"}
  ],
  "extra_params": {
    "madhab": "taqrib",
    "tone": "general"
  }
}
```

---

### ۲.۲. استعلام تخصصی فقهی و قرآنی (`/v1/developer/ai/ask`)
اندپوینت اختصاصی با ساختار پاسخ‌دهی غنی، شامل استنادات دقیق به آیات و احادیث و تفکیک ارجاعات.

- **آدرس:** `POST /v1/developer/ai/ask`
- **بدنه درخواست:**
```json
{
  "query": "تفسیر آیه ۳۵ سوره نور",
  "madhab": "taqrib",
  "tone": "academic",
  "source_filter": ["quran", "tafsir"]
}
```

- **پاسخ نمونه:**
```json
{
  "success": true,
  "data": {
    "answer": "الله نور السماوات و الارض؛ مفسران در تفسیر این تمثیل نورانی بیان کرده‌اند...",
    "citations": [
      {
        "type": "QURAN",
        "title": "سوره النور - آیه ۳۵",
        "pageNumber": 354,
        "index": 35
      }
    ],
    "referencedAyahs": [
      {"surahId": 24, "ayahNumber": 35, "text": "اللَّهُ نُورُ السَّمَاوَاتِ وَالْأَرْضِ..."}
    ],
    "referencedHadiths": [],
    "modelUsed": "gemini-2.5-flash",
    "usage": {
      "prompt_tokens": 142,
      "completion_tokens": 280,
      "total_tokens": 422
    }
  }
}
```

---

### ۲.۳. بازیابی برداری و قطعات اسنادی (`/v1/developer/ai/rag-search`)
کاوش معنایی برداری در پایگاه دانش کتب و استخراج مستقیم پاراگراف‌های مرتبط.

- **آدرس:** `POST /v1/developer/ai/rag-search`
- **بدنه درخواست:**
```json
{
  "query": "عوامل افزایش برکت در زندگی",
  "limit": 5,
  "min_relevance_score": 0.6
}
```

---

## ۳. مشخصات اندپوینت‌های کتابخانه (Library Platform)

تمامی اندپوینت‌های کتابخانه به صورت Read-Only و بهینه‌سازی‌شده برای پاسخ‌دهی سریع طراحی شده‌اند.

### ۳.۱. دریافت فهرست و کاتالوگ کتب
- **آدرس:** `GET /v1/developer/library/books`
- **پارامترهای اختیاری:** `q` (جستجو در عنوان و نویسنده)، `categoryId` (فیلتر موضوعی)، `page` و `limit`.

### ۳.۲. شناسنامه کتاب و ساختار فصول (TOC)
- **آدرس:** `GET /v1/developer/library/books/{book_id}`
- **خروجی:** اطلاعات نشر، زبان، تعداد جلد، و فهرست کامل فصول.

### ۳.۳. دریافت متن کامل یک فصل
- **آدرس:** `GET /v1/developer/library/books/{book_id}/chapters/{chapter_id}`
- **خروجی:** متن کامل فصل، پاراگراف‌ها، و زمان تخمینی مطالعه.

### ۳.۴. جستجوی پرسرعت هیبریدی در متون کتب (`/v1/developer/library/search`)
- **آدرس:** `POST /v1/developer/library/search`
- **بدنه درخواست:**
```json
{
  "query": "شروط توبه نصوح",
  "search_mode": "hybrid",
  "limit": 10
}
```

### ۳.۵. گفتگوی هوشمند بر مبنای محتوای یک کتاب (`/v1/developer/library/books/{book_id}/chat`)
- **آدرس:** `POST /v1/developer/library/books/{book_id}/chat`
- **بدنه درخواست:**
```json
{
  "query": "دیدگاه نویسنده در فصل دوم درباره جبر و اختیار چیست؟"
}
```

---

## ۴. نمونه کدهای آماده (Ready-to-Use SDKs & Examples)

### ۴.۱. پایتون با کتابخانه رسمی OpenAI
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.ettehad-islamic.org/v1/developer",
    api_key="ak_live_your_api_key_here"
)

# فراخوانی ساده
response = client.chat.completions.create(
    model="ettehad-islamic-v1",
    messages=[
        {"role": "user", "content": "معیار تمییز روایات متواتر از واحد چیست؟"}
    ]
)

print(response.choices[0].message.content)
```

---

### ۴.۲. پایتون با قابلیت استریم زنده (Streaming SSE)
```python
import httpx
import json

async def stream_chat():
    url = "https://api.ettehad-islamic.org/v1/developer/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "ak_live_your_api_key_here"
    }
    payload = {
        "model": "ettehad-islamic-v1",
        "messages": [{"role": "user", "content": "آداب و احکام صله رحم را توضیح دهید."}],
        "stream": True
    }

    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        print(content, end="", flush=True)
                    except json.JSONDecodeError:
                        pass

# اجرا: asyncio.run(stream_chat())
```

---

### ۴.۳. جاوااسکریپت / تایپ‌اسکریپت (Node.js & Frontend)
```typescript
import fetch from "node-fetch";

async function askIslamicQuestion(query: string) {
  const response = await fetch("https://api.ettehad-islamic.org/v1/developer/ai/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": "ak_live_your_api_key_here"
    },
    body: JSON.stringify({
      query: query,
      madhab: "taqrib",
      tone: "general"
    })
  });

  const res = await response.json();
  if (res.success) {
    console.log("پاسخ:", res.data.answer);
    console.log("استنادات قرآنی:", res.data.referencedAyahs);
  } else {
    console.error("خطا:", res.error.message);
  }
}

askIslamicQuestion("آثار انفاق پنهانی در روایات");
```

---

### ۴.۴. فلاتر / دارت (Flutter & Dart Client)
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class EttehadApiClient {
  final String apiKey;
  final String baseUrl = "https://api.ettehad-islamic.org/v1/developer";

  EttehadApiClient({required this.apiKey});

  /// جستجو در محتوای کتب اسلامی
  Future<List<dynamic>> searchBooks(String query) async {
    final response = await http.post(
      Uri.parse('$baseUrl/library/search'),
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: jsonEncode({
        'query': query,
        'search_mode': 'hybrid',
        'limit': 10,
      }),
    );

    if (response.statusCode == 200) {
      final json = jsonDecode(utf8.decode(response.bodyBytes));
      return json['data']['results'] as List<dynamic>;
    } else {
      throw Exception('خطای سرور: ${response.statusCode}');
    }
  }
}
```

---

## ۵. ماتریس کدهای خطا (Error Handling Matrix)

| کد خطا | وضعیت HTTP | شرح و راهنما |
| :--- | :--- | :--- |
| `API_KEY_INVALID` | 401 | هدر `X-API-Key` ارسال نشده، نامعتبر است یا کلید باطل شده است. |
| `RATE_LIMIT_EXCEEDED` | 429 | تعداد درخواست‌ها در بازه یک دقیقه‌ای بیش از سقف مجاز (پیش‌فرض ۶۰ درخواست در دقیقه) است. |
| `QUOTA_EXCEEDED` | 429 | سهمیه توکن ماهانه حساب توسعه‌دهنده به اتمام رسیده است (می‌توانید از طریق پنل آن را ارتقا دهید). |
| `BOOK_NOT_FOUND` | 404 | کتاب درخواستی در سامانه یافت نشد. |
| `VALIDATION_FAILED` | 400 | پارامترهای ارسالی در بدنه درخواست ناقص بوده یا ساختار صحیحی ندارند. |
