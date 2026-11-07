@echo off
.venv\Scripts\activate
uvicorn backend.main:app --reload
