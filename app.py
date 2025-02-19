from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import subprocess
import time

app = Flask(__name__)

# Ensure cookies.txt is present
COOKIES_PATH = "cookies.txt"
if not os.path.exists(COOKIES_PATH):
    raise FileNotFoundError("cookies.txt file is missing. Upload it to the same folder.")

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Function to extract M3U8 stream
def extract_m3u8(video_url):
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'format': 'best',
        'skip_download': True,
        'cookies': COOKIES_PATH  # Using cookies.txt
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])
        for f in formats:
            if "m3u8" in f["url"]:
                return f["url"]
    return None

# Function to convert M3U8 to MP4
def convert_m3u8_to_mp4(m3u8_url, output_file):
    command = [
        "ffmpeg", "-i", m3u8_url, "-c", "copy", "-bsf:a", "aac_adtstoasc", output_file
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_file

@app.route("/extract", methods=["GET"])
def extract():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"error": "URL is required"}), 400

    m3u8_url = extract_m3u8(video_url)
    if not m3u8_url:
        return jsonify({"error": "Failed to extract M3U8 stream"}), 500

    return jsonify({"m3u8_url": m3u8_url})

@app.route("/convert", methods=["GET"])
def convert():
    m3u8_url = request.args.get("m3u8_url")
    if not m3u8_url:
        return jsonify({"error": "M3U8 URL is required"}), 400

    timestamp = int(time.time())
    output_file = f"{DOWNLOAD_FOLDER}/{timestamp}.mp4"

    convert_m3u8_to_mp4(m3u8_url, output_file)

    return jsonify({"download_link": f"/get_video/{timestamp}.mp4"})

@app.route("/get_video/<filename>")
def get_video(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
