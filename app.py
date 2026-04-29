import os
import shutil
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from translate_engine.engine import translate_image, LANGUAGE_MAP, get_ocr

app = Flask(__name__)

UPLOAD_DIR = Path(__file__).parent / "uploads"

# 启动时初始化 OCR 并清理旧文件
@app.before_request
def init_once():
    if not hasattr(app, "_initialized"):
        if UPLOAD_DIR.exists():
            shutil.rmtree(UPLOAD_DIR)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        # 预加载 OCR 模型
        get_ocr()
        app._initialized = True


@app.route("/")
def index():
    return render_template("index.html", languages=LANGUAGE_MAP)


@app.route("/api/translate", methods=["POST"])
def api_translate():
    if "files" not in request.files:
        return jsonify({"error": "未上传文件"}), 400

    target_lang = request.form.get("lang", "vi")
    if target_lang not in LANGUAGE_MAP:
        return jsonify({"error": f"不支持的语言: {target_lang}"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "未找到有效文件"}), 400

    results = []
    for f in files:
        if f.filename == "":
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            continue

        uid = uuid.uuid4().hex
        orig_name = f"{uid}{ext}"
        trans_name = f"{uid}_translated{ext}"
        orig_path = UPLOAD_DIR / orig_name
        trans_path = UPLOAD_DIR / trans_name

        f.save(orig_path)

        result = translate_image(str(orig_path), str(trans_path), LANGUAGE_MAP[target_lang])

        results.append({
            "original": f"/uploads/{orig_name}",
            "translated": f"/uploads/{trans_name}",
            "translations": result.get("translations", 0),
            "error": result.get("error"),
        })

    return jsonify({"results": results})


@app.route("/uploads/<filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
