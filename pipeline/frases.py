#!/usr/bin/env python3
"""Transcrição em frases, uma por linha com o segundo em que começa — o formato barato para
escrever as cenas (sem o tempo de cada palavra).

    frases.py <transcricao.json>
"""
import json
import sys

d = json.load(open(sys.argv[1]))
ws = d.get("words") or [w for s in d["segments"] for w in s["words"]]
linha, ini = [], None
for w in ws:
    if ini is None:
        ini = float(w["start"])
    linha.append(w["word"].strip())
    if w["word"].rstrip().endswith((".", "?", "!")) or len(linha) >= 22:
        print(f"{ini:6.1f} {' '.join(linha)}")
        linha, ini = [], None
if linha:
    print(f"{ini:6.1f} {' '.join(linha)}")
