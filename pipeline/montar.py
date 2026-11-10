#!/usr/bin/env python3
"""Etapa 7: junta enquadramento.json + cenas.json num spec.json e chama o template.

    kit/.venv/bin/python montar.py <pasta> --template explainer [--so-validar] [--fim 21 --cenas outro.json]

--so-validar: só confere o cenas.json (âncoras, larguras, logos, imagens); sai 1 se houver erro.
--fim: renderiza só os primeiros N segundos em teste-<template>.mp4 (teste de enquadramento ou de template).
O vídeo usado é o limpo.mp4 (cortado + áudio tratado) e a legenda é a legenda.json.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("pasta")
ap.add_argument("--template", default="explainer")
ap.add_argument("--so-validar", action="store_true")
ap.add_argument("--fim", type=float)
ap.add_argument("--cenas", default="cenas.json", help="outro arquivo de cenas (testes)")
a = ap.parse_args()

P = Path(a.pasta).resolve()
build = RAIZ / "templates" / a.template / "build.py"
if not build.exists():
    sys.exit(f"template \"{a.template}\" não existe")
enq = json.loads((P / "enquadramento.json").read_text())
cen = json.loads((P / a.cenas).read_text())
spec = dict(cen)
spec.update({"video": "limpo.mp4", "transcript": "legenda.json", "out": "reel.mp4", "template": a.template,
             "paleta": enq.get("paleta"), "fundo": enq.get("fundo"), "enquadramento": enq, "workers": cen.get("workers", 3)})
nome_spec = "spec.json"
if a.fim:                      # teste de um trecho: não mexe no spec.json nem no reel.mp4 da pipeline
    spec["end"] = a.fim
    spec["out"] = f"teste-{a.template}.mp4"
    nome_spec = f"teste-{a.template}.spec.json"
(P / nome_spec).write_text(json.dumps(spec, ensure_ascii=False, indent=1))

sys.path.insert(0, str(RAIZ / "templates"))
mod_spec = importlib.util.spec_from_file_location(f"tpl_{a.template}", build)
mod = importlib.util.module_from_spec(mod_spec)
mod_spec.loader.exec_module(mod)

erros, avisos = mod.validar(P / nome_spec)
for av in avisos:
    print(av)
if erros:
    print("\n".join(erros))
    sys.exit(1)
if a.so_validar:
    print("cenas ok")
    sys.exit(0)
mod.main(str(P / nome_spec))
out = P / spec["out"]
print(f"{out.name}: template {a.template}, paleta {enq.get('paleta')}, fundo {enq.get('fundo')}")
