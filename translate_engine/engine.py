"""
图片翻译引擎
从 archive/translate_photo.py 重构而来，支持多语言目标翻译
"""

import os
from pathlib import Path

import cv2
import numpy as np
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageFont


LANGUAGE_MAP = {
    "en": "en",
    "vi": "vi",
    "fr": "fr",
    "de": "de",
    "th": "th",
    "id": "id",
    "ja": "ja",
}

_ocr_instance = None


def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(
            lang="ch",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_limit_side_len=1280,
            text_det_limit_type="max",
            text_det_thresh=0.4,
        )
    return _ocr_instance


def translate_text(text: str, translator: GoogleTranslator, retries: int = 3) -> str:
    last_error = None
    for _ in range(retries):
        try:
            return translator.translate(text)
        except Exception as e:
            last_error = e
    return text


def get_font(size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def has_cjk(text: str) -> bool:
    for c in text:
        if "一" <= c <= "鿿" or "㐀" <= c <= "䶿":
            return True
    return False


MIN_FONT_SIZE = 16


def translate_image(input_path: str, output_path: str, target_lang: str) -> dict:
    img = cv2.imread(input_path)
    if img is None:
        return {"success": False, "translations": 0, "error": "无法读取图片"}

    h, w = img.shape[:2]
    ocr = get_ocr()
    translator = GoogleTranslator(source="zh-CN", target=target_lang)

    result = ocr.predict(input_path)
    if not result or not result[0]:
        Image.open(input_path).save(output_path)
        return {"success": True, "translations": 0, "error": None}

    r = result[0]
    texts = r.get("rec_texts", [])
    scores = r.get("rec_scores", [])
    polys = r.get("dt_polys", [])

    if not texts:
        Image.open(input_path).save(output_path)
        return {"success": True, "translations": 0, "error": None}

    temp_pil = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_pil)

    items = []
    for i, text in enumerate(texts):
        if not text or not text.strip():
            continue
        score = float(scores[i]) if i < len(scores) else 0
        if score < 0.3:
            continue
        if not has_cjk(text):
            continue
        if i >= len(polys):
            continue

        poly = polys[i]
        xs = [int(p[0]) for p in poly]
        ys = [int(p[1]) for p in poly]
        x_min, y_min = min(xs), min(ys)
        x_max, y_max = max(xs), max(ys)
        box_h = y_max - y_min

        if box_h < 20:
            continue

        x_min = max(0, min(x_min, w - 1))
        y_min = max(0, min(y_min, h - 1))
        x_max = max(0, min(x_max, w))
        y_max = max(0, min(y_max, h))

        if x_max <= x_min or y_max <= y_min:
            continue

        vi_text = translate_text(text, translator)
        if not vi_text:
            continue

        box_w = x_max - x_min
        # 先按原文框高度估算字号
        font_size = max(int(box_h * 0.85), MIN_FONT_SIZE)
        font = get_font(font_size)

        try:
            bbox = temp_draw.textbbox((0, 0), vi_text, font=font)
            text_w = bbox[2] - bbox[0]
        except Exception:
            text_w = len(vi_text) * font_size * 0.6

        # 如果译文超出原文框，尝试缩小字号（但不低于 MIN_FONT_SIZE）
        if text_w > box_w:
            needed_size = max(int(font_size * box_w / text_w), MIN_FONT_SIZE)
            if needed_size >= MIN_FONT_SIZE and needed_size < font_size:
                font_size = needed_size
                font = get_font(font_size)
                try:
                    bbox = temp_draw.textbbox((0, 0), vi_text, font=font)
                    text_w = bbox[2] - bbox[0]
                except Exception:
                    text_w = len(vi_text) * font_size * 0.6

        # 如果字号已到最小但译文仍超出，计算需要扩展的宽度
        expand_x = 0
        if text_w > box_w:
            expand_x = int((text_w - box_w) / 2) + 6

        e_x_min = max(0, x_min - expand_x)
        e_x_max = min(w, x_max + expand_x)

        # 取周围像素中位数作为文字颜色参考
        margin = 8
        y1 = max(0, y_min - margin)
        y2 = min(h, y_max + margin)
        x1 = max(0, e_x_min - margin)
        x2 = min(w, e_x_max + margin)
        regions = []
        if y1 < y_min:
            regions.append(img[y1:y_min, x1:x2].reshape(-1, 3))
        if y_max < y2:
            regions.append(img[y_max:y2, x1:x2].reshape(-1, 3))
        if x1 < e_x_min:
            regions.append(img[y_min:y_max, x1:e_x_min].reshape(-1, 3))
        if e_x_max < x2:
            regions.append(img[y_min:y_max, e_x_max:x2].reshape(-1, 3))

        if regions:
            surround = np.concatenate(regions)
            avg_color = np.median(surround, axis=0).astype(int).tolist()
            avg_color_rgb = (avg_color[2], avg_color[1], avg_color[0])
        else:
            avg_color_rgb = (255, 255, 255)

        items.append((poly, vi_text, e_x_min, y_min, e_x_max, y_max, avg_color_rgb, font_size))

    if not items:
        Image.open(input_path).save(output_path)
        return {"success": True, "translations": 0, "error": None}

    # 使用 inpainting 擦除原文
    img_work = img.copy()
    mask = np.zeros((h, w), dtype=np.uint8)
    for poly, vi_text, e_x_min, y_min, e_x_max, y_max, bg_rgb, fs in items:
        cv2.rectangle(mask, (e_x_min, y_min), (e_x_max, y_max), 255, -1)

    avg_box_h = np.mean([item[5] - item[3] for item in items])
    inpaint_radius = max(2, min(int(avg_box_h * 0.15), 4))
    img_work = cv2.inpaint(img_work, mask, inpaint_radius, cv2.INPAINT_TELEA)

    # 写入译文
    img_pil = Image.fromarray(cv2.cvtColor(img_work, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    for poly, vi_text, e_x_min, y_min, e_x_max, y_max, bg_rgb, final_font_size in items:
        box_w = e_x_max - e_x_min
        box_h = y_max - y_min

        font = get_font(final_font_size)

        try:
            bbox = draw.textbbox((0, 0), vi_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except Exception:
            text_w = len(vi_text) * final_font_size * 0.6
            text_h = final_font_size

        brightness = (bg_rgb[0] * 299 + bg_rgb[1] * 587 + bg_rgb[2] * 114) / 1000
        text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)

        draw_x = e_x_min + max(0, (box_w - text_w) // 2)
        draw_y = y_min + max(0, (box_h - text_h) // 2)
        draw_x = max(0, draw_x)
        draw_y = max(0, draw_y)

        draw.text((draw_x, draw_y), vi_text, fill=text_color, font=font)

    img_pil.save(output_path)
    return {"success": True, "translations": len(items), "error": None}
