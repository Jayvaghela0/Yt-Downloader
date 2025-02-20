from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL
import os
import requests

app = Flask(__name__)

# Google reCAPTCHA Secret Key
RECAPTCHA_SECRET_KEY = "YOUR_SECRET_KEY"

# reCAPTCHA Verification Function
def verify_recaptcha(token):
    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {
        "secret": RECAPTCHA_SECRET_KEY,
        "response": token
    }
    try:
        result = requests.post(url, data=data).json()
        return result.get("success", False)
    except Exception as e:
        print("reCAPTCHA verification failed:", e)
        return False

# Direct MP4 Extract Function (Embed Trick Use Karke)
def extract_mp4_url(video_url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
        'cookiefile': 'cookies.txt',
        'referer': 'https://www.youtube.com/embed/',  
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
    except Exception as e:
        print(f"Error extracting MP4 URL: {e}")
        return None

@app.route("/")
def home():
    return "Flask App is Running!"

@app.route('/get_mp4', methods=['POST'])
def get_mp4():
    data = request.json
    video_url = data.get("url")
    recaptcha_token = data.get("recaptcha_token")

    if not video_url or not recaptcha_token:
        return jsonify({"error": "YouTube URL and reCAPTCHA token required"}), 400

    if not verify_recaptcha(recaptcha_token):
        return jsonify({"error": "reCAPTCHA verification failed"}), 403

    mp4_url = extract_mp4_url(video_url)
    if not mp4_url:
        return jsonify({"error": "MP4 URL extraction failed"}), 500

    return jsonify({"mp4_url": mp4_url})

if __name__ == '__main__':

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
