#!/usr/bin/env python3
"""Etapa 4: limpa a voz e deixa o volume no padrão do Instagram (-14 LUFS).

    audio.py <cortado.mp4> <limpo.mp4>

Cadeia fixa: passa-alta 80 Hz (ronco e vento), redução de ruído leve, compressor
suave, e loudnorm em duas passadas (mede, depois aplica com os valores medidos) para
-14 LUFS integrado e pico de -1,5 dBTP. O vídeo é copiado sem recodificar.
Imprime "antes → depois" em LUFS.
"""
import json
import re
import subprocess
import sys

ALVO, PICO, LRA = -14.0, -1.5, 11.0
CADEIA = "highpass=f=80,afftdn=nf=-25:nt=w,acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2"


def medir_loudnorm(video, filtro):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-vn", "-af",
                        f"{filtro},loudnorm=I={ALVO}:TP={PICO}:LRA={LRA}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    return json.loads(re.findall(r"\{[^{}]*\}", r.stderr, re.S)[-1])


def integrado(video):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else float("nan")


def main(entrada, saida):
    antes = integrado(entrada)
    m = medir_loudnorm(entrada, CADEIA)
    ln = (f"loudnorm=I={ALVO}:TP={PICO}:LRA={LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", entrada, "-map", "0:v", "-map", "0:a", "-c:v", "copy",
                    "-af", f"{CADEIA},{ln},aresample=48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", saida],
                   check=True)
    depois = integrado(saida)
    print(json.dumps({"antes_lufs": round(antes, 1), "depois_lufs": round(depois, 1), "alvo_lufs": ALVO}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
