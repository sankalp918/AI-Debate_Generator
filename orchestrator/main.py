# orchestrator/main.py
import requests
import os
import json
import base64
from moviepy.editor import VideoFileClip, concatenate_videoclips
import tempfile
import uuid
from flask import Flask, request, jsonify, render_template_string, send_file
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# HTML interface for user input
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Debate Generator</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 30px; border-radius: 10px; }
        input, select { width: 100%; padding: 10px; margin: 10px 0; font-size: 16px; }
        button { background: #007bff; color: white; padding: 12px 30px; border: none; 
                 border-radius: 5px; font-size: 18px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .status { margin-top: 20px; padding: 15px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .processing { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Debate Generator</h1>
        <form id="debateForm">
            <label>Debate Topic:</label>
            <input type="text" id="topic" placeholder="e.g., AI will replace most human jobs within 20 years" required>

            <label>Number of Rounds:</label>
            <select id="rounds">
                <option value="1">1 Round</option>
                <option value="2" selected>2 Rounds</option>
                <option value="3">3 Rounds</option>
            </select>

            <label>Colab API URL (from ngrok):</label>
            <input type="text" id="colab_url" placeholder="https://xxxx-xx-xx.ngrok.io" required>

            <button type="submit">Generate Debate</button>
        </form>

        <div id="status"></div>
    </div>

    <script>
        document.getElementById('debateForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const statusDiv = document.getElementById('status');
            statusDiv.className = 'status processing';
            statusDiv.innerHTML = 'Processing... This may take several minutes.';

            const formData = {
                topic: document.getElementById('topic').value,
                rounds: parseInt(document.getElementById('rounds').value),
                colab_url: document.getElementById('colab_url').value
            };

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (result.success) {
                    statusDiv.className = 'status success';
                    statusDiv.innerHTML = `Success! Video saved to: ${result.video_path}<br>
                                         <a href="/download/${result.filename}" download>Download Video</a>`;
                } else {
                    statusDiv.className = 'status error';
                    statusDiv.innerHTML = `Error: ${result.error}`;
                }
            } catch (error) {
                statusDiv.className = 'status error';
                statusDiv.innerHTML = `Error: ${error.message}`;
            }
        });
    </script>
</body>
</html>
"""


class DebateGenerator:
    def __init__(self, colab_url=None):
        self.text_service = "http://text-generation:8001"
        self.tts_service = "http://tts:8002"
        # Normalize to avoid trailing slashes that can create double slashes in requests
        self.lipsync_service = (colab_url or "https://your-ngrok-url.ngrok.io").rstrip('/')

    def generate_debate(self, topic, rounds=3):
        session_id = str(uuid.uuid4())
        video_clips: list[str] = []
        context: str = ""
        texts: list[tuple[str, str, str]] = []

        logging.info(f"Starting debate: {topic}, {rounds} rounds")
        logging.info(f"Using Colab endpoint: {self.lipsync_service}")

        # First pass – generate text and update context immediately
        for round_num in range(rounds):
            logging.info(f"Round {round_num + 1}/{rounds}")
            # Person 1 (pro)
            pro_text = self._generate_text(topic, 'pro', context)
            texts.append(('person1', pro_text, f"pro_{round_num}"))
            context += f"Pro: {pro_text}\n"
            # Person 2 (con)
            con_text = self._generate_text(topic, 'con', context)
            texts.append(('person2', con_text, f"con_{round_num}"))
            context += f"Con: {con_text}\n"

        # Second pass – synthesize audio and video
        for speaker, text, clip_id in texts:
            audio_path = self._generate_audio(text, speaker, session_id, clip_id)
            if not audio_path:
                logging.error(f"Audio generation failed for {speaker} clip {clip_id}, skipping clip")
                continue
            video_path = self._generate_lipsync_colab(speaker, audio_path, session_id, clip_id)
            if not video_path:
                logging.error(f"Lip‑sync generation failed for {speaker} clip {clip_id}, skipping clip")
                continue
            video_clips.append(video_path)

        if not video_clips:
            raise Exception("No video clips generated")

        final_video = self._combine_videos(video_clips, session_id)
        return final_video, session_id

    def _generate_text(self, topic, position, context):
        try:
            response = requests.post(f"{self.text_service}/generate",
                                     json={'topic': topic, 'position': position, 'context': context},
                                     timeout=3000)

            if response.status_code == 200:
                return response.json()['content']
        except Exception as e:
            logging.error(f"Text generation error: {e}")

        # Fallback
        if position == 'pro':
            return f"I support {topic} because it represents progress and innovation."
        else:
            return f"I oppose {topic} because we must consider the human impact."

    def _generate_audio(self, text, speaker, session_id, clip_id):
        try:
            response = requests.post(f"{self.tts_service}/synthesize",
                                     json={'text': text, 'speaker': speaker},
                                     timeout=3000)

            if response.status_code == 200:
                audio_path = f"/tmp/{session_id}_{clip_id}.wav"
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                return audio_path
        except Exception as e:
            logging.error(f"Audio generation error: {e}")
        return None

    def _generate_lipsync_colab(self, person, audio_path, session_id, clip_id):
        try:
            image_path = f"/app/assets/{person}.jpg"

            # Read files and encode to base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
            with open(audio_path, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode()

            # Send to Colab
            # Allow opting out of TLS verification if the container lacks CA roots or ngrok TLS misbehaves
            verify_tls = os.getenv('LIPSYNC_VERIFY_TLS', 'true').lower() not in ('0', 'false', 'no')

            response = requests.post(
                f"{self.lipsync_service}/lipsync",
                json={'image': image_data, 'audio': audio_data},
                headers={'Content-Type': 'application/json'},
                timeout=6000,  # 10-minute timeout
                verify=verify_tls
            )

            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    video_data = base64.b64decode(result['video'])
                    video_path = f"/tmp/{session_id}_{clip_id}.mp4"
                    with open(video_path, 'wb') as f:
                        f.write(video_data)
                    return video_path
        except Exception as e:
            logging.error(f"Lipsync error: {e}")
        return None

    def _combine_videos(self, video_paths, session_id):
        clips = []
        for path in video_paths:
            if os.path.exists(path):
                clips.append(VideoFileClip(path))

        final_clip = concatenate_videoclips(clips, method="compose")
        output_path = f"/app/output/{session_id}_debate.mp4"
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')

        for clip in clips:
            clip.close()
        final_clip.close()

        return output_path


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/generate', methods=['POST'])
def generate_debate():
    try:
        data = request.json
        topic = data.get('topic')
        rounds = data.get('rounds', 2)
        colab_url = data.get('colab_url')

        generator = DebateGenerator(colab_url)
        video_path, session_id = generator.generate_debate(topic, rounds)

        return jsonify({
            'success': True,
            'video_path': video_path,
            'filename': f"{session_id}_debate.mp4"
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download/<filename>')
def download(filename):
    return send_file(f"/app/output/{filename}", as_attachment=True)


@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
