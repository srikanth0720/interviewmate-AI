import httpx
from fastapi import HTTPException
from backend.config import settings


# Check API key
def require_gnani_key():

    if not settings.gnani_api_key:
        raise HTTPException(
            status_code=503,
            detail="Gnani API key is not configured."
        )


# -----------------------------------
# SPEECH TO TEXT (STT)
# -----------------------------------

async def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    language_code: str
):

    require_gnani_key()

    headers = {
        "X-API-Key-ID": settings.gnani_api_key
    }

    files = {
        "audio_file": (
            filename or "answer.wav",
            audio_bytes,
            content_type or "audio/wav"
        )
    }

    data = {
        "model": settings.stt_model,
        "language_code": language_code
    }

    timeout = httpx.Timeout(90.0, connect=20.0)

    async with httpx.AsyncClient(timeout=timeout) as client:

        response = await client.post(
            settings.stt_url,
            headers=headers,
            files=files,
            data=data
        )

    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"Prisma request failed ({response.status_code}): {response.text[:500]}"
        )

    payload = response.json()

    transcript = payload.get("transcript") or payload.get("text")

    # Handle empty transcription
    if not transcript or not transcript.strip():

        raise HTTPException(
            status_code=422,
            detail={
                "message": "No speech was detected in the audio.",
                "request_id": payload.get("request_id"),
                "model": payload.get("model"),
                "processing_time": payload.get("processing_time")
            }
        )

    return {
        "transcript": transcript,
        "detected_language_code": payload.get("detected_language_code"),
        "model": payload.get("model", settings.stt_model),
        "request_id": payload.get("request_id")
    }


# -----------------------------------
# TEXT TO SPEECH (TTS)
# -----------------------------------

async def synthesize_speech(text: str, language: str = "en-IN"):

    require_gnani_key()

    payload = {
        "text": text[:3000],
        "voice": settings.tts_voice,
        "model": settings.tts_model,
        "language": language,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav"
        }
    }

    headers = {
        "X-API-Key-ID": settings.gnani_api_key,
        "Content-Type": "application/json"
    }

    timeout = httpx.Timeout(120.0, connect=20.0)

    async with httpx.AsyncClient(timeout=timeout) as client:

        response = await client.post(
            settings.tts_url,
            headers=headers,
            json=payload
        )

    if response.is_error:

        raise HTTPException(
            status_code=502,
            detail=f"Timbre request failed ({response.status_code}): {response.text[:500]}"
        )

    return (
        response.content,
        response.headers.get("content-type", "audio/wav")
    )