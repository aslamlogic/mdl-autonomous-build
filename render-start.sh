#!/usr/bin/env bash
python -m uvicorn meta_ui.main:app --host 0.0.0.0 --port $PORT
