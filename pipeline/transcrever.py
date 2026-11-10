#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.12.*"
# dependencies = ["faster-whisper", "numpy"]
# ///
"""Transcreve um vídeo com tempo por palavra, no formato que o kit (reel.py) lê.

    transcrever.py <video> <saida.json> [--nomes "Orca, Omarchy"] [--modelo large-v3]

--nomes entra no prompt inicial do Whisper: sem ele, nome de produto sai errado
("a Agência IA", "O Marchy"). Ponha os produtos e termos técnicos do vídeo.
"""
import argparse
import json
import subprocess

import numpy as np
from faster_whisper import WhisperModel

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("saida")
ap.add_argument("--nomes", default="")
ap.add_argument("--modelo", default="large-v3")
ap.add_argument("--lingua", default="pt")
ap.add_argument("--quieto", action="store_true", help="não imprime a transcrição, só o resumo")
ap.add_argument("--apresentador", help="aplica também as correções de apresentadores/<nome>.json")
a = ap.parse_args()

# o leitor de áudio do faster-whisper (PyAV) quebra com versões novas; o ffmpeg decodifica
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0

model = WhisperModel(a.modelo, device="cpu", compute_type="int8")
segs, _ = model.transcribe(audio, language=a.lingua, word_timestamps=True, beam_size=5,
                           condition_on_previous_text=False,  # com regravação o texto se repete e o modelo entra em laço
                           initial_prompt=(a.nomes + ".") if a.nomes else None)
out = {"text": "", "segments": [], "words": [], "duration": len(audio) / 16000}
for s in segs:
    ws = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)} for w in (s.words or [])]
    out["segments"].append({"start": s.start, "end": s.end, "text": s.text.strip(), "words": ws})
    out["words"] += ws
    if not a.quieto:
        print(f"{s.start:7.2f} {s.text.strip()}", flush=True)
out["text"] = " ".join(s["text"] for s in out["segments"])
with open(a.saida, "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"\n{len(out['words'])} palavras -> {a.saida}")

# nomes de produto e erros conhecidos (catalogo/logos/logos.json, catalogo/correcoes.json, apresentador)
import sys  # noqa: E402
from pathlib import Path  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nomes import corrigir, tabela  # noqa: E402
out["words"], trocas = corrigir(out["words"], tabela(apresentador=a.apresentador))
for s in out["segments"]:
    s["words"] = [w for w in out["words"] if s["start"] - 0.01 <= w["start"] < s["end"] + 0.01]
    s["text"] = " ".join(w["word"] for w in s["words"])
out["text"] = " ".join(w["word"] for w in out["words"])
with open(a.saida, "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("correções:\n" + ("\n".join(trocas) or "nenhuma"))
