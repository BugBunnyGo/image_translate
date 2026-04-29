"""
照片中文翻译为越南语
流程：OCR识别 → 翻译 → 擦除原文 → 写入译文
使用 PaddleOCR 3.x + deep-translator
"""

import argparse
import os
from pathlib import Path

import cv2
import numpy as np
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageFont


def init_ocr():
    """初始化 PaddleOCR（中文，使用轻量模型）"""
    from paddleocr import PaddleOCR
    return PaddleOCR(
        lang="ch",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_det_limit_side_len=1920,
        text_det_limit_type="max",
    )


def translate_text(text: str, translator: GoogleTranslator, retries: int = 3) -> str:
    """中文翻译为越南语，带重试"""
    last_error = None
    for _ in range(retries):
        try:
            return translator.translate(text)
        except Exception as e:
            last_error = e
    print(f"  翻译失败 '{text}': {last_error}")
    return text


def get_font(size: int):
    """获取支持越南语字符的字体"""
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
    """判断文本是否包含中文"""
    for c in text:
        if "一" <= c <= "鿿" or "㐀" <= c <= "䶿":
            return True
    return False


def process_image(image_path: str, output_dir: str, ocr, translator: GoogleTranslator):
    """单张图片的完整处理流程"""
    img = cv2.imread(image_path)
    if img is None:
        print(f"  无法读取图片: {image_path}")
        return

    h, w = img.shape[:2]

    # OCR 识别
    result = ocr.predict(image_path)
    if not result:
        print(f"  未检测到文字: {image_path}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out = os.path.join(output_dir, os.path.basename(image_path))
        Image.open(image_path).save(out)
        return

    r = result[0]
    texts = r.get("rec_texts", [])
    scores = r.get("rec_scores", [])
    polys = r.get("dt_polys", [])

    if not texts:
        print(f"  未检测到文字: {image_path}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out = os.path.join(output_dir, os.path.basename(image_path))
        Image.open(image_path).save(out)
        return

    # 收集需要处理的文本框（包含中文的，仅翻译叠加营销文字）
    items = []  # (box, text, vi_text, x_min, y_min, x_max, y_max, avg_color_rgb)
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

        # 仅翻译叠加营销文字（高度 >= 20px），跳过手机屏幕内的小字UI
        if box_h < 20:
            continue

        # 确保坐标在图像范围内
        x_min = max(0, min(x_min, w - 1))
        y_min = max(0, min(y_min, h - 1))
        x_max = max(0, min(x_max, w))
        y_max = max(0, min(y_max, h))

        if x_max <= x_min or y_max <= y_min:
            continue

        # 翻译
        vi_text = translate_text(text, translator)
        if not vi_text:
            continue

        # 计算擦除用背景色：取周围更大区域的众数颜色
        margin = 8
        y1 = max(0, y_min - margin)
        y2 = min(h, y_max + margin)
        x1 = max(0, x_min - margin)
        x2 = min(w, x_max + margin)
        regions = []
        if y1 < y_min:
            regions.append(img[y1:y_min, x1:x2].reshape(-1, 3))
        if y_max < y2:
            regions.append(img[y_max:y2, x1:x2].reshape(-1, 3))
        if x1 < x_min:
            regions.append(img[y_min:y_max, x1:x_min].reshape(-1, 3))
        if x_max < x2:
            regions.append(img[y_min:y_max, x_max:x2].reshape(-1, 3))

        if regions:
            surround = np.concatenate(regions)
            # 使用中位数颜色（比平均色更抗渐变干扰）
            avg_color = np.median(surround, axis=0).astype(int).tolist()
            avg_color_rgb = (avg_color[2], avg_color[1], avg_color[0])
        else:
            avg_color_rgb = (255, 255, 255)

        items.append((poly, text, vi_text, x_min, y_min, x_max, y_max, avg_color_rgb))

    if not items:
        print(f"  无中文文字: {image_path}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        out = os.path.join(output_dir, os.path.basename(image_path))
        Image.open(image_path).save(out)
        return

    # 用 OpenCV 先擦除原文（在 cv2 图像上操作，坐标一致）
    img_work = img.copy()
    for poly, text, vi_text, x_min, y_min, x_max, y_max, bg_rgb in items:
        # 计算边界矩形
        pts = np.array([[int(p[0]), int(p[1])] for p in poly], dtype=np.int32)
        # 使用边界矩形擦除
        cv2.rectangle(img_work, (x_min, y_min), (x_max, y_max), tuple(reversed(bg_rgb)), -1)

    # 转为 PIL 写入译文
    img_pil = Image.fromarray(cv2.cvtColor(img_work, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    for poly, text, vi_text, x_min, y_min, x_max, y_max, bg_rgb in items:
        box_w = x_max - x_min
        box_h = y_max - y_min

        # 估算字体大小：根据原文框高度
        font_size = max(int(box_h * 0.8), 12)
        # 如果译文太长，适当缩小
        font = get_font(font_size)

        # 测量译文宽度
        try:
            bbox = draw.textbbox((0, 0), vi_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except Exception:
            text_w = len(vi_text) * font_size * 0.6
            text_h = font_size

        # 如果译文太宽，缩小字体
        if text_w > box_w * 1.2 and font_size > 8:
            new_size = max(int(font_size * box_w / text_w), 8)
            font = get_font(new_size)
            try:
                bbox = draw.textbbox((0, 0), vi_text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            except Exception:
                text_w = len(vi_text) * new_size * 0.6
                text_h = new_size

        # 决定文字颜色：根据背景色亮度
        brightness = (bg_rgb[0] * 299 + bg_rgb[1] * 587 + bg_rgb[2] * 114) / 1000
        text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)

        # 居中写入译文
        draw_x = x_min + max(0, (box_w - text_w) // 2)
        draw_y = y_min + max(0, (box_h - text_h) // 2)

        # 确保不超出边界
        draw_x = max(0, draw_x)
        draw_y = max(0, draw_y)

        draw.text((draw_x, draw_y), vi_text, fill=text_color, font=font)

    # 保存
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = os.path.join(output_dir, os.path.basename(image_path))
    img_pil.save(output_path)
    print(f"  已保存: {output_path} ({len(items)} 处翻译)")


def main():
    parser = argparse.ArgumentParser(description="照片中文翻译为越南语")
    parser.add_argument("input", help="输入图片路径或目录")
    parser.add_argument("-o", "--output", default="./output", help="输出目录")
    parser.add_argument("-n", type=int, default=10, help="每次处理数量")
    args = parser.parse_args()

    # 收集图片
    if os.path.isfile(args.input):
        images = [args.input]
    else:
        images = [
            os.path.join(args.input, f)
            for f in sorted(os.listdir(args.input))
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp"))
        ]

    if not images:
        print("未找到图片")
        return

    images = images[: args.n]
    print(f"共 {len(images)} 张图片待处理")

    # 初始化
    print("初始化 OCR...")
    ocr = init_ocr()
    translator = GoogleTranslator(source="zh-CN", target="vi")

    # 处理
    for i, img_path in enumerate(images, 1):
        print(f"[{i}/{len(images)}] {img_path}")
        process_image(img_path, args.output, ocr, translator)

    print(f"\n完成！输出目录: {args.output}")


if __name__ == "__main__":
    main()
