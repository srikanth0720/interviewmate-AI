import json
from pathlib import Path
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.database import Base, engine, get_db
from backend.models import InterviewSession, InterviewAnswer
from backend.schemas import StartSessionRequest, EvaluateRequest
from backend.questions import QUESTIONS
from backend.services.gnani import transcribe_audio, synthesize_speech
from backend.services.evaluator import evaluate_answer

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
Base.metadata.create_all(bind=engine)

app = FastAPI(title="InterviewMate AI", version="1.0.0", description="Voice-based AI interview coach using Gnani Prisma and Timbre.")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/api/health")
def health():
    from backend.config import settings
    return {
        "status": "ok",
        "gnani_key_configured": bool(settings.gnani_api_key),
        "evon_endpoint_configured": bool(settings.evon_api_url),
        "models": {"stt": settings.stt_model, "tts": settings.tts_model}
    }

@app.get("/api/questions")
def get_questions(category: str = "Python"):
    if category not in QUESTIONS:
        raise HTTPException(status_code=404, detail="Unknown interview category.")
    return {"category": category, "questions": QUESTIONS[category]}

@app.post("/api/interview/start")
def start_interview(payload: StartSessionRequest, db: Session = Depends(get_db)):
    if payload.category not in QUESTIONS:
        raise HTTPException(status_code=400, detail="Unsupported category.")
    session = InterviewSession(category=payload.category, language=payload.language)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "category": session.category, "language": session.language}

@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language_code: str = Form("en-IN")
):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Audio file is empty.")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file is too large (15 MB maximum).")
    allowed = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/flac", "audio/aac", "audio/mp4", "audio/x-m4a"}
    content_type = audio.content_type or "application/octet-stream"
    if content_type not in allowed and not (audio.filename or "").lower().endswith((".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a")):
        raise HTTPException(status_code=415, detail="Unsupported audio format. Please record WAV or upload WAV/MP3/M4A.")
    return await transcribe_audio(data, audio.filename or "answer.wav", content_type, language_code)

@app.post("/api/evaluate")
async def evaluate(payload: EvaluateRequest, db: Session = Depends(get_db)):
    session = db.get(InterviewSession, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    result = await evaluate_answer(payload.question, payload.transcript)
    total = float(result.get("total_score", 0))
    answer = InterviewAnswer(
        session_id=session.id,
        question=payload.question,
        transcript=payload.transcript,
        total_score=total,
        evaluation_json=json.dumps(result, ensure_ascii=False)
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return {"answer_id": answer.id, **result}

@app.post("/api/speak")
async def speak(text: str = Form(...), language: str = Form("en-IN")):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")
    audio, content_type = await synthesize_speech(text.strip(), language)
    return Response(content=audio, media_type=content_type, headers={"Content-Disposition": 'inline; filename="interviewmate-feedback.wav"'})

@app.get("/api/history")
def history(db: Session = Depends(get_db)):
    sessions = db.query(InterviewSession).order_by(desc(InterviewSession.created_at)).limit(30).all()
    output = []
    for session in sessions:
        answers = sorted(session.answers, key=lambda x: x.created_at)
        scores = [a.total_score for a in answers]
        output.append({
            "session_id": session.id,
            "category": session.category,
            "language": session.language,
            "created_at": session.created_at.isoformat(),
            "answers_count": len(answers),
            "average_score": round(sum(scores) / len(scores), 1) if scores else None
        })
    return {"history": output}

@app.delete("/api/history")
def clear_history(db: Session = Depends(get_db)):
    try:
        sessions = db.query(InterviewSession).all()
        deleted_count = len(sessions)

        for session in sessions:
            db.delete(session)

        db.commit()

        return {
            "message": "Interview history cleared successfully.",
            "deleted_sessions": deleted_count
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to clear interview history."
        )

@app.get("/api/interview/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    answers = []
    for a in sorted(session.answers, key=lambda x: x.created_at):
        answers.append({
            "answer_id": a.id,
            "question": a.question,
            "transcript": a.transcript,
            "total_score": a.total_score,
            "evaluation": json.loads(a.evaluation_json)
        })
    return {"session_id": session.id, "category": session.category, "language": session.language, "answers": answers}

@app.get("/api/healthz")
def healthz():
    return {"ok": True}
