from flask import Flask, request, jsonify, send_file
from gtts import gTTS
from elevenlabs import generate, set_api_key, voices, Voice, VoiceSettings
import tempfile
import uuid
import os
import subprocess
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Set ElevenLabs API key from environment
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
if ELEVENLABS_API_KEY:
    set_api_key(ELEVENLABS_API_KEY)
    logging.info("ElevenLabs API key configured")
else:
    logging.warning("No ElevenLabs API key found, will use gTTS fallback")

# ElevenLabs voices for realistic speech
# Using professional-sounding voices for debate
ELEVENLABS_VOICES = {
    'person1': {
        'voice_id': 'pNInz6obpgDQGcFmaJgB',  # Adam - Deep, authoritative male voice
        'settings': VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.3,
            use_speaker_boost=True
        )
    },
    'person2': {
        'voice_id': 'EXAVITQu4vr4xnSDxMaL',  # Bella - Professional, confident female voice
        'settings': VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.3,
            use_speaker_boost=True
        )
    }
}

# Fallback gTTS voices
GTTS_VOICES = {
    'person1': {'lang': 'en', 'tld': 'com', 'slow': False},
    'person2': {'lang': 'en', 'tld': 'co.uk', 'slow': False}
}


def generate_with_elevenlabs(text, speaker):
    """Generate speech using ElevenLabs API"""
    try:
        voice_config = ELEVENLABS_VOICES.get(speaker, ELEVENLABS_VOICES['person1'])
        settings = voice_config['settings']

        # Generate audio with ElevenLabs (v0.2.27 API)
        # Note: This version only supports stability and similarity_boost
        audio = generate(
            text=text,
            voice=voice_config['voice_id'],
            model="eleven_multilingual_v2"
        )
        
        return audio
    except Exception as e:
        logging.error(f"ElevenLabs generation error: {e}")
        return None


def generate_with_gtts(text, speaker):
    """Fallback to gTTS for speech generation"""
    try:
        config = GTTS_VOICES.get(speaker, GTTS_VOICES['person1'])
        tts = gTTS(
            text=text,
            lang=config['lang'],
            tld=config.get('tld', 'com'),
            slow=config['slow']
        )
        return tts
    except Exception as e:
        logging.error(f"gTTS generation error: {e}")
        return None


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

        # Generate unique filename
        session_id = str(uuid.uuid4())
        temp_dir = f"/tmp/tts_{session_id}"
        os.makedirs(temp_dir, exist_ok=True)

        mp3_path = f"{temp_dir}/speech.mp3"
        wav_path = f"{temp_dir}/speech.wav"

        try:
            # Try ElevenLabs first if API key is available
            if ELEVENLABS_API_KEY:
                logging.info("Using ElevenLabs TTS")
                audio_bytes = generate_with_elevenlabs(text, speaker)
                
                if audio_bytes:
                    # Save ElevenLabs audio directly to MP3
                    with open(mp3_path, 'wb') as f:
                        f.write(audio_bytes)
                else:
                    logging.warning("ElevenLabs failed, falling back to gTTS")
                    # Fallback to gTTS
                    tts = generate_with_gtts(text, speaker)
                    if tts:
                        tts.save(mp3_path)
                    else:
                        return jsonify({'error': 'All TTS methods failed'}), 500
            else:
                # Use gTTS as primary if no ElevenLabs key
                logging.info("Using gTTS (no ElevenLabs API key)")
                tts = generate_with_gtts(text, speaker)
                if tts:
                    tts.save(mp3_path)
                else:
                    return jsonify({'error': 'TTS generation failed'}), 500

            if not os.path.exists(mp3_path):
                return jsonify({'error': 'Failed to generate MP3'}), 500

            # Convert to WAV with specific format for lip sync compatibility
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', mp3_path,
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '16000',  # 16kHz sample rate (SadTalker requirement)
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