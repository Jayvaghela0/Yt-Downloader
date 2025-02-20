from flask import Flask, request, jsonify, send_from_directory
from yt_dlp import YoutubeDL
import os

app = Flask(__name__)

# Temporary folder create karein
if not os.path.exists('temp'):
    os.makedirs('temp')

# Direct MP4 Extract Function (Embed Trick Use Karke)
def extract_mp4_url(video_url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Best MP4 format choose karega
        'quiet': True,
        'cookiefile': 'cookies.txt',  # Agar login required ho toh cookies use karein
        'referer': 'https://www.youtube.com/embed/',  # Embed trick
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')  # Direct MP4 URL return karega
    except Exception as e:
        print(f"Error extracting MP4 URL: {e}")
        return None

@app.route("/")
def home():
    return "Flask App is Running!"

@app.route('/get_mp4', methods=['GET'])
def get_mp4():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "YouTube URL required"}), 400

    mp4_url = extract_mp4_url(video_url)
    if not mp4_url:
        return jsonify({"error": "MP4 URL extraction failed"}), 500

    return jsonify({"mp4_url": mp4_url})

if __name__ == '__main__':

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
