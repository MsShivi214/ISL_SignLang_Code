import json
import os

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from isl.manifest import OUTPUT_DIR, SIGN_ANIM_DIR, VIDEO_DATA_DIR, build_phrase_manifest
from isl.translate import translate_sentence_to_signs, translate_to_animation_sequence, translate_to_video

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/avatar")
def avatar_viewer():
    return render_template("viewer.html")


@app.route("/baker")
def baker_tool():
    return render_template("baker.html")


@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    result = translate_to_video(text)
    video_url = f"/videos/{result['video_filename']}" if result["video_filename"] else None

    return jsonify(
        {
            "gloss": result["gloss"],
            "missing": result["missing"],
            "video_url": video_url,
        }
    )


@app.route("/api/translate_avatar", methods=["POST"])
def api_translate_avatar():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    result = translate_to_animation_sequence(text)
    return jsonify(
        {
            "gloss": result["gloss"],
            "missing": result["missing"],
            "clip_urls": [f"/animations/{name}" for name in result["clips"]],
        }
    )


@app.route("/api/translate_sentence", methods=["POST"])
def api_translate_sentence():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    result = translate_sentence_to_signs(text)
    return jsonify(
        {
            "signs": [
                {"label": sign["label"], "clip_url": f"/animations/{sign['clip']}"}
                for sign in result["signs"]
            ],
            "missing": result["missing"],
        }
    )


@app.route("/api/save_animation", methods=["POST"])
def api_save_animation():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    tracks = data.get("tracks")
    if not name or not isinstance(tracks, dict):
        return jsonify({"error": "name and tracks are required"}), 400

    safe_name = secure_filename(name)
    if not safe_name:
        return jsonify({"error": "invalid name"}), 400

    os.makedirs(SIGN_ANIM_DIR, exist_ok=True)
    out_path = os.path.join(SIGN_ANIM_DIR, f"{safe_name}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"name": name, "tracks": tracks}, f)

    return jsonify({"saved": f"{safe_name}.json"})


@app.route("/api/videos")
def api_videos():
    manifest = build_phrase_manifest()
    videos = [
        {"key": key, "name": os.path.splitext(os.path.basename(path))[0], "url": f"/source-videos/{os.path.basename(path)}"}
        for key, path in manifest.items()
    ]
    return jsonify(videos)


@app.route("/source-videos/<path:filename>")
def serve_source_video(filename):
    return send_from_directory(VIDEO_DATA_DIR, filename)


@app.route("/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/animations/<path:filename>")
def serve_animation(filename):
    return send_from_directory(SIGN_ANIM_DIR, filename)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SIGN_ANIM_DIR, exist_ok=True)
    app.run(debug=True, port=5000)
