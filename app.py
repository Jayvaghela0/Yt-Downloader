from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import time
import threading
import subprocess

app = Flask(__name__)

# Temporary video storage folder
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def delete_file_after_delay(file_path, delay=120):
    """Automatically delete files after a delay."""
    time.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)

@app.route("/extract", methods=["GET"])
def extract():
    """Extract M3U8 URL from a YouTube video."""
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': True,
        'skip_download': True,
        'extract_flat': False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        m3u8_url = None

        for f in formats:
            if "m3u8" in f["url"]:
                m3u8_url = f["url"]
                break

    if not m3u8_url:
        return jsonify({"error": "M3U8 stream not found"}), 404

    return jsonify({"m3u8_url": m3u8_url})

@app.route("/convert", methods=["GET"])
def convert():
    """Convert M3U8 stream to MP4 using FFmpeg."""
    m3u8_url = request.args.get("m3u8_url")
    if not m3u8_url:
        return jsonify({"error": "No M3U8 URL provided"}), 400

    filename = f"{int(time.time())}.mp4"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    ffmpeg_command = [
        "ffmpeg", "-i", m3u8_url, "-c", "copy", filepath
    ]
    
    process = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if process.returncode != 0:
        return jsonify({"error": "FFmpeg conversion failed"}), 500

    threading.Thread(target=delete_file_after_delay, args=(filepath,)).start()

    return jsonify({"download_link": f"/get_video/{filename}"})

@app.route("/get_video/<filename>", methods=["GET"])
def get_video(filename):
    """Serve the converted MP4 file."""
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
