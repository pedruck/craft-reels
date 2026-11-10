#!/usr/bin/env python3
"""Folha de aprovação de cortes (só com --parar-em cortes): uma linha por corte que tira fala,
com o quadro antes e depois da emenda e o texto que sai. Pausas não entram.

    "$KIT_PY" aprovacao.py <pasta>          grava <pasta>/aprovacao.jpg
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "kit" / "fonts" / "inter-600-normal.woff2"
P = Path(sys.argv[1])
plano = json.loads((P / "cortes.json").read_text())
cortes = [c for c in plano["cortes"] if c.get("aplicar") and c["tipo"] not in ("pausa", "inicio", "fim")][:30]
QW, QH, TXT = 135, 240, 760
f_txt = ImageFont.truetype(str(FONTE), 22)
f_tit = ImageFont.truetype(str(FONTE), 26)
folha = Image.new("RGB", (2 * QW + TXT + 40, 60 + max(1, len(cortes)) * (QH + 16)), "#1e1e2e")
d = ImageDraw.Draw(folha)
d.text((20, 16), f"{len(cortes)} cortes que tiram fala (pausas não aparecem) — quadro antes | depois da emenda", font=f_tit, fill="#cdd6f4")
with tempfile.TemporaryDirectory(dir=P) as tmp:
    for k, c in enumerate(cortes):
        y = 60 + k * (QH + 16)
        for j, t in enumerate((max(0, c["inicio"] - 0.15), c["fim"] + 0.15)):
            q = Path(tmp) / f"{k}_{j}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(P / "bruto.mp4"), "-frames:v", "1",
                            "-vf", f"scale={QW}:{QH}:force_original_aspect_ratio=increase,crop={QW}:{QH}", str(q)], check=True)
            folha.paste(Image.open(q), (20 + j * QW, y))
        x = 20 + 2 * QW + 16
        d.text((x, y + 4), f"{k + 1}. {c['inicio']:.2f}–{c['fim']:.2f}s  {c['tipo']}", font=f_tit, fill="#cba6f7")
        texto = f"sai: \"{c.get('sai', '')}\"" if c.get("sai") else c.get("nota", "")
        linhas, atual = [], ""
        for p in (texto + "  · " + c.get("nota", "")).split():
            if f_txt.getlength(atual + " " + p) > TXT - 20:
                linhas.append(atual)
                atual = p
            else:
                atual = (atual + " " + p).strip()
        linhas.append(atual)
        for i, ln in enumerate(linhas[:7]):
            d.text((x, y + 44 + i * 28), ln, font=f_txt, fill="#cdd6f4")
folha.save(P / "aprovacao.jpg", quality=82)
print(f"{len(cortes)} cortes -> {P / 'aprovacao.jpg'}")
