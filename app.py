from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import threading
import time
import hashlib

app = Flask(__name__)

# Sirf Cloudflare Worker se requests allow karne ke liye
ALLOWED_WORKER_URL = "https://your-cloudflare-worker.workers.dev"

def check_worker_access():
    """✅ Sirf Cloudflare Worker se aane wale requests allow karega"""
    referer = request.headers.get("Referer")
    if referer is None or not referer.startswith(ALLOWED_WORKER_URL):
        return jsonify({"error": "Access Denied"}), 403

app.before_request(check_worker_access)

DOWNLOAD_FOLDER = "downloads"
COOKIES_FILE = "cookies.txt"
BACKEND_URL = ALLOWED_WORKER_URL  # ✅ Backend URL ko Cloudflare Worker se replace kiya

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.youtube.com/",
}

download_tasks = {}
file_timestamps = {}

def delete_after_delay(file_path, delay=300):
    """✅ 5 minute baad file delete karega"""
    time.sleep(delay)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            file_timestamps.pop(file_path, None)
            print(f"Deleted: {file_path}")
    except Exception as e:
        print(f"Error deleting file: {e}")

@app.route("/get_formats", methods=["GET"])
def get_formats():
    """✅ Sirf MP4 formats allow karega"""
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
    """✅ Agar video available hai to wahi return karega"""
    url = request.args.get("url")
    format_id = request.args.get("format_id")

    if not url or not format_id:
        return jsonify({"error": "URL and Format required"}), 400

    video_hash = hashlib.md5((url + format_id).encode()).hexdigest()
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{video_hash}.mp4")

    if file_path in file_timestamps and os.path.exists(file_path):
        return jsonify({
            "status": "completed",
            "title": "Cached Video",
            "download_link": f"{BACKEND_URL}/file/{os.path.basename(file_path)}"
        })

    download_tasks[video_hash] = {"status": "processing"}
    threading.Thread(target=download_video_task, args=(url, format_id, video_hash)).start()

    return jsonify({"task_id": video_hash, "status": "started"})

def download_video_task(video_url, format_id, video_hash):
    """✅ Background me video download karega"""
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

        file_timestamps[file_path] = time.time()
        threading.Thread(target=delete_after_delay, args=(file_path, 300)).start()

        download_tasks[video_hash] = {
            "status": "completed",
            "title": info["title"],
            "download_link": f"{BACKEND_URL}/file/{os.path.basename(file_path)}"
        }

    except Exception as e:
        download_tasks[video_hash] = {"status": "failed", "error": str(e)}

@app.route("/status/<task_id>")
def check_status(task_id):
    """✅ Task ka status check karega"""
    if task_id in download_tasks:
        return jsonify(download_tasks[task_id])
    return jsonify({"error": "Task not found"}), 404

@app.route("/file/<filename>")
def serve_file(filename):
    """✅ Downloaded file serve karega agar available hai"""
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
