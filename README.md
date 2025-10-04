# AI Debate Generator

An automated debate video generation system that creates realistic debate videos using AI-powered text generation, text-to-speech, and lip-sync animation. The system generates arguments for both sides of a debate topic, converts them to speech, and creates animated videos with synchronized lip movements.

## 🎯 Features

- **AI-Powered Debate Generation**: Generate compelling arguments for both sides of any debate topic
- **Text-to-Speech**: Convert generated text to natural-sounding speech with different voices for each debater
- **Lip-Sync Animation**: Create realistic talking head videos using SadTalker with GPU acceleration
- **Microservices Architecture**: Modular Docker-based architecture for scalability and maintainability
- **Web Interface**: Simple web UI to input debate topics and generate videos
- **Flexible Rounds**: Support for multiple debate rounds (1-3 rounds)

## 🏗️ Architecture

The system consists of four main components:

1. **Orchestrator Service** (Port 8000)
   - Main entry point and coordination service
   - Web UI for user interaction
   - Handles the complete pipeline workflow
   - Manages video assembly and output

2. **Text Generation Service** (Port 8001)
   - Generates debate arguments using LM Studio or fallback templates
   - Supports both pro and con positions
   - Integrates with local LLM models

3. **Text-to-Speech Service** (Port 8002)
   - Converts text to speech using gTTS
   - Supports different voices/accents for each debater
   - Outputs WAV files optimized for lip-sync

4. **SadTalker (Google Colab)**
   - Runs on Google Colab with A100 GPU runtime
   - Generates realistic lip-sync animations
   - Exposed via ngrok tunnel

## 📋 Prerequisites

### Local Setup
- Docker and Docker Compose
- Python 3.8+ (for local testing)
- LM Studio (optional, for local LLM text generation)
- 8GB+ RAM recommended

### Google Colab Setup
- Google account with Colab access
- Colab Pro/Pro+ recommended for A100 GPU access
- ngrok account for tunneling

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
    git clone <repository-url>
    cd AI-Debate_Generator
```

### 2. Setup Local Services

Create required directories:
```bash
    mkdir -p output assets
```

Add debate avatar images to the `assets/` folder:
- `person1.jpg` - Image for first debater
- `person2.jpg` - Image for second debater
- `background.jpg` - Optional background image

### 3. Start Docker Services

Build and start all services:
```bash
    docker-compose up --build
```

This will start:
- Text Generation Service on http://localhost:8001
- TTS Service on http://localhost:8002
- Orchestrator Service on http://localhost:8000

### 4. Setup SadTalker on Google Colab

**Important**: SadTalker must run on Google Colab with A100 GPU runtime for optimal performance.

1. Open `SadTalker_Colab.ipynb` in Google Colab
2. Select Runtime → Change runtime type → A100 GPU
3. Run all cells in the notebook to:
   - Install Python 3.8 and dependencies
   - Clone and setup SadTalker repository
   - Download required models
   - Start Flask API service
   - Expose via ngrok tunnel

4. Copy the ngrok URL (e.g., `https://xxxx-xx-xx.ngrok.io`)

### 5. Configure LM Studio (Optional)

For better text generation quality:

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Load a model (recommended: OpenAI GPT-4 or similar)
3. Start the local server on port 1234
4. The system will automatically use LM Studio if available, otherwise fallback to template responses

## 🎬 Usage

### Web Interface

1. Open your browser and navigate to http://localhost:8000
2. Fill in the form:
   - **Debate Topic**: Enter any debate topic (e.g., "AI will replace most human jobs within 20 years")
   - **Number of Rounds**: Select 1-3 rounds
   - **Colab API URL**: Paste the ngrok URL from your Colab notebook
3. Click "Generate Debate"
4. Wait for processing (may take several minutes)
5. Download the generated video

### API Usage

Generate a debate programmatically:

```bash
    curl -X POST http://localhost:8000/generate \
      -H "Content-Type: application/json" \
      -d '{
        "topic": "AI will improve healthcare outcomes",
        "rounds": 2,
        "colab_url": "https://your-ngrok-url.ngrok.io"
      }'
```

### Testing Individual Services

Test the pipeline components:

```bash
    python test_pipeline.py
```

## 📁 Project Structure

```
AI-Debate_Generator/
├── docker-compose.yml          # Docker orchestration config
├── README.md                   # This file
├── SadTalker_Colab.ipynb      # Colab notebook for lip-sync
├── test_pipeline.py           # Testing script
├── assets/                    # Input images
│   ├── person1.jpg           # Debater 1 avatar
│   ├── person2.jpg           # Debater 2 avatar
│   └── background.jpg        # Background image
├── output/                    # Generated videos (created automatically)
├── orchestrator/             # Main coordination service
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── text-generation/          # Text generation service
│   ├── Dockerfile
│   ├── text_generator.py
│   └── requirements.txt
└── tts/                      # Text-to-speech service
    ├── Dockerfile
    ├── tts_service.py
    └── requirements.txt
```

## 🔧 Configuration

### Environment Variables

You can customize the services using environment variables in `docker-compose.yml`:

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - LM_STUDIO_URL=http://host.docker.internal:1234
```

### Voice Configuration

Edit `tts/tts_service.py` to customize voices:

```python
VOICES = {
    'person1': {'lang': 'en', 'tld': 'com', 'slow': False},
    'person2': {'lang': 'en', 'tld': 'co.uk', 'slow': False}
}
```

## 🐛 Troubleshooting

### Services Not Starting
- Check if ports 8000, 8001, 8002 are available
- Run `docker-compose logs` to see error messages
- Ensure Docker has sufficient memory allocation (8GB+)

### LM Studio Connection Issues
- Verify LM Studio is running on port 1234
- Check firewall settings
- The system will use fallback templates if LM Studio is unavailable

### Colab Connection Issues
- Ensure ngrok tunnel is active in Colab
- Check if Colab runtime is still active (reconnect if needed)
- Verify A100 GPU is allocated in Colab settings

### Video Generation Fails
- Check that avatar images exist in `assets/` folder
- Ensure images are in supported formats (JPG, PNG)
- Verify sufficient disk space in `output/` directory

### Audio Quality Issues
- TTS generates 16kHz mono WAV files for optimal lip-sync
- FFmpeg is used for audio format conversion
- Check TTS service logs for conversion errors

## 📦 Dependencies

### Core Services
- **Flask**: Web framework for microservices
- **Docker**: Containerization platform
- **MoviePy**: Video editing and assembly
- **gTTS**: Google Text-to-Speech
- **Requests**: HTTP client library

### SadTalker (Colab)
- **PyTorch**: Deep learning framework
- **SadTalker**: Lip-sync animation model
- **FFmpeg**: Video/audio processing
- **ngrok**: Tunneling service

## 🚀 Performance Tips

1. **Use Colab Pro/Pro+**: A100 GPU significantly speeds up video generation
2. **Local LLM**: LM Studio provides better debate quality than fallbacks
3. **Image Quality**: Higher resolution avatars (1024x1024) produce better results
4. **Shorter Debates**: 1-2 rounds process faster than 3 rounds
5. **Keep Colab Active**: Colab may disconnect after inactivity

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional TTS voice options
- More sophisticated debate logic
- Video editing features (transitions, backgrounds)
- Support for more languages
- Real-time progress tracking

## 📄 License

This project is provided as-is for educational and research purposes.

## 🙏 Acknowledgments

- [SadTalker](https://github.com/OpenTalker/SadTalker) - Lip-sync animation model
- [LM Studio](https://lmstudio.ai/) - Local LLM runtime
- [gTTS](https://github.com/pndurette/gTTS) - Text-to-speech library
- [MoviePy](https://zulko.github.io/moviepy/) - Video editing library

**Note**: This system requires significant computational resources. The SadTalker component MUST run on Google Colab with A100 GPU runtime for acceptable performance. Local GPU execution is possible but requires NVIDIA GPU with 16GB+ VRAM and proper CUDA setup.

