import os
import sys
import json
import requests

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://api.unitysi.ir"

def verify():
    s = requests.Session()
    s.trust_env = False

    # 1. Login
    login_r = s.post(f"{BASE_URL}/v1/auth/login", json={"phone_number": "09120000000", "password": "123456"}, timeout=15)
    token = login_r.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get All Books
    r = s.get(f"{BASE_URL}/v1/library/books", timeout=15)
    books = r.json().get("data", [])
    print(f"==================================================================")
    print(f"📚 مجموع کتب ثبت‌شده در کتابخانه آنلاین: {len(books)}")
    print(f"==================================================================")

    for idx, b in enumerate(books, 1):
        b_id = b["id"]
        title = b["title"]
        madhhab = b.get("madhhab", "نامشخص")
        cat = b.get("category", "")
        # Get chunk count
        chk_r = s.get(f"{BASE_URL}/v1/admin/library/chunks?bookId={b_id}&limit=100", headers=headers, timeout=15)
        chunks = chk_r.json().get("data", [])
        chunk_count = len(chunks) if isinstance(chunks, list) else len(chunks.get("items", []))
        print(f"{idx:02d}. [{b_id}] «{title}» | مذهب: {madhhab} | دسته‌بندی: {cat} | چانک‌ها: {chunk_count}")

    # 3. Test Semantic Search Query
    print("\n" + "=" * 66)
    print("🔍 آزمایش جستجوی معنایی و بازیابی وکتوری از سرور")
    print("=" * 66)
    test_queries = [
        "حکم نماز مسافر و شروط قصر",
        "ارکان و مبانی اسلام و حدیث جبرئیل",
        "فضیلت قرائت و تلاوت قرآن کریم"
    ]
    for q in test_queries:
        search_r = s.post(f"{BASE_URL}/v1/library/ai/semantic-search", json={"query": q, "limit": 3}, headers=headers, timeout=25)
        if search_r.status_code == 200:
            res = search_r.json().get("data", [])
            print(f"\nپرسش: «{q}» -> {len(res)} نتیجه یافت شد:")
            for item in res[:2]:
                title = item.get("book_title") or item.get("title") or "منبع معارفی"
                snippet = (item.get("text") or item.get("snippet") or "")[:90].replace("\n", " ")
                print(f"   • کتاب: {title} | امتیاز: {item.get('score', 'N/A')} | متن: {snippet}...")
        else:
            print(f"کوئری «{q}»: کد {search_r.status_code}")

if __name__ == "__main__":
    verify()
