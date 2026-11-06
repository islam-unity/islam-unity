import os
import json
import shutil
import sqlite3
import urllib.request
from PIL import Image, ImageDraw

ROOT = r"d:\unity_V2"
FLUTTER_DIR = os.path.join(ROOT, "flutter_app")
ASSETS_DATA = os.path.join(FLUTTER_DIR, "assets", "data")
ASSETS_IMAGES = os.path.join(FLUTTER_DIR, "assets", "images")
ASSETS_FONTS = os.path.join(FLUTTER_DIR, "assets", "fonts")

os.makedirs(ASSETS_DATA, exist_ok=True)
os.makedirs(ASSETS_IMAGES, exist_ok=True)
os.makedirs(ASSETS_FONTS, exist_ok=True)

# 1. Copy complete Quran JSON
quran_src = os.path.join(ROOT, "mobile_app", "public", "data", "quran_complete.json")
if os.path.exists(quran_src):
    shutil.copy2(quran_src, os.path.join(ASSETS_DATA, "quran_complete.json"))
    print("Copied quran_complete.json")

# 2. Copy official Ettehad Logos
logo_kit = os.path.join(ROOT, "ettehad-logo-kit")
logos_to_copy = {
    "logo_symbol_color.png": os.path.join(logo_kit, "png", "ettehad-symbol-color-512.png"),
    "logo_symbol_white.png": os.path.join(logo_kit, "png", "ettehad-symbol-white-1024.png"),
    "logo_lockup.png": os.path.join(logo_kit, "png", "ettehad-lockup-stacked-color-1024.png"),
    "logo_horizontal.png": os.path.join(logo_kit, "png", "ettehad-lockup-horizontal-color-1600.png"),
    "app_icon.png": os.path.join(logo_kit, "store-icons", "ettehad-store-square-dark-1024.png"),
}
for dest_name, src_path in logos_to_copy.items():
    if os.path.exists(src_path):
        shutil.copy2(src_path, os.path.join(ASSETS_IMAGES, dest_name))
        print(f"Copied {dest_name}")

# 3. Export SQLite ettehad.db tables into structured offline JSON
db_path = os.path.join(ROOT, "ettehad.db")
offline_db = {
    "categories": [],
    "posters": [],
    "books": [],
    "chapters": [],
    "chunks": [],
    "shelves": [],
    "shelf_books": [],
    "scholars": [],
    "meetings": [],
    "threads": [],
    "messages": [],
    "posts": [],
    "ai_sections": [],
    "tadabbur": [],
    "reciters": [],
    "prayer_times": [],
    "dhikr_categories": [],
    "dhikrs": []
}

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("SQLite tables found:", tables)

    def fetch_all(table_name, limit=None):
        if table_name not in tables:
            return []
        q = f'SELECT * FROM "{table_name}"'
        if limit:
            q += f" LIMIT {limit}"
        rows = cur.execute(q).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for k, v in d.items():
                if isinstance(v, bytes):
                    d[k] = v.decode("utf-8", errors="ignore")
            result.append(d)
        return result

    offline_db["categories"] = fetch_all("library_categories")
    offline_db["posters"] = fetch_all("library_posters")
    offline_db["books"] = fetch_all("books")
    offline_db["chapters"] = fetch_all("book_chapters")
    offline_db["chunks"] = fetch_all("knowledge_chunks")
    offline_db["shelves"] = fetch_all("user_shelves")
    offline_db["shelf_books"] = fetch_all("shelf_books")
    offline_db["scholars"] = fetch_all("scholars")
    offline_db["meetings"] = fetch_all("scholar_meetings")
    offline_db["threads"] = fetch_all("consultation_threads")
    offline_db["messages"] = fetch_all("consultation_messages")
    offline_db["posts"] = fetch_all("posts")
    offline_db["ai_sections"] = fetch_all("ai_section_configs")
    offline_db["tadabbur"] = fetch_all("quran_ayah_tadabbur")
    offline_db["reciters"] = fetch_all("quran_reciters")
    offline_db["prayer_times"] = fetch_all("city_prayer_times")
    offline_db["dhikr_categories"] = fetch_all("dhikr_categories")
    offline_db["dhikrs"] = fetch_all("dhikrs")

    conn.close()

with open(os.path.join(ASSETS_DATA, "ettehad_offline_db.json"), "w", encoding="utf-8") as f:
    json.dump(offline_db, f, ensure_ascii=False, indent=2)
print("Saved ettehad_offline_db.json:", {k: len(v) for k, v in offline_db.items()})

# 4. Also copy the SQLite database directly so sqflite / offline inspection has full 17.5MB DB bundled!
if os.path.exists(db_path):
    shutil.copy2(db_path, os.path.join(ASSETS_DATA, "ettehad.db"))
    print("Bundled full ettehad.db (17.5 MB) into assets/data/ettehad.db")

# 5. Download Vazirmatn TTF fonts for offline Persian & Arabic typography
font_urls = {
    "Vazirmatn-Regular.ttf": "https://github.com/rastikerdar/vazirmatn/raw/master/fonts/ttf/Vazirmatn-Regular.ttf",
    "Vazirmatn-Medium.ttf": "https://github.com/rastikerdar/vazirmatn/raw/master/fonts/ttf/Vazirmatn-Medium.ttf",
    "Vazirmatn-Bold.ttf": "https://github.com/rastikerdar/vazirmatn/raw/master/fonts/ttf/Vazirmatn-Bold.ttf",
    "Vazirmatn-ExtraBold.ttf": "https://github.com/rastikerdar/vazirmatn/raw/master/fonts/ttf/Vazirmatn-ExtraBold.ttf",
}
for fname, url in font_urls.items():
    dest = os.path.join(ASSETS_FONTS, fname)
    if not os.path.exists(dest):
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"Downloaded font {fname}")
        except Exception as e:
            print(f"Could not download {fname}: {e}")

# 6. Generate Android launcher icons for flutter_app
res_dir = os.path.join(FLUTTER_DIR, "android", "app", "src", "main", "res")
square_icon = Image.open(os.path.join(logo_kit, "store-icons", "ettehad-store-square-dark-1024.png")).convert("RGBA")
mipmaps = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}
for folder, sz in mipmaps.items():
    p = os.path.join(res_dir, folder)
    os.makedirs(p, exist_ok=True)
    ic = square_icon.resize((sz, sz), Image.Resampling.LANCZOS)
    ic.save(os.path.join(p, "ic_launcher.png"))
print("Updated Flutter Android mipmap launcher icons!")
