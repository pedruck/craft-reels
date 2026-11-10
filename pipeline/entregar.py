#!/usr/bin/env python3
"""Etapa 10: entrega em <pasta>/saida/.

    entregar.py <pasta>

    saida/<nome>.mp4        1080x1920, a versão para postar
    saida/<nome>-leve.mp4   720 px, para mandar pelo WhatsApp
    saida/relatorio.md      o que foi feito
"""
import shutil
import subprocess
import sys
from pathlib import Path

P = Path(sys.argv[1])
S = P / "saida"
S.mkdir(exist_ok=True)
nome = P.name
shutil.copy2(P / "final.mp4", S / f"{nome}.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(S / f"{nome}.mp4"), "-vf", "scale=720:-2", "-c:v", "libx264", "-crf", "26",
                "-preset", "slow", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(S / f"{nome}-leve.mp4")], check=True)
shutil.copy2(P / "relatorio.md", S / "relatorio.md")
mb = lambda p: p.stat().st_size / 1e6  # noqa: E731
print(f"{S / (nome + '.mp4')} ({mb(S / (nome + '.mp4')):.0f} MB) e {nome}-leve.mp4 ({mb(S / (nome + '-leve.mp4')):.1f} MB)")
