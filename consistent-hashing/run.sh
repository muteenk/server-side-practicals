#!/usr/bin/env bash
cd "$(dirname "$0")"

uvicorn server:app --host 0.0.0.0 --port 9001 &
uvicorn server:app --host 0.0.0.0 --port 9002 &
uvicorn server:app --host 0.0.0.0 --port 9003 &
wait
