#!/usr/bin/env python3
"""Word-timed transcript for reel.py, made locally (no API key).

craft-reels replaced the Groq call of the original kit with pipeline/transcrever.py
(faster-whisper large-v3 on the CPU). reel.py only calls this when a spec has no
"transcript", which the craft pipeline never leaves out.
"""
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def transcribe(video, out):
    subprocess.run([str(RAIZ / 'pipeline' / 'transcrever.py'), str(video), str(out), '--quieto'], check=True)
