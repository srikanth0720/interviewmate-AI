import json
import re
import httpx
from fastapi import HTTPException
from backend.config import settings

RUBRIC = {
    "technical_correctness": 30,
    "relevance": 20,
    "completeness": 20,
    "clarity": 15,
    "communication": 15
}

def _fallback_evaluation(question: str, answer: str):
    # Transparent local fallback for development if an Evon-compatible endpoint is not configured.
    words = re.findall(r"\b[\w'-]+\b", answer)
    length = len(words)
    q_terms = {w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", question)}
    a_terms = {w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", answer)}
    overlap = len(q_terms & a_terms) / max(1, len(q_terms))
    relevance = round(8 + 12 * min(1, overlap * 2), 1)
    completeness = round(min(20, length / 7), 1)
    clarity = 10 if length >= 25 else 7 if length >= 10 else 4
    communication = 10 if length >= 15 else 6
    technical = round(min(30, 10 + 20 * min(1, overlap * 1.5)), 1)
    scores = {
        "technical_correctness": technical,
        "relevance": relevance,
        "completeness": completeness,
        "clarity": clarity,
        "communication": communication
    }
    total = round(sum(scores.values()), 1)
    return {
        "scores": scores,
        "total_score": total,
        "strengths": ["Your answer was captured successfully."],
        "weaknesses": ["This is a basic development-mode evaluation, not a full LLM judgement."],
        "missing_concepts": ["Add a concrete example and explain the key concept step by step."],
        "improved_answer": "Build your answer with: definition, how it works, a practical example, and when you would use it.",
        "practical_suggestions": ["Use specific technical terms.", "Give one real example.", "Keep the answer structured."],
        "next_interview_question": "Can you explain that concept with a practical example?",
        "evaluation_mode": "fallback_demo"
    }

async def evaluate_answer(question: str, answer: str):
    if not settings.evon_api_url:
        return _fallback_evaluation(question, answer)

    system_prompt = """You are a fair technical and HR interview coach. Evaluate only what the candidate said. Do not infer personality, confidence, accent quality, or facts not present in the transcript. Return ONLY valid JSON with keys: scores (technical_correctness out of 30, relevance out of 20, completeness out of 20, clarity out of 15, communication out of 15), total_score, strengths (array), weaknesses (array), missing_concepts (array), improved_answer (string), practical_suggestions (array), next_interview_question (string). Be constructive and specific."""
    user_prompt = f"Question:\n{question}\n\nCandidate transcript:\n{answer}"
    headers = {"Content-Type": "application/json"}
    if settings.evon_api_key:
        headers["Authorization"] = f"Bearer {settings.evon_api_key}"
    body = {
        "model": settings.evon_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(settings.evon_api_url, headers=headers, json=body)
    if response.is_error:
        raise HTTPException(status_code=502, detail=f"LLM evaluation endpoint failed ({response.status_code}): {response.text[:400]}")
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        result["evaluation_mode"] = "configured_llm"
        return result
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=502, detail="LLM endpoint response was not in the expected OpenAI-compatible JSON format.")
