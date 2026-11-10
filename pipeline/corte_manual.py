#!/usr/bin/env python3
"""Acrescenta em cortes.json um corte achado assistindo o vídeo CORTADO (regra C).

    craft corte <pasta> <inicio> <fim> "<nota>"         tempos do cortado.mp4 (ou deste script direto)

Converte para o tempo do bruto e, se a ponta cair a menos de 0,3 s de uma emenda,
estende até a emenda — senão sobra uma lasca do trecho vizinho (foi assim que um
"podem" solto de 0,5 s ficou num vídeo de teste). Depois: craft run <pasta> de novo.
"""
import json
import sys
from pathlib import Path

P, t0, t1, nota = Path(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
ficam = json.loads((P / "cortado.trechos.json").read_text())["ficam"]


def bruto(t, lado):
    base = 0.0
    for i0, i1 in ficam:
        d = i1 - i0
        if t <= base + d + 1e-6:
            r = i0 + (t - base)
            if lado == "ini" and r - i0 < 0.3:
                return i0 - 0.01          # encosta no corte anterior
            if lado == "fim" and i1 - r < 0.3:
                return i1 + 0.01          # encosta no corte seguinte
            return r
        base += d
    return ficam[-1][1] + 0.01


plano = json.loads((P / "cortes.json").read_text())
c = {"inicio": round(bruto(t0, "ini"), 3), "fim": round(bruto(t1, "fim"), 3), "tipo": "manual", "aplicar": True, "nota": nota}
plano["cortes"].append(c)
(P / "cortes.json").write_text(json.dumps(plano, ensure_ascii=False, indent=1))
print(f"bruto {c['inicio']:.2f}-{c['fim']:.2f}: {nota}")
