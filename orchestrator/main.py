import requests
import os
import json
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
import tempfile
import uuid
import time
from flask import Flask, request, jsonify

app = Flask(__name__)


class DebateGenerator:
    def __init__(self):
        self.text_service = "http://text-generation:8001"
        self.tts_service = "http://tts:8002"
        self.lipsync_service = "http://lipsync:8003"

    def generate_debate(self, topic, rounds=3):
        """Generate complete debate video"""
        session_id = str(uuid.uuid4())
        video_clips = []
        context = ""

        print(f"Starting debate generation for: {topic}")

        for round_num in range(rounds):
            print(f"Round {round_num + 1}/{rounds}")

            # Generate pro argument
            print("Generating pro argument...")
            pro_text = self._generate_text(topic, 'pro', context)
            print(f"Pro text: {pro_text[:100]}...")

            print("Generating pro audio...")
            pro_audio = self._generate_audio(pro_text, 'person1', session_id, f"pro_{round_num}")

            if pro_audio:
                print("Generating pro video...")
                pro_video = self._generate_lipsync('person1', pro_audio, session_id, f"pro_{round_num}")
                if pro_video and self._validate_video(pro_video):
                    video_clips.append(pro_video)
                    context += f"Pro argument: {pro_text}\n"
                else:
                    print("Failed to generate valid pro video")
                    continue
            else:
                print("Failed to generate pro audio")
                continue

            # Generate con argument
            print("Generating con argument...")
            con_text = self._generate_text(topic, 'con', context)
            print(f"Con text: {con_text[:100]}...")

            print("Generating con audio...")
            con_audio = self._generate_audio(con_text, 'person2', session_id, f"con_{round_num}")

            if con_audio:
                print("Generating con video...")
                con_video = self._generate_lipsync('person2', con_audio, session_id, f"con_{round_num}")
                if con_video and self._validate_video(con_video):
                    video_clips.append(con_video)
                    context += f"Con argument: {con_text}\n"
                else:
                    print("Failed to generate valid con video")
            else:
                print("Failed to generate con audio")

        if not video_clips:
            raise Exception("No valid video clips generated")

        # Combine all clips
        print(f"Combining {len(video_clips)} video clips...")
        final_video = self._combine_videos(video_clips, session_id)
        print(f"Final video saved: {final_video}")
        return final_video

    def _generate_text(self, topic, position, context):
        """Generate debate text"""
        try:
            response = requests.post(f"{self.text_service}/generate", json={
                'topic': topic,
                'position': position,
                'context': context
            }, timeout=6000)
            response.raise_for_status()

            result = response.json()
            content = result.get('content', '').strip()

            # Validate content
            if not content or len(content) < 10 or content == '...':
                print(f"Invalid text generated: '{content}', using fallback")
                raise Exception("Generated text too short or invalid")

            print(f"Generated text ({len(content)} chars): {content}")
            return content

        except Exception as e:
            print(f"Text generation error: {e}")
            # Fallback text
            if position == 'pro':
                return f"I strongly support the idea that {topic}. This technological advancement will bring significant benefits to society, including increased efficiency, reduced costs, and new opportunities for human creativity and innovation."
            else:
                return f"I disagree with the notion that {topic}. While technology advances rapidly, human skills like creativity, emotional intelligence, and complex problem-solving remain irreplaceable. We should focus on human-AI collaboration rather than replacement."

    def _generate_audio(self, text, speaker, session_id, clip_id):
        """Generate TTS audio"""
        try:
            # Send as JSON, not form data
            response = requests.post(f"{self.tts_service}/synthesize",
                                     json={
                                         'text': text,
                                         'speaker': speaker
                                     },
                                     timeout=6000
                                     )

            if response.status_code != 200:
                print(f"TTS error: {response.status_code} - {response.text}")
                return None

            audio_path = f"/tmp/{session_id}_{clip_id}_audio.wav"
            with open(audio_path, 'wb') as f:
                f.write(response.content)

            # Validate audio file
            if os.path.getsize(audio_path) < 1000:  # Less than 1KB is probably invalid
                print(f"Audio file too small: {os.path.getsize(audio_path)} bytes")
                return None

            return audio_path

        except Exception as e:
            print(f"Audio generation error: {e}")
            return None

    def _generate_lipsync(self, person, audio_path, session_id, clip_id):
        """Generate lip-synced video"""
        try:
            image_path = f"/app/assets/{person}.jpg"

            if not os.path.exists(image_path):
                print(f"Image not found: {image_path}")
                return None

            if not os.path.exists(audio_path):
                print(f"Audio not found: {audio_path}")
                return None

            print(f"Sending lipsync request: {image_path}, {audio_path}")

            files = {
                'image': ('face.jpg', open(image_path, 'rb'), 'image/jpeg'),
                'audio': ('audio.wav', open(audio_path, 'rb'), 'audio/wav')
            }

            response = requests.post(f"{self.lipsync_service}/lipsync",
                                     files=files,
                                     timeout=6000
                                     )

            # Close files
            files['image'][1].close()
            files['audio'][1].close()

            if response.status_code != 200:
                print(f"Lipsync error: {response.status_code} - {response.text}")
                return None

            video_path = f"/tmp/{session_id}_{clip_id}_video.mp4"
            with open(video_path, 'wb') as f:
                f.write(response.content)

            return video_path

        except Exception as e:
            print(f"Lipsync generation error: {e}")
            return None

    def _validate_video(self, video_path):
        """Validate video file"""
        try:
            if not os.path.exists(video_path):
                print(f"Video file doesn't exist: {video_path}")
                return False

            file_size = os.path.getsize(video_path)
            if file_size < 10000:  # Less than 10KB is probably invalid
                print(f"Video file too small: {file_size} bytes")
                return False

            # Try to open with moviepy
            clip = VideoFileClip(video_path)
            duration = clip.duration
            clip.close()

            if duration <= 0:
                print(f"Invalid video duration: {duration}")
                return False

            print(f"Video validated: {video_path}, duration: {duration}s, size: {file_size} bytes")
            return True

        except Exception as e:
            print(f"Video validation error: {e}")
            return False

    def _combine_videos(self, video_paths, session_id):
        """Combine video clips into final output"""
        try:
            clips = []
            for path in video_paths:
                if self._validate_video(path):
                    clips.append(VideoFileClip(path))

            if not clips:
                raise Exception("No valid video clips to combine")

            final_clip = concatenate_videoclips(clips, method="compose")

            output_path = f"/app/output/{session_id}_debate.mp4"
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f"/tmp/{session_id}_temp_audio.m4a",
                remove_temp=True
            )

            # Cleanup
            for clip in clips:
                clip.close()
            final_clip.close()

            return output_path

        except Exception as e:
            print(f"Video combination error: {e}")
            raise


@app.route('/generate', methods=['POST'])
def generate_debate():
    try:
        data = request.json
        topic = data.get('topic', 'Artificial Intelligence')
        rounds = data.get('rounds', 2)

        generator = DebateGenerator()
        video_path = generator.generate_debate(topic, rounds)

        return jsonify({
            'success': True,
            'video_path': video_path,
            'message': f'Debate video generated successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'orchestrator'})


if __name__ == '__main__':
    # Test with a simple topic
    generator = DebateGenerator()
    topic = "Artificial Intelligence will replace most human jobs within 20 years"
    try:
        video_path = generator.generate_debate(topic, rounds=1)
        print(f"Success! Video saved to: {video_path}")
    except Exception as e:
        print(f"Error: {e}")