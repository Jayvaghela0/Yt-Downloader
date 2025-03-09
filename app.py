from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import threading
import time
import hashlib

app = Flask(__name__)

# ✅ Sirf tumhare Blogger domain se requests allow karne ke liye CORS set kiya
CORS(app, resources={r"/*": {"origins": "https://youtubevideodownloaderfullhdfree.blogspot.com"}})

DOWNLOAD_FOLDER = "downloads"
COOKIES_FILE = "cookies.txt"
BACKEND_URL = "https://yt-downloader-3pl3.onrender.com"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.youtube.com/",
}

download_tasks = {}
file_timestamps = {}

def delete_after_delay(file_path, delay=180):  # ✅ 3-minute delete timer
    time.sleep(delay)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            file_timestamps.pop(file_path, None)
            print(f"Deleted: {file_path}")
    except Exception as e:
        print(f"Error deleting file: {e}")

def is_valid_request():
    """✅ Sirf allowed domain se requests allow karega"""
    referer = request.headers.get("Referer", "")
    return referer.startswith("https://youtubevideodownloaderfullhdfree.blogspot.com")

def get_next_filename():
    """✅ Next available filename find karega (VIDEO1, VIDEO2, etc.)"""
    existing_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith("VIDEO") and f.endswith(".mp4")]
    existing_numbers = [int(f.replace("VIDEO", "").replace(".mp4", "")) for f in existing_files if f.replace("VIDEO", "").replace(".mp4", "").isdigit()]
    next_number = max(existing_numbers) + 1 if existing_numbers else 1
    return f"VIDEO{next_number}.mp4"

@app.route("/get_formats", methods=["GET"])
def get_formats():
    if not is_valid_request():
        return jsonify({"error": "Unauthorized request"}), 403

    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        ydl_opts = {
            "cookiefile": COOKIES_FILE,
            "http_headers": HEADERS,
            "quiet": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        allowed_resolutions = {320, 480, 720, 1080}
        allowed_ext = "mp4"
        unique_formats = {}

        for f in info.get("formats", []):
            resolution = f.get("height")
            ext = f.get("ext")
            format_id = f.get("format_id")

            if resolution in allowed_resolutions and ext == allowed_ext:
                if resolution not in unique_formats:
                    unique_formats[resolution] = {
                        "format_id": format_id,
                        "resolution": resolution,
                        "ext": ext
                    }

        formats = list(unique_formats.values())

        if not formats:
            return jsonify({"error": "No supported formats found"}), 404

        return jsonify({"title": info["title"], "formats": formats})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["GET"])
def start_download():
    if not is_valid_request():
        return jsonify({"error": "Unauthorized request"}), 403

    url = request.args.get("url")
    format_id = request.args.get("format_id")

    if not url or not format_id:
        return jsonify({"error": "URL and Format required"}), 400

    file_name = get_next_filename()  # ✅ Unique file name generate karega
    file_path = os.path.join(DOWNLOAD_FOLDER, file_name)

    # ✅ Har baar naya download hoga (old file check nahi karega)
    download_tasks[file_name] = {"status": "processing"}
    threading.Thread(target=download_video_task, args=(url, format_id, file_name)).start()

    return jsonify({"task_id": file_name, "status": "started"})

def download_video_task(video_url, format_id, file_name):
    file_path = os.path.join(DOWNLOAD_FOLDER, file_name)

    try:
        ydl_opts = {
            "format": format_id,
            "outtmpl": file_path,
            "cookiefile": COOKIES_FILE,
            "http_headers": HEADERS,
            "noprogress": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(video_url, download=True)

        file_timestamps[file_path] = time.time()
        threading.Thread(target=delete_after_delay, args=(file_path, 180)).start()  # ✅ 3-minute delete timer

        download_tasks[file_name] = {
            "status": "completed",
            "download_link": f"{BACKEND_URL}/file/{file_name}"
        }

    except Exception as e:
        download_tasks[file_name] = {"status": "failed", "error": str(e)}

@app.route("/status/<task_id>")
def check_status(task_id):
    if not is_valid_request():
        return jsonify({"error": "Unauthorized request"}), 403

    if task_id in download_tasks:
        return jsonify(download_tasks[task_id])
    return jsonify({"error": "Task not found"}), 404

@app.route("/file/<filename>")
def serve_file(filename):
    if not is_valid_request():
        return jsonify({"error": "Unauthorized request"}), 403

    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
