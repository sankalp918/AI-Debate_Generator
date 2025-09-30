from flask import Flask, request, jsonify, send_file
import os
import sys
import uuid
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

# Add SadTalker to Python path
sys.path.append('/app/SadTalker')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

SADTALKER_PATH = "/app/SadTalker"


def setup_sadtalker_environment():
    """Setup SadTalker environment variables and paths"""
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # Force first GPU
    os.environ['TORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'



def check_models():
    """Check if required models are available"""
    required_models = [
        f"{SADTALKER_PATH}/checkpoints/mapping_00109-model.pth.tar",
        f"{SADTALKER_PATH}/checkpoints/mapping_00229-model.pth.tar",
        f"{SADTALKER_PATH}/checkpoints/SadTalker_V002.safetensors"
    ]

    missing = [model for model in required_models if not os.path.exists(model)]
    return len(missing) == 0, missing


@app.route('/lipsync', methods=['POST'])
def create_lipsync():
    logging.info("Starting SadTalker lip sync generation")

    try:
        # Validate request
        if 'image' not in request.files or 'audio' not in request.files:
            return jsonify({'error': 'Missing image or audio file'}), 400

        image_file = request.files['image']
        audio_file = request.files['audio']

        if not image_file.filename or not audio_file.filename:
            return jsonify({'error': 'Empty filenames'}), 400

        # Setup temporary directory
        session_id = str(uuid.uuid4())
        temp_dir = f"/tmp/sadtalker_{session_id}"
        os.makedirs(temp_dir, exist_ok=True)

        # Save input files
        image_path = f"{temp_dir}/source_image.jpg"
        audio_path = f"{temp_dir}/audio.wav"
        results_dir = f"{temp_dir}/results"

        image_file.save(image_path)
        audio_file.save(audio_path)

        # Validate files
        if os.path.getsize(image_path) < 5000:
            return jsonify({'error': 'Image file too small'}), 400
        if os.path.getsize(audio_path) < 5000:
            return jsonify({'error': 'Audio file too small'}), 400

        logging.info(f"Processing: image={os.path.getsize(image_path)}B, audio={os.path.getsize(audio_path)}B")

        # Setup SadTalker environment
        setup_sadtalker_environment()

        # Run SadTalker inference
        cmd = [
            'python', 'inference.py',
            '--driven_audio', audio_path,
            '--source_image', image_path,
            '--result_dir', results_dir,
            '--still',  # Use still mode for single image
            '--preprocess', 'crop',  # Crop face from image
            '--enhancer', 'gfpgan'  # Use GFPGAN for face enhancement
        ]

        logging.info(f"Running SadTalker: {' '.join(cmd)}")

        # Run from SadTalker directory
        result = subprocess.run(
            cmd,
            cwd=SADTALKER_PATH,
            capture_output=True,
            text=True,
            timeout=6000  # 10 minute timeout
        )

        logging.info(f"SadTalker completed with code: {result.returncode}")

        if result.stdout:
            logging.info(f"Stdout: {result.stdout}")
        if result.stderr:
            logging.info(f"Stderr: {result.stderr}")

        # Find generated video
        output_files = []
        if os.path.exists(results_dir):
            for root, dirs, files in os.walk(results_dir):
                for file in files:
                    if file.endswith('.mp4'):
                        output_files.append(os.path.join(root, file))

        if result.returncode == 0 and output_files:
            # Use the first (and typically only) output file
            output_path = output_files[0]
            file_size = os.path.getsize(output_path)

            if file_size < 50000:  # Less than 50KB is probably broken
                return jsonify({'error': f'Generated video too small: {file_size}B'}), 500

            logging.info(f"SadTalker success: {file_size} bytes")

            # Copy to a temporary location for serving
            final_output = f"/tmp/{session_id}_sadtalker.mp4"
            shutil.copy2(output_path, final_output)

            return send_file(
                final_output,
                as_attachment=True,
                download_name=f"{session_id}_talking.mp4",
                mimetype='video/mp4'
            )
        else:
            error_msg = f"SadTalker failed: {result.stderr}"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 500

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'SadTalker generation timed out (10 minutes)'}), 500
    except Exception as e:
        logging.error(f"SadTalker error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        # Cleanup
        try:
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    models_ok, missing_models = check_models()

    # Check if CUDA is available
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        device_count = torch.cuda.device_count()
    except:
        cuda_available = False
        device_count = 0

    return jsonify({
        'status': 'healthy' if models_ok else 'unhealthy',
        'service': 'sadtalker',
        'models_available': models_ok,
        'missing_models': missing_models if not models_ok else [],
        'cuda_available': cuda_available,
        'gpu_count': device_count,
        'sadtalker_path': SADTALKER_PATH
    })


@app.route('/models', methods=['GET'])
def list_models():
    """List available models"""
    models_dir = f"{SADTALKER_PATH}/checkpoints"
    models = []

    if os.path.exists(models_dir):
        for file in os.listdir(models_dir):
            if file.endswith(('.pth', '.tar', '.safetensors')):
                file_path = os.path.join(models_dir, file)
                models.append({
                    'name': file,
                    'size': os.path.getsize(file_path),
                    'path': file_path
                })

    return jsonify({'models': models})


if __name__ == '__main__':
    logging.info("Starting SadTalker service...")

    # Check models on startup
    models_ok, missing = check_models()
    if models_ok:
        logging.info("All required models found")
    else:
        logging.warning(f"Missing models: {missing}")

    app.run(host='0.0.0.0', port=8003, debug=False)
