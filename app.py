from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import threading
import time

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = "downloads"
COOKIES_FILE = "cookies.txt"
BACKEND_URL = "https://your-app.onrender.com"  # ✅ Apna backend URL daalo

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.youtube.com/",
}

download_tasks = {}

def delete_after_delay(file_path, delay=300):
    time.sleep(delay)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted: {file_path}")
    except Exception as e:
        print(f"Error deleting file: {e}")

@app.route("/")
def home():
    return "YouTube Video Downloader is Running!"

@app.route("/get_formats", methods=["GET"])
def get_formats():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        ydl_opts = {
            "cookiefile": COOKIES_FILE,
            "http_headers": HEADERS,
            "noprogress": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {"format_id": f["format_id"], "resolution": f.get("format_note", "Unknown"), "ext": f["ext"]}
                for f in info["formats"]
                if f.get("vcodec") != "none" and f.get("acodec") == "none"
            ]

        return jsonify({"title": info["title"], "formats": formats})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def download_video_task(video_url, format_id, video_id):
    try:
        ydl_opts = {
            "format": format_id,
            "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
            "cookiefile": COOKIES_FILE,
            "http_headers": HEADERS,
            "noprogress": True,
            "merge_output_format": "mp4",  # ✅ Fix: Ensure MP4 output
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info)

        threading.Thread(target=delete_after_delay, args=(file_path, 300)).start()
        
        download_tasks[video_id] = {
            "status": "completed",
            "title": info["title"],
            "download_link": f"{BACKEND_URL}/file/{os.path.basename(file_path)}"
        }

    except Exception as e:
        download_tasks[video_id] = {"status": "failed", "error": str(e)}

@app.route("/download", methods=["GET"])
def start_download():
    url = request.args.get("url")
    format_id = request.args.get("format")

    if not url or not format_id:
        return jsonify({"error": "URL and format required"}), 400

    video_id = str(int(time.time()))
    download_tasks[video_id] = {"status": "processing"}

    threading.Thread(target=download_video_task, args=(url, format_id, video_id)).start()

    return jsonify({"task_id": video_id, "status": "started"})

@app.route("/status/<task_id>")
def check_status(task_id):
    if task_id in download_tasks:
        return jsonify(download_tasks[task_id])
    return jsonify({"error": "Task not found"}), 404

@app.route("/file/<filename>")
def serve_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
