#!/usr/bin/env bash
source .venv/bin/activate
uvicorn backend.main:app --reload
