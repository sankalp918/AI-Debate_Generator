# Quick Start Guide - Enhanced Realistic Debates

## 🚀 Get Professional-Quality AI Debates in 5 Steps

### Step 1: Get Your ElevenLabs API Key (Recommended)
1. Go to [elevenlabs.io](https://elevenlabs.io/) and sign up
2. Get your API key from the dashboard
3. Copy `.env.example` to `.env`
4. Add your key: `ELEVENLABS_API_KEY=your_key_here`

**Without ElevenLabs**: The system works fine with free gTTS, just less realistic.

### Step 2: Prepare Your Assets
```bash
    # Create directories
    mkdir -p assets output
    
    # Add images to assets folder
    # - assets/person1.jpg (first debater headshot)
    # - assets/person2.jpg (second debater headshot) 
    # - assets/podcast_background.jpg (optional - will auto-generate if missing)
```

**Image Tips**:
- Use clear, well-lit headshots
- Face should be clearly visible
- 1024x1024 recommended resolution
- Front-facing photos work best

### Step 3: Start Docker Services
```bash
  docker-compose up --build
```

Wait for all services to be healthy (about 2-3 minutes first time).

### Step 4: Setup SadTalker on Google Colab
1. Open `SadTalker_Colab.ipynb` in [Google Colab](https://colab.research.google.com/)
2. Change runtime: Runtime → Change runtime type → A100 GPU
3. Run all cells (takes ~10 minutes first time)
4. Copy the ngrok URL that appears (e.g., `https://xxxx-xxxx.ngrok.io`)

**Important**: Follow `SADTALKER_UPGRADE_INSTRUCTIONS.md` to enable enhanced expressions!

### Step 5: Generate Your First Debate!
1. Open `http://localhost:8000` in your browser
2. Enter a debate topic (e.g., "AI will improve healthcare")
3. Select number of rounds (1-3)
4. Paste your Colab ngrok URL
5. Click "Generate Debate"
6. Wait 5-10 minutes (depends on length)
7. Download your professional debate video!

## 🎭 What You Get

### With ElevenLabs + Enhanced SadTalker:
- ✅ Ultra-realistic human voices with emotion
- ✅ Natural head movements and gestures
- ✅ Expressive facial animations
- ✅ Professional podcast-style layout
- ✅ 1080p HD quality
- ✅ Professional face enhancement

### With Free Options (gTTS):
- ✅ Functional debate videos
- ✅ Basic facial animations
- ✅ Standard quality
- ⚠️ Less realistic voices
- ⚠️ Minimal gestures (unless you apply SadTalker enhancements)

## 💡 Pro Tips

### For Maximum Realism:
1. **Use ElevenLabs** - The voice quality difference is massive
2. **Apply Enhanced SadTalker Parameters** - See `SADTALKER_UPGRADE_INSTRUCTIONS.md`
3. **Use High-Quality Images** - Good lighting, clear faces
4. **Add Custom Podcast Background** - Makes it look like a real studio
5. **Use Colab Pro with A100** - 3-4x faster processing

### Voice Customization:
The system uses:
- **Person 1**: Adam (deep male voice)
- **Person 2**: Bella (professional female voice)

To change voices, edit `tts/tts_service.py` and browse [ElevenLabs Voice Library](https://elevenlabs.io/voice-library)

### Background Customization:
- Add `assets/podcast_background.jpg` for custom studio look
- Without it, auto-generates a professional gradient
- Use podcast studio images for authenticity

## 🔍 Troubleshooting

**"Connection refused" errors**
- Wait for Docker services to fully start (check with `docker-compose logs`)

**"ElevenLabs API error"**
- Check your API key in `.env`
- Verify you have credits in your ElevenLabs account
- System will auto-fallback to gTTS if there's an issue

**"No video generated"**
- Ensure Colab session is active
- Check ngrok URL is correct and working
- Look at Colab output for errors

**Videos look stiff/robotic**
- Apply enhanced SadTalker parameters (see `SADTALKER_UPGRADE_INSTRUCTIONS.md`)
- Increase `expression_scale` to 1.5 for more movement

**Slow generation**
- Use Colab Pro with A100 GPU
- Reduce to 1 round for faster testing
- Check if Colab disconnected

## 📊 Expected Processing Times

With A100 GPU + ElevenLabs:
- **1 Round**: ~3-5 minutes
- **2 Rounds**: ~6-8 minutes  
- **3 Rounds**: ~10-15 minutes

With T4 GPU + gTTS:
- **1 Round**: ~8-12 minutes
- **2 Rounds**: ~15-20 minutes
- **3 Rounds**: ~25-35 minutes

## 🎯 Example Topics to Try

- "Remote work is better than office work"
- "AI will create more jobs than it destroys"
- "Social media has a net positive impact on society"
- "Electric vehicles are the future of transportation"
- "Space exploration should be prioritized over ocean exploration"

## 📚 Next Steps

- Read `README.md` for detailed configuration options
- See `SADTALKER_UPGRADE_INSTRUCTIONS.md` for gesture enhancements
- Customize voices in `tts/tts_service.py`
- Add your own podcast background images
- Experiment with debate topics and rounds

## 🆘 Need Help?

Check the logs:
```bash
    # See all service logs
    docker-compose logs
    
    # See specific service
    docker-compose logs tts
    docker-compose logs orchestrator
```

Happy debating! 🎤
