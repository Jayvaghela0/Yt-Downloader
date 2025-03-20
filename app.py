from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import threading
import time
import hashlib

app = Flask(__name__)

# 🟢 CORS: Sirf tumhare Blogger domain se requests allow honge
CORS(app, resources={r"/*": {"origins": "https://youtubevideodownloaderfullhdfree.blogspot.com"}})

# 🟢 Configurations
DOWNLOAD_FOLDER = "downloads"
COOKIES_FILE = "cookies.txt"
BACKEND_URL = "https://yt-downloader-3pl3.onrender.com"

# Folder create karlo agar exist nahi karta
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🟢 Headers for yt-dlp
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.youtube.com/",
}

# Active Download Tasks
download_tasks = {}

# ✅ Function: Sirf allowed domain se requests allow karega
def is_valid_request():
    referer = request.headers.get("Referer", "")
    return referer.startswith("https://youtubevideodownloaderfullhdfree.blogspot.com")

# ✅ Function: 3 minute baad file delete karne ka kaam karega
def delete_after_delay(file_path, delay=180):
    time.sleep(delay)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted: {file_path}")
    except Exception as e:
        print(f"Error deleting file: {e}")

# ✅ Route: Video ke available formats fetch karega (Shorts + Long Videos)
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

        allowed_resolutions = {144, 240, 360, 480, 720, 1080}  # ✅ Shorts ke liye chhoti resolutions add ki hain
        allowed_ext = "mp4"
        unique_formats = {}

        for f in info.get("formats", []):
            resolution = f.get("height")
            ext = f.get("ext")
            format_id = f.get("format_id")

            if resolution and resolution in allowed_resolutions and ext == allowed_ext:
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

# ✅ Route: Video download request handle karega (Shorts + Long Videos)
@app.route("/download", methods=["GET"])
def start_download():
    if not is_valid_request():
        return jsonify({"error": "Unauthorized request"}), 403

    url = request.args.get("url")
    format_id = request.args.get("format_id")

    if not url or not format_id:
        return jsonify({"error": "URL and Format required"}), 400

    # Har baar naye naam ke liye unique hash generate karo
    video_hash = hashlib.md5((url + format_id + str(time.time())).encode()).hexdigest()
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{video_hash}.mp4")

    # Har request par naya download shuru hoga
    threading.Thread(target=download_video_task, args=(url, format_id, video_hash)).start()

    return jsonify({"task_id": video_hash, "status": "started"})

# ✅ Function: Video download karne ka actual kaam yeh karega (Shorts + Long Videos)
def download_video_task(video_url, format_id, video_hash):
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{video_hash}.mp4")

    try:
        ydl_opts = {
            "format": format_id,
            "outtmpl": file_path,
            "cookiefile": COOKIES_FILE,
            "http_headers": HEADERS,
            "noprogress": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        # ✅ File 3 minute ke baad delete ho jayegi
        threading.Thread(target=delete_after_delay, args=(file_path, 180)).start()

        # ✅ Download ho gaya, ab frontend ko serve karne ke liye store karlo
        download_tasks[video_hash] = {
            "status": "completed",
            "title": info["title"],
            "download_link": f"{BACKEND_URL}/file/{os.path.basename(file_path)}"
        }

    except Exception as e:
        download_tasks[video_hash] = {"status": "failed", "error": str(e)}

# ✅ Route: Download status check karne ke liye
@app.route("/status/<task_id>")
def check_status(task_id):
    if not is_valid_request():
        return jsonify({"error": "Unauthorized request"}), 403

    if task_id in download_tasks:
        return jsonify(download_tasks[task_id])
    return jsonify({"error": "Task not found"}), 404

# ✅ Route: File serve karne ke liye
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
