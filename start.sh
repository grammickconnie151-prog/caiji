#!/bin/bash
set -e
python -m playwright install chromium
exec streamlit run app.py --server.address=0.0.0.0 --server.port="${PORT:-8501}"
