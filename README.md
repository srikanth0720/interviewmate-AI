# InterviewMate AI

A voice-based interview practice MVP built with FastAPI, SQLite, Gnani Prisma (speech-to-text), and Gnani Timbre (text-to-speech).

## Features

- Python, DSA, DBMS, HR and Behavioral question categories
- Browser microphone recording encoded as WAV
- Gnani Prisma transcription (REST, max 30 seconds per clip)
- Structured interview feedback and score breakdown
- Optional OpenAI-compatible LLM evaluation endpoint
- Transparent local demo scoring when no LLM endpoint is configured
- Gnani Timbre spoken feedback
- SQLite session history
- Responsive frontend

## Requirements

- Python 3.10+
- A Gnani API key with STT and TTS permissions/credits
- Modern browser with microphone access
- Internet access to call Gnani APIs

## Setup (Windows PowerShell)

```powershell
cd InterviewMate-AI
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example backend\.env
```

Open `.env` and set `GNANI_API_KEY`. Keep this file private. Do not upload it to GitHub.

Run the app from the project root:

```powershell
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000

## Setup (macOS/Linux)

```bash
cd InterviewMate-AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GNANI_API_KEY
uvicorn backend.main:app --reload
```

## Gnani integration

### Prisma STT

The app calls `POST https://api.vachana.ai/stt/v3` with:

- Header: `X-API-Key-ID`
- Multipart file field: `audio_file`
- `model=prisma-v3.0`
- `language_code=en-IN`, `te-IN`, `hi-IN`, or `indic-auto`

Prisma REST supports audio up to 30 seconds and formats including WAV, MP3, OGG, FLAC, AAC and M4A. The frontend creates a mono 16 kHz WAV file.

### Timbre TTS

The app calls `POST https://api.vachana.ai/api/v1/tts/inference` with the Timbre model and returns the generated WAV audio to the browser. The selected voice is controlled by `GNANI_TTS_VOICE`.

## Evon / evaluation mode

The contest email says Evon is available on Hugging Face, but this project does not assume that your account has a hosted Evon API. If Gnani provides an OpenAI-compatible inference endpoint, set `EVON_API_URL`, `EVON_API_KEY`, and `EVON_MODEL` in `.env`.

If no endpoint is configured, the app uses a clearly labelled **development fallback scoring heuristic**. This is not an LLM and should not be presented as Evon-powered evaluation in your public demo. Ask Gnani for the approved Evon endpoint before claiming Evon integration.

## API routes

- `GET /api/health`
- `GET /api/questions?category=Python`
- `POST /api/interview/start`
- `POST /api/transcribe` (multipart: `audio`, `language_code`)
- `POST /api/evaluate`
- `POST /api/speak` (multipart: `text`, `language`)
- `GET /api/history`
- `GET /api/interview/{session_id}`

## Troubleshooting

- **403 / forbidden:** check API key, account permissions and remaining programme credits.
- **429 from Timbre:** wait for the active request to finish before sending another.
- **Unsupported language:** check Gnani's current supported-language list and use a valid language code.
- **No microphone:** use localhost or HTTPS, allow browser microphone permission, and use a modern browser.
- **Prisma duration error:** keep each recording to 30 seconds or less.
- **No semantic evaluation:** configure an approved LLM endpoint; the default fallback is only for UI development.

## Deployment notes

Deploy the FastAPI application as one service first. Set the environment variables in the hosting provider's secret/environment settings. Do not deploy `.env` or commit API credentials. For SQLite persistence on cloud hosts, use a persistent disk; otherwise use a managed PostgreSQL database and set `DATABASE_URL`.

## Disclaimer

This is a starter MVP. Verify current model access, account limits, supported languages, voice names, and the Evon inference route in your own Gnani dashboard before submission.
