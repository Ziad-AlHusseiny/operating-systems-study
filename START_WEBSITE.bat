@echo off
cd /d "%~dp0"
title Operating Systems Study
echo Starting Operating Systems Study at http://127.0.0.1:8000/#/dashboard
start "" http://127.0.0.1:8000
python -m http.server 8000 --directory study-website
