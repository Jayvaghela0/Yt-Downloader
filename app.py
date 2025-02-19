from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
import subprocess
import os

app = Flask(__name__)

# Temporary folder banayein (agar nahi hai toh)
if not os.path.exists('temp'):
    os.makedirs('temp')

# M3U8 stream extract karein (cookies aur headers ke sath)
def extract_m3u8_url(video_url):
    ydl_opts = {
        'format': 'best',  # Best quality ka stream extract karein
        'quiet': True,     # Logs ko suppress karein
        'cookiefile': 'cookies.txt',  # Cookies file ka use karein
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',  # User-Agent
        'headers': {
            'Referer': 'https://www.youtube.com/',
            'Origin': 'https://www.youtube.com',
        },
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get('formats', [])
        for f in formats:
            if f.get('protocol') == 'm3u8':  # M3U8 stream dhoondhein
                return f['url']
    return None

# MP4 format mein convert karein
def convert_to_mp4(m3u8_url, output_file):
    command = [
        'ffmpeg',
        '-i', m3u8_url,  # Input M3U8 URL
        '-c', 'copy',    # Copy codec (no re-encoding)
        output_file      # Output MP4 file
    ]
    subprocess.run(command, check=True)

# Download endpoint
@app.route('/download', methods=['GET'])
def download_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL parameter is required"}), 400

    try:
        # M3U8 stream extract karein
        m3u8_url = extract_m3u8_url(video_url)
        if not m3u8_url:
            return jsonify({"error": "Could not extract M3U8 stream"}), 500

        # MP4 format mein convert karein
        output_file = "temp/output.mp4"
        convert_to_mp4(m3u8_url, output_file)

        # Download link banayein
        download_link = f"http://your-domain.com/{output_file}"
        return jsonify({"download_link": download_link})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
