import os
import math
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

def reshape_fa(text):
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text

def draw_gradient(draw, width, height, color1, color2):
    for y in range(height):
        r = int(color1[0] + (color2[0] - color1[0]) * (y / height))
        g = int(color1[1] + (color2[1] - color1[1]) * (y / height))
        b = int(color1[2] + (color2[2] - color1[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

def draw_ornate_border(draw, width, height, gold_color):
    # Outer border
    draw.rectangle([14, 14, width - 15, height - 15], outline=gold_color, width=2)
    # Inner border
    draw.rectangle([22, 22, width - 23, height - 23], outline=gold_color, width=1)
    # Corner diamonds
    corners = [(18, 18), (width - 19, 18), (18, height - 19), (width - 19, height - 19)]
    for cx, cy in corners:
        draw.polygon([(cx, cy - 6), (cx + 6, cy), (cx, cy + 6), (cx - 6, cy)], fill=gold_color)

def draw_star(draw, cx, cy, radius, gold_color):
    points = []
    for i in range(16):
        r = radius if i % 2 == 0 else radius * 0.5
        angle = i * math.pi / 8
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=gold_color)

def generate_cover(filename, title, author, category, color_top, color_bot, gold_color=(235, 185, 80)):
    width, height = 400, 600
    img = Image.new("RGB", (width, height), color_top)
    draw = ImageDraw.Draw(img)

    # 1. Background gradient
    draw_gradient(draw, width, height, color_top, color_bot)

    # 2. Subtle geometric texture / circle medallion in center
    cx, cy = width // 2, 250
    draw.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], outline=(gold_color[0], gold_color[1], gold_color[2]), width=1)
    draw.ellipse([cx - 100, cy - 100, cx + 100, cy + 100], outline=(gold_color[0], gold_color[1], gold_color[2]), width=1)
    draw_star(draw, cx, cy - 110, 10, gold_color)
    draw_star(draw, cx, cy + 110, 10, gold_color)

    # 3. Ornate border
    draw_ornate_border(draw, width, height, gold_color)

    # 4. Spine shadow effect (right side for RTL Persian book cover)
    for x in range(width - 25, width):
        alpha = int(70 * ((x - (width - 25)) / 25))
        # darken line
        pass

    # 5. Fonts
    font_dir = "assets/fonts"
    font_bold = ImageFont.truetype(os.path.join(font_dir, "Vazirmatn-Bold.ttf"), 25)
    font_extrabold = ImageFont.truetype(os.path.join(font_dir, "Vazirmatn-ExtraBold.ttf"), 30)
    font_medium = ImageFont.truetype(os.path.join(font_dir, "Vazirmatn-Medium.ttf"), 17)
    font_small = ImageFont.truetype(os.path.join(font_dir, "Vazirmatn-Regular.ttf"), 13)

    # 6. Top Badge
    top_badge_text = reshape_fa("مجموعه کتب معارف اتحاد • فریقین")
    bbox = draw.textbbox((0, 0), top_badge_text, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 45), top_badge_text, fill=gold_color, font=font_small)

    # 7. Category Pill
    cat_text = reshape_fa(f"❖  {category}  ❖")
    bbox = draw.textbbox((0, 0), cat_text, font=font_medium)
    tw = bbox[2] - bbox[0]
    draw.rectangle([(width - tw) // 2 - 12, 130, (width + tw) // 2 + 12, 160], outline=gold_color, width=1)
    draw.text(((width - tw) // 2, 134), cat_text, fill=gold_color, font=font_medium)

    # 8. Title (Wrapped if long)
    words = title.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        test_line = " ".join(curr)
        bbox = draw.textbbox((0, 0), reshape_fa(test_line), font=font_extrabold)
        if bbox[2] - bbox[0] > 320:
            if len(curr) > 1:
                curr.pop()
                lines.append(" ".join(curr))
                curr = [w]
            else:
                lines.append(test_line)
                curr = []
    if curr:
        lines.append(" ".join(curr))

    y_title = 220
    for line in lines:
        reshaped_line = reshape_fa(line)
        bbox = draw.textbbox((0, 0), reshaped_line, font=font_extrabold)
        tw = bbox[2] - bbox[0]
        # Text shadow
        draw.text(((width - tw) // 2 + 2, y_title + 2), reshaped_line, fill=(0, 0, 0), font=font_extrabold)
        draw.text(((width - tw) // 2, y_title), reshaped_line, fill=(255, 255, 255), font=font_extrabold)
        y_title += 45

    # 9. Divider line
    draw.line([(cx - 70, y_title + 15), (cx + 70, y_title + 15)], fill=gold_color, width=2)
    draw_star(draw, cx, y_title + 15, 6, gold_color)

    # 10. Author
    auth_prefix = reshape_fa("اثر ارزشمند:")
    bbox = draw.textbbox((0, 0), auth_prefix, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 450), auth_prefix, fill=(200, 200, 200), font=font_small)

    auth_text = reshape_fa(author)
    bbox = draw.textbbox((0, 0), auth_text, font=font_bold)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 475), auth_text, fill=(255, 245, 215), font=font_bold)

    # 11. Footer Seal / Publisher
    pub_text = reshape_fa("انتشارات دارالمعارف الاسلامیه")
    bbox = draw.textbbox((0, 0), pub_text, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 545), pub_text, fill=gold_color, font=font_small)

    out_path = os.path.join("assets/images/covers", filename)
    img.save(out_path, "PNG", quality=95)
    print(f"Generated {out_path}")

def main():
    covers = [
        ("cover_bk_fiqh_quduri.png", "مختصر القدوري", "أبو الحسين أحمد القدوري", "فقه حنفی", (10, 46, 110), (5, 20, 55)),
        ("cover_bk_hadith_riyad.png", "رياض الصالحين", "الإمام يحيى بن شرف النووي", "جوامع الحدیث", (15, 75, 55), (6, 38, 28)),
        ("cover_bk_hadith_qudsi40.png", "الأحاديث القدسية", "نخبة من علماء الحديث", "احادیث قدسی", (95, 30, 45), (45, 12, 20)),
        ("cover_bk_hadith_nawawi40.png", "الأربعون النووية", "الإمام محيي الدين النووي", "جوامع الکلم", (110, 55, 15), (55, 25, 5)),
        ("cover_bk_hadith_shamail.png", "الشمائل المحمدية", "الإمام محمد بن عيسى الترمذي", "سیره و شمائل نبوی", (18, 80, 85), (8, 40, 45)),
        ("cover_bk_fiqh_bidayat.png", "بداية المجتهد", "ابن رشد الحفيد القرطبي", "فقه مقارن فریقین", (40, 25, 95), (18, 10, 50)),
        ("cover_bk_misc_tibyan.png", "التبيان في حملة القرآن", "الإمام يحيى بن شرف النووي", "آداب و علوم قرآن", (25, 60, 95), (12, 30, 50)),
        ("cover_bk_fiqh_sharai.png", "شرائع الإسلام", "المحقق الحلي جعفر بن الحسن", "فقه جعفری اثناعشری", (70, 40, 15), (35, 20, 8)),
        ("cover_bk_tafsir_jalalayn.png", "تفسير الجلالين", "جلال الدين المحلي والسيوطي", "تفسیر قرآن کریم", (12, 65, 50), (5, 32, 24)),
        ("cover_bk_fiqh_umda.png", "عمدة الفقه", "ابن قدامة المقدسي", "فقه حنبلی", (35, 50, 75), (15, 25, 40)),
        ("cover_bk_fiqh_risala.png", "رسالة ابن أبي زيد", "ابن أبي زيد القيرواني", "فقه مالکی", (80, 35, 20), (40, 18, 10)),
        ("cover_bk_fiqh_minhaj.png", "منهاج الطالبين", "الإمام يحيى بن شرف النووي", "فقه شافعی", (20, 60, 70), (10, 30, 35)),
        ("cover_bk_misc_adhkar.png", "الأذكار المنتخبة", "الإمام يحيى بن شرف النووي", "ادعیه و اذکار نبوی", (60, 25, 75), (30, 12, 40)),
    ]

    for c in covers:
        generate_cover(c[0], c[1], c[2], c[3], c[4], c[5])

if __name__ == "__main__":
    main()
