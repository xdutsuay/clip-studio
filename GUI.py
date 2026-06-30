import webbrowser
from pathlib import Path

import tomlkit
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

import utils.clip_gui as clip_gui
import utils.gui_utils as gui

HOST = "localhost"
PORT = 4000

app = Flask(__name__, template_folder="GUI")
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    return redirect(url_for("clip_studio"))


@app.route("/clip", methods=["GET"])
def clip_studio():
    return render_template(
        "clip.html",
        file="export/manifest.json",
        audio_files=clip_gui.list_audio_files(),
        backgrounds=clip_gui.list_background_keys(),
        local_backgrounds=clip_gui.list_local_background_files(),
        clips=clip_gui.list_clips(),
    )


@app.route("/clip/generate", methods=["POST"])
def clip_generate():
    audio = request.form.get("audio", "").strip()
    upload = request.files.get("audio_upload")

    if upload and upload.filename:
        name = secure_filename(upload.filename)
        dest = Path("assets/audio") / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        upload.save(dest)
        audio = name

    hook = request.form.get("hook", "").strip()
    if not audio or not hook:
        flash("Audio and hook are required.", "error")
        return redirect(url_for("clip_studio"))

    background = request.form.get("background") or None
    background_file = request.form.get("background_file") or None
    theme = request.form.get("theme", "tech_insight")
    topic = request.form.get("topic", "").strip() or None
    duration_raw = request.form.get("duration", "").strip()
    duration = float(duration_raw) if duration_raw else None

    code, output = clip_gui.run_clip_generation(
        audio=audio,
        hook=hook,
        background=background if not background_file else None,
        background_file=background_file,
        theme=theme,
        topic=topic,
        duration=duration,
    )

    if code != 0:
        flash(f"Clip failed (exit {code}). See terminal log.", "error")
        app.logger.error(output)
    else:
        flash("Clip rendered successfully!", "success")

    return redirect(url_for("clip_studio"))


@app.route("/clip/carousel", methods=["POST"])
def clip_carousel():
    manifest = Path("export/manifest.json")
    if not manifest.is_file():
        flash("No manifest.json — generate a clip first.", "error")
        return redirect(url_for("clip_studio"))

    import subprocess
    import sys

    pdf_cmd = [
        sys.executable,
        "scripts/clip_to_carousel.py",
        "export/manifest.json",
    ]
    pdf_proc = subprocess.run(pdf_cmd, capture_output=True, text=True)
    if pdf_proc.returncode != 0:
        flash("Carousel PDF failed.", "error")
        return redirect(url_for("clip_studio"))

    code, output = clip_gui.run_carousel_push()
    if code != 0:
        flash("PDF created; LGE push failed (is linkedin-growth-engine running?).", "error")
    else:
        flash("Carousel pushed to linkedin-growth-engine — review in Kanban.", "success")

    return redirect(url_for("clip_studio"))


@app.route("/backgrounds", methods=["GET"])
def backgrounds():
    return render_template("backgrounds.html", file="background_videos.json")


@app.route("/background/add", methods=["POST"])
def background_add():
    youtube_uri = request.form.get("youtube_uri").strip()
    filename = request.form.get("filename").strip()
    citation = request.form.get("citation").strip()
    position = request.form.get("position").strip()
    gui.add_background(youtube_uri, filename, citation, position)
    return redirect(url_for("backgrounds"))


@app.route("/background/delete", methods=["POST"])
def background_delete():
    key = request.form.get("background-key")
    gui.delete_background(key)
    return redirect(url_for("backgrounds"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    config_path = Path("config.toml")
    if not config_path.is_file():
        flash("config.toml not found — legacy Reddit mode only.", "error")
        return redirect(url_for("clip_studio"))

    config_load = tomlkit.loads(config_path.read_text())
    config = gui.get_config(config_load)
    checks = gui.get_checks()

    if request.method == "POST":
        data = request.form.to_dict()
        config = gui.modify_settings(data, config_load, checks)

    return render_template("settings.html", file="config.toml", data=config, checks=checks)


@app.route("/videos.json")
def videos_json():
    path = Path("video_creation/data/videos.json")
    if not path.is_file():
        return jsonify([])
    return send_from_directory("video_creation/data", "videos.json")


@app.route("/background_videos.json")
def backgrounds_json():
    return send_from_directory("utils", "background_videos.json")


@app.route("/backgrounds.json")
def backgrounds_json_legacy():
    return send_from_directory("utils", "background_videos.json")


@app.route("/results/<path:name>")
def results(name):
    return send_from_directory(".", name, as_attachment=True)


@app.route("/voices/<path:name>")
def voices(name):
    return send_from_directory("GUI/voices", name, as_attachment=True)


if __name__ == "__main__":
    webbrowser.open(f"http://{HOST}:{PORT}/clip", new=2)
    print("Clip Studio GUI → http://localhost:4000/clip")
    app.run(port=PORT)
