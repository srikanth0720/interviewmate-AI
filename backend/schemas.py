from pydantic import BaseModel, Field

class StartSessionRequest(BaseModel):
    category: str = Field(default="Python", max_length=40)
    language: str = Field(default="en-IN", max_length=30)

class EvaluateRequest(BaseModel):
    session_id: int
    question: str = Field(min_length=3, max_length=2000)
    transcript: str = Field(min_length=1, max_length=10000)
