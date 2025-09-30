from flask import Flask, request, jsonify, send_file
from gtts import gTTS
import tempfile
import uuid
import os
import subprocess
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VOICES = {
    'person1': {'lang': 'en', 'tld': 'com', 'slow': False},
    'person2': {'lang': 'en', 'tld': 'co.uk', 'slow': False}  # Different accent
}


@app.route('/synthesize', methods=['POST'])
def synthesize():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        text = data.get('text', '')
        speaker = data.get('speaker', 'person1')

        logging.info(f"TTS request: speaker={speaker}, text_length={len(text)}")

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        if len(text.strip()) == 0:
            return jsonify({'error': 'Empty text provided'}), 400

        # Get voice config
        config = VOICES.get(speaker, VOICES['person1'])

        # Generate unique filename
        session_id = str(uuid.uuid4())
        temp_dir = f"/tmp/tts_{session_id}"
        os.makedirs(temp_dir, exist_ok=True)

        mp3_path = f"{temp_dir}/speech.mp3"
        wav_path = f"{temp_dir}/speech.wav"

        try:
            # Generate speech with gTTS
            tts = gTTS(
                text=text,
                lang=config['lang'],
                tld=config.get('tld', 'com'),
                slow=config['slow']
            )

            # Save to MP3
            tts.save(mp3_path)

            if not os.path.exists(mp3_path):
                return jsonify({'error': 'Failed to generate MP3'}), 500

            # Convert to WAV with specific format for lip sync compatibility
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', mp3_path,
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '16000',  # 16kHz sample rate (Wav2Lip requirement)
                '-ac', '1',  # Mono
                '-y',  # Overwrite
                wav_path
            ]

            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logging.error(f"FFmpeg error: {result.stderr}")
                return jsonify({'error': f'Audio conversion failed: {result.stderr}'}), 500

            if not os.path.exists(wav_path):
                return jsonify({'error': 'WAV file not generated'}), 500

            # Validate output
            file_size = os.path.getsize(wav_path)
            if file_size < 1000:  # Less than 1KB is probably invalid
                return jsonify({'error': f'Generated audio too small: {file_size} bytes'}), 500

            logging.info(f"TTS success: {wav_path}, size: {file_size} bytes")

            return send_file(
                wav_path,
                as_attachment=True,
                download_name=f"{session_id}_speech.wav",
                mimetype='audio/wav'
            )

        finally:
            # Cleanup MP3 (keep WAV for now as it's being sent)
            try:
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
            except:
                pass

    except Exception as e:
        logging.error(f"TTS error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'tts'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=False)