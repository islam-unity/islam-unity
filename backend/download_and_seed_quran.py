"""
Download and Seed Complete Quran Data
Source: Tanzil Project certified text via Al-Quran Cloud API
Editions:
  - Uthmani Arabic Script: quran-uthmani
  - Simple Clean Arabic (Search): quran-simple-clean
  - Persian Translations:
      * Hussein Ansarian: fa.ansarian
      * Nasser Makarem Shirazi: fa.makarem
      * Mohammad Mahdi Fooladvand: fa.fooladvand
"""

import os
import sys
import json
import sqlite3
import urllib.request
import time
from datetime import datetime, timezone

BISMILLAH_UTHMANI = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
BISMILLAH_CLEAN = "بسم الله الرحمن الرحيم"

EDITIONS = {
    "uthmani": "quran-uthmani",
    "clean": "quran-simple-clean",
    "ansarian": "fa.ansarian",
    "makarem": "fa.makarem",
    "fooladvand": "fa.fooladvand",
}


def fetch_edition(edition_id: str, retries: int = 3) -> dict:
    url = f"https://api.alquran.cloud/v1/quran/{edition_id}"
    print(f"Downloading {edition_id} from {url}...")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Ettehad-Quran-Downloader/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 200 and "data" in data:
                    print(f"  -> Successfully downloaded {edition_id}")
                    return data["data"]
                raise ValueError(f"Invalid API response: {data.get('status')}")
        except Exception as e:
            print(f"  [Attempt {attempt}/{retries}] Error fetching {edition_id}: {e}")
            if attempt < retries:
                time.sleep(2)
            else:
                raise


def get_surah_manifest_from_db(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT id, name_arabic, name_persian, name_transliterated,
               ayah_count, revelation_type, juz_number, revelation_order,
               start_page, end_page, summary
        FROM quran_surahs ORDER BY id
    """)
    rows = c.fetchall()
    conn.close()
    return {
        r[0]: {
            "name_arabic": r[1],
            "name_persian": r[2],
            "name_transliterated": r[3],
            "ayah_count": r[4],
            "revelation_type": r[5],
            "juz_number": r[6],
            "revelation_order": r[7],
            "start_page": r[8],
            "end_page": r[9],
            "summary": r[10]
        }
        for r in rows
    }


def process_quran_data(raw_data: dict, manifest_map: dict) -> dict:
    print("Processing and aligning Quran text & translations...")
    uthmani_surahs = raw_data["uthmani"]["surahs"]
    clean_surahs = raw_data["clean"]["surahs"]
    ansarian_surahs = raw_data["ansarian"]["surahs"]
    makarem_surahs = raw_data["makarem"]["surahs"]
    fooladvand_surahs = raw_data["fooladvand"]["surahs"]

    combined_surahs = []
    total_ayahs_count = 0

    for s_idx in range(114):
        s_id = s_idx + 1
        u_surah = uthmani_surahs[s_idx]
        c_surah = clean_surahs[s_idx]
        ans_surah = ansarian_surahs[s_idx]
        mak_surah = makarem_surahs[s_idx]
        foo_surah = fooladvand_surahs[s_idx]

        m_item = manifest_map.get(s_id)
        if m_item:
            name_arabic = m_item["name_arabic"]
            name_persian = m_item["name_persian"]
            name_translit = m_item["name_transliterated"]
            ayah_count = m_item["ayah_count"]
            revelation_type = m_item["revelation_type"]
            juz_number = m_item["juz_number"]
            revelation_order = m_item["revelation_order"]
            start_page = m_item["start_page"]
            end_page = m_item["end_page"]
            summary = m_item["summary"]
        else:
            name_arabic = u_surah.get("name", "")
            name_persian = u_surah.get("englishNameTranslation", "")
            name_translit = u_surah.get("englishName", "")
            ayah_count = len(u_surah.get("ayahs", []))
            revelation_type = u_surah.get("revelationType", "MAKKI").upper()
            juz_number = 1
            revelation_order = s_id
            start_page = 1
            end_page = 1
            summary = ""

        surah_ayahs = []
        num_ayahs = len(u_surah["ayahs"])

        for a_idx in range(num_ayahs):
            u_ayah = u_surah["ayahs"][a_idx]
            c_ayah = c_surah["ayahs"][a_idx]
            ans_ayah = ans_surah["ayahs"][a_idx]
            mak_ayah = mak_surah["ayahs"][a_idx]
            foo_ayah = foo_surah["ayahs"][a_idx]

            ayah_num = u_ayah["numberInSurah"]
            global_num = u_ayah["number"]

            ar_text = u_ayah["text"].strip()
            clean_text = c_ayah["text"].strip()

            # Standard convention: Bismillah is part of verse 1 ONLY in Surah 1 (Al-Fatihah).
            # For Surahs 2..114 (except 9 which has no Bismillah), strip leading Bismillah so verse text is pure.
            if s_id > 1 and s_id != 9 and ayah_num == 1:
                if ar_text.startswith(BISMILLAH_UTHMANI):
                    ar_text = ar_text[len(BISMILLAH_UTHMANI):].strip()
                if clean_text.startswith(BISMILLAH_CLEAN):
                    clean_text = clean_text[len(BISMILLAH_CLEAN):].strip()

            juz_val = u_ayah.get("juz", 1)
            hq = u_ayah.get("hizbQuarter", 1)
            hizb_val = (hq - 1) // 4 + 1
            page_val = u_ayah.get("page", 1)
            sajda_val = bool(u_ayah.get("sajda", False))

            ayah_dict = {
                "ayahNumber": ayah_num,
                "globalNumber": global_num,
                "textArabic": ar_text,
                "textClean": clean_text,
                "textPersian": ans_ayah["text"].strip(),
                "translations": {
                    "ansarian": ans_ayah["text"].strip(),
                    "makarem": mak_ayah["text"].strip(),
                    "fooladvand": foo_ayah["text"].strip(),
                },
                "juz": juz_val,
                "hizb": hizb_val,
                "page": page_val,
                "sajdah": sajda_val
            }
            surah_ayahs.append(ayah_dict)
            total_ayahs_count += 1

        surah_dict = {
            "id": s_id,
            "nameArabic": name_arabic,
            "namePersian": name_persian,
            "nameTransliterated": name_translit,
            "ayahCount": ayah_count,
            "revelationType": revelation_type,
            "revelationOrder": revelation_order,
            "juzNumber": juz_number,
            "startPage": start_page,
            "endPage": end_page,
            "summary": summary,
            "ayahs": surah_ayahs
        }
        combined_surahs.append(surah_dict)

    dataset = {
        "info": {
            "name": "القرآن الكريم",
            "description": "متن کامل ۱۱۴ سوره و ۶۲۳۶ آیه قرآن کریم با خط عثمان طه و ترجمه‌های معتبر فارسی (استاد انصاریان، مکارم شیرازی و فولادوند)",
            "source": "Tanzil Project / King Fahd Glorious Quran Printing Complex via Al-Quran Cloud API",
            "totalSurahs": len(combined_surahs),
            "totalAyahs": total_ayahs_count,
            "totalPages": 604,
            "totalJuz": 30,
            "version": "1.0.0",
            "generatedAt": datetime.now(timezone.utc).isoformat()
        },
        "surahs": combined_surahs
    }
    print(f"Processed {len(combined_surahs)} surahs and {total_ayahs_count} ayahs.")
    return dataset


def save_json_files(dataset: dict, base_dir: str):
    targets = [
        os.path.join(base_dir, "app", "data", "quran_complete.json"),
        os.path.join(base_dir, "app", "static", "quran_complete.json"),
        os.path.join(os.path.dirname(base_dir), "mobile_app", "public", "data", "quran_complete.json")
    ]

    for p in targets:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        print(f"Saving JSON to {p}...")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        size_mb = os.path.getsize(p) / (1024 * 1024)
        print(f"  -> Written successfully ({size_mb:.2f} MB)")


def seed_sqlite_database(db_path: str, dataset: dict):
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping.")
        return

    print(f"Seeding SQLite database: {db_path}...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. Update/Verify Surahs
    for s in dataset["surahs"]:
        c.execute("""
            INSERT INTO quran_surahs (id, name_arabic, name_persian, name_transliterated,
                                      ayah_count, revelation_type, juz_number, revelation_order,
                                      start_page, end_page, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name_arabic=excluded.name_arabic,
                name_persian=excluded.name_persian,
                name_transliterated=excluded.name_transliterated,
                ayah_count=excluded.ayah_count,
                revelation_type=excluded.revelation_type,
                juz_number=excluded.juz_number,
                revelation_order=excluded.revelation_order,
                start_page=excluded.start_page,
                end_page=excluded.end_page,
                summary=excluded.summary
        """, (
            s["id"], s["nameArabic"], s["namePersian"], s["nameTransliterated"],
            s["ayahCount"], s["revelationType"], s["juzNumber"], s["revelationOrder"],
            s["startPage"], s["endPage"], s["summary"]
        ))

    # 2. Insert/Update Ayahs
    ayah_count = 0
    for s in dataset["surahs"]:
        s_id = s["id"]
        for a in s["ayahs"]:
            ayah_num = a["ayahNumber"]
            ar_text = a["textArabic"]
            clean_text = a["textClean"]
            pe_text = a["textPersian"]
            juz_val = a["juz"]
            hizb_val = a["hizb"]
            page_val = a["page"]
            sajdah_val = 1 if a["sajdah"] else 0
            trans_json = json.dumps(a["translations"], ensure_ascii=False)

            # Check if ayah exists
            c.execute("SELECT id FROM quran_ayahs WHERE surah_id = ? AND ayah_number = ?", (s_id, ayah_num))
            existing = c.fetchone()
            if existing:
                c.execute("""
                    UPDATE quran_ayahs SET
                        text_arabic = ?,
                        text_persian = ?,
                        text_clean = ?,
                        juz = ?,
                        hizb = ?,
                        page = ?,
                        sajdah = ?
                    WHERE surah_id = ? AND ayah_number = ?
                """, (ar_text, pe_text, clean_text, juz_val, hizb_val, page_val, sajdah_val, s_id, ayah_num))
            else:
                c.execute("""
                    INSERT INTO quran_ayahs (surah_id, ayah_number, text_arabic, text_persian, text_clean, juz, hizb, page, sajdah)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (s_id, ayah_num, ar_text, pe_text, clean_text, juz_val, hizb_val, page_val, sajdah_val))

            # Update or create tadabbur record with translations
            c.execute("SELECT id, brief_tafsir FROM quran_ayah_tadabbur WHERE surah_id = ? AND ayah_number = ?", (s_id, ayah_num))
            t_row = c.fetchone()
            if t_row:
                # Update translations
                c.execute("""
                    UPDATE quran_ayah_tadabbur SET
                        translations = ?
                    WHERE surah_id = ? AND ayah_number = ?
                """, (trans_json, s_id, ayah_num))
            else:
                c.execute("""
                    INSERT INTO quran_ayah_tadabbur (surah_id, ayah_number, brief_tafsir, keywords, ai_tadabbur, reflection_question, related_ayahs, translations)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s_id, ayah_num,
                    "پیام توحیدی و هدایت الهی برای رشد و رستگاری انسان در دنیا و آخرت.",
                    json.dumps([], ensure_ascii=False),
                    json.dumps([], ensure_ascii=False),
                    "چگونه می‌توان از این آیه شریفه در زندگی فردی و جمعی بهره جست؟",
                    json.dumps([], ensure_ascii=False),
                    trans_json
                ))

            ayah_count += 1

    conn.commit()
    conn.close()
    print(f"  -> Seeding complete for {db_path}. Total ayahs in DB: {ayah_count}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_db = os.path.join(base_dir, "ettehad.db")
    root_db = os.path.join(os.path.dirname(base_dir), "ettehad.db")

    manifest_map = get_surah_manifest_from_db(backend_db)
    if not manifest_map:
        manifest_map = get_surah_manifest_from_db(root_db)

    raw_data = {}
    for key, eid in EDITIONS.items():
        raw_data[key] = fetch_edition(eid)

    dataset = process_quran_data(raw_data, manifest_map)
    save_json_files(dataset, base_dir)

    seed_sqlite_database(backend_db, dataset)
    if os.path.exists(root_db) and os.path.abspath(backend_db) != os.path.abspath(root_db):
        seed_sqlite_database(root_db, dataset)

    print("\nAll tasks completed successfully!")


if __name__ == "__main__":
    main()
