# Repository Guidelines

This guide keeps contributors aligned on the AI debate generator stack, from Flask services to media tooling. Use it alongside the root `README.md` when spinning up or modifying services.

## Project Structure & Module Organization
- `orchestrator/` runs the Flask UI, calls text/voice services, stitches clips with MoviePy, and writes renders to `output/`.
- `text-generation/` exposes a Flask API that proxies LM Studio at `host.docker.internal:1234` with fallbacks in `text_generator.py`.
- `tts/` wraps ElevenLabs or gTTS for voice tracks; `ffmpeg` conversions happen inside the container.
- `assets/` stores speaker images and backgrounds consumed by the orchestrator; `output/` collects finished debates.
- `SadTalker_Colab.ipynb` documents the remote lip-sync flow; keep an active ngrok URL before attempting full runs.

## Build, Test, and Development Commands
- `docker-compose up --build` — rebuilds and launches orchestrator (8000), text generation (8001), and TTS (8002).
- `docker-compose logs -f orchestrator` — tails orchestrator logs to watch LM Studio and TTS requests.
- `python test_pipeline.py` — runs smoke checks for text, TTS, and orchestrator endpoints while containers are live.
- `python test_pipeline.py --colab-url <https://xxxx.ngrok.io>` — exercises the full video pipeline once SadTalker is reachable.

## Coding Style & Naming Conventions
- Follow PEP 8: four-space indentation, `snake_case` functions, and descriptive constants like `LM_STUDIO_URL`.
- Keep Flask routes slim; move media or API helpers into dedicated modules.
- Prefer `logging` over `print` for flow (`logging.info`) and errors (`logging.error`).

## Testing Guidelines
- Extend `test_pipeline.py` when adding endpoints or media paths; assert HTTP status codes and key payload fields.
- Run the base smoke tests before opening a PR; document Colab URLs for video or lip-sync changes.
- Note residual test gaps (e.g., missing assets) in PR descriptions if they block automation.

## Commit & Pull Request Guidelines
- Use imperative, capitalized commit subjects (e.g., `Add orchestrator retry logic`); group related changes per commit.
- PRs should describe intent, list local test runs, link issues or notebooks, and include sample output paths from `output/`.
- Flag configuration updates (LM Studio endpoints, API keys) so reviewers can adjust their environments quickly.

## Security & Configuration Tips
- Store API keys (e.g., `ELEVENLABS_API_KEY`) in `.env` only; never commit credentials.
- Keep LM Studio on port 1234 for health checks, and document overrides in PR notes if you deviate.
- Validate `assets/` filenames (`person1.jpg`, `person2.jpg`) before publishing, especially when swapping speaker media.
