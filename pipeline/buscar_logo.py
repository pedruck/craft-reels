#!/usr/bin/env python3
"""Baixa a logo de uma marca do Simple Icons (SVG, CC0) e põe no catálogo (catalogo/logos).

    craft logo <chave> <slug> "<Nome>" [--falado "docker,dóquer"] [--erro "doca=Docker" ...]

slug = nome do ícone em simpleicons.org (docker, archlinux, obsidian, obsstudio,
libreoffice, apple, claude...). O SVG sai pintado na cor oficial da marca.
Quando o produto tem logo própria fora do Simple Icons (Orca, Omarchy), baixe do
repositório oficial (confira a licença) e edite catalogo/logos/logos.json à mão.
"""
import argparse
import json
import re
import urllib.request
from pathlib import Path

VER = "16.34.0"
LOGOS = Path(__file__).resolve().parent.parent / "catalogo" / "logos"
ap = argparse.ArgumentParser()
ap.add_argument("chave")
ap.add_argument("slug")
ap.add_argument("nome")
ap.add_argument("--falado", default="")
ap.add_argument("--erro", action="append", default=[])
ap.add_argument("--fundo", default="#ffffff")
a = ap.parse_args()


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


svg = get(f"https://cdn.jsdelivr.net/npm/simple-icons@{VER}/icons/{a.slug}.svg").decode()
dados = json.loads(get(f"https://cdn.jsdelivr.net/npm/simple-icons@{VER}/data/simple-icons.json"))
dados = dados if isinstance(dados, list) else dados.get("icons", [])
slug_de = lambda t: re.sub(r"[^a-z0-9]", "", t.lower().replace("+", "plus").replace(".", "dot").replace("&", "and"))  # noqa: E731
cor = next((i["hex"] for i in dados if i.get("slug") == a.slug or slug_de(i["title"]) == a.slug), "111111")
if cor.lower() in ("ffffff", "fff"):
    a.fundo = "#111111"
svg = svg.replace("<svg ", f'<svg fill="#{cor}" ', 1)
(LOGOS / f"{a.chave}.svg").write_text(svg)

cat_p = LOGOS / "logos.json"
cat = json.loads(cat_p.read_text())
falado = [f.strip().lower() for f in a.falado.split(",") if f.strip()] or [a.nome.lower()]
erros = dict(e.split("=", 1) for e in a.erro)
cat[a.chave] = {"nome": a.nome, "icone": f"{a.chave}.svg", "fundo": a.fundo, "falado": falado,
                "erros": {k.lower(): v for k, v in erros.items()},
                "fonte": f"simpleicons.org/{a.slug} (simple-icons@{VER}, CC0; a marca é de quem é dona)"}
cat_p.write_text(json.dumps(cat, ensure_ascii=False, indent=1))
print(f"{a.nome}: logos/{a.chave}.svg, cor #{cor}")
