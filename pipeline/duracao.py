#!/usr/bin/env python3
"""Etapa 8: garante o limite de duração do reel (60 s).

    duracao.py <reel.mp4> <final.mp4> [--limite 60] [--max 1.25] [--sem-limite]

Até o limite: copia. Passou: acelera o vídeo inteiro (imagem e voz juntas, então
legenda e visuais continuam na palavra certa) só o necessário, até --max. O tom da
voz não muda (atempo; nunca asetrate). Se nem no máximo couber, entrega acelerado no
máximo e avisa: quem decide o que tirar é a pessoa (nada é cortado sozinho).
Imprime um JSON numa linha.
"""
import argparse
import json
import math
import shutil
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument("entrada")
ap.add_argument("saida")
ap.add_argument("--limite", type=float, default=60.0)
ap.add_argument("--max", type=float, default=1.25)
ap.add_argument("--sem-limite", action="store_true")
a = ap.parse_args()


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))


d0 = dur(a.entrada)
r = {"antes": round(d0, 2), "fator": 1.0}
if d0 <= a.limite or a.sem_limite:
    shutil.copy2(a.entrada, a.saida)
    r["depois"] = round(d0, 2)
    r["resumo"] = f"{d0:.1f}s, dentro do limite" if d0 <= a.limite else f"{d0:.1f}s, acima de {a.limite:.0f}s mas sem limite (pedido)"
else:
    fator = min(a.max, math.ceil(d0 / (a.limite - 0.3) * 100) / 100)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.entrada, "-filter_complex",
                    f"[0:v]setpts=PTS/{fator},fps=30[v];[0:a]atempo={fator}[a]", "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.saida], check=True)
    d1 = dur(a.saida)
    r.update(fator=fator, depois=round(d1, 2), resumo=f"{d0:.1f}s → {d1:.1f}s (acelerado {fator:.2f}x, tom da voz igual)")
    if d1 > a.limite + 0.05:
        r["aviso"] = (f"mesmo em {fator:.2f}x ficou com {d1:.1f}s (faltam {d1 - a.limite:.1f}s) → mostre a lista de cenas "
                      f"(relatorio.md) à pessoa e pergunte qual sai; ou ela pede \"pode passar de 60 s\" (--sem-limite)")
print(json.dumps(r, ensure_ascii=False))
