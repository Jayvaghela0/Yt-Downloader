from flask import Flask, request, jsonify, send_from_directory
from yt_dlp import YoutubeDL
import subprocess
import os

app = Flask(__name__)

# Static directory create karein
if not os.path.exists('static'):
    os.makedirs('static')

# FFmpeg ka path set karein
FFMPEG_PATH = "/usr/bin/ffmpeg"
os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_PATH)

# M3U8 Stream Extract Function
def extract_m3u8_url(video_url):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'cookiefile': 'cookies.txt',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'headers': {
            'Referer': 'https://www.youtube.com/',
            'Origin': 'https://www.youtube.com',
        },
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            formats = info.get('formats', [])
            for f in formats:
                if f.get('protocol') == 'm3u8':
                    return f['url']
            return info['url']
    except Exception as e:
        return None

# MP4 Conversion Function
def convert_to_mp4(m3u8_url, output_file):
    command = [FFMPEG_PATH, '-i', m3u8_url, '-c', 'copy', f'static/{output_file}']
    subprocess.run(command, check=True)

@app.route("/")
def home():
    return "Flask App is Running!"

@app.route('/download', methods=['GET'])
def download_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL parameter is required"}), 400

    try:
        m3u8_url = extract_m3u8_url(video_url)
        if not m3u8_url:
            return jsonify({"error": "Could not extract M3U8 stream"}), 500

        output_file = "output.mp4"
        convert_to_mp4(m3u8_url, output_file)

        return jsonify({"download_link": f"https://your-app.onrender.com/static/output.mp4"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>')
def serve_file(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
