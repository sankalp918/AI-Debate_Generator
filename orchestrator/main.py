import base64
import logging
import os
import uuid

import numpy as np
import requests
from PIL import Image
from flask import Flask, request, jsonify, render_template_string, send_file
from moviepy.editor import (
    VideoFileClip, concatenate_videoclips, CompositeVideoClip,
    ImageClip, ColorClip
)

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
            
            const rounds = parseInt(document.getElementById('rounds').value);
            const estimatedTime = rounds === 1 ? '3-5' : rounds === 2 ? '6-10' : '10-15';
            statusDiv.innerHTML = `🎬 Generating debate...<br>
                                  Expected time: ${estimatedTime} minutes<br>
                                  <small>Please wait, do not close this page...</small>`;

            const formData = {
                topic: document.getElementById('topic').value,
                rounds: rounds,
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
                    statusDiv.innerHTML = `✅ Success! Video generated!<br><br>
                                         <strong>File:</strong> ${result.filename}<br>
                                         <a href="/download/${result.filename}" download style="display: inline-block; margin-top: 10px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px;">📥 Download Video</a>`;
                } else {
                    statusDiv.className = 'status error';
                    let errorHTML = `❌ <strong>Error:</strong> ${result.error}<br><br>`;
                    
                    // Add specific troubleshooting based on error
                    if (result.error.includes('Image not found')) {
                        errorHTML += `<strong>Solution:</strong> Add person1.jpg and person2.jpg to the assets/ folder`;
                    } else if (result.error.includes('Colab') || result.error.includes('ngrok')) {
                        errorHTML += `<strong>Possible causes:</strong><br>
                                     • Colab session timed out - refresh your Colab notebook<br>
                                     • ngrok URL is incorrect or expired<br>
                                     • Check Colab logs for errors`;
                    } else if (result.error.includes('timeout')) {
                        errorHTML += `<strong>Solution:</strong> The request took too long. Try:<br>
                                     • Using fewer rounds<br>
                                     • Check your internet connection<br>
                                     • Verify Colab is still running`;
                    }
                    
                    if (result.details) {
                        errorHTML += `<br><br><details style="margin-top: 10px;"><summary style="cursor: pointer;">🔍 Technical Details</summary><pre style="background: #fff; padding: 10px; border-radius: 5px; overflow-x: auto; font-size: 11px;">${result.details}</pre></details>`;
                    }
                    
                    statusDiv.innerHTML = errorHTML;
                }
            } catch (error) {
                statusDiv.className = 'status error';
                statusDiv.innerHTML = `❌ <strong>Network Error:</strong> ${error.message}<br><br>
                                     <strong>Possible causes:</strong><br>
                                     • Docker services not running<br>
                                     • Connection timeout<br>
                                     • Check: docker-compose logs`;
            }
        });
    </script>
</body>
</html>
"""


def create_podcast_background(width=1920, height=1080):
    """Create or load podcast studio background"""
    background_path = "/app/assets/podcast_background.jpg"
    
    if os.path.exists(background_path):
        # Use custom background if provided
        bg_img = Image.open(background_path)
        bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
        return ImageClip(np.array(bg_img))
    else:
        # Create a professional-looking gradient background
        logging.info("No custom background found, creating default podcast background")
        # Create a dark gradient background
        gradient = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(height):
            # Gradient from dark blue to darker blue
            r = int(15 + (25 - 15) * (i / height))
            g = int(25 + (40 - 25) * (i / height))
            b = int(45 + (60 - 45) * (i / height))
            gradient[i, :] = [r, g, b]
        return ImageClip(gradient)


def composite_speaker_on_background(video_path, position='left', background_clip=None):
    """Composite speaker video onto podcast background"""
    try:
        speaker_clip = VideoFileClip(video_path)
        
        # Create background if not provided
        if background_clip is None:
            background_clip = create_podcast_background()
        
        # Set background duration to match speaker
        background_clip = background_clip.set_duration(speaker_clip.duration)
        
        # Resize speaker video to fit in frame (about 40% of width)
        target_width = int(1920 * 0.35)
        aspect_ratio = speaker_clip.h / speaker_clip.w
        target_height = int(target_width * aspect_ratio)
        
        speaker_resized = speaker_clip.resize(width=target_width)
        
        # Position speaker on left or right
        if position == 'left':
            x_pos = 150  # Left side with margin
        else:
            x_pos = 1920 - target_width - 150  # Right side with margin
        
        y_pos = (1080 - target_height) // 2  # Vertically centered
        
        # Create composite
        speaker_positioned = speaker_resized.set_position((x_pos, y_pos))
        
        composite = CompositeVideoClip(
            [background_clip, speaker_positioned],
            size=(1920, 1080)
        )
        
        return composite
        
    except Exception as e:
        logging.error(f"Compositing error: {e}")
        # Return original video if compositing fails
        return VideoFileClip(video_path)


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
            logging.info(f"Generating {position} text for: {topic}")
            response = requests.post(
                f"{self.text_service}/generate",
                json={'topic': topic, 'position': position, 'context': context},
                                timeout=90  # allow adequate generation time for large models
            )

            if response.status_code == 200:
                text = response.json()['content']
                logging.info(f"{position.upper()} text generated: {len(text)} chars")
                return text
            else:
                logging.warning(f"Text service returned {response.status_code}, using fallback")
        except Exception as e:
            logging.error(f"Text generation error: {e}")
            import traceback
            traceback.print_exc()

        # Fallback
        if position == 'pro':
            return f"I support {topic} because it represents progress and innovation."
        else:
            return f"I oppose {topic} because we must consider the human impact."

    def _generate_audio(self, text, speaker, session_id, clip_id):
        try:
            logging.info(f"Generating audio for {speaker}: {len(text)} chars")
            response = requests.post(
                f"{self.tts_service}/synthesize",
                json={'text': text, 'speaker': speaker},
                                timeout=90  # increased to 90s to accommodate longer TTS processing times
            )

            if response.status_code == 200:
                audio_path = f"/tmp/{session_id}_{clip_id}.wav"
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                logging.info(f"Audio saved: {audio_path}")
                return audio_path
            else:
                logging.error(f"TTS service returned {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"Audio generation error: {e}")
            import traceback
            traceback.print_exc()
        return None

    def _generate_lipsync_colab(self, person, audio_path, session_id, clip_id):
        try:
            image_path = f"/app/assets/{person}.jpg"
            
            # Check if image exists
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            logging.info(f"Generating lip-sync for {person}...")

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
                                timeout=6000,  # true 100-minute timeout
                verify=verify_tls
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logging.info(f"Lip-sync successful for {person}")
                    video_data = base64.b64decode(result['video'])
                    video_path = f"/tmp/{session_id}_{clip_id}.mp4"
                    with open(video_path, 'wb') as f:
                        f.write(video_data)
                    logging.info(f"Video saved: {video_path}")
                    return video_path
                else:
                    logging.error(f"Colab returned success=False: {result.get('error', 'Unknown error')}")
            else:
                logging.error(f"Colab service returned {response.status_code}: {response.text[:500]}")
        except FileNotFoundError as e:
            logging.error(f"File not found: {e}")
        except Exception as e:
            logging.error(f"Lipsync error: {e}")
            import traceback
            traceback.print_exc()
        return None

    def _combine_videos(self, video_paths, session_id):
        """Combine videos with podcast-style compositing"""
        logging.info(f"Combining {len(video_paths)} video clips...")
        clips = []
        position_toggle = 'left'  # Alternate speakers between left and right
        
        for i, path in enumerate(video_paths):
            if os.path.exists(path):
                logging.info(f"Processing clip {i+1}/{len(video_paths)}: {path}")
                # Composite each speaker on podcast background
                position = 'left' if i % 2 == 0 else 'right'
                composited = composite_speaker_on_background(path, position=position)
                clips.append(composited)
            else:
                logging.warning(f"Video file not found: {path}")

        if not clips:
            raise Exception("No valid video clips to combine")
        
        logging.info("Concatenating video clips...")
        final_clip = concatenate_videoclips(clips, method="compose")
        output_path = f"/app/output/{session_id}_debate.mp4"
        
        logging.info(f"Writing final video to: {output_path}")
        # Higher quality settings for better output
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=24,
            preset='medium',
            bitrate='5000k',
            verbose=False,
            logger=None
        )

        logging.info("Cleaning up clips...")
        for clip in clips:
            clip.close()
        final_clip.close()
        
        logging.info(f"Final video created: {output_path}")
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

        if not topic:
            return jsonify({'success': False, 'error': 'No topic provided'}), 400
        if not colab_url:
            return jsonify({'success': False, 'error': 'No Colab URL provided'}), 400

        logging.info(f"=== Starting debate generation ===")
        logging.info(f"Topic: {topic}")
        logging.info(f"Rounds: {rounds}")
        logging.info(f"Colab URL: {colab_url}")

        generator = DebateGenerator(colab_url)
        video_path, session_id = generator.generate_debate(topic, rounds)

        logging.info(f"=== Debate generation completed ===")
        return jsonify({
            'success': True,
            'video_path': video_path,
            'filename': f"{session_id}_debate.mp4"
        })
    except Exception as e:
        error_msg = str(e)
        logging.error(f"=== Debate generation FAILED ===")
        logging.error(f"Error: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': error_msg,
            'details': traceback.format_exc()
        }), 500


@app.route('/download/<filename>')
def download(filename):
    return send_file(f"/app/output/{filename}", as_attachment=True)


@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
